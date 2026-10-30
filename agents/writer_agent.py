"""
Writer Agent:
    CV kanıtlarına (RAG) dayanarak ilana özel ön yazı yazar.
    Critic reddederse geri bildirime göre ön yazıyı revize eder.
"""

import re
from datetime import date

import config
import prompts
from schemas import CVProfile, JobProfile
from state import CoachState
from tools.llm_tools import text_call
from tools.report_tools import evidence_block


def clean_letter(text: str, cv: CVProfile, job: JobProfile) -> str:
    """Markdown vurgularını temizler, bilinen yer tutucuları gerçek değerlerle doldurur.

    Küçük model prompt'a rağmen [Tarih] gibi yer tutucular yazabildiği için bunlar kodla çözülür.
    Tanımadığımız yer tutucular olduğu gibi kalır ve Critic tarafından yakalanır.
    """
    values = {
        "pozisyon adı": job.title,
        "pozisyon": job.title,
        "şirket adı": job.company,
        "şirket": job.company,
        "ad soyad": cv.name,
        "adınız": cv.name,
        "ad": cv.name,
        "tarih": date.today().strftime("%d.%m.%Y"),
    }

    def fill(match: re.Match) -> str:
        value = values.get(match.group(1).strip().lower())
        return value if value else match.group(0)

    text = re.sub(r"\[([^\]\n]{2,60})\]", fill, text.replace("**", ""))

    return text.strip()


def cover_letter_node(state: CoachState) -> dict:
    cv, job, match = state["cv"], state["job"], state["match"]
    missing = ", ".join(item.skill for item in match.by_status("missing")) or "yok"

    user_message = (
        f"Aday: {cv.name} ({cv.title}, {cv.years_experience:g} yıl)\n"
        f"İlan: {job.title} - {job.company}\n"
        f"İlandaki sorumluluklar: {'; '.join(job.responsibilities[:5])}\n"
        f"CV kanıtları (becerilere göre):\n{evidence_block(match)}\n"
        f"Adayda olmayan zorunlu beceriler (var gibi sunma): {missing}"
    )

    letter = text_call(
        config.llm,
        prompts.COVER_LETTER.format(lang=config.OUTPUT_LANG),
        user_message,
    )

    return {"cover_letter": clean_letter(letter, cv, job), "revisions": 0}


def revise_node(state: CoachState) -> dict:
    critique = state["critique"]

    user_message = (
        f"ÖN YAZI:\n{state['cover_letter']}\n\n"
        f"DESTEKSİZ İDDİALAR: {critique.unsupported_claims}\n"
        f"GERİ BİLDİRİM: {critique.feedback}"
    )

    letter = text_call(
        config.llm,
        prompts.REVISE_COVER_LETTER.format(lang=config.OUTPUT_LANG),
        user_message,
    )

    return {
        "cover_letter": clean_letter(letter, state["cv"], state["job"]),
        "revisions": state.get("revisions", 0) + 1,
    }
