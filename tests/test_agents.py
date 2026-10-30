from agents.job_parser_agent import fill_header_fields, merge_alternatives
from agents.writer_agent import clean_letter
from schemas import JobProfile

from .conftest import CV, JOB


def test_merge_alternatives_joins_pair_found_in_text():
    skills = ["Java", "PostgreSQL", "Oracle"]
    text = "PostgreSQL veya Oracle gibi ilişkisel veritabanlarında deneyim."

    assert merge_alternatives(skills, text) == ["Java", "PostgreSQL veya Oracle"]


def test_merge_alternatives_keeps_unrelated_skills_apart():
    skills = ["Java", "Docker", "Kubernetes"]
    text = "Java bilmek, Docker ve Kubernetes tecrübesi."

    assert merge_alternatives(skills, text) == skills


def test_fill_header_fields_from_first_line():
    job = JobProfile(required_skills=["Java"])

    fill_header_fields(job, "Softtech · Java Backend Geliştirici (Orta Seviye)\nKonum: İstanbul")

    assert job.company == "Softtech"
    assert job.title == "Java Backend Geliştirici (Orta Seviye)"


def test_fill_header_fields_keeps_model_values():
    job = JobProfile(company="Acme", title="Veri Mühendisi")

    fill_header_fields(job, "Softtech · Java Backend Geliştirici")

    assert (job.company, job.title) == ("Acme", "Veri Mühendisi")


def test_clean_letter_fills_known_placeholders():
    letter = clean_letter("**Sayın** yetkili, [Şirket Adı] için [Pozisyon Adı] başvurusu. [Ad Soyad]", CV, JOB)

    assert "[" not in letter and "**" not in letter
    assert "Softtech" in letter and "Deniz Kaya" in letter


def test_clean_letter_leaves_unknown_placeholders_for_critic():
    assert "[Maaş Beklentisi]" in clean_letter("Beklentim [Maaş Beklentisi].", CV, JOB)
