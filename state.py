"""
Bu dosyada LangGraph state yapısı tanımlanır.
Düğümler (agent'lar) arasında taşınan tüm veri burada toplanır.
"""

import operator
from typing import Annotated, TypedDict

from schemas import CVProfile, Critique, GapPlan, InterviewPrep, JobProfile, MatchResult


class CoachState(TypedDict, total=False):
    cv_text: str
    job_text: str
    interactive: bool
    cv: CVProfile
    job: JobProfile
    match: MatchResult
    gaps: GapPlan
    cover_letter: str
    critique: Critique
    revisions: int
    interview: InterviewPrep
    report_path: str
    warnings: Annotated[list[str], operator.add]
