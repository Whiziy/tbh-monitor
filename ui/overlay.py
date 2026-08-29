"""Overlay window with tab navigation: LIVE | HISTORY | SETTINGS."""

from __future__ import annotations

from typing import List, Callable, Optional

from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QGraphicsOpacityEffect,
)

from core.models import RunStats, BattleRecord
from ui import theme


def _value_label(text: str = "-", small: bool = False) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("role", "value-small" if small else "value")
    return lbl


def _tag_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("role", "label")
    return lbl


from PyQt6.QtGui import QIcon
from pathlib import Path
import sys, os

def get_asset_icon() -> QIcon:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent
    
    icon_path = base / "assets" / "icon.ico"
    if not icon_path.exists():
        icon_path = base / "assets" / "icon.png"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


class OverlayWindow(QWidget):
    def __init__(self, config: dict, on_settings_changed: Optional[Callable] = None):
        super().__init__()
        self._config = config
        self._drag_offset: QPoint | None = None
        self._on_settings_changed = on_settings_changed
        self._current_tab = "live"
        self._history_records: List[BattleRecord] = []
        self._notification_timer: Optional[QTimer] = None

        self.setWindowTitle("TaskBarHero Monitor")
        self.setWindowIcon(get_asset_icon())
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(config.get("window", {}).get("opacity", 0.9))

        self._build_ui()
        self.move(
            config.get("window", {}).get("start_x", 40),
            config.get("window", {}).get("start_y", 40),
        )
        self.set_waiting()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QWidget(objectName="card")
        self.card.setStyleSheet(theme.CARD_STYLE + theme.TAB_STYLE + theme.TOGGLE_STYLE + theme.HISTORY_CARD_STYLE + theme.SCROLLBAR_STYLE)
        outer.addWidget(self.card)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(theme.PADDING, theme.PADDING, theme.PADDING, theme.PADDING)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("TBH MONITOR")
        title.setProperty("role", "title")
        header.addWidget(title)
        header.addStretch(1)

        self.status_dot = QLabel("\u25cf")
        self.status_dot.setStyleSheet(f"color:{theme.TEXT_MUTED};")
        header.addWidget(self.status_dot)

        min_btn = QPushButton("\u2500")
        min_btn.setFixedSize(18, 18)
        min_btn.setToolTip("Minimize")
        min_btn.setStyleSheet(
            "QPushButton { color: #8A8F98; background: transparent; border: none; font-size: 11px; font-weight: bold; }"
            "QPushButton:hover { color: #F5F6F7; }"
        )
        min_btn.clicked.connect(self.showMinimized)
        header.addWidget(min_btn)

        close_btn = QPushButton("\u00d7")
        close_btn.setFixedSize(18, 18)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(
            "QPushButton { color: #8A8F98; background: transparent; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #F5F6F7; }"
        )
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        root.addLayout(header)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        self._tab_buttons = {}
        for tab_id, label in [("live", "LIVE"), ("history", "HISTORY"), ("settings", "SETTINGS")]:
            btn = QPushButton(label)
            btn.setProperty("role", "tab")
            btn.setProperty("active", "true" if tab_id == "live" else "false")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, t=tab_id: self._switch_tab(t))
            tab_row.addWidget(btn)
            self._tab_buttons[tab_id] = btn
        tab_row.addStretch(1)
        root.addLayout(tab_row)

        self._live_page = self._build_live_page()
        self._history_page = self._build_history_page()
        self._settings_page = self._build_settings_page()

        root.addWidget(self._live_page)
        root.addWidget(self._history_page)
        root.addWidget(self._settings_page)

        self._notification_label = QLabel()
        self._notification_label.setProperty("role", "notification")
        self._notification_label.setStyleSheet(theme.NOTIFICATION_STYLE)
        self._notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notification_label.hide()
        root.addWidget(self._notification_label)

        self._history_page.hide()
        self._settings_page.hide()

    def _build_live_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.dps_value = _value_label("0")
        self.dps_value.setProperty("role", "value")
        
        dps_box = QWidget()
        dps_box.setStyleSheet(f"background: {theme.BG_CARD}; border: 1px solid {theme.BORDER}; border-radius: 12px;")
        dps_col = QVBoxLayout(dps_box)
        dps_col.setContentsMargins(12, 8, 12, 8)
        dps_col.setSpacing(2)
        dps_col.addWidget(_tag_label("DPS"))
        dps_col.addWidget(self.dps_value)
        layout.addWidget(dps_box)

        self.waiting_label = QLabel("Menunggu game terdeteksi…")
        self.waiting_label.setProperty("role", "label")
        self.waiting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.waiting_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.gold_value = _value_label("0", small=True)
        self.exp_value = _value_label("0", small=True)
        self.mobs_value = _value_label("0/0", small=True)
        self.time_value = _value_label("00:00", small=True)
        self.stage_value = _value_label("-", small=True)
        self.mode_value = _value_label("-", small=True)

        pairs = [
            ("GOLD", self.gold_value),
            ("EXP", self.exp_value),
            ("MOBS", self.mobs_value),
            ("TIME", self.time_value),
            ("STAGE", self.stage_value),
            ("MODE", self.mode_value),
        ]
        for i, (label, value_widget) in enumerate(pairs):
            row, col = divmod(i, 2)
            cell = QVBoxLayout()
            cell.setContentsMargins(10, 6, 10, 6)
            cell.setSpacing(2)
            cell.addWidget(_tag_label(label))
            cell.addWidget(value_widget)
            
            wrapper = QWidget()
            wrapper.setStyleSheet(f"background: {theme.BG_CARD}; border: 1px solid {theme.BORDER}; border-radius: 8px;")
            wrapper.setLayout(cell)
            grid.addWidget(wrapper, row, col)

        self.grid_widget = QWidget()
        self.grid_widget.setLayout(grid)
        layout.addWidget(self.grid_widget)

        return page

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._history_scroll.setFixedHeight(200)

        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(6)
        self._history_layout.addStretch(1)

        self._history_scroll.setWidget(self._history_container)
        layout.addWidget(self._history_scroll)

        self._history_empty_label = QLabel("Belum ada battle tercatat")
        self._history_empty_label.setProperty("role", "label")
        self._history_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._history_empty_label)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("CLEAR")
        clear_btn.setProperty("role", "tab")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._on_clear_history_clicked)
        btn_row.addStretch(1)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("CHEST AUTO-DETECT")
        header.setProperty("role", "label")
        layout.addWidget(header)

        chest_settings = self._config.get("chest_detect", {})
        self._toggle_buttons = {}

        for chest_id, label, color in [
            ("blue", "Legendary Chest", theme.BLUE_CHEST),
            ("gold", "Rare Chest", theme.GOLD_CHEST),
            ("other", "Common Chest", theme.TEXT_PRIMARY),
        ]:
            enabled = chest_settings.get(chest_id, True)
            btn = QPushButton(f"{'ON' if enabled else 'OFF'}  {label}")
            btn.setProperty("role", "toggle")
            btn.setProperty("checked", "true" if enabled else "false")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, cid=chest_id: self._toggle_chest(cid))
            layout.addWidget(btn)
            self._toggle_buttons[chest_id] = btn

        layout.addStretch(1)

        credit_box = QVBoxLayout()
        credit_box.setSpacing(2)
        credit_title = QLabel("CREDITS")
        credit_title.setProperty("role", "label")
        credit_link = QLabel('<a href="https://github.com/whiziy" style="color: #6EE7B7; text-decoration: none;">github.com/whiziy</a>')
        credit_link.setOpenExternalLinks(True)
        credit_link.setStyleSheet(f"font: 9pt '{theme.FONT_FAMILY}';")

        credit_box.addWidget(credit_title)
        credit_box.addWidget(credit_link)
        layout.addLayout(credit_box)

        return page

    def _switch_tab(self, tab_id: str) -> None:
        self._current_tab = tab_id
        for tid, btn in self._tab_buttons.items():
            btn.setProperty("active", "true" if tid == tab_id else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._live_page.setVisible(tab_id == "live")
        self._history_page.setVisible(tab_id == "history")
        self._settings_page.setVisible(tab_id == "settings")

    def _toggle_chest(self, chest_id: str) -> None:
        chest_cfg = self._config.setdefault("chest_detect", {})
        current = chest_cfg.get(chest_id, True)
        chest_cfg[chest_id] = not current

        btn = self._toggle_buttons[chest_id]
        labels = {"blue": "Legendary Chest", "gold": "Rare Chest", "other": "Common Chest"}
        enabled = chest_cfg[chest_id]
        btn.setText(f"{'ON' if enabled else 'OFF'}  {labels[chest_id]}")
        btn.setProperty("checked", "true" if enabled else "false")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

        if self._on_settings_changed:
            self._on_settings_changed()

    def _on_clear_history_clicked(self) -> None:
        if hasattr(self, '_clear_history_cb') and self._clear_history_cb:
            self._clear_history_cb()

    def set_clear_history_callback(self, callback: Callable) -> None:
        self._clear_history_cb = callback

    def set_waiting(self) -> None:
        self.status_dot.setStyleSheet(f"color:{theme.TEXT_MUTED};")
        self.waiting_label.show()
        self.grid_widget.hide()
        self.dps_value.setText("--")

    def set_live(self) -> None:
        self.status_dot.setStyleSheet(f"color:{theme.ACCENT};")
        self.waiting_label.hide()
        self.grid_widget.show()

    def update_stats(self, stats: RunStats) -> None:
        if not stats.connected:
            self.set_waiting()
            return
        self.set_live()
        self.dps_value.setText(f"{stats.dps:,.0f}")
        self.gold_value.setText(f"{stats.gold:,}")
        self.exp_value.setText(f"{stats.exp:,}")
        self.mobs_value.setText(f"{stats.mobs_killed}/{stats.mobs_total}")
        self.time_value.setText(self._format_time(stats.elapsed_sec))
        self.stage_value.setText(stats.stage)
        self.mode_value.setText(stats.mode)

    def show_notification(self, text: str, color: str = theme.ACCENT) -> None:
        self._notification_label.setText(text)
        self._notification_label.setStyleSheet(
            f"background: rgba(15, 17, 21, 230);"
            f"border: 1px solid {color};"
            f"border-radius: 10px;"
            f"color: {color};"
            f"font: 11pt '{theme.FONT_FAMILY}';"
            f"font-weight: 600;"
            f"padding: 8px 14px;"
        )
        self._notification_label.show()

        if self._notification_timer:
            self._notification_timer.stop()
        self._notification_timer = QTimer(self)
        self._notification_timer.setSingleShot(True)
        self._notification_timer.timeout.connect(self._notification_label.hide)
        self._notification_timer.start(3000)

    def update_history(self, records: List[BattleRecord]) -> None:
        self._history_records = records

        while self._history_layout.count() > 1:
            item = self._history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not records:
            self._history_empty_label.show()
            self._history_scroll.hide()
            return

        self._history_empty_label.hide()
        self._history_scroll.show()

        for rec in reversed(records[-20:]):
            card = self._make_history_card(rec)
            self._history_layout.insertWidget(self._history_layout.count() - 1, card)

    def _make_history_card(self, rec: BattleRecord) -> QWidget:
        card = QWidget()
        card.setProperty("role", "history-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        top = QHBoxLayout()
        mode_lbl = QLabel(f"{rec.mode} \u2022 {rec.stage}")
        mode_lbl.setProperty("role", "label")
        top.addWidget(mode_lbl)
        top.addStretch(1)

        ts = rec.timestamp.split("T")[-1] if "T" in rec.timestamp else rec.timestamp
        time_lbl = QLabel(ts)
        time_lbl.setProperty("role", "label")
        top.addWidget(time_lbl)
        layout.addLayout(top)

        stats_text = f"DPS {rec.dps:,.0f}  |  Gold {rec.gold:,}  |  EXP {rec.exp:,}  |  {self._format_time(rec.duration_sec)}"
        stats_lbl = QLabel(stats_text)
        stats_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font: {theme.FONT_HISTORY};")
        layout.addWidget(stats_lbl)

        return card

    @staticmethod
    def _format_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
