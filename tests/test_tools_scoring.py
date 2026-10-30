import pytest

from tools.document_tools import DocumentError, chunk_text, load_document
from tools.scoring_tools import build_match, canon

from .conftest import CV, CV_TEXT, JOB


def test_load_document_missing_file():
    with pytest.raises(DocumentError, match="bulunamadı"):
        load_document("yok.pdf")


def test_load_document_too_short(tmp_path):
    file = tmp_path / "bos.txt"
    file.write_text("kısa", encoding="utf-8")

    with pytest.raises(DocumentError, match="yeterli metin"):
        load_document(str(file))


def test_chunk_text_merges_short_lines():
    chunks = chunk_text(
        "BAŞLIK\n- Bu satır yeterince uzun bir madde olarak yazıldı.\n- Bir tane daha uzun madde."
    )

    assert chunks[0].startswith("BAŞLIK\n- Bu satır")
    assert all(len(chunk) >= 20 for chunk in chunks)


def test_chunk_text_joins_wrapped_pdf_lines():
    chunks = chunk_text(
        "- Kritik raporların süresini 12 saniyeden 3 saniyeye\ndüşürdüm.\n"
        "- Siparişler arası iletişim için RabbitMQ kullandım."
    )

    assert chunks[0].endswith("3 saniyeye düşürdüm.")
    assert chunks[1].startswith("- Siparişler")


def test_canon_aliases():
    assert canon("K8s") == "kubernetes"
    assert canon("  Postgres ") == "postgresql"


def test_index_returns_cosine_similarity(cv_index):
    text, similarity = cv_index.search("RabbitMQ tekrar deneme", k=1)[0]

    assert "RabbitMQ" in text
    assert 0 < similarity <= 1.0001


def test_match_statuses(cv_index):
    match = build_match(CV, JOB, CV_TEXT, cv_index, {}, uncertain_similarity=0.99)
    status = {item.skill: item.status for item in match.required}

    assert status["Java"] == "matched"
    assert status["PostgreSQL veya Oracle"] == "matched"
    assert status["CI/CD"] == "matched"
    assert status["Apache Kafka"] == "uncertain"
    assert status["Kubernetes"] == "missing"
    assert 0 <= match.score <= 100


def test_turkish_skill_names_match_english_evidence(cv_index):
    job = JOB.model_copy(update={"required_skills": ["Birim Test"], "nice_to_have_skills": []})
    cv = CV.model_copy(update={"skills": ["JUnit"]})
    match = build_match(cv, job, "JUnit ve Mockito kullandım.", cv_index, {}, 0.99)

    assert match.required[0].status == "matched"


def test_user_note_turns_skill_into_matched(cv_index):
    notes = {"kubernetes": "Okulda lab çalıştım"}
    match = build_match(CV, JOB, CV_TEXT, cv_index, notes, 0.99)
    kubernetes = next(item for item in match.required if item.skill == "Kubernetes")

    assert (kubernetes.status, kubernetes.source) == ("matched", "user")
