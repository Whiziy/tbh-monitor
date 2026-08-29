"""tbh-monitor entry point."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from core.detector import GameDetector
from core.memory_reader import GameReader
from core.live_json_reader import LiveJsonReader
from core.native_reader import NativeReader
from core.models import RunStats, BattleRecord
from core.battle_history import BattleHistory
from ui.overlay import OverlayWindow


class _Signals(QObject):
    game_found = pyqtSignal(int, str)
    game_lost = pyqtSignal()


def load_config() -> dict:
    config_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "config.json"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    config_path = Path(__file__).parent / "config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


class App:
    def __init__(self, config: dict):
        self.config = config
        self.stats = RunStats()
        self.reader: GameReader | None = None
        self.live_reader: LiveJsonReader | None = None
        self.native_reader: NativeReader | None = None
        self.history = BattleHistory()
        self._had_stats = False
        self._live_json_mode = config.get("live_json_mode", False)
        self._native_mode = config.get("native_reader_mode", False)

        try:
            from core.discord_rpc import DiscordRPCManager
            self.discord_rpc = DiscordRPCManager()
            self.discord_rpc.connect()
        except Exception:
            self.discord_rpc = None

        self._signals = _Signals()
        self._signals.game_found.connect(self._on_game_found)
        self._signals.game_lost.connect(self._on_game_lost)

        self.window = OverlayWindow(config, on_settings_changed=self._save_settings)
        self.window.set_clear_history_callback(self._clear_history)
        self.window.update_history(self.history.records)
        self.window.show()

        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self._tick)
        self.tick_timer.setInterval(int(config.get("reader_tick_sec", 0.25) * 1000))

        if self._native_mode:
            print("[main] Native reader mode enabled")
            self.native_reader = NativeReader()
            self.tick_timer.start()
        elif self._live_json_mode:
            path = config.get("live_json_path")
            self.live_reader = LiveJsonReader(path=path)
            self.tick_timer.start()
        else:
            self.detector = GameDetector(
                candidates=config["process_candidates"],
                poll_interval_sec=config.get("poll_interval_sec", 2.0),
                on_found=lambda pid, name: self._signals.game_found.emit(pid, name),
                on_lost=lambda: self._signals.game_lost.emit(),
            )
            self.detector.start()

            if config.get("demo_mode", False):
                self._on_game_found(pid=0, name="demo")

    def _on_game_found(self, pid: int, name: str) -> None:
        try:
            self.reader = GameReader(pid, demo_mode=self.config.get("demo_mode", False))
        except OSError:
            self.reader = None
            return
        self.stats.reset_run()
        self._had_stats = False
        self.tick_timer.start()

    def _on_game_lost(self) -> None:
        self.tick_timer.stop()
        if self._had_stats and self.stats.elapsed_sec > 5:
            record = BattleRecord.from_stats(self.stats)
            self.history.add(record)
            self.window.update_history(self.history.records)
        if self.reader:
            self.reader.close()
            self.reader = None
        self.stats = RunStats()
        self.window.update_stats(self.stats)

    def _tick(self) -> None:
        print("[tick] checking...")
        if self._native_mode:
            prev_connected = self.stats.connected
            prev_stats = RunStats(
                mode=self.stats.mode, stage=self.stats.stage,
                dps=self.stats.dps, total_damage=self.stats.total_damage,
                gold=self.stats.gold, exp=self.stats.exp,
                mobs_killed=self.stats.mobs_killed, mobs_total=self.stats.mobs_total,
                elapsed_sec=self.stats.elapsed_sec, connected=self.stats.connected,
                run_start_ts=self.stats.run_start_ts,
            )
            self.stats = self.native_reader.read(self.stats)
            self.window.update_stats(self.stats)

            if self.stats.connected and self.stats.elapsed_sec > 1:
                self._had_stats = True

            # Record battle history ONLY on Stage Clear event from LogManager
            if self.stats.stage_clear_event is not None:
                evt = self.stats.stage_clear_event
                record = BattleRecord(
                    mode=self.stats.mode,
                    stage=f"Act {evt.act} - Stage {evt.stage}",
                    dps=self.stats.dps,
                    total_damage=self.stats.total_damage,
                    gold=self.stats.gold,
                    exp=self.stats.exp,
                    mobs_killed=self.stats.mobs_killed,
                    mobs_total=self.stats.mobs_total,
                    duration_sec=float(evt.duration_sec) if evt.duration_sec > 0 else self.stats.elapsed_sec,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    result="CLEAR"
                )
                self.history.add(record)
                self.window.update_history(self.history.records)
        elif self._live_json_mode:
            prev_connected = self.stats.connected
            prev_stats = RunStats(
                mode=self.stats.mode, stage=self.stats.stage,
                dps=self.stats.dps, total_damage=self.stats.total_damage,
                gold=self.stats.gold, exp=self.stats.exp,
                mobs_killed=self.stats.mobs_killed, mobs_total=self.stats.mobs_total,
                elapsed_sec=self.stats.elapsed_sec, connected=self.stats.connected,
                run_start_ts=self.stats.run_start_ts,
            )
            self.stats = self.live_reader.read(self.stats)
            self.window.update_stats(self.stats)

            if self.stats.connected and self.stats.elapsed_sec > 1:
                self._had_stats = True

            if prev_connected and not self.stats.connected and self._had_stats:
                if prev_stats.elapsed_sec > 5:
                    record = BattleRecord.from_stats(prev_stats)
                    self.history.add(record)
                    self.window.update_history(self.history.records)
                self._had_stats = False
                self.stats = RunStats()
        else:
            if self.reader is None:
                return
            self.stats = self.reader.read(self.stats)
            self.window.update_stats(self.stats)

            if self.stats.connected and self.stats.elapsed_sec > 1:
                self._had_stats = True

        if hasattr(self, "discord_rpc") and self.discord_rpc:
            self.discord_rpc.update_presence(
                stage=self.stats.stage,
                mode=self.stats.mode,
                gold=self.stats.gold,
                dps=self.stats.dps,
                in_game=self.stats.connected,
            )

        if self.stats.chest_detected:
            chest_type = self.stats.chest_detected
            chest_cfg = self.config.get("chest_detect", {})
            if chest_cfg.get(chest_type, True):
                from ui import theme
                from core.win_toast import send_windows_toast
                chest_names = {
                    "blue": "LEGENDARY CHEST",
                    "gold": "RARE CHEST",
                    "other": "COMMON CHEST",
                }
                display_name = chest_names.get(chest_type, chest_type.upper())
                colors = {
                    "blue": theme.BLUE_CHEST,
                    "gold": theme.GOLD_CHEST,
                    "other": theme.ACCENT,
                }
                # Show overlay notification
                self.window.show_notification(
                    f"\u2728 {display_name} DETECTED!",
                    colors.get(chest_type, theme.ACCENT),
                )
                # Send Windows OS Toast Notification (Notification Center)
                send_windows_toast(
                    "Task Bar Hero Monitor",
                    f"✨ {display_name} DETECTED!",
                    msec=4000
                )
            self.stats.chest_detected = None

    def _save_settings(self) -> None:
        save_config(self.config)

    def _clear_history(self) -> None:
        self.history.clear()
        self.window.update_history(self.history.records)


def main() -> None:
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tbh.monitor.overlay.1.1")
    except Exception:
        pass

    config = load_config()
    app = QApplication(sys.argv)
    from ui.overlay import get_asset_icon
    app.setWindowIcon(get_asset_icon())
    from PyQt6.QtGui import QIcon
    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    controller = App(config)  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
