# Quick Start - Tunee Download Manager mit PyAutoGUI 🚀

## Installation (einmalig)

```bash
cd /mnt/llm-data/projekte/cgc_tunee_download
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Starten

```bash
cd /mnt/llm-data/projekte/cgc_tunee_download
source .venv/bin/activate
python main.py
```

Oder mit dem Script:
```bash
./main.py
```

## Workflow

### 1. GUI öffnet sich

- **Tab "Song Download"**: Hier werden Songs heruntergeladen
- **Tab "Certificates"**: Hier werden Zertifikate verwaltet

### 2. Vorbereitung

1. **Browser-Position:** Der Browser öffnet sich automatisch
2. **Einloggen:** Bei erstem Start mit Google einloggen
3. **Navigation:** Zur gewünschten Conversation navigieren (falls nicht automatisch)
4. **Song-Liste:** Stelle sicher dass die Song-Liste links sichtbar ist
5. **"All Music"** klicken falls nötig

### 3. Download starten

1. **URL eingeben** (optional - wird automatisch erkannt)
2. **"Download starten"** klicken
3. **Warten:** Dialog "Vorbereitung" erscheint
4. **"Weiter"** klicken wenn Song-Liste sichtbar ist

### 4. Automatischer Download läuft

Die App macht jetzt automatisch:

✅ **Song-Erkennung:** Findet alle Songs in der Liste (scrollt automatisch)
✅ **Download per Song:**
   - Scrollt Song in View
   - Findet Download-Button (PyAutoGUI - bildbasiert)
   - Klickt Download-Button → Modal öffnet
   - Klickt MP3, RAW, LRC, VIDEO Downloads
   - Klickt Lyric Video Download
   - 5 Dateien heruntergeladen! 🎵

### 5. Fortschritt beobachten

- **Progress Bar:** Zeigt Fortschritt (z.B. "Song 5 von 23")
- **Log:** Zeigt Details für jeden Song
- **Status:** Grüne ✅ = Erfolg, Rote ❌ = Fehler

### 6. Fertig!

Alle Downloads sind in:
```
~/Downloads/tunee/SongName_MM-SS/
```

Jeder Song-Ordner enthält:
- `SongName.mp3` - Audio
- `SongName.flac` - Lossless Audio
- `SongName.lrc` - Lyrics mit Timestamps
- `SongName.mp4` - Lyric Video (2x: mit und ohne Lyrics)

## Fehlerbehandlung

### Templates nicht gefunden

**Problem:** "⚠️ Template nicht gefunden: templates/download_button.png"

**Lösung:**
```bash
cd /mnt/llm-data/projekte/cgc_tunee_download
ls -la templates/
# Sollte 6 PNG-Files zeigen
```

Falls Templates fehlen → mit Flameshot neu erstellen (siehe README.md)

### PyAutoGUI findet Buttons nicht

**Problem:** "❌ Download-Button nicht gefunden"

**Mögliche Ursachen:**
1. **Browser auf falschem Monitor** → Browser auf rechten Monitor verschieben
2. **Browser-Zoom nicht 100%** → Ctrl+0 drücken
3. **Templates passen nicht** → Neue Templates erstellen

**Debug:**
```bash
python test_click.py  # Testet nur einen Song
```

### Songs werden nicht erkannt

**Problem:** "0 Songs gefunden"

**Lösung:**
1. Stelle sicher dass "All Music" sichtbar ist
2. Klicke auf "All Music" im Browser
3. Scrolle NICHT - bleibe oben in der Liste
4. Klicke "Weiter" in der GUI

### Download hängt

**Problem:** Download bleibt bei einem Song hängen

**Notfall-Stop:**
- Maus in **obere linke Ecke** bewegen → PyAutoGUI stoppt (FAILSAFE)
- Oder "Stopp" Button in GUI klicken

## Multi-Monitor Setup

Die Templates wurden auf dem **rechten Monitor** erstellt (3-Monitor Setup).

**Wichtig:**
- Browser muss auf dem **gleichen Monitor** sein wie bei Template-Erstellung
- Oder: Neue Templates auf dem aktuellen Monitor erstellen

## Bekannte Limitationen

- ⚠️ Browser-Zoom muss 100% sein
- ⚠️ Browser-Position muss stimmen (gleicher Monitor wie Templates)
- ⚠️ Während Download läuft: Maus NICHT bewegen (oder nur minimal)
- ⚠️ Fenster nicht überlagern (Browser muss sichtbar sein)

## Tipps & Tricks

### Schneller Download

Die App downloaded bereits parallel:
- Während ein Song processed wird, lädt der nächste im Hintergrund

### Unterbrochene Downloads fortsetzen

Die App prüft automatisch ob Dateien schon existieren.
→ Einfach "Download starten" nochmal klicken, bereits gedownloadete Songs werden übersprungen

### Nur bestimmte Songs downloaden

Aktuell: Alle Songs in der Conversation werden heruntergeladen.
→ Feature-Request: Song-Auswahl vor Download?

## Support

Bei Problemen:
1. **Log-Output prüfen** in der GUI
2. **test_click.py laufen lassen** für Debug
3. **Screenshots checken** ob Templates noch passen
4. **Issue erstellen** mit Log-Output

## Erfolgs-Check ✅

Nach erfolgreichem Download solltest du sehen:

```
[Song 1/23] Song Name
    1️⃣ Suche Song in Liste...
    2️⃣ Scrolle Song in View...
    3️⃣ Suche Download-Button...
    ✅ Download-Button gefunden bei x=1234, y=567
    4️⃣ Klicke Download-Button...
    5️⃣ Suche Modal-Buttons...
    ✅ Modal geöffnet (MP3 bei x=890, y=456)
    6️⃣ Klicke Downloads...
       → MP3...
       → RAW...
       → LRC...
       → VIDEO...
    7️⃣ Warte auf Lyric Video Modal...
    ✅ Lyric Video Download gefunden
       → Klicke VIDEO Download...
    ✅ VIDEO Download gestartet
    ✅ Alle Downloads erfolgreich!
```

🎉 **Happy Downloading!**
