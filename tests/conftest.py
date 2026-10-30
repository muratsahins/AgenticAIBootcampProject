"""
Testler Ollama gerektirmez: sahte embedding ve sahte LLM kullanılır.
"""

import hashlib

import numpy as np
import pytest
from langchain_core.embeddings import Embeddings

import config
from agents import clarification_agent
from graph import build_graph
from schemas import (
    CVProfile,
    Critique,
    Experience,
    GapPlan,
    InterviewPrep,
    InterviewQuestion,
    JobProfile,
    JobSkills,
)
from tools import cv_tools


class FakeEmbeddings(Embeddings):
    """Kelime torbası tabanlı deterministik embedding (ortak kelime = benzerlik)."""

    DIM = 64

    def _vector(self, text: str) -> list[float]:
        vector = np.zeros(self.DIM)

        for word in text.lower().split():
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.DIM] += 1

        return vector.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeLLM:
    """with_structured_output ve invoke arayüzünü taklit eder; kuyruktaki yanıtları sırayla verir."""

    def __init__(self, structured: dict[type, list], text: list[str]):
        self.structured = {schema: list(items) for schema, items in structured.items()}
        self.text = list(text)
        self.calls: list[str] = []

    def with_structured_output(self, schema, method=None):
        outer = self

        class Bound:
            def invoke(self, _messages):
                outer.calls.append(schema.__name__)
                queue = outer.structured[schema]
                return queue.pop(0) if len(queue) > 1 else queue[0]

        return Bound()

    def invoke(self, _messages):
        self.calls.append("text")
        content = self.text.pop(0) if len(self.text) > 1 else self.text[0]

        class Message:
            pass

        message = Message()
        message.content = content

        return message


CV = CVProfile(
    name="Deniz Kaya",
    title="Java Backend Geliştirici",
    years_experience=0,
    skills=["Java", "Spring Boot", "PostgreSQL", "RabbitMQ", "Docker", "Jenkins", "JUnit"],
    experiences=[
        Experience(role="Backend Geliştirici", company="Anadolu Yazılım", start_year=2022),
        Experience(role="Stajyer", company="Marmara Dijital", start_year=2021, end_year=2021),
    ],
)

JOB = JobProfile(
    title="Java Backend Geliştirici",
    company="Softtech",
    required_skills=[
        "Java",
        "Spring Boot",
        "PostgreSQL veya Oracle",
        "Apache Kafka",
        "Kubernetes",
        "CI/CD",
    ],
    nice_to_have_skills=["Redis"],
    min_years_experience=3,
)

CV_TEXT = (
    "Deniz Kaya Java Backend Geliştirici\n"
    "- Spring Boot ile REST servisleri geliştirdim ve PostgreSQL sorgularını optimize ettim.\n"
    "- Asenkron iletişim için RabbitMQ kullandım, tekrar deneme mekanizması kurdum.\n"
    "- Docker ile paketledim, Jenkins ile derleme sürecini otomatikleştirdim.\n"
)

JOB_TEXT = "Softtech Java Backend Geliştirici ilanı. " * 5


def make_llm(grounded=(True,), **overrides) -> FakeLLM:
    structured = {
        CVProfile: [CV],
        JobProfile: [JOB],
        JobSkills: [JobSkills(required_skills=["Java"])],
        GapPlan: [GapPlan()],
        Critique: [
            Critique(is_grounded=g, unsupported_claims=["x"], feedback="f") for g in grounded
        ],
        InterviewPrep: [
            InterviewPrep(
                questions=[InterviewQuestion(question="q", why_asked="w", answer_tip="t")]
            )
        ],
    }
    text = overrides.pop("text", ["Sayın yetkili, ben Deniz Kaya."])
    structured.update(overrides)

    return FakeLLM(structured=structured, text=text)


@pytest.fixture
def cv_index():
    return cv_tools.create_cv_index(CV_TEXT.splitlines(), FakeEmbeddings())


@pytest.fixture
def run_graph(tmp_path, monkeypatch, cv_index):
    """Grafiği sahte LLM ve geçici hafıza/çıktı klasörleriyle çalıştırır."""
    monkeypatch.setattr(config, "MEMORY_PATH", tmp_path / "memory.json")
    monkeypatch.setattr(config, "OUTPUT_PATH", tmp_path / "out")
    monkeypatch.setattr(cv_tools, "load_cv_index", lambda folder=None: cv_index)

    def run(llm=None, ask=None):
        monkeypatch.setattr(config, "llm", llm or make_llm())

        if ask is not None:
            monkeypatch.setattr(clarification_agent, "ask_user", ask)

        state = {
            "cv_text": CV_TEXT,
            "job_text": JOB_TEXT,
            "interactive": ask is not None,
            "warnings": [],
        }

        return build_graph().invoke(state)

    return run
