# CGC Tunee Download — VLM Agent

Automatisierter Download von Songs von tunee.ai mit UI-TARS 1.5 7B Vision-Model + PyAutoGUI.

## Status: VLM-Ansatz (neu)

Alle programmatischen Ansätze (Playwright, PyAutoGUI-Templates, JS-Click) sind gescheitert.
Neuer Ansatz: Lokales Vision-Model "sieht" den Bildschirm und steuert Maus/Tastatur direkt.

## Architektur

```
Screenshot (mss) → UI-TARS 1.5 7B (Ollama) → Action Parser → PyAutoGUI → Loop
```

```
cgc_tunee_download/
├── src/
│   ├── __init__.py
│   ├── screenshot.py      # mss Screenshot → Base64 PNG
│   ├── vlm.py             # Ollama Vision-Client (UI-TARS 1.5 7B)
│   ├── actions.py          # Action-Parser + PyAutoGUI-Executor
│   └── orchestrator.py     # Agent-Loop: screenshot → VLM → execute → repeat
├── main.py                 # CLI Entry Point (argparse)
├── start.sh                # Launcher (venv, deps, Ollama-Check)
├── requirements.txt        # openai, pyautogui, mss, pillow
├── cookies/
│   └── chrome_profile/     # Persistentes Chrome-Profil (Google Login)
├── downloads/
└── old_code/               # Alter Playwright/PyAutoGUI-Code
```

## Wie es funktioniert

### Agent-Loop:
1. Screenshot aufnehmen (mss → Base64 PNG)
2. An UI-TARS senden mit Task-Beschreibung + History
3. VLM antwortet mit Thought + Action
4. Action parsen (Koordinaten 0-1000 → absolute Pixel)
5. Via PyAutoGUI ausführen (click, type, scroll, etc.)
6. 2s warten, repeat bis `finished()` oder max_steps

### UI-TARS Output-Format:
```
Thought: I see the download button on the right side of the song row
Action: click(start_box='<|box_start|>(500,300)<|box_end|>')
```

Koordinaten sind **normalisiert auf 0-1000**:
```python
abs_x = round(screen_width * x / 1000)
abs_y = round(screen_height * y / 1000)
```

### Download-Workflow pro Song:
1. Hover über Song-Zeile → Download-Icons erscheinen (normalerweise hidden)
2. Download-Icon (Pfeil nach unten) klicken → Download-Modal öffnet sich
3. Modal hat 4 Buttons: MP3 Download, RAW Download, VIDEO, LRC Download
4. Reihenfolge: **MP3 → RAW → LRC → VIDEO** (VIDEO zuletzt!)
5. LRC: Falls ausgegraut → Song ist Instrumental, überspringen
6. VIDEO: Öffnet zweites Modal mit Download-Button → Klick startet Download
   → Schließt BEIDE Modals automatisch → Nächster Song

## Systemvoraussetzungen

- **GPU**: NVIDIA RTX PRO 4500 (32GB VRAM)
- **Ollama**: `sudo snap start ollama.ollama`
- **Model**: `ollama pull 0000/ui-tars-1.5-7b` (~15GB), dann `ollama create ui-tars-gui -f Modelfile`
- **Display**: X11 :0
- **Python**: 3.12+, PyAutoGUI braucht `python3-tk`

## Starten

```bash
cd /mnt/llm-data/projekte/cgc_tunee_download

# Normal (startet Chrome + Agent)
./start.sh

# Test-Modus (ein Screenshot + VLM-Aufruf, keine Ausführung)
./start.sh --test

# Chrome schon offen
./start.sh --no-chrome

# Benutzerdefinierter Task
./start.sh --task "Click the first song's download button"

# Mehr Steps erlauben
./start.sh --steps 100
```

## Dependencies

- `openai` — (nicht direkt genutzt, aber kompatible API)
- `pyautogui` — Maus/Tastatur-Steuerung
- `mss` — Screenshot-Capture
- `pillow` — Bildverarbeitung

## Bekanntes

- **Ollama cold-start**: Model laden dauert ~30s beim ersten Aufruf
- **Inference-Speed**: ~5-10s pro VLM-Aufruf (7B auf RTX PRO 4500)
- **PyAutoGUI FAILSAFE**: Maus in obere linke Ecke (0,0) = Abbruch
- **History-Limit**: Letzte 10 Actions als Kontext
- **Multi-Monitor**: `--monitor N` wählt den Monitor (1=primary)
- **Modelfile**: Das Original-Ollama-Model hat ein kaputtes Template (`{{ .Prompt }}`), daher custom `ui-tars-gui` mit Qwen2.5VL Chat-Template
- **Gotcha**: Songs mit gleichem Titel aber unterschiedlicher Länge → später: Ordner `Titel_Länge`
- **Gotcha**: Instrumentals haben LRC ausgegraut → später: leere .lrc mit "This is an instrumental"
