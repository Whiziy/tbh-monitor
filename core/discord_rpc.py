"""Discord Rich Presence integration for Task Bar Hero Monitor."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Default public Application Client ID for Task Bar Hero Monitor
DISCORD_CLIENT_ID = "1278504938173497344"  # Default fallback ID or generic RPC ID


class DiscordRPCManager:
    def __init__(self, client_id: str = DISCORD_CLIENT_ID):
        self.client_id = client_id
        self._rpc = None
        self._connected = False
        self._lock = threading.Lock()
        self._start_ts: Optional[float] = None
        self._enabled = True

    def connect((self) -> bool:
        if not self._enabled or self._connected:
            return self._connected

        def _do_connect():
            try:
                from pypresence import Presence
                with self._lock:
                    self._rpc = Presence(self.client_id)
                    self._rpc.connect()
                    self._connected = True
                    self._start_ts = time.time()
                logger.info("Connected to Discord RPC")
            except Exception as e:
                logger.debug(f"Discord RPC connection failed: {e}")
                self._connected = False

        t = threading.Thread(target=_do_connect, daemon=True)
        t.start()
        return False

    def update_presence(
        self,
        stage: str = "-",
        mode: str = "-",
        gold: int = 0,
        dps: float = 0.0,
        in_game: bool = True,
    ) -> None:
        if not self._connected or not self._rpc:
            self.connect()
            return

        def _do_update():
            try:
                with self._lock:
                    if not self._connected or not self._rpc:
                        return

                    if not in_game:
                        self._rpc.update(
                            details="In Main Menu / Idle",
                            state="Task Bar Hero Monitor",
                            large_image="icon",
                            large_text="Task Bar Hero",
                            start=int(self._start_ts or time.time()),
                        )
                        return

                    # Format details & state
                    stage_str = stage if stage != "-" else "Stage 1-1"
                    mode_str = f" ({mode})" if mode != "-" and mode else ""
                    
                    details_text = f"Gold: {gold:,} 💰 | DPS: {dps:,.0f}"
                    state_text = f"{stage_str}{mode_str}"

                    self._rpc.update(
                        details=details_text,
                        state=state_text,
                        large_image="icon",
                        large_text="Task Bar Hero Monitor",
                        small_image="gold",
                        small_text=f"Total Gold: {gold:,}",
                        start=int(self._start_ts or time.time()),
                    )
            except Exception as e:
                logger.debug(f"Discord RPC update failed: {e}")
                self._connected = False

        t = threading.Thread(target=_do_update, daemon=True)
        t.start()

    def close(self) -> None:
        def _do_close():
            with self._lock:
                if self._rpc and self._connected:
                    try:
                        self._rpc.close()
                    except Exception:
                        pass
                self._connected = False
                self._rpc = None

        t = threading.Thread(target=_do_close, daemon=True)
        t.start()
