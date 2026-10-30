from pathlib import Path

import pytest

import config
from schemas import JobProfile, JobSkills
from tools.llm_tools import LLMError
from tools.memory_tools import Memory

from .conftest import make_llm


def test_end_to_end_writes_report(run_graph):
    state = run_graph(ask=lambda skill, evidence: None)
    report = Path(state["report_path"])

    assert report.is_file()

    text = report.read_text(encoding="utf-8")

    assert "Uyum Skoru" in text and "Mülakat Hazırlığı" in text
    assert Memory(config.MEMORY_PATH).history[-1]["company"] == "Softtech"


def test_human_in_the_loop_updates_score_and_memory(run_graph):
    asked = []

    def ask(skill, evidence):
        asked.append(skill)
        return "RabbitMQ ile benzer akışlar kurdum"

    state = run_graph(ask=ask)
    kafka = next(item for item in state["match"].required if item.skill == "Apache Kafka")

    assert asked == ["Apache Kafka"]
    assert kafka.status == "matched" and kafka.source == "user"
    assert Memory(config.MEMORY_PATH).get_note("Apache Kafka")


def test_non_interactive_leaves_uncertain(run_graph):
    state = run_graph(ask=None)
    kafka = next(item for item in state["match"].required if item.skill == "Apache Kafka")

    assert kafka.status == "uncertain"


def test_critic_loop_stops_at_max_revisions(run_graph):
    llm = make_llm(grounded=(False,))
    state = run_graph(llm=llm)

    assert state["revisions"] == config.MAX_REVISIONS
    assert llm.calls.count("Critique") == config.MAX_REVISIONS + 1


def test_critic_accepts_first_time(run_graph):
    state = run_graph(llm=make_llm(grounded=(True,)))

    assert state["revisions"] == 0


def test_placeholder_in_letter_forces_revision(run_graph):
    llm = make_llm(
        grounded=(True,),
        text=["Beklentim [Maaş Beklentisi] TL.", "Sayın Softtech yetkilisi, ben Deniz Kaya."],
    )
    state = run_graph(llm=llm)

    assert state["revisions"] == 1
    assert "[" not in state["cover_letter"]


def test_known_placeholders_are_filled_without_revision(run_graph):
    llm = make_llm(grounded=(True,), text=["Sayın [Şirket Adı], [Pozisyon Adı] için başvuruyorum."])
    state = run_graph(llm=llm)

    assert state["revisions"] == 0
    assert "Softtech" in state["cover_letter"] and "[" not in state["cover_letter"]


def test_years_computed_from_dates_not_llm(run_graph):
    state = run_graph()

    assert state["cv"].years_experience == 4
    assert state["match"].experience_factor == 1.0


def test_empty_job_skills_falls_back_then_fails(run_graph):
    llm = make_llm()
    llm.structured[JobProfile] = [JobProfile(title="X", company="Y")]
    llm.structured[JobSkills] = [JobSkills()]

    with pytest.raises(LLMError, match="zorunlu beceri"):
        run_graph(llm=llm)


def test_empty_job_skills_recovered_by_second_prompt(run_graph):
    llm = make_llm()
    llm.structured[JobProfile] = [JobProfile(title="X", company="Y")]

    state = run_graph(llm=llm)

    assert [item.skill for item in state["match"].required] == ["Java"]
    assert any("ikinci denemede" in warning for warning in state["warnings"])
