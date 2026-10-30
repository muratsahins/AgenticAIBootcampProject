"""
Interview Agent:
    İlan ve adayın zayıf noktalarına göre mülakat soruları ile cevap ipuçları hazırlar.
"""

import config
import prompts
from schemas import InterviewPrep
from state import CoachState
from tools.llm_tools import LLMError, structured_call
from tools.report_tools import evidence_block


def interview_node(state: CoachState) -> dict:
    cv, job, match = state["cv"], state["job"], state["match"]
    weak_skills = ", ".join(
        item.skill for item in match.by_status("missing") + match.by_status("uncertain")
    )

    user_message = (
        f"İlan: {job.title}\n"
        f"Zorunlu beceriler: {', '.join(job.required_skills)}\n"
        f"Adayın zayıf noktaları: {weak_skills or 'yok'}\n"
        f"Aday özeti: {cv.title}, {cv.years_experience:g} yıl\n"
        f"CV kanıtları:\n{evidence_block(match)}"
    )

    try:
        interview = structured_call(
            config.llm,
            InterviewPrep,
            prompts.INTERVIEW_PREP.format(lang=config.OUTPUT_LANG),
            user_message,
        )
    except LLMError as error:
        return {
            "interview": InterviewPrep(),
            "warnings": [f"Mülakat hazırlığı üretilemedi: {error}"],
        }

    return {"interview": interview}
