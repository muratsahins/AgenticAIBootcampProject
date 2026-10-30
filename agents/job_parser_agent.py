"""
Job Parser Agent:
    İlan metnini yapılandırılmış profile (zorunlu beceriler, artılar, deneyim yılı) dönüştürür.
    Küçük modeller listeyi boş bırakabildiği için ikinci bir odaklı prompt denenir;
    yine de beceri çıkmazsa sahte skor üretmek yerine hata verilir.
"""

import re

import config
import prompts
from schemas import JobProfile, JobSkills
from state import CoachState
from tools.llm_tools import LLMError, structured_call


def merge_alternatives(skills: list[str], job_text: str) -> list[str]:
    """İlanda 'X veya Y' olarak geçen ve modelin ayrı çıkardığı becerileri tek öğede birleştirir."""
    merged = list(skills)

    for first in skills:
        for second in skills:
            if first == second or first not in merged or second not in merged:
                continue

            pattern = rf"{re.escape(first)}\s+(?:veya|or)\s+{re.escape(second)}"

            if re.search(pattern, job_text, re.IGNORECASE):
                merged[merged.index(first)] = f"{first} veya {second}"
                merged.remove(second)

    return merged


def fill_header_fields(job: JobProfile, job_text: str) -> None:
    """Model başlık/şirketi boş bıraktıysa ilanın ilk satırından ('Şirket · Pozisyon') çıkarır."""
    first_line = next((line.strip() for line in job_text.splitlines() if line.strip()), "")
    company, separator, title = first_line.partition("·")

    if separator:
        job.company = job.company or company.strip()
        job.title = job.title or title.strip()
    else:
        job.title = job.title or first_line


def job_parser_node(state: CoachState) -> dict:
    job = structured_call(config.llm, JobProfile, prompts.PARSE_JOB, state["job_text"])
    fill_header_fields(job, state["job_text"])
    warnings = []

    if not job.required_skills:
        skills = structured_call(config.llm, JobSkills, prompts.EXTRACT_SKILLS, state["job_text"])
        job.required_skills = skills.required_skills
        job.nice_to_have_skills = job.nice_to_have_skills or skills.nice_to_have_skills
        warnings.append("İlan becerileri ikinci denemede (odaklı prompt) çıkarıldı.")

    if not job.required_skills:
        raise LLMError("İlandan zorunlu beceri çıkarılamadı; ilan metnini kontrol edin.")

    job.required_skills = merge_alternatives(job.required_skills, state["job_text"])

    return {"job": job, "warnings": warnings}
