"""
Bu dosyada nihai Markdown raporu oluşturulur ve diske yazılır.
"""

import re
from datetime import datetime
from pathlib import Path

from schemas import JobProfile, MatchResult, SkillEvidence
from state import CoachState

ICONS = {"matched": "✅", "uncertain": "❓", "missing": "❌"}
TR_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _skill_table(items: list[SkillEvidence]) -> str:
    if not items:
        return "_Belirtilmemiş._\n"
    rows = ["| Beceri | Durum | Kaynak |", "|---|---|---|"]
    for s in items:
        rows.append(f"| {s.skill} | {ICONS[s.status]} {s.status} | {s.source} |")
    return "\n".join(rows) + "\n"


def build_report(state: CoachState) -> str:
    cv, job, match = state["cv"], state["job"], state["match"]
    out = [
        f"# Başvuru Raporu: {job.title} @ {job.company}",
        f"_Aday: {cv.name} · Oluşturulma: {datetime.now():%Y-%m-%d %H:%M}_\n",
        f"## Uyum Skoru: **{match.score}/100**",
        f"Deneyim faktörü: {match.experience_factor:.2f}\n",
        "### Zorunlu beceriler",
        _skill_table(match.required),
        "### Tercih edilen beceriler",
        _skill_table(match.nice_to_have),
    ]
    gaps = state.get("gaps")
    if gaps and gaps.items:
        out.append("## Eksik Analizi")
        for g in gaps.items:
            out.append(
                f"- **{g.skill}** (önem: {g.severity})\n"
                f"  - Nasıl ele alınmalı: {g.how_to_frame}\n"
                f"  - Öğrenme önerisi: {g.learning_suggestion}"
            )
        out.append("")
    out += ["## Ön Yazı", state.get("cover_letter", ""), ""]
    critique = state.get("critique")
    if critique:
        verdict = "doğrulandı" if critique.is_grounded else "tam doğrulanamadı"
        out.append(f"_Denetim: ön yazı CV ile {verdict} ({state.get('revisions', 0)} revizyon)._")
        for claim in critique.unsupported_claims if not critique.is_grounded else []:
            out.append(f"- Desteksiz iddia: {claim}")
        out.append("")
    interview = state.get("interview")
    if interview and interview.questions:
        out.append("## Mülakat Hazırlığı")
        for i, q in enumerate(interview.questions, 1):
            out.append(
                f"{i}. **{q.question}**\n   - Neden sorulur: {q.why_asked}\n   - İpucu: {q.answer_tip}"
            )
        out.append("")
    if state.get("warnings"):
        out.append("## Uyarılar")
        out += [f"- {w}" for w in state["warnings"]]
    return "\n".join(out)


def write_report(output_dir: Path, job: JobProfile, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    name = f"{job.company}-{job.title}".translate(TR_ASCII).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-") or "rapor"
    path = output_dir / f"{slug}-{datetime.now():%Y%m%d-%H%M%S}.md"
    path.write_text(content, encoding="utf-8")
    return path


def evidence_block(match: MatchResult) -> str:
    """Eşleşen becerilerin CV kanıtlarını ön yazı ve mülakat prompt'ları için listeler."""
    lines = [
        f"* {item.skill}: {item.evidence[:300]}"
        for item in match.by_status("matched") + match.by_status("matched", required=False)
        if item.evidence
    ]

    return "\n".join(lines) or "(kanıt bulunamadı)"
