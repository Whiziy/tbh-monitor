"""Reads tbh-meter's live.json output and maps it to RunStats.

tbh-meter writes ~/tbh-meter/live.json ~1x/sec with real game data.
This reader polls that file and translates the raw fields into our
RunStats format, avoiding the need to port the full IL2CPP resolver.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

from core.models import RunStats

DIFFICULTY_NAMES = {0: "Normal", 1: "Nightmare", 2: "Hell", 3: "Torment"}
STALE_THRESHOLD_SEC = 5.0
DEFAULT_PATH = Path.home() / "tbh-meter" / "live.json"


class LiveJsonReader:
    def __init__(self, path: Optional[str] = None):
        self._path = Path(path) if path else DEFAULT_PATH
        self._last_mtime: float = 0.0
        self._last_run: int = -1
        self._cached: Optional[dict] = None
        self._run_start_ts: float = time.time()

    def close(self) -> None:
        self._cached = None

    def _is_stale(self) -> bool:
        try:
            mtime = os.path.getmtime(self._path)
        except OSError:
            return True
        return (time.time() - mtime) > STALE_THRESHOLD_SEC

    def _load(self) -> Optional[dict]:
        try:
            mtime = os.path.getmtime(self._path)
            if mtime == self._last_mtime and self._cached is not None:
                return self._cached
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._last_mtime = mtime
            self._cached = data
            return data
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def read(self, stats: RunStats) -> RunStats:
        raw = self._load()
        if raw is None or self._is_stale():
            stats.connected = False
            return stats

        stats.connected = True

        run = raw.get("run", 0)
        if run != self._last_run:
            self._last_run = run
            self._run_start_ts = time.time()
            stats.reset_run()

        elapsed = raw.get("elapsed", 0)
        stats.elapsed_sec = float(elapsed)

        damage = raw.get("damage_now", 0.0)
        stats.total_damage = float(damage)
        stats.dps = stats.total_damage / max(stats.elapsed_sec, 1.0)

        gold = raw.get("gold_now")
        stats.gold = int(gold) if gold is not None else 0

        xp = raw.get("xp_now")
        stats.exp = int(xp) if xp is not None else 0

        stats.mobs_killed = int(raw.get("mobs", 0))
        total_mobs = raw.get("total_mobs")
        stats.mobs_total = int(total_mobs) if total_mobs is not None else 0

        difficulty = raw.get("difficulty")
        stats.mode = DIFFICULTY_NAMES.get(difficulty, "-") if difficulty is not None else "-"

        act = raw.get("act")
        stage_no = raw.get("stageNo")
        stage_key = raw.get("stageKey")
        if act is not None and stage_no is not None:
            stats.stage = f"Act {act} - Stage {stage_no}"
        elif stage_key is not None:
            stats.stage = f"Stage {stage_key}"
        else:
            stats.stage = "-"

        drops = raw.get("drops", [0, 0, 0])
        if len(drops) >= 3:
            if not hasattr(self, "_prev_drops"):
                self._prev_drops = [0, 0, 0]
            chest_names = ["other", "gold", "blue"]
            for i in range(3):
                if drops[i] > self._prev_drops[i]:
                    stats.chest_detected = chest_names[i]
            self._prev_drops = list(drops)

        return stats
