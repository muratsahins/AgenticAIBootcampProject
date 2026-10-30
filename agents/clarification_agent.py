"""
Clarification Agent:
    CV'de kesin kanıtı olmayan (belirsiz) becerileri kullanıcıya sorar.
    Verilen cevap kalıcı hafızaya yazılır, skor yeniden hesaplanır.
"""

from rich.console import Console
from rich.panel import Panel

import config
from state import CoachState
from tools.memory_tools import Memory
from tools.scoring_tools import rescore


console = Console()


def ask_user(skill: str, evidence: str) -> str | None:
    detail = f", en yakın bölüm:\n[dim]{evidence[:250]}[/dim]" if evidence else "."

    console.print(
        Panel(
            f"İlan [bold]{skill}[/bold] istiyor. CV'nde kesin bir ifade yok{detail}",
            title="Netleştirme",
            border_style="yellow",
        )
    )

    try:
        answer = console.input("Bu konuda deneyimin var mı? Kısaca anlat (yoksa boş bırak): ")
    except EOFError:
        return None

    return answer.strip() or None


def clarification_node(state: CoachState) -> dict:
    match = state["match"]

    if not state.get("interactive", True):
        return {}

    memory = Memory(config.MEMORY_PATH)
    uncertain = match.by_status("uncertain") + match.by_status("uncertain", required=False)

    for item in uncertain:
        note = ask_user(item.skill, item.evidence)

        if note:
            memory.confirm_skill(item.skill, note)
            item.status, item.evidence, item.source = "matched", note, "user"
        else:
            item.status = "missing"

    return {"match": rescore(match)}
