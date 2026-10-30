"""
Gap Agent:
    Eksik veya belirsiz kalan beceriler için önem derecesi, başvuruda nasıl ele alınacağı
    ve kısa bir öğrenme önerisi üretir.
"""

import config
import prompts
from schemas import GapPlan
from state import CoachState
from tools.llm_tools import LLMError, structured_call


def gap_node(state: CoachState) -> dict:
    match = state["match"]

    targets = (
        match.by_status("missing")
        + match.by_status("uncertain")
        + match.by_status("missing", required=False)[:3]
    )

    if not targets:
        return {"gaps": GapPlan()}

    listing = "\n".join(f"- {item.skill} ({item.status})" for item in targets)
    user_message = (
        f"İlan: {state['job'].title}\n"
        f"Aday: {state['cv'].title}\n"
        f"Eksik/belirsiz:\n{listing}"
    )

    try:
        gaps = structured_call(
            config.llm,
            GapPlan,
            prompts.GAP_ANALYSIS.format(lang=config.OUTPUT_LANG),
            user_message,
        )
    except LLMError as error:
        return {"gaps": GapPlan(), "warnings": [f"Eksik analizi üretilemedi: {error}"]}

    return {"gaps": gaps}
