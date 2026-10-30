"""
Bu uygulama LangGraph kullanarak CV-İlan Eşleştirme ve Başvuru Koçu agent sistemi oluşturur.

CV Parser Agent ve Job Parser Agent:
    CV ve ilanı yapılandırılmış profillere dönüştürür.

Matching Agent:
    Becerileri eşleştirir, CV vector database'inden (RAG) kanıt getirir, skoru hesaplar.

Clarification Agent:
    Belirsiz becerileri kullanıcıya sorar, cevabı kalıcı hafızaya yazar.

Gap Agent, Writer Agent, Critic Agent, Interview Agent:
    Eksik analizi, ön yazı (denetim ve revizyon döngüsüyle) ve mülakat hazırlığı üretir.

Report Agent:
    Sonuçları Markdown raporuna yazar.

Önce 01_create_vector_db.py ile CV indekslenmelidir.

Kullanım:
    python 02_cv_job_coach.py --cv data/sample_cv.pdf --job data/sample_job_softtech.txt
"""

import argparse

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import config
from graph import build_graph
from schemas import MatchResult
from tools import cv_tools
from tools.document_tools import DocumentError, load_document
from tools.llm_tools import LLMError


console = Console()

STEP_LABELS = {
    "cv_parser": "CV ayrıştırıldı",
    "job_parser": "İlan ayrıştırıldı",
    "matching": "Beceri eşleştirmesi yapıldı",
    "clarification": "Belirsiz beceriler netleştirildi",
    "gap": "Eksik analizi tamamlandı",
    "writer": "Ön yazı yazıldı",
    "critic": "Ön yazı denetlendi",
    "revise": "Ön yazı revize edildi",
    "interview": "Mülakat hazırlığı üretildi",
    "report": "Rapor kaydedildi",
}

STATUS_LABELS = {
    "matched": "eşleşti",
    "uncertain": "belirsiz",
    "missing": "eksik",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CV-İlan Eşleştirme ve Başvuru Koçu")
    parser.add_argument("--cv", required=True, help="CV dosyası (.pdf/.txt/.md)")
    parser.add_argument("--job", required=True, help="İlan dosyası (.txt/.md/.pdf) veya URL")
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Belirsiz beceriler için soru sorma",
    )

    return parser.parse_args()


def print_match(match: MatchResult) -> None:
    table = Table(title=f"Uyum Skoru: {match.score}/100")
    table.add_column("Beceri")
    table.add_column("Tür")
    table.add_column("Durum")

    for item in match.required:
        table.add_row(item.skill, "zorunlu", STATUS_LABELS[item.status])

    for item in match.nice_to_have:
        table.add_row(item.skill, "artı", STATUS_LABELS[item.status])

    console.print(table)


def main() -> int:
    args = parse_args()

    try:
        cv_text = load_document(args.cv)
        job_text = load_document(args.job)
    except DocumentError as error:
        console.print(f"[red]Hata:[/red] {error}")
        return 2

    if not cv_tools.index_matches_cv(cv_text):
        console.print(
            "[red]Hata:[/red] Bu CV için vector database bulunamadı veya güncel değil.\n"
            f"Önce şunu çalıştırın: python 01_create_vector_db.py --cv {args.cv}"
        )
        return 2

    graph = build_graph()
    console.print(f"Model: {config.LLM_MODEL} | Embedding: {config.EMBEDDING_MODEL}")

    state = {
        "cv_text": cv_text,
        "job_text": job_text,
        "interactive": not args.no_interactive,
        "warnings": [],
    }

    try:
        with console.status("Agent çalışıyor...") as status:
            for update in graph.stream(state, stream_mode="updates"):
                for node, delta in update.items():
                    delta = delta or {}
                    state.update({key: value for key, value in delta.items() if key != "warnings"})
                    state["warnings"] += delta.get("warnings", [])

                    # Kullanıcıdan girdi alınabilmesi için canlı göstergeyi geçici durdur
                    status.stop()
                    console.print(f"[OK] {STEP_LABELS.get(node, node)}")
                    status.start()
    except LLMError as error:
        console.print(f"[red]Model hatası:[/red] {error}")
        console.print("Ollama çalışıyor mu? (ollama serve) Model yüklü mü? (ollama list)")
        return 1
    except Exception as error:
        console.print(f"[red]Beklenmeyen hata:[/red] {error}")
        return 1

    print_match(state["match"])
    console.print(Panel(state.get("cover_letter", ""), title="Ön Yazı", border_style="green"))

    for warning in state["warnings"]:
        console.print(f"[yellow]Uyarı: {warning}[/yellow]")

    console.print(f"\nRapor: {state.get('report_path')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
