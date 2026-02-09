# Tunee Download Automation mit lokalem Vision-Modell (UI-TARS)

## Hintergrund: Warum ein neuer Ansatz?

Alle bisherigen programmatischen Ansätze zur Automatisierung der Tunee.ai-Downloads sind gescheitert:

| Ansatz | Problem |
|--------|---------|
| **PyAutoGUI Klicks** | Läuft auf KVM-VM → Maus verlässt VM-Fenster → Klicks gehen ins Leere |
| **Playwright `page.mouse.click()`** | CDP-basiert (KVM-sicher), aber Download-Modal öffnet sich nur kurz und schliesst sich sofort wieder |
| **JavaScript `element.click()`** | React-Events werden nicht korrekt ausgelöst |
| **`dispatchEvent()`** | Gleiche Probleme wie element.click() |
| **Template-Matching + Klick** | Kombination aus PyAutoGUI-Suche + Klick scheitert an den obigen Problemen |

Die Tunee.ai-Seite ist dynamisch aufgebaut (React/Next.js) mit Hover-CSS, Modals und komplexem Event-Handling. Programmatische DOM-Manipulation funktioniert nicht zuverlässig.

**Lösung**: Ein lokales Vision-Modell (VLM) das wie ein Mensch den Bildschirm "sieht" und die Maus steuert — direkt auf einem Server mit GPU, nicht in der KVM-VM.

---

## Empfohlenes Modell: UI-TARS 7B

**UI-TARS** (ByteDance) ist ein spezialisiertes Vision-Language-Modell für GUI-Automatisierung. Es wurde auf Millionen von GUI-Screenshots trainiert und kann:
- Bildschirminhalt verstehen (Buttons, Texte, Modals, Listen)
- Maus-Aktionen zurückgeben (click, move, scroll, type)
- Multi-Step Aufgaben eigenständig abarbeiten

### Warum UI-TARS 7B?

| Modell | Grösse | VRAM | Stärken | Schwächen |
|--------|--------|------|---------|-----------|
| **UI-TARS 7B** | 7B | ~16 GB (FP16) / ~8 GB (INT4) | Spezialisiert auf GUI-Tasks, gute Maus-Steuerung, aktiv weiterentwickelt | Langsamer als kleinere Modelle |
| UI-TARS 72B | 72B | ~80 GB | Beste Ergebnisse | Zu gross für 32GB VRAM |
| ShowUI 2B | 2B | ~4 GB | Sehr schnell, kompakt | Weniger intelligent bei komplexen Multi-Step Tasks |
| CogAgent 9B | 9B | ~20 GB | Gute visuelle Erkennung | Weniger spezialisiert auf GUI-Aktionen |
| OS-Atlas 7B | 7B | ~16 GB | Gute Element-Grounding | Keine native Action-Generierung |

**Empfehlung**: UI-TARS 7B in FP16 (~16 GB VRAM) — passt gut in 32 GB und lässt Raum für den Browser.

---

## Architektur

```
┌─────────────────────────────────────────────────────┐
│                   GPU Server (32GB VRAM)             │
│                                                      │
│  ┌─────────────┐    ┌──────────────────────┐        │
│  │   Chrome     │    │   vLLM / Ollama      │        │
│  │   Browser    │◄───│   UI-TARS 7B         │        │
│  │   (Tunee.ai) │    │   (localhost:8000)    │        │
│  └──────┬───────┘    └──────────┬───────────┘        │
│         │                       │                    │
│         │    Screenshots        │   Aktionen         │
│         │                       │   (click, type)    │
│  ┌──────▼───────────────────────▼───────────┐       │
│  │         Orchestrator Script               │       │
│  │         (Python)                          │       │
│  │                                           │       │
│  │  1. Screenshot aufnehmen                  │       │
│  │  2. An VLM senden mit Prompt              │       │
│  │  3. Aktion ausführen (PyAutoGUI)          │       │
│  │  4. Warten → Loop                         │       │
│  └───────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

**Wichtig**: Alles läuft direkt auf dem GPU-Server (nicht in der KVM-VM). PyAutoGUI funktioniert hier zuverlässig, weil die Maus nicht aus dem Fenster "wandert".

---

## Setup-Anleitung

### 1. vLLM installieren und UI-TARS starten

```bash
# vLLM installieren
pip install vllm

