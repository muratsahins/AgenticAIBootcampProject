"""
CV Parser Agent:
    CV metnini yapılandırılmış profile (beceriler, deneyimler, eğitim) dönüştürür.
    Deneyim süresi LLM'e bırakılmaz; başlangıç/bitiş yıllarından hesaplanır.
"""

import config
import prompts
from schemas import CVProfile
from state import CoachState
from tools.llm_tools import structured_call
from tools.scoring_tools import estimate_years


def cv_parser_node(state: CoachState) -> dict:
    cv = structured_call(config.llm, CVProfile, prompts.PARSE_CV, state["cv_text"])
    cv.years_experience = estimate_years(cv)

    return {"cv": cv}
