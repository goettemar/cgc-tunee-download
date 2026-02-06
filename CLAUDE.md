# CGC Tunee Download

Automatisierter Download von Songs von tunee.ai mit Playwright + Python.

## Status: Funktionsfähig (GUI + CLI)

Der Song-Download funktioniert. Certificates sind implementiert (separater Tab).

## Architektur

```
cgc_tunee_download/
├── src/
│   ├── auth.py            # Chrome-Profil & Cookie-Management
│   ├── browser.py         # Playwright-Automation (Klicks, Downloads)
│   ├── downloader.py      # (ungenutzt, für direkten httpx-Download)
│   ├── gui/
│   │   ├── main_window.py     # Hauptfenster mit Tabs
│   │   ├── download_tab.py    # Song-Download UI
│   │   ├── certificate_tab.py # Certificate UI
│   │   └── log_widget.py      # Log-Ausgabe Widget
│   └── core/
│       ├── signals.py         # Qt Signals für Worker-GUI Kommunikation
│       ├── song_worker.py     # QThread für Song-Downloads
│       └── cert_worker.py     # QThread für Certificate-Downloads
├── cookies/
│   └── chrome_profile/    # Persistentes Chrome-Profil (Google Login)
├── main.py                # GUI-Einstiegspunkt
├── main_cli.py            # CLI-Einstiegspunkt
├── start.sh               # Startscript mit venv
└── CLAUDE.md
```

## Wie es funktioniert

### Download-Workflow pro Song (VEREINFACHT):
1. **Download-Button** direkt neben dem Song in der linken Liste klicken (Icon neben dem Stern)
2. Download-Modal öffnet sich mit 4 Download-Buttons:
   - **Index 0**: MP3 (direkter Download)
   - **Index 1**: RAW/FLAC (direkter Download)
   - **Index 2**: VIDEO (öffnet Lyric Video Modal → dort Download)
   - **Index 3**: LRC (direkter Download, ausgegraut bei Instrumentals)
3. Reihenfolge: MP3 → RAW → LRC → VIDEO (Video zum Schluss wegen Modal)
4. **Fertig!** Kein rechtes Panel nötig, alles im linken Frame!

### Besonderheiten:
- **Instrumentals**: LRC-Button ist ausgegraut → Tool erstellt leere `.lrc` mit "This is an instrumental"
- **Video**: Öffnet separates "Lyric Video" Modal, dort nochmal Download klicken
- **Eindeutigkeit**: Ordnername enthält Duration (z.B. `Song_03-45`), Dateien nur den Namen

### Download-Ordner:
```
~/Downloads/tunee/
├── Quiet_Resolve_03-45/       # Ordner = Name + Duration
│   ├── Quiet_Resolve.mp3      # Dateien = nur Name
│   ├── Quiet_Resolve.flac
│   ├── Quiet_Resolve.lrc
│   └── Quiet_Resolve.mp4
├── Quiet_Resolve_04-12/       # Gleicher Name, andere Duration = anderer Song
│   └── ...
```

**Warum Duration im Ordnernamen?**
- Eindeutige Identifikation auch bei gleichem Song-Namen
- Tunee kann selbst V2 erstellen - das bleibt im Namen erhalten
- Certificates können später über Name + Duration zugeordnet werden
- CGC Musikmanagement importiert mit echtem Namen

## Certificates

### Separater Prozess (Certificate Tab):
1. Scannt `~/Downloads/tunee/` nach Ordnern ohne `.pdf`
2. Öffnet Tunee-Conversation im Browser
3. Für jeden Ordner ohne Certificate:
   - Sucht passenden Song auf Tunee (nach Name)
   - 3-Punkte-Menü → "Copyright Certificate"
   - Download-Button im Certificate-Modal klicken
   - PDF im Song-Ordner speichern als `{SongName}_certificate.pdf`

### Certificate-Workflow im Browser:
1. Song anklicken (muss in Tunee-Conversation sein)
2. 3-Punkte-Menü öffnen
3. "Copyright Certificate" klicken
4. Modal mit Certificate-Infos öffnet sich
5. Download-Button oben rechts klicken → PDF wird heruntergeladen

## GUI Features

### Song-Download Tab:
- URL-Eingabe für Tunee-Conversation
- Start/Stop Button
- Fortschrittsanzeige: "Song X von Y"
- Log-Ausgabe (farbig: grün=Erfolg, rot=Fehler, gelb=Warnung)