# UI-TARS 7B herunterladen und starten
vllm serve bytedance-research/UI-TARS-7B-SFT \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype float16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.7 \
  --trust-remote-code
```

**Alternative mit Ollama** (einfacher, aber evtl. langsamer):

```bash
# Ollama installieren
curl -fsSL https://ollama.ai/install.sh | sh

# UI-TARS 7B laden (falls verfügbar als GGUF)
ollama pull ui-tars:7b

# Starten
ollama serve
```

### 2. Python-Dependencies

```bash
pip install openai pyautogui pillow mss
```

- `openai`: Für OpenAI-kompatible API (vLLM stellt diese bereit)
- `pyautogui`: Maus/Tastatur-Steuerung (funktioniert auf GPU-Server nativ)
- `pillow`: Bild-Verarbeitung
- `mss`: Schnelle Screenshots

### 3. Display-Setup auf dem GPU-Server

Der Server braucht einen laufenden Display-Server (X11 oder Wayland) für PyAutoGUI und Chrome:

```bash
# Falls headless: Xvfb als virtuellen Display starten
sudo apt install xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Oder mit VNC für Remote-Beobachtung
sudo apt install x11vnc tigervnc-standalone-server
vncserver :1 -geometry 1920x1080 -depth 24
export DISPLAY=:1
```

**Empfehlung**: VNC verwenden, damit man den Fortschritt beobachten kann.

### 4. Chrome starten

```bash
google-chrome \
  --no-sandbox \
  --user-data-dir=./cookies/chrome_profile \
  --window-size=1920,1080 \
  --window-position=0,0 \
  "https://www.tunee.ai"
```

Beim ersten Start manuell einloggen (Cookie-Profil wird gespeichert).

---

## Orchestrator-Script: Konzept

Das Herzstück ist ein Python-Script das in einer Loop arbeitet:

```python
#!/usr/bin/env python3
"""
Tunee Download Orchestrator mit UI-TARS Vision Model.

Loop:
1. Screenshot aufnehmen
2. An UI-TARS senden mit Task-Beschreibung
3. Aktion ausführen
4. Repeat
"""

import base64
import time
import pyautogui
import mss
from openai import OpenAI
from PIL import Image
import io

# vLLM API (OpenAI-kompatibel)
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # vLLM braucht keinen API-Key
)

MODEL = "bytedance-research/UI-TARS-7B-SFT"

def take_screenshot() -> str:
    """Screenshot als Base64-String."""
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        pil_img = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

