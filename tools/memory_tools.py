"""
Bu dosyada kalıcı hafıza yönetilir: kullanıcının doğruladığı beceriler ve
geçmiş başvurular JSON dosyasında saklanır.
"""

import json
from datetime import datetime
from pathlib import Path

from tools.scoring_tools import canon


class Memory:
    def __init__(self, path: Path):
        self.path = path
        self.confirmed_skills: dict[str, str] = {}
        self.history: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return  # bozuk hafıza dosyası uygulamayı durdurmamalı
        self.confirmed_skills = data.get("confirmed_skills", {})
        self.history = data.get("history", [])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"confirmed_skills": self.confirmed_skills, "history": self.history}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_note(self, skill: str) -> str | None:
        return self.confirmed_skills.get(canon(skill))

    def confirm_skill(self, skill: str, note: str) -> None:
        self.confirmed_skills[canon(skill)] = note
        self._save()

    def add_application(self, company: str, title: str, score: int) -> None:
        self.history.append(
            {
                "date": datetime.now().isoformat(timespec="seconds"),
                "company": company,
                "title": title,
                "score": score,
            }
        )
        self._save()
