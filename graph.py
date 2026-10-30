"""
Bu dosyada LangGraph akışı kurulur.

Akış:
    cv_parser -> job_parser -> matching
    matching -> (belirsiz beceri varsa) clarification -> gap -> writer -> critic
    critic -> (reddedildiyse ve limit dolmadıysa) revise -> critic
    critic -> interview -> report
"""

from langgraph.graph import END, START, StateGraph

import config
from agents.clarification_agent import clarification_node
from agents.critic_agent import critic_node
from agents.cv_parser_agent import cv_parser_node
from agents.gap_agent import gap_node
from agents.interview_agent import interview_node
from agents.job_parser_agent import job_parser_node
from agents.matching_agent import matching_node
from agents.report_agent import report_node
from agents.writer_agent import cover_letter_node, revise_node
from state import CoachState


def matching_router(state: CoachState) -> str:
    match = state["match"]
    has_uncertain = match.by_status("uncertain") or match.by_status("uncertain", required=False)

    return "clarification" if has_uncertain else "gap"


def critic_router(state: CoachState) -> str:
    if state["critique"].is_grounded or state.get("revisions", 0) >= config.MAX_REVISIONS:
        return "interview"

    return "revise"


def build_graph():
    builder = StateGraph(CoachState)

    builder.add_node("cv_parser", cv_parser_node)
    builder.add_node("job_parser", job_parser_node)
    builder.add_node("matching", matching_node)
    builder.add_node("clarification", clarification_node)
    builder.add_node("gap", gap_node)
    builder.add_node("writer", cover_letter_node)
    builder.add_node("critic", critic_node)
    builder.add_node("revise", revise_node)
    builder.add_node("interview", interview_node)
    builder.add_node("report", report_node)

    builder.add_edge(START, "cv_parser")
    builder.add_edge("cv_parser", "job_parser")
    builder.add_edge("job_parser", "matching")

    builder.add_conditional_edges(
        "matching",
        matching_router,
        {"clarification": "clarification", "gap": "gap"},
    )

    builder.add_edge("clarification", "gap")
    builder.add_edge("gap", "writer")
    builder.add_edge("writer", "critic")

    builder.add_conditional_edges(
        "critic",
        critic_router,
        {"revise": "revise", "interview": "interview"},
    )

    builder.add_edge("revise", "critic")
    builder.add_edge("interview", "report")
    builder.add_edge("report", END)

    return builder.compile()
