"""
Matching Agent:
    CV ve ilan becerilerini eşleştirir. CV vector database'inden (RAG) kanıt getirir,
    kullanıcı hafızasındaki onaylı becerileri hesaba katar ve skoru deterministik hesaplar.
"""

import config
from state import CoachState
from tools import cv_tools
from tools.memory_tools import Memory
from tools.scoring_tools import build_match


def matching_node(state: CoachState) -> dict:
    index = cv_tools.load_cv_index()
    warnings = []

    if index is None:
        warnings.append("CV vector database bulunamadı; anlamsal eşleşme kapalı.")

    memory = Memory(config.MEMORY_PATH)

    match = build_match(
        state["cv"],
        state["job"],
        state["cv_text"],
        index,
        memory.confirmed_skills,
        config.UNCERTAIN_SIMILARITY,
    )

    return {"match": match, "warnings": warnings}
