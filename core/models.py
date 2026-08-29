"""Shared data structures passed from the reader thread to the UI thread."""

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class StageClearEvent:
    act: int
    stage: int
    duration_sec: int


@dataclass
class RunStats:
    connected: bool = False
    mode: str = "-"
    stage: str = "-"
    dps: float = 0.0
    total_damage: float = 0.0
    gold: int = 0
    exp: int = 0
    mobs_killed: int = 0
    mobs_total: int = 0
    run_start_ts: float = field(default_factory=time.time)
    elapsed_sec: float = 0.0
    chest_detected: Optional[str] = None
    stage_clear_event: Optional[StageClearEvent] = None

    def reset_run(self) -> None:
        self.dps = 0.0
        self.total_damage = 0.0
        self.gold = 0
        self.exp = 0
        self.mobs_killed = 0
        self.mobs_total = 0
        self.run_start_ts = time.time()
        self.elapsed_sec = 0.0
        self.chest_detected = None
        self.stage_clear_event = None


@dataclass
class BattleRecord:
    mode: str = "-"
    stage: str = "-"
    dps: float = 0.0
    total_damage: float = 0.0
    gold: int = 0
    exp: int = 0
    mobs_killed: int = 0
    mobs_total: int = 0
    duration_sec: float = 0.0
    timestamp: str = ""
    result: str = "completed"

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "stage": self.stage,
            "dps": round(self.dps, 1),
            "total_damage": round(self.total_damage, 1),
            "gold": self.gold,
            "exp": self.exp,
            "mobs_killed": self.mobs_killed,
            "mobs_total": self.mobs_total,
            "duration_sec": round(self.duration_sec, 1),
            "timestamp": self.timestamp,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BattleRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_stats(cls, stats: RunStats) -> "BattleRecord":
        from datetime import datetime
        return cls(
            mode=stats.mode,
            stage=stats.stage,
            dps=stats.dps,
            total_damage=stats.total_damage,
            gold=stats.gold,
            exp=stats.exp,
            mobs_killed=stats.mobs_killed,
            mobs_total=stats.mobs_total,
            duration_sec=stats.elapsed_sec,
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