def ask_vlm(screenshot_b64: str, task: str) -> dict:
    """Sendet Screenshot + Task an UI-TARS, gibt Aktion zurück."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}"
                    }
                },
                {
                    "type": "text",
                    "text": task
                }
            ]
        }],
        max_tokens=256
    )
    # UI-TARS gibt Aktionen im Format:
    # {"action": "click", "x": 500, "y": 300}
    # {"action": "type", "text": "hello"}
    # {"action": "scroll", "direction": "down"}
    return parse_action(response.choices[0].message.content)

def execute_action(action: dict):
    """Führt die vom VLM zurückgegebene Aktion aus."""
    if action["action"] == "click":
        pyautogui.click(action["x"], action["y"])
    elif action["action"] == "type":
        pyautogui.typewrite(action["text"])
    elif action["action"] == "scroll":
        direction = -3 if action["direction"] == "down" else 3
        pyautogui.scroll(direction)
    elif action["action"] == "move":
        pyautogui.moveTo(action["x"], action["y"])
    elif action["action"] == "done":
        return False  # Task abgeschlossen
    time.sleep(1)
    return True

def parse_action(response_text: str) -> dict:
    """Parst die VLM-Antwort in eine Aktion."""
    # UI-TARS gibt strukturierte Aktionen zurück
    # Format variiert je nach Modell-Version
    # Beispiel: "click(500, 300)" oder JSON
    # TODO: Anpassen an tatsächliches Output-Format
    import json
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: Text parsen
        if "click" in response_text.lower():
            # Koordinaten extrahieren
            import re
            nums = re.findall(r'\d+', response_text)
            if len(nums) >= 2:
                return {"action": "click", "x": int(nums[0]), "y": int(nums[1])}
        return {"action": "done"}
```

### Task-Prompts für Tunee

Die Stärke des VLM-Ansatzes: Man beschreibt die Aufgabe in natürlicher Sprache.

```python
# Song in Liste finden und Download-Modal öffnen
TASK_OPEN_DOWNLOAD = """
Ich sehe eine Song-Liste auf tunee.ai.
Bewege die Maus über den Song "{song_name}" mit der Dauer {duration}.
Wenn ein Download-Icon (Pfeil nach unten) erscheint, klicke darauf.
"""

# MP3 herunterladen
TASK_DOWNLOAD_MP3 = """
Ich sehe ein Download-Modal.
Finde die Zeile "MP3" und klicke auf den "Download" Button in dieser Zeile.
"""

# RAW herunterladen
TASK_DOWNLOAD_RAW = """
Ich sehe ein Download-Modal.
Finde die Zeile "RAW" und klicke auf den "Download" Button in dieser Zeile.
"""

# LRC herunterladen
TASK_DOWNLOAD_LRC = """
Ich sehe ein Download-Modal.
Finde die Zeile "LRC" und klicke auf den "Download" Button in dieser Zeile.
"""

# VIDEO herunterladen (öffnet Lyric Video Modal)
TASK_DOWNLOAD_VIDEO = """
Ich sehe ein Download-Modal.
Finde die Zeile "VIDEO" und klicke auf den "Download" Button in dieser Zeile.
"""

# Lyric Video Download
TASK_LYRIC_VIDEO = """
Ich sehe ein Lyric Video Modal/Player.
Finde den "Download" Button und klicke darauf.
"""

# Modal schliessen
TASK_CLOSE_MODAL = """
Ich sehe ein Modal/Dialog. Drücke Escape oder klicke ausserhalb um es zu schliessen.
"""
```

### Download-Loop pro Song

```python
async def download_song(song_name: str, duration: str):
    """Kompletter Download eines Songs über VLM-Steuerung."""

    # 1. Download-Modal öffnen
    task = TASK_OPEN_DOWNLOAD.format(song_name=song_name, duration=duration)
    for attempt in range(5):
        screenshot = take_screenshot()
        action = ask_vlm(screenshot, task)
        execute_action(action)
        time.sleep(2)

        # Prüfe ob Modal offen ist
        screenshot = take_screenshot()
        check = ask_vlm(screenshot, "Ist ein Download-Modal sichtbar? Antworte nur 'ja' oder 'nein'.")
        if "ja" in check.get("text", "").lower():
            break

    # 2. Downloads in Reihenfolge: MP3 → RAW → LRC → VIDEO
    for task_prompt in [TASK_DOWNLOAD_MP3, TASK_DOWNLOAD_RAW, TASK_DOWNLOAD_LRC]:
        screenshot = take_screenshot()
        action = ask_vlm(screenshot, task_prompt)
        execute_action(action)
        time.sleep(3)  # Warte auf Download-Start

    # 3. VIDEO → öffnet Lyric Video Modal
    screenshot = take_screenshot()
    action = ask_vlm(screenshot, TASK_DOWNLOAD_VIDEO)
    execute_action(action)
    time.sleep(3)

    # 4. Lyric Video Download
    screenshot = take_screenshot()
    action = ask_vlm(screenshot, TASK_LYRIC_VIDEO)
    execute_action(action)
    time.sleep(3)

    # 5. Modal schliessen
    screenshot = take_screenshot()
    action = ask_vlm(screenshot, TASK_CLOSE_MODAL)
    execute_action(action)
    time.sleep(1)
```

---

## Alternative: UI-TARS-Desktop (Electron App)

ByteDance bietet eine fertige Desktop-App: **[UI-TARS-Desktop](https://github.com/bytedance/UI-TARS-Desktop)**

- Electron-basiert, nimmt automatisch Screenshots
- Verbindet sich mit lokalem vLLM/Ollama-Endpoint
- Führt Maus/Tastatur-Aktionen aus
- Man gibt den Task in natürlicher Sprache ein

```bash
# Installation
git clone https://github.com/bytedance/UI-TARS-Desktop.git
cd UI-TARS-Desktop
npm install
npm run build

# Konfiguration: Settings → Model Provider
# URL: http://localhost:8000/v1
# Model: bytedance-research/UI-TARS-7B-SFT

# Verwendung:
# 1. Chrome mit Tunee öffnen
# 2. In UI-TARS-Desktop eingeben:
#    "Download all songs from the list. For each song: hover over it,
#     click the download icon, then click MP3 Download, RAW Download,
#     LRC Download, and VIDEO Download buttons."
```

**Vorteil**: Kein eigenes Script nötig.
**Nachteil**: Weniger Kontrolle über den genauen Ablauf, evtl. zu generisch für 50 Songs.

---

## VRAM-Budget (32 GB)

| Komponente | VRAM |
|-----------|------|
| UI-TARS 7B (FP16) | ~16 GB |
| Chrome Browser | ~2-4 GB |
| Screenshot-Processing | ~1 GB |
| **Reserve** | **~11 GB** |
| **Total** | **~20-21 GB von 32 GB** |

Falls VRAM knapp wird: INT4-Quantisierung reduziert auf ~8 GB, aber mit Qualitätsverlust.

---

## Vorteile gegenüber programmatischem Ansatz

1. **Kein DOM-Hacking**: Das VLM "sieht" den Bildschirm wie ein Mensch — egal ob React, Angular oder statisches HTML
2. **Hover-CSS funktioniert**: Echte Mausbewegung über PyAutoGUI auf dem Server (nicht KVM)
3. **Modal-Problem gelöst**: Das VLM wartet auf visuelles Feedback, nicht auf DOM-Events
4. **Robust gegen UI-Änderungen**: Tunee ändert das Layout? Das VLM passt sich an
5. **Keine Coordinate-Berechnung**: VLM gibt direkt Bildschirm-Koordinaten zurück

## Risiken und Einschränkungen

1. **Geschwindigkeit**: ~2-5 Sekunden pro VLM-Inference → bei 50 Songs × 6 Aktionen = 300 Aufrufe → ~15-25 Minuten
2. **Halluzinationen**: VLM könnte falsche Koordinaten zurückgeben → Retry-Logik nötig
3. **Modell-Setup**: vLLM/CUDA muss auf dem Server korrekt installiert sein
4. **Display nötig**: Server braucht X11/Xvfb + VNC für GUI

---

## Nächste Schritte

1. **Auf GPU-Server wechseln** (dieses Repo dorthin klonen)
2. **CUDA/vLLM installieren** und UI-TARS 7B starten
3. **VNC einrichten** für Remote-Zugriff auf den Desktop
4. **Chrome starten** und bei Tunee einloggen (Cookie-Profil übernehmen)
5. **Orchestrator-Script** erstellen und testen (erst ein Song, dann alle)
6. Optional: UI-TARS-Desktop ausprobieren als Alternative

---

## Referenzen

- UI-TARS Paper: https://arxiv.org/abs/2501.12326
- UI-TARS auf HuggingFace: https://huggingface.co/bytedance-research/UI-TARS-7B-SFT
- UI-TARS-Desktop: https://github.com/bytedance/UI-TARS-Desktop
- vLLM Dokumentation: https://docs.vllm.ai/
- ShowUI: https://huggingface.co/showlab/ShowUI-2B
- CogAgent: https://huggingface.co/THUDM/CogAgent-9B
