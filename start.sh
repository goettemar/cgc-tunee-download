#!/bin/bash
#
# CGC Tunee Download — Launcher
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Eltern-venv deaktivieren falls vorhanden (CGC Launcher Kompatibilitaet)
deactivate 2>/dev/null || true
unset VIRTUAL_ENV PYTHONHOME

VENV_DIR=".venv"

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║   CGC Tunee Download                                  ║"
echo "║   Template-Matching + PySide6 GUI                     ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Virtual Environment erstellen falls nicht vorhanden
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Erstelle Virtual Environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Aktivieren
source "$VENV_DIR/bin/activate"

# Abhängigkeiten prüfen/installieren
MARKER="$VENV_DIR/.gui_installed"
if [ ! -f "$MARKER" ] || [ requirements.txt -nt "$MARKER" ]; then
    echo -e "${YELLOW}Installiere Abhängigkeiten...${NC}"
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    touch "$MARKER"
    echo -e "${GREEN}Installation abgeschlossen.${NC}"
fi

# Verzeichnisse erstellen
mkdir -p data downloads

# ffprobe prüfen (benötigt für Dauer-Erkennung)
if ! command -v ffprobe &>/dev/null; then
    echo -e "${YELLOW}ffprobe fehlt (benötigt für Dauer-Erkennung)${NC}"
    if command -v apt-get &>/dev/null; then
        echo -e "${YELLOW}Installiere ffmpeg...${NC}"
        sudo apt-get install -y ffmpeg -qq
    else
        echo -e "${RED}Bitte manuell installieren: sudo apt-get install ffmpeg${NC}"
        echo -e "${RED}Ohne ffprobe werden alle Songs als 00m00s erkannt → falsche Duplikate!${NC}"
    fi
fi

# tkinter prüfen (benötigt für PyAutoGUI)
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo -e "${YELLOW}python3-tk fehlt (benötigt für PyAutoGUI)${NC}"
    if command -v apt-get &>/dev/null; then
        echo -e "${YELLOW}Installiere python3-tk...${NC}"
        sudo apt-get install -y python3-tk -qq
        # venv neu erstellen damit tkinter verfügbar wird
        echo -e "${YELLOW}Erstelle Virtual Environment neu (tkinter-Support)...${NC}"
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip -q
        pip install -r requirements.txt -q
        touch "$MARKER"
    else
        echo -e "${RED}Bitte manuell installieren: sudo apt-get install python3-tk${NC}"
    fi
fi

# XWayland xauth-Fix
if [ "$XDG_SESSION_TYPE" = "wayland" ] && [ -n "$XAUTHORITY" ] && [ -n "$DISPLAY" ]; then
    COOKIE=$(xauth -f "$XAUTHORITY" list 2>/dev/null | head -1 | awk '{print $3}')
    if [ -n "$COOKIE" ]; then
        if ! xauth list 2>/dev/null | grep -q "unix${DISPLAY}"; then
            xauth add "$DISPLAY" MIT-MAGIC-COOKIE-1 "$COOKIE" 2>/dev/null
            echo -e "${YELLOW}XWayland xauth-Fix angewendet (Display ${DISPLAY})${NC}"
        fi
    fi
fi

# App starten (GUI per default, --cli für CLI-Modus)
echo ""
echo -e "${GREEN}Starte CGC Tunee Download...${NC}"
"$VENV_DIR/bin/python" main.py "$@"
