"""Parse UI-TARS output and execute actions via PyAutoGUI."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import pyautogui

from .screenshot import get_screen_size, get_image_size, get_monitor_offset

# Safety: don't move to (0,0) corner instantly
pyautogui.FAILSAFE = True
# Small pause between PyAutoGUI calls
pyautogui.PAUSE = 0.3


@dataclass
class ParsedAction:
    thought: str
    action_type: str
    params: dict
    raw: str  # original response text


def _extract_coords(box_str: str, img_size: tuple[int, int] | None = None) -> tuple[int, int]:
    """Extract (x, y) from '<|box_start|>(x,y)<|box_end|>' and scale to absolute desktop pixels.

    UI-TARS outputs coordinates in the pixel space of the image it processed.
    We scale from image coords → monitor coords, then add the monitor's
    offset in the virtual desktop so PyAutoGUI hits the right spot.
    """
    m = re.search(r"\((\d+)\s*,\s*(\d+)\)", box_str)
    if not m:
        raise ValueError(f"Cannot parse coordinates from: {box_str}")
    img_x, img_y = int(m.group(1)), int(m.group(2))
    sw, sh = get_screen_size()
    off_x, off_y = get_monitor_offset()

    if img_size:
        iw, ih = img_size
        mon_x = round(img_x * sw / iw)
        mon_y = round(img_y * sh / ih)
    else:
        mon_x, mon_y = img_x, img_y

    # Clamp to monitor bounds, then add monitor offset for absolute desktop coords
    mon_x = max(0, min(mon_x, sw - 1))
    mon_y = max(0, min(mon_y, sh - 1))
    return mon_x + off_x, mon_y + off_y


def parse_response(text: str) -> ParsedAction:
    """Parse a UI-TARS response into a structured action.

    Expected format:
        Thought: <reasoning>
        Action: <action_call>
    """
    thought = ""
    action_line = ""

    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("thought:"):
            thought = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("action:"):
            action_line = stripped.split(":", 1)[1].strip()

    if not action_line:
        # Fallback: search for any action pattern in the full text
        # Match known action names followed by parenthesized args
        actions_re = r"(click|left_double|right_single|type|hotkey|scroll|drag|wait|finished)\("
        m_fb = re.search(actions_re, text)
        if m_fb:
            # Extract from the action name to the matching closing paren
            start = m_fb.start()
            action_line = text[start:]
            # Find the outermost closing paren
            depth = 0
            for i, ch in enumerate(action_line):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        action_line = action_line[:i + 1]
                        break
        else:
            action_line = text.strip().splitlines()[-1].strip()

    # Strip trailing suffixes like "#2", "# step 3", etc.
    action_line = re.sub(r"#\d+\s*$", "", action_line).strip()

    # Parse action call: name(params) — allow trailing junk after closing paren
    m = re.match(r"(\w+)\((.*)\)", action_line, re.DOTALL)
    if not m:
        return ParsedAction(thought=thought, action_type="unknown", params={"raw": action_line}, raw=text)

    action_type = m.group(1)
    params_str = m.group(2)

    params: dict = {}
    # Parse keyword arguments: key='value' or key="value" or key=number
    for km in re.finditer(r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|(\d+(?:\.\d+)?))", params_str):
        key = km.group(1)
        val = km.group(2) if km.group(2) is not None else km.group(3) if km.group(3) is not None else km.group(4)
        params[key] = val

    return ParsedAction(thought=thought, action_type=action_type, params=params, raw=text)


def execute(action: ParsedAction, img_size: tuple[int, int] | None = None) -> bool:
    """Execute a parsed action via PyAutoGUI. Returns True if the task is finished."""
    at = action.action_type

    if at == "finished":
        return True

    if at == "click":
        x, y = _extract_coords(action.params.get("start_box", ""), img_size)
        pyautogui.click(x, y)

    elif at == "left_double":
        x, y = _extract_coords(action.params.get("start_box", ""), img_size)
        pyautogui.doubleClick(x, y)

    elif at == "right_single":
        x, y = _extract_coords(action.params.get("start_box", ""), img_size)
        pyautogui.rightClick(x, y)

    elif at == "type":
        content = action.params.get("content", "")
        pyautogui.typewrite(content, interval=0.03) if content.isascii() else pyautogui.write(content)

    elif at == "hotkey":
        keys = action.params.get("key", "").split("+")
        pyautogui.hotkey(*[k.strip() for k in keys])

    elif at == "scroll":
        box = action.params.get("start_box")
        direction = action.params.get("direction", "down")
        amount = int(action.params.get("amount", 3))
        clicks = amount if direction == "up" else -amount
        if box:
            x, y = _extract_coords(box, img_size)
            pyautogui.scroll(clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)

    elif at == "drag":
        x1, y1 = _extract_coords(action.params.get("start_box", ""), img_size)
        x2, y2 = _extract_coords(action.params.get("end_box", ""), img_size)
        pyautogui.moveTo(x1, y1)
        pyautogui.drag(x2 - x1, y2 - y1, duration=0.5)

    elif at == "wait":
        secs = float(action.params.get("time", 2))
        time.sleep(secs)

    else:
        print(f"  [WARN] Unknown action type: {at}")

    return False
