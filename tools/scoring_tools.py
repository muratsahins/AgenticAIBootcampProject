"""
Bu dosyada CV ile ilan arasındaki deterministik eşleştirme ve skorlama yapılır.
Skor LLM'e bırakılmaz; aynı girdi her seferinde aynı sonucu vermelidir.
"""

import re
from datetime import datetime

from schemas import CVProfile, JobProfile, MatchResult, SkillEvidence
from tools.cv_tools import CVIndex

ALIASES = {
    "js": "javascript",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "dotnet": ".net",
    "restful": "rest",
    "rest api": "rest",
    "restful api": "rest",
    "springboot": "spring boot",
    "ci cd": "ci/cd",
    "cicd": "ci/cd",
    "mssql": "sql server",
    "birim test": "unit testing",
    "birim testi": "unit testing",
    "birim testleri": "unit testing",
    "birim test yazma": "unit testing",
    "mikroservis mimarisi": "microservices architecture",
    "mikroservis": "microservices architecture",
}

# Bir beceriyi doğrudan kanıtlayan araçlar (varsa beceri "eşleşti" sayılır)
IMPLIED_BY = {
    "unit testing": {"junit", "mockito", "testng", "pytest", "xunit", "nunit"},
    "ci/cd": {"jenkins", "gitlab ci", "github actions", "azure devops", "teamcity"},
    "microservices architecture": {"microservices", "mikroservis"},
}
# İlişkili ama aynı olmayan teknolojiler (varsa beceri "belirsiz" sayılır, kullanıcıya sorulur)
RELATED = {
    "apache kafka": {"rabbitmq", "activemq", "kafka streams", "pulsar"},
    "kafka": {"rabbitmq", "activemq", "pulsar"},
    "kubernetes": {"openshift", "docker swarm", "helm"},
    "redis": {"memcached", "hazelcast", "ehcache"},
    "oracle": {"pl/sql", "sql server", "db2"},
}

REQUIRED_WEIGHT, NICE_WEIGHT, EXPERIENCE_WEIGHT = 0.65, 0.15, 0.20
_ALTERNATIVE_RE = re.compile(r"\s+(?:veya|or)\s+|\s*/\s*(?=[A-Za-z]{3,}\b)", re.IGNORECASE)
UNCERTAIN_CREDIT = 0.5  # belirsiz beceri, kapsama puanına yarım sayılır


def canon(skill: str) -> str:
    s = re.sub(r"\s+", " ", skill.strip().lower())
    return ALIASES.get(s, s)


def _surface_forms(skill: str) -> set[str]:
    c = canon(skill)
    return {c} | {alias for alias, target in ALIASES.items() if target == c}


def _in_text(skill: str, text_lower: str) -> bool:
    return any(
        re.search(rf"(?<![\w]){re.escape(form)}(?![\w])", text_lower)
        for form in _surface_forms(skill)
    )


def _best_evidence(store: CVIndex | None, query: str) -> tuple[str, float]:
    hit = store.search(query, k=1) if store else []
    return hit[0] if hit else ("", 0.0)


def _present(term: str, cv_skills: set[str], text_lower: str) -> bool:
    return canon(term) in cv_skills or _in_text(term, text_lower)


def classify_skill(
    skill: str,
    cv_skills: set[str],
    cv_text: str,
    store: CVIndex | None,
    user_note: str | None,
    uncertain_similarity: float,
) -> SkillEvidence:
    if user_note:
        return SkillEvidence(
            skill=skill, status="matched", evidence=user_note, similarity=1.0, source="user"
        )
    text_lower = cv_text.lower()
    # "PostgreSQL veya Oracle" gibi alternatiflerde biri yeterlidir
    alternatives = [a.strip() for a in _ALTERNATIVE_RE.split(skill) if a.strip()] or [skill]
    for alt in alternatives:
        if _present(alt, cv_skills, text_lower):
            text, sim = _best_evidence(store, f"{alt} deneyimi")
            return SkillEvidence(
                skill=skill, status="matched", evidence=text, similarity=sim, source="cv"
            )
        implied = next(
            (t for t in IMPLIED_BY.get(canon(alt), ()) if _present(t, cv_skills, text_lower)), None
        )
        if implied:
            text, sim = _best_evidence(store, f"{implied} deneyimi")
            return SkillEvidence(
                skill=skill, status="matched", evidence=text, similarity=sim, source="cv"
            )
    for alt in alternatives:
        related = next(
            (t for t in RELATED.get(canon(alt), ()) if _present(t, cv_skills, text_lower)), None
        )
        if related:
            text, sim = _best_evidence(store, f"{related} deneyimi")
            return SkillEvidence(skill=skill, status="uncertain", evidence=text, similarity=sim)
    best_text, best_sim = _best_evidence(store, f"{skill} deneyimi")
    if best_sim >= uncertain_similarity:
        return SkillEvidence(
            skill=skill, status="uncertain", evidence=best_text, similarity=best_sim
        )
    return SkillEvidence(skill=skill, status="missing", similarity=best_sim)


def _coverage(items: list[SkillEvidence]) -> float:
    if not items:
        return 1.0
    points = sum(
        1.0 if s.status == "matched" else UNCERTAIN_CREDIT if s.status == "uncertain" else 0.0
        for s in items
    )
    return points / len(items)


def estimate_years(cv: CVProfile, current_year: int | None = None) -> float:
    """Deneyim yılını LLM'in aritmetiğine bırakmadan başlangıç/bitiş yıllarından hesaplar.

    Staj dönemleri sayılmaz. Hiçbir görevde yıl bilgisi yoksa LLM'in verdiği değer kullanılır.
    """
    year_now = current_year or datetime.now().year
    total, found = 0, False
    for exp in cv.experiences:
        if exp.start_year <= 0 or re.search(r"staj|intern", exp.role, re.IGNORECASE):
            continue
        found = True
        total += max(0, (exp.end_year or year_now) - exp.start_year)
    return float(total) if found else cv.years_experience


def experience_factor(cv: CVProfile, job: JobProfile) -> float:
    if job.min_years_experience <= 0:
        return 1.0
    return min(1.0, estimate_years(cv) / job.min_years_experience)


def compute_score(
    required: list[SkillEvidence], nice: list[SkillEvidence], exp_factor: float
) -> int:
    raw = (
        REQUIRED_WEIGHT * _coverage(required)
        + NICE_WEIGHT * _coverage(nice)
        + EXPERIENCE_WEIGHT * exp_factor
    )
    return round(100 * raw)


def build_match(
    cv: CVProfile,
    job: JobProfile,
    cv_text: str,
    store: CVIndex | None,
    notes: dict[str, str],
    uncertain_similarity: float,
) -> MatchResult:
    cv_skills = {canon(s) for s in cv.skills}

    def classify(skill: str) -> SkillEvidence:
        return classify_skill(
            skill, cv_skills, cv_text, store, notes.get(canon(skill)), uncertain_similarity
        )

    required = [classify(s) for s in job.required_skills]
    nice = [classify(s) for s in job.nice_to_have_skills]
    exp = experience_factor(cv, job)
    return MatchResult(
        score=compute_score(required, nice, exp),
        experience_factor=exp,
        required=required,
        nice_to_have=nice,
    )


def rescore(match: MatchResult) -> MatchResult:
    """Kullanıcı yanıtları statüleri değiştirdikten sonra skoru yeniden hesaplar."""
    return match.model_copy(
        update={"score": compute_score(match.required, match.nice_to_have, match.experience_factor)}
    )