### Certificate Tab:
- Ordner-Scanner findet Song-Ordner ohne PDF
- Liste der Ordner ohne Certificate
- Start Button zum Nachladen
- Fortschrittsanzeige

### Technische Details:
- QThread-Worker für asynchrone Downloads
- Signals für GUI-Updates aus dem Worker
- Dark Theme im VS Code Stil

## Bekannte Probleme & Lösungsansätze

### Aktuelles Hauptproblem: Download-Buttons in Song-Liste nicht klickbar

**Problem:**
- Download-Buttons in der linken Song-Liste erscheinen nur bei Hover (CSS opacity)
- Playwright findet die Buttons nicht zuverlässig
- Modal öffnet sich nicht konsistent nach Button-Klick
- Nur der erste Song funktioniert manchmal

**Bisherige Versuche (alle fehlgeschlagen):**
1. ❌ Hover über Song-Zeile + Button-Suche → Buttons bleiben invisible
2. ❌ Koordinaten-basierter Klick → Modal öffnet sich nicht
3. ❌ Song anklicken + rechtes Panel → Button-Klick öffnet kein Modal
4. ❌ 3-Punkte-Menü im rechten Panel → Menü öffnet sich nicht

### Geplante Lösungsansätze für morgen:

#### Option 1: PyAutoGUI (Empfohlen)
**Konzept:** Bildbasierte Automation statt HTML-Parsing

```python
import pyautogui
import time

# 1. Screenshot vom Download-Button machen (einmalig)
# 2. Button per Bilderkennung finden und klicken
button_location = pyautogui.locateOnScreen('download_button.png')
if button_location:
    pyautogui.click(button_location)
```

**Vorteile:**
- ✅ Ignoriert HTML-Struktur komplett
- ✅ Funktioniert mit jedem Browser
- ✅ Hover wird automatisch durch Mausbewegung ausgelöst
- ✅ Sehr robust gegen Website-Änderungen

**Implementierung:**
1. Template-Screenshots erstellen (Download-Button, Modal-Buttons, etc.)
2. PyAutoGUI findet Buttons per Bilderkennung
3. Klickt direkt auf die Pixel-Koordinaten

#### Option 2: Lokales LLM mit Computer Use
**Konzept:** LLM steuert Browser wie ein Mensch (z.B. Claude Computer Use, GPT-4V)

```python
# Lokales LLM (z.B. Ollama mit Vision-Modell)
# 1. Screenshot machen
# 2. LLM: "Wo ist der Download-Button?"
# 3. LLM gibt Koordinaten zurück
# 4. Klick auf Koordinaten
```

**Vorteile:**
- ✅ Flexibel - versteht UI wie ein Mensch
- ✅ Kann mit UI-Änderungen umgehen
- ✅ Keine Template-Screenshots nötig

**Nachteile:**
- ⚠️ Langsamer (LLM-Inferenz pro Aktion)
- ⚠️ Braucht gutes Vision-Model (Llama 3.2 Vision, Qwen2-VL)

#### Option 3: Claude.ai API mit Computer Use
**Konzept:** Claude.ai API nutzen für Browser-Steuerung

**Vorteile:**
- ✅ Claude kann es nachweislich (manuell getestet)
- ✅ Sehr intelligent, versteht UI perfekt

**Nachteile:**
- ❌ Token-Kosten pro Song sehr hoch
- ❌ Nicht für 50+ Songs skalierbar
- ❌ Braucht Internet + API-Key

### Weitere bekannte Probleme:

1. **Google Login**: Playwright-Chromium wird von Google blockiert → Lösung: Echtes Chrome mit `channel="chrome"`

2. **3-Punkte-Menü finden**: Position variiert → Lösung: Suche nach SVG mit 3 Dots, rechtester Button in der Gruppe

3. **Video-Modal**: VIDEO-Button öffnet separates Modal → Lösung: VIDEO zum Schluss, dann Modal-Download

## Entwicklung

```bash
# Setup
cd /mnt/llm-data/projekte/cgc_tunee_download
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# GUI starten
./start.sh

# CLI starten (alte Variante)
./start.sh --cli
./start.sh --cli "https://www.tunee.ai/conversation/CONVERSATION_ID"
```

## Dependencies

- `playwright` - Browser-Automation
- `httpx` - (für späteren direkten Download)
- `pyside6` - GUI Framework
