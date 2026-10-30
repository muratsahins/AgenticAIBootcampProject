"""
Report Agent:
    Tüm analizleri tek bir Markdown raporunda toplar, output/ klasörüne yazar
    ve başvuruyu kalıcı hafızaya kaydeder.
"""

import config
from state import CoachState
from tools.memory_tools import Memory
from tools.report_tools import build_report, write_report


def report_node(state: CoachState) -> dict:
    report_path = write_report(config.OUTPUT_PATH, state["job"], build_report(state))

    memory = Memory(config.MEMORY_PATH)
    memory.add_application(state["job"].company, state["job"].title, state["match"].score)

    return {"report_path": str(report_path)}
