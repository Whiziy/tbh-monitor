"""Auto-detects the Task Bar Hero process by name.

Runs on its own thread. Emits callbacks when the game is found (with its
PID) and when it disappears, so the UI can flip between "waiting" and
"live" states without the user doing anything manually.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import psutil


class GameDetector:
    def __init__(
        self,
        candidates: list[str],
        poll_interval_sec: float,
        on_found: Callable[[int, str], None],
        on_lost: Callable[[], None],
    ) -> None:
        raw = {c.lower() for c in candidates}
        self._candidates = raw | {c.removesuffix(".exe") for c in raw}
        self._poll_interval = poll_interval_sec
        self._on_found = on_found
        self._on_lost = on_lost

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._current_pid: Optional[int] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self._current_pid is None:
                match = self._find_game_process()
                if match is not None:
                    pid, name = match
                    self._current_pid = pid
                    self._on_found(pid, name)
            else:
                if not self._pid_alive(self._current_pid):
                    self._current_pid = None
                    self._on_lost()

            self._stop_event.wait(self._poll_interval)

    def _find_game_process(self) -> Optional[tuple[int, str]]:
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").strip()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name.lower() in self._candidates:
                return proc.info["pid"], name
        return None

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
