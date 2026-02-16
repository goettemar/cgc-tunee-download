# CGC Tunee Download

## Projektname
CGC Tunee Download

## Beschreibung
CGC Tunee Download ist ein Python-Tool zum automatisierten Herunterladen von Songs aus `tunee.ai`.

Das Projekt kombiniert:
- GUI-Automation mit `PyAutoGUI`
- Bildschirmaufnahme mit `mss` bzw. Wayland-Fallbacks
- OpenCV-Template-Matching für stabile Klick-Positionen
- eine optionale PySide6-Desktop-GUI für Bedienung, Status und Logs

Zusätzlich gibt es einen separaten Zertifikat-Workflow zum Herunterladen von PDF-Copyright-Zertifikaten pro Song.

Hinweis zum Projektlayout:
- Im Projektroot gibt es aktuell **kein** `pyproject.toml`.
- Ein minimales Legacy-`pyproject.toml` liegt unter `old_code/pyproject.toml`.

## Features
- Download-Workflow für Songs (MP3, RAW, LRC, VIDEO) per Template-Matching
- Duplikat-Erkennung über vorerstellte Song-Ordner und Laufzeit-/Namensvergleich
- Automatisches Einsortieren der Downloads nach `~/Downloads/tunee/NN - Name - MMmSSs`
- Separater Zertifikat-Downloader (PDF) inkl. Zuordnung zum richtigen Song-Ordner
- GUI mit:
  - Preflight-Checks (Display, Monitor, Templates, Chrome/CDP)
  - Start/Stop, Fortschritt, Live-Log
  - Projekt-Scan (Ordnerstruktur aus Tunee-Songliste)
  - Statistik (heruntergeladen, Duplikate, Fehler)
  - Songs-Übersichtstabelle inkl. Zertifikat-Status
  - Einstellungsseite (Monitor, Limits, Timing, Schwellen)
- CLI-Modus für Song- und Zertifikat-Downloads
- Multi-Monitor-Unterstützung
- Wayland-Unterstützung via XDG-Portal (`_portal_helper.py`) mit `gnome-screenshot`-Fallback

## Installation
### Voraussetzungen
- Linux-Desktop mit grafischer Session (`X11` oder `Wayland`)
- Python 3.12+
- Google Chrome (`google-chrome` im `PATH`)
- Für Dauer-Erkennung: `ffprobe` (Paket `ffmpeg`)
- Für `PyAutoGUI`: `python3-tk`

### Standard-Setup (empfohlen)
`start.sh` übernimmt Setup und Start automatisch:

```bash
./start.sh
```

Das Skript:
- erstellt bei Bedarf `.venv`
- installiert `requirements.txt`
- legt `data/` und `downloads/` an
- prüft `ffprobe` und `tkinter`
- startet dann `main.py`

## Usage (CLI + GUI)
### GUI (Default)
Start:

```bash
./start.sh
```

Ablauf in der GUI:
1. Optional: `Chrome starten` (mit Remote-Debug-Port 9222)
2. Optional: `Projekt scannen` (liest Songliste via CDP und erstellt Ordner)
3. `Start` für Song-Downloads
4. Optional: `Zertifikate laden` für PDF-Zertifikate

### CLI
Song-Download im CLI-Modus:

```bash
./start.sh --cli
```

Nützliche Optionen:

```bash
./start.sh --cli --list-monitors
./start.sh --cli --songs 50 --scrolls 15 --monitor 1
./start.sh --cli --no-chrome
```

Zertifikate im CLI-Modus:

```bash
./start.sh --cli --cert --songs 50 --scrolls 15 --monitor 1
```

Wichtige CLI-Flags aus `main.py`:
- `--gui` (Default)
- `--cli`
- `--cert` (nur mit `--cli`)
- `--songs <int>`
- `--scrolls <int>`
- `--monitor <int>`
- `--list-monitors`
- `--no-chrome`
- `--url <url>`

## Architektur
### Überblick
Das aktive System ist template-basiert (OpenCV + PyAutoGUI). Ein VLM-Client (`src/vlm.py`) ist vorhanden, gehört aber nicht zum Standardablauf des aktuellen GUI/CLI-Downloadpfads.

### Hauptkomponenten
- `main.py`
  - Einstiegspunkt
  - Moduswahl GUI/CLI
  - CLI-Parameter und Start der jeweiligen Orchestrierung
- `start.sh`
  - Launcher inkl. venv/dependency/bootstrap
- `src/orchestrator.py`
  - Haupt-Workflow für Song-Downloads
  - Klick-Reihenfolge (MP3/RAW/LRC/VIDEO)
  - Download-Warten, Duplikat-Logik, Dateiverschiebung
- `src/cert_orchestrator.py`
  - separater PDF-Zertifikat-Workflow
- `src/scraper.py`
  - Songlisten-Ermittlung über Chrome DevTools Protocol (Port 9222)
- `src/template_match.py`
  - Template-Erkennung (`find_template`, `find_all_templates`, `find_button_in_row`)
- `src/screenshot.py`, `src/_portal_helper.py`
  - Screenshot-Abstraktion für X11/Wayland
- `src/events.py`
  - Event-Schnittstelle für CLI-Output und GUI-Signale
- `src/gui/*`
  - PySide6-Oberfläche (Dashboard, Songs, Einstellungen, Worker)

### Daten- und Ausgabepfade
- Output: `~/Downloads/tunee`
- Temporäre Browserdaten (Launcher/GUI-Start):
  - `~/.cache/cgc_tunee_download/chrome_profile`
- GUI-Konfiguration:
  - `data/config.json`
- Templates (aktuell genutzt):
  - `old_code/templates/*.png`

## Dependencies
### Python (`requirements.txt`)
- `PySide6>=6.6.0`
- `opencv-python>=4.8.0`
- `pyautogui>=0.9.54`
- `mss>=9.0.0`
- `pillow>=10.0.0`
- `requests>=2.31.0`
- `websocket-client>=1.6.0`

### Systemabhängigkeiten (aus Code/CI/Startskript)
- `google-chrome`
- `ffmpeg` / `ffprobe`
- `python3-tk`
- bei GUI/CI zusätzlich relevante Laufzeitlibs (z. B. `libegl1`, `libxkbcommon0`, `libdbus-1-3`)

