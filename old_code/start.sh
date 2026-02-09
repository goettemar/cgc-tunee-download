#!/bin/bash
#
# CGC Tunee Download - Start Script
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║   CGC Tunee Download Manager                          ║"
echo "║                                                       ║"
echo "║   GUI: ./start.sh                                     ║"
echo "║   CLI: ./start.sh --cli [URL]                         ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Virtual Environment erstellen falls nicht vorhanden
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Erstelle Virtual Environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Aktivieren (nur für pip install, nicht für exec)
source "$VENV_DIR/bin/activate"

# Abhängigkeiten prüfen/installieren
if [ ! -f "$VENV_DIR/.installed" ]; then
    echo -e "${YELLOW}Installiere Abhängigkeiten...${NC}"
    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    # Playwright Browser installieren
    echo -e "${YELLOW}Installiere Playwright Browser...${NC}"
    playwright install chromium

    touch "$VENV_DIR/.installed"
    echo -e "${GREEN}Installation abgeschlossen.${NC}"
fi

# Verzeichnisse erstellen
mkdir -p cookies downloads

# tkinter prüfen (benötigt für PyAutoGUI/mouseinfo)
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
        playwright install chromium
        touch "$VENV_DIR/.installed"
    else
        echo -e "${RED}Bitte manuell installieren: sudo apt-get install python3-tk${NC}"
    fi
fi

# XWayland xauth-Fix: python-xlib findet den Cookie nicht wenn das
# Display-Feld in der Xauthority leer ist (typisch bei Wayland/Mutter).
# Wir kopieren den Cookie mit explizitem Display-Nummer :0.
if [ "$XDG_SESSION_TYPE" = "wayland" ] && [ -n "$XAUTHORITY" ] && [ -n "$DISPLAY" ]; then
    COOKIE=$(xauth -f "$XAUTHORITY" list 2>/dev/null | head -1 | awk '{print $3}')
    if [ -n "$COOKIE" ]; then
        # Prüfen ob der Eintrag mit Display-Nummer schon existiert
        if ! xauth list 2>/dev/null | grep -q "unix${DISPLAY}"; then
            xauth add "$DISPLAY" MIT-MAGIC-COOKIE-1 "$COOKIE" 2>/dev/null
            echo -e "${YELLOW}XWayland xauth-Fix angewendet (Display ${DISPLAY})${NC}"
        fi
    fi
fi

# App starten (expliziter Pfad zum venv-Python verhindert Konflikte mit cgc_launcher)
echo ""

# CLI-Modus?
if [ "$1" = "--cli" ]; then
    shift
    echo -e "${GREEN}Starte im CLI-Modus...${NC}"
    exec "$VENV_DIR/bin/python" main_cli.py "$@"
else
    echo -e "${GREEN}Starte GUI...${NC}"
    exec "$VENV_DIR/bin/python" main.py "$@"
fi
