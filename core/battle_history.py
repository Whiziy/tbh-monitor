"""Persistence layer for battle records — simple JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from core.models import BattleRecord

DEFAULT_PATH = Path(__file__).parent.parent / "battle_history.json"


class BattleHistory:
    def __init__(self, path: Path = DEFAULT_PATH):
        self._path = path
        self._records: List[BattleRecord] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._records = [BattleRecord.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError):
                self._records = []

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([r.to_dict() for r in self._records], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, record: BattleRecord) -> None:
        self._records.append(record)
        self._save()

    @property
    def records(self) -> List[BattleRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()
        self._save()
