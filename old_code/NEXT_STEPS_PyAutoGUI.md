# PyAutoGUI Implementation Plan

## Warum PyAutoGUI?
Tunee.ai macht native HTML-Downloads zu schwer:
- Buttons sind nur bei Hover sichtbar (CSS opacity)
- Playwright kann sie nicht zuverlässig finden/klicken
- PyAutoGUI umgeht das Problem komplett durch **Bilderkennung**

## Setup

```bash
pip install pyautogui pillow opencv-python
```

## Implementierungs-Schritte

### 1. Template-Screenshots erstellen
Einmalig: Screenshots von den Buttons machen

**Benötigte Templates:**
- `templates/download_button_hover.png` - Download-Button wenn Song gehovered ist
- `templates/modal_mp3_button.png` - MP3 Button im Modal
- `templates/modal_raw_button.png` - RAW Button im Modal
- `templates/modal_video_button.png` - VIDEO Button im Modal
- `templates/modal_lrc_button.png` - LRC Button im Modal
- `templates/lyric_video_download.png` - Download im Lyric Video Modal

### 2. Basis-Workflow

```python
import pyautogui
import time

def download_song_by_visual(song_name: str):
    """Download Song mit PyAutoGUI (bildbasiert)"""

    # 1. Suche Song in Liste (per Text-OCR oder manuelles Scrollen)
    #    Alternativ: Playwright findet Song, PyAutoGUI klickt

    # 2. Bewege Maus über Song (Hover aktivieren)
    pyautogui.moveTo(x, y)  # Song-Position
    time.sleep(1.5)  # Warte auf Hover-Animation

    # 3. Finde Download-Button per Bilderkennung
    button_loc = pyautogui.locateOnScreen('templates/download_button_hover.png',
                                          confidence=0.8)
    if button_loc:
        pyautogui.click(button_loc)
        time.sleep(1.5)

    # 4. Modal sollte offen sein - klicke Buttons
    for template in ['modal_mp3_button.png', 'modal_raw_button.png', ...]:
        btn = pyautogui.locateOnScreen(f'templates/{template}', confidence=0.8)
        if btn:
            pyautogui.click(btn)
            time.sleep(2)  # Warte auf Download
```

### 3. Hybrid-Ansatz (Empfohlen)

**Playwright für Navigation + PyAutoGUI für Klicks**

```python
class HybridBrowser:
    def __init__(self, page):
        self.page = page

    async def download_song(self, song_name, duration):
        # 1. Playwright: Finde Song-Position
        pos = await self.page.evaluate('''() => {
            // Finde Duration-Element
            const el = document.querySelector('text="02:54"');
            const rect = el.getBoundingClientRect();
            return {x: rect.left, y: rect.top};
        }''')

        # 2. PyAutoGUI: Hover über Song
        pyautogui.moveTo(pos['x'], pos['y'])
        time.sleep(1.5)

        # 3. PyAutoGUI: Klicke Download-Button (per Bilderkennung)
        button = pyautogui.locateOnScreen('templates/download_button.png')
        pyautogui.click(button)

        # 4. PyAutoGUI: Klicke Modal-Buttons
        # ...
```

## Vorteile dieses Ansatzes

✅ **Robust:** Funktioniert auch wenn HTML sich ändert
✅ **Einfach:** Keine komplexe Button-Suche
✅ **Zuverlässig:** Sieht was ein Mensch sieht
✅ **Hover funktioniert:** Echte Mausbewegung

## Alternative: Lokales LLM mit Vision

Falls PyAutoGUI nicht funktioniert:

```python
# Ollama mit Llama 3.2 Vision oder Qwen2-VL
def find_button_with_llm(screenshot_path):
    response = ollama.chat(
        model='llama3.2-vision',
        messages=[{
            'role': 'user',
            'content': 'Where is the download button? Return x,y coordinates.',
            'images': [screenshot_path]
        }]
    )
    return parse_coordinates(response)
```

## Nächste Schritte:

1. [x] PyAutoGUI installieren ✅
2. [x] Hybrid-Ansatz implementieren (Playwright + PyAutoGUI) ✅
3. [ ] Template-Screenshots erstellen (Download-Button, Modal-Buttons) **← DU BIST HIER**
4. [ ] Testen mit erstem Song
5. [ ] Bei Erfolg: Alle 50 Songs durchlaufen

## Implementierungs-Status

### ✅ Fertig:
- PyAutoGUI + Dependencies installiert (pillow, opencv-python)
- `src/browser_hybrid.py` - Hybrid-Browser-Klasse implementiert
- `create_templates.py` - Interaktiver Template-Creator
- `test_hybrid_browser.py` - Test-Suite für Hybrid-Download
- `templates/README.md` - Dokumentation für Templates

### 📋 TODO:
1. **Templates erstellen:**
   ```bash
   python create_templates.py
   ```

2. **Templates testen:**
   ```bash
   python test_hybrid_browser.py
   ```

3. **GUI integrieren:**
   - `src/core/song_worker.py` erweitern um Hybrid-Option
   - UI-Switch: "Playwright" vs "Hybrid (PyAutoGUI)"

## Fallback-Plan:

Falls PyAutoGUI auch nicht klappt:
- API Reverse Engineering (Network-Tab analysieren)
- Claude API Computer Use (teuer, aber funktioniert garantiert)
