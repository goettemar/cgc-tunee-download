# Template Screenshots

Dieses Verzeichnis enthält Template-Screenshots für bildbasierte Automation mit PyAutoGUI.

## Benötigte Templates

### Download-Workflow

1. **download_button.png** - Download-Button in der Song-Liste (bei Hover sichtbar)
   - Icon neben dem Stern-Icon
   - Erscheint nur wenn Song gehovered ist
   - Screenshot: Nur das Icon (klein, ~20x20px)

2. **modal_mp3.png** - MP3 Button im Download-Modal
   - Text "MP3" + Icon
   - Erster Button im Modal (dient als Positionsanker für alle anderen Buttons)
   - Screenshot: Der komplette Button

3. **lyric_video_download.png** - Download-Button im Lyric Video Modal
   - Öffnet sich nach Klick auf VIDEO-Button
   - Download-Button oben rechts im Modal
   - Screenshot: Der komplette Button

### Nicht mehr benötigt (position-basiert über MP3-Anker)

Die folgenden Templates sind **optional** - RAW, VIDEO und LRC werden über
Position-Offsets relativ zur MP3-Position geklickt:
- MP3 (+0px), RAW (+100px), VIDEO (+200px), LRC (+300px)
- `modal_raw.png`, `modal_video.png`, `modal_lrc.png` werden nicht mehr gesucht

## Screenshots erstellen

### Vorbereitung:
1. Tunee.ai Conversation mit Songs öffnen
2. Browser auf ~1920x1080 stellen (Standard-Größe)
3. Zoom auf 100%

### Methode 1: Manuell (Screenshots Tool)
```bash
# Linux: Screenshot Tool mit Auswahl
gnome-screenshot -a

# Oder: Flameshot (besser)
flameshot gui
```

1. Hover über Song → Download-Button erscheint
2. Screenshot vom Button → `download_button.png`
3. Klick auf Download-Button → Modal öffnet
4. Screenshot vom MP3-Button → `modal_mp3.png`
5. Klick auf VIDEO → Lyric Video Modal
6. Screenshot vom Download-Button → `lyric_video_download.png`

### Methode 2: Mit Helper-Script
```bash
python create_templates.py
```

Das Script öffnet Tunee, zeigt wo geklickt werden soll, und erstellt automatisch Screenshots.

## Multi-Song-Workflow

Der neue Workflow findet jeden Song per **Name + Duration** (nicht nur Duration):
1. Song-Liste wird per JS-Evaluate durchsucht (exakter Name-Match)
2. Liste scrollt automatisch bis der Song im Viewport sichtbar ist
3. PyAutoGUI bewegt die echte Maus zum Song (triggert CSS :hover)
4. Template-Matching findet den Download-Button
5. Nach jedem Song: Modals schließen, Maus wegbewegen, Liste zurückscrollen

## Template-Qualität

**Wichtig für gutes Matching:**
- Scharfe Screenshots (kein Blur)
- Nur der Button (nicht zu viel Hintergrund)
- Normal-State (nicht pressed/active)
- 100% Zoom im Browser
- Keine Schatten/Highlights wenn möglich

## Testen

```python
import pyautogui

# Template finden
location = pyautogui.locateOnScreen('templates/download_button.png', confidence=0.8)
if location:
    print(f"Gefunden bei: {location}")
    pyautogui.click(location)
```

## Troubleshooting

**Template nicht gefunden:**
- Confidence senken (0.7 statt 0.8)
- Screenshot neu erstellen (bessere Qualität)
- Browser-Zoom prüfen (muss 100% sein)
- Screen-Resolution prüfen (sollte gleich sein)

**Falsche Position geklickt:**
- Template zu groß → mehr Hintergrund croppen
- Template zu klein → etwas mehr Kontext einbeziehen
