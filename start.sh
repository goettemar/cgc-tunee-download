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
