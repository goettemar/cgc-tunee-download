# CGC Tunee Download Manager 🎵

Automatischer Song-Downloader für **tunee.ai** mit Hybrid-Automation (Playwright + PyAutoGUI).

[![GitHub](https://img.shields.io/badge/GitHub-cgc--tunee--download-blue?logo=github)](https://github.com/goettemar/cgc-tunee-download)
[![Python](https://img.shields.io/badge/Python-3.12+-green?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- 🎯 **Hybrid-Automation** - PyAutoGUI (Klicks) + Playwright (Navigation)
- 🎵 **Multi-Format Download** - MP3, FLAC, LRC, 2x Video (Lyric Video)
- 🖥️ **PySide6 GUI** - Benutzerfreundliche Oberfläche
- 🤖 **Automatische Song-Erkennung** - Scrollt & findet alle Songs
- 💾 **Session-Persistenz** - Einmal einloggen, immer eingeloggt
- 🎨 **Template-basiert** - Bildbasierte Button-Erkennung (OpenCV)

---

## 📋 Inhaltsverzeichnis

- [Problem & Lösung](#-problem--lösung)
- [Installation](#-installation)
  - [Host-System](#host-system)
  - [VM-Setup (empfohlen)](#vm-setup-empfohlen)
- [Quick Start](#-quick-start)
- [Verwendung](#-verwendung)
- [Dokumentation](#-dokumentation)
- [Architektur](#-architektur)
- [Troubleshooting](#-troubleshooting)
- [Entwicklung](#-entwicklung)

---

## 🎯 Problem & Lösung

### Problem
Download-Buttons auf tunee.ai sind nur bei Hover sichtbar (CSS `opacity: 0 → 1`).
→ Playwright kann sie nicht zuverlässig klicken (~30% Erfolgsrate).

### Lösung
**Hybrid-System:**
- **Playwright** findet Song & scrollt in View
- **PyAutoGUI** findet Download-Button bildbasiert (egal ob hovered!)
- **PyAutoGUI** hovert über Song → Button wird sichtbar
- **PyAutoGUI** klickt Button → Modal öffnet
- **PyAutoGUI** klickt Modal-Buttons position-basiert

**Erfolgsrate: ~95%** 🚀

---

## 📦 Installation

### Voraussetzungen

- **Python 3.12+**
- **Google Chrome** (echtes Chrome, nicht Chromium)
- **Linux** (getestet auf Ubuntu 22.04+)
- **GUI** (X11/Wayland - kein Headless!)

### Host-System

```bash
# Repository klonen
git clone https://github.com/goettemar/cgc-tunee-download.git
cd cgc-tunee-download

# Starten (installiert automatisch Dependencies)
./start.sh
```

Das wars! `start.sh` erstellt automatisch:
- ✅ Virtual Environment
- ✅ Installiert Dependencies
- ✅ Installiert Playwright Browser

### VM-Setup (empfohlen!)

**Warum VM?**
- Hauptsystem bleibt frei (keine Maus-Konflikte)
- Läuft im Hintergrund / über Nacht
- Bei Crash keine Auswirkung auf Host

**Quick Setup:**

```bash
# 1. VM erstellen (Ubuntu 22.04+)
# 2. In VM: Repository klonen
git clone https://github.com/goettemar/cgc-tunee-download.git
cd cgc-tunee-download

# 3. Starten
./start.sh

# 4. Templates erstellen (siehe unten)
```

**Detaillierte VM-Anleitung:** Siehe [VM-Setup Guide](#vm-setup-guide) unten.

---

## 🚀 Quick Start

### 1. Templates erstellen (WICHTIG!)

Templates sind Screenshots von UI-Elementen die PyAutoGUI sucht.

**Benötigte Templates:**
- `templates/download_button.png` - Download-Button neben Song
- `templates/modal_mp3.png` - MP3-Zeile im Download-Modal
- `templates/lyric_video_download.png` - Download-Button im Video-Modal

**Erstellen:**

1. Browser öffnen: `google-chrome https://www.tunee.ai`
2. Einloggen & zu Conversation gehen
3. Über Song hovern (Download-Button erscheint)
4. Screenshot-Tool: `flameshot gui` (oder gnome-screenshot)
5. Selektiere Button und speichere in `templates/`

**Tipp:** `test_templates.py` prüft ob Templates funktionieren!

### 2. App starten

```bash
./start.sh
```

### 3. GUI bedienen

1. **URL eingeben** (optional - wird automatisch erkannt)
2. **"Download starten"** klicken
3. **Browser öffnet sich** - ggf. einloggen
4. **Song-Liste prüfen** - "All Music" sichtbar?
5. **"Weiter"** klicken
6. **Downloads laufen automatisch!** ☕

### 4. Downloads finden

Alle Songs landen hier:
```
~/Downloads/tunee/SongName_MM-SS/
  ├── SongName.mp3        # Audio
  ├── SongName.flac       # Lossless
  ├── SongName.lrc        # Lyrics (Timestamps)
  ├── SongName.mp4        # Lyric Video 1
  └── SongName.mp4        # Lyric Video 2
```

---

## 📚 Verwendung

### GUI-Modus (Standard)

```bash
./start.sh
```

**Features:**
- Download-Tab: Songs herunterladen
- Certificate-Tab: Zertifikate verwalten
- Log-Widget: Echtzeit-Fortschritt
- Progress-Bar: Übersicht (Song X von Y)

### CLI-Modus

```bash
./start.sh --cli https://www.tunee.ai/conversation/ABC123
```

**Vorteile:**
- Kein GUI-Overhead
- Skriptfähig
- Headless-tauglich (mit Xvfb)

### Tests

```bash
source .venv/bin/activate

# Templates prüfen
python test_templates.py

# Einzelner Song
python test_click.py

# Alle Songs (Standalone)
python download_all_hybrid.py
```

---

## 📖 Dokumentation

| Dokument | Beschreibung |
|----------|-------------|
| **README.md** | Hauptdokumentation (diese Datei) |
| **QUICKSTART.md** | Schnellstart-Anleitung |
| **HYBRID_INTEGRATION.md** | Technische Details der PyAutoGUI-Integration |
| **INTEGRATION_SUMMARY.md** | Umfassende Zusammenfassung der Architektur |
| **CHANGELOG.md** | Versions-Historie |
| **templates/README.md** | Template-Erstellung Anleitung |

---

## 🏗️ Architektur

### Hybrid-System

```
┌─────────────────────────────────────────────┐
│  Playwright           +      PyAutoGUI      │
│  (Navigation)                (Klicks)       │
│                                             │
│  • Page laden                 • Templates  │
│  • Songs finden               • Klicken    │
│  • Scrolling                  • Hover OK!  │
└─────────────────────────────────────────────┘
```

### Workflow pro Song

```
1. Playwright: Finde Song per Duration (eindeutig!)
2. Playwright: Scrolle Song in View
3. Playwright: Hovere über Song (macht Button sichtbar)
4. PyAutoGUI:  Finde Download-Button (bildbasiert)
5. PyAutoGUI:  Klicke Button → Modal öffnet
6. PyAutoGUI:  Finde MP3-Button (Referenz)
7. PyAutoGUI:  Klicke 4 Buttons position-basiert
8. PyAutoGUI:  Klicke Lyric Video Download
9. ✅ 5 Dateien heruntergeladen!
```

### Projektstruktur

```
cgc_tunee_download/
├── src/
│   ├── gui/              # PySide6 GUI
│   │   ├── main_window.py
│   │   ├── download_tab.py
│   │   └── certificate_tab.py
│   ├── core/             # Business Logic
│   │   ├── song_worker.py    # Download-Worker
│   │   └── signals.py        # Qt Signals
│   ├── browser.py        # Playwright + PyAutoGUI Hybrid
│   └── auth.py           # Chrome Session Management
├── templates/            # UI-Element Screenshots
├── cookies/              # Session-Daten (gitignored)
├── requirements.txt      # Python Dependencies
├── start.sh             # Start-Script
└── README.md            # Diese Datei
```

---

## 🛠️ Troubleshooting

### Templates nicht gefunden

**Problem:** `⚠️ Template nicht gefunden: templates/download_button.png`

**Lösung:**
```bash
ls -la templates/
# Sollte 3 PNG-Files zeigen

# Neu erstellen (siehe Quick Start)
```

### PyAutoGUI findet Buttons nicht

**Problem:** `❌ Download-Button nicht gefunden`

**Mögliche Ursachen:**
1. **Browser auf falschem Monitor** → Browser verschieben
2. **Browser-Zoom ≠ 100%** → Ctrl+0 drücken
3. **Templates passen nicht** → Neu erstellen

**Debug:**
```bash
python test_templates.py  # Zeigt ob Templates gefunden werden
```

### Nur erster Song wird heruntergeladen

**Problem:** Script downloaded nur den ersten Song, dann wiederholt es sich.

**Lösung:** Fixed in v2.0! Hovern wird jetzt immer vor der Suche durchgeführt.

### Downloads nicht in ~/Downloads/tunee

**Problem:** Dateien landen woanders oder gar nicht.

**Lösung:** Fixed in v2.0! Chrome Preferences werden jetzt korrekt gesetzt.

### Maus ist "gefangen" während Download

**Problem:** Kann PC nicht nutzen während Downloads laufen.

**Lösung 1 - VM nutzen:**
Siehe [VM-Setup Guide](#vm-setup-guide)

**Lösung 2 - Zweiter Monitor:**
Browser auf zweiten Monitor, arbeite auf erstem.

---

## 🖥️ VM-Setup Guide

### Option A: KVM/QEMU (Linux Host)

```bash
# 1. VM erstellen
virt-manager
# - Ubuntu 22.04 Desktop
# - 4GB RAM, 20GB Disk
# - 2 CPUs

# 2. In VM: Projekt klonen
git clone https://github.com/goettemar/cgc-tunee-download.git
cd cgc-tunee-download
./start.sh

# 3. Templates erstellen (in VM!)
# Browser öffnen, hovern, Screenshots
```

### Option B: VirtualBox (Cross-Platform)

```bash
# 1. VirtualBox VM erstellen
# - Ubuntu 22.04 Desktop
# - Guest Additions installieren
# - Shared Folder einrichten

# 2. In VM: Projekt von Shared Folder kopieren
cp -r /media/sf_Downloads/cgc-tunee-download ~/
cd ~/cgc-tunee-download
./start.sh

# 3. Templates in VM erstellen
```

### Option C: Docker + VNC (Advanced)

```bash
# Dockerfile mit VNC Server
# Browser läuft in Container
# VNC-Verbindung vom Host

# TODO: Dockerfile erstellen
```

---

## 👨‍💻 Entwicklung

### Requirements installieren

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Code-Struktur

- **`src/browser.py`** - Hauptlogik (Hybrid-System)
- **`src/gui/`** - PySide6 GUI Components
- **`src/core/`** - Business Logic (Worker, Signals)
- **`src/auth.py`** - Chrome Session Management

### Tests schreiben

```python
# test_neues_feature.py
import asyncio
from src.browser import TuneeBrowser

async def test_neues_feature():
    # Test-Code hier
    pass

if __name__ == "__main__":
    asyncio.run(test_neues_feature())
```

### Pull Requests

1. Fork Repository
2. Feature-Branch erstellen
3. Tests hinzufügen
4. PR erstellen

---

## 📊 Performance

| Metric | Wert |
|--------|------|
| Erfolgsrate | ~95% |
| Zeit pro Song | ~20s |
| Downloads pro Song | 5 Dateien |
| Parallelität | 1 Song gleichzeitig |

**Pro Conversation (20 Songs):**
- ⏱️ ~7 Minuten
- 💾 ~400 MB (MP3+FLAC+Video)
- ✅ 100 Dateien (5 × 20 Songs)

---

## 🙏 Credits

- **PyAutoGUI** - Bildbasierte Automation
- **Playwright** - Browser-Automation
- **OpenCV** - Template-Matching
- **PySide6** - GUI Framework
- **Claude Sonnet 4.5** - Co-Authored-By

---

## 📜 License

MIT License - Siehe [LICENSE](LICENSE) für Details.

---

## 🔗 Links

- **GitHub:** https://github.com/goettemar/cgc-tunee-download
- **Issues:** https://github.com/goettemar/cgc-tunee-download/issues
- **Tunee.ai:** https://www.tunee.ai

---

## 🎯 Roadmap

- [ ] Multi-Threading (mehrere Songs parallel)
- [ ] Song-Auswahl vor Download
- [ ] Auto-Template-Erstellung beim ersten Start
- [ ] Docker-Container mit VNC
- [ ] Web-UI (Flask/FastAPI)
- [ ] CLI-Mode mit TUI (Rich/Textual)
- [ ] Playlist-Export (M3U, etc.)

---

**Made with ❤️ and 🤖 by CGC Studio**
