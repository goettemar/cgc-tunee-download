# Tunee.ai Download Automation

Hybrid-Ansatz: Playwright für Browser-Navigation + Python für direkte Downloads.

## Problem

Die Download-URLs auf tunee.ai werden erst dynamisch generiert, wenn man auf die Download-Buttons klickt. Reines Web-Scraping funktioniert daher nicht.

## Lösung

1. **Playwright** navigiert durch die UI (Songs anklicken, Menü öffnen, Download-Modal öffnen)
2. **URLs werden extrahiert** sobald das Modal geöffnet ist
3. **Python/httpx** lädt die Dateien direkt herunter (schneller, paralleler möglich)

## Installation

```bash
cd /mnt/llm-data/projekte/cgc_tunee_download

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Playwright Browser installieren
playwright install chromium
```

## Verwendung

```bash
# Standard-URL (aus der Konfiguration)
python main.py

# Eigene URL
python main.py "https://www.tunee.ai/conversation/DEINE_ID"
```

### Erster Start (Login erforderlich)

1. Browser öffnet sich automatisch
2. Logge dich mit Google ein
3. Warte bis die Musik-Seite vollständig geladen ist
4. Drücke ENTER im Terminal
5. Cookies werden gespeichert für zukünftige Sessions

### Weitere Starts

Cookies werden automatisch geladen - kein erneuter Login nötig (solange Session gültig).

## Projektstruktur

```
cgc_tunee_download/
├── src/
│   ├── auth.py         # Cookie/Session-Management
│   ├── browser.py      # Playwright-Automation
│   └── downloader.py   # Direkter Download mit httpx
├── cookies/            # Gespeicherte Browser-Session
├── downloads/          # Heruntergeladene Dateien
├── requirements.txt
├── main.py             # Einstiegspunkt
└── README.md
```

## Download-Reihenfolge

Pro Song werden 4 Formate heruntergeladen:
1. MP3 - Für Sharing und Speicherung
2. RAW - Lossless (FLAC/WAV)
3. LRC - Synchronisierte Lyrics
4. VIDEO - MP4

## Ausgabe-Struktur

```
downloads/
├── Sacred_Shadows_Surge/
│   ├── Sacred_Shadows_Surge.mp3
│   ├── Sacred_Shadows_Surge.flac
│   ├── Sacred_Shadows_Surge.lrc
│   └── Sacred_Shadows_Surge.mp4
├── Stone_Saints_Rise/
│   └── ...
└── download_log_20240115_143022.json
```

## Troubleshooting

**"Musik-Liste nicht gefunden"**
- Login abgelaufen → Lösche `cookies/tunee_session.json` und starte neu

**"Keine URLs gefunden"**
- Website-Struktur hat sich geändert → Selektoren in `browser.py` anpassen

**Downloads schlagen fehl**
- Session-Cookies ungültig → Neu einloggen
- Rate-Limiting → Längere Pausen zwischen Downloads einbauen
