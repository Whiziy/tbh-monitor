# Task Bar Hero Monitor (TBH Monitor)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-v6.6%2B-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

A lightweight, modern, glassmorphic HUD overlay & battle monitor for **Task Bar Hero** (Unity IL2CPP game). Built with Python & PyQt6, providing real-time combat stats, DPS tracking, stage detection, battle logs, and Windows native Toast notifications for chest drops.

Developed by [whiziy](https://github.com/whiziy).

---

## 📸 Preview

<p align="center">
  <img src="assets/preview.png" alt="TBH Monitor Preview" width="380" />
</p>

---

## ✨ Features

- ⚡ **Real-time Live Stats**: Instant DPS calculations, Gold, EXP, Mobs killed, Stage duration, Current Act & Stage, and Mode difficulty (Normal/Nightmare/Hell/Torment).
- 📦 **Chest Auto-Detect & Notifications**: Automatic detection for Legendary, Rare, and Common chest drops with native Windows OS Toast Notifications.
- 📜 **Battle History**: Automatically records stage completion logs (DPS, duration, EXP, Gold, result) saved locally to `battle_history.json`.
- 🎨 **Modern Glassmorphic UI**: Translucent, frameless, draggable overlay UI designed with Segoe UI typography and customizable toggles.
- ⚙️ **Native Memory Reader**: Pure Python memory reader attached directly via Windows APIs (`ReadProcessMemory`) — fast, low footprint, zero external server required.

---

## 🚀 Download & Installation

### Pre-built Executable (Windows)
1. Go to the [Releases](https://github.com/whiziy/tbh-monitor/releases) page.
2. Download `tbh-monitor.exe`.
3. Launch **Task Bar Hero**, then run `tbh-monitor.exe`.

---

## 🛠️ Building from Source

### Requirements
- Windows 10 / 11 (64-bit)
- Python 3.10+

### Setup Steps
```bash
# Clone repository
git clone https://github.com/whiziy/tbh-monitor.git
cd tbh-monitor

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Build single-file EXE
python -m PyInstaller build.spec
```

The compiled binary will be generated inside the `dist/` directory.

---

## ⚙️ Configuration (`config.json`)

```json
{
  "poll_interval_sec": 3.0,
  "tick_interval_ms": 1000,
  "demo_mode": false,
  "native_reader_mode": true,
  "chest_detect": {
    "blue": true,
    "gold": true,
    "other": true
  }
}
```

---

## 📜 License & Credits

- Developed by **[whiziy](https://github.com/whiziy)**.
- Memory reading architecture inspired by [tbh-meter](https://github.com/mad-labs-org/tbh-meter).
