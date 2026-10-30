"""
Critic Agent:
    Ön yazıdaki iddiaları CV ve kullanıcı notlarıyla karşılaştırır.
    Köşeli parantezli yer tutucular LLM'e bırakılmadan kodla yakalanır.
"""

import re

import config
import prompts
from schemas import Critique
from state import CoachState
from tools.llm_tools import LLMError, structured_call
from tools.memory_tools import Memory


PLACEHOLDER_PATTERN = re.compile(r"\[[^\]\n]{2,60}\]")


def critic_node(state: CoachState) -> dict:
    memory = Memory(config.MEMORY_PATH)
    notes = "\n".join(f"{skill}: {note}" for skill, note in memory.confirmed_skills.items())

    user_message = (
        f"CV METNİ:\n{state['cv_text']}\n\n"
        f"ADAY NOTLARI:\n{notes or '-'}\n\n"
        f"ÖN YAZI:\n{state['cover_letter']}"
    )

    update = {}

    try:
        critique = structured_call(
            config.llm,
            Critique,
            prompts.CRITIC.format(lang=config.OUTPUT_LANG),
            user_message,
        )
    except LLMError as error:
        critique = Critique(is_grounded=True, feedback="Denetim yapılamadı")
        update["warnings"] = [f"Critic çalışmadı: {error}"]

    placeholders = PLACEHOLDER_PATTERN.findall(state["cover_letter"])

    if placeholders:
        critique = critique.model_copy(
            update={
                "is_grounded": False,
                "unsupported_claims": critique.unsupported_claims
                + [f"Yer tutucu: {placeholder}" for placeholder in placeholders],
                "feedback": critique.feedback
                + " Köşeli parantezli yer tutucuları kaldır; gerçek bilgiyi yaz.",
            }
        )

    return {"critique": critique, **update}
