"""Windows OS Toast Notification module.

Uses PyQt6 QSystemTrayIcon to deliver native Windows Toast Notifications
directly to the Windows Notification Center / Taskbar.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QSystemTrayIcon, QApplication
from PyQt6.QtGui import QIcon
from typing import Optional

_tray_icon: Optional[QSystemTrayIcon] = None


def get_tray_icon() -> QSystemTrayIcon:
    global _tray_icon
    if _tray_icon is None:
        _tray_icon = QSystemTrayIcon()
        app = QApplication.instance()
        if app:
            _tray_icon.setIcon(app.windowIcon() if app.windowIcon() else QIcon())
        _tray_icon.setVisible(True)
    return _tray_icon


def send_windows_toast(title: str, message: str, msec: int = 4000) -> None:
    """Send a native Windows OS Toast Notification (Notification Center / Taskbar popup)."""
    try:
        tray = get_tray_icon()
        tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, msec)
    except Exception as e:
        print(f"[win_toast] Failed to send toast: {e}")
