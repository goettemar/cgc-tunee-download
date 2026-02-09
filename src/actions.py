"""Parse UI-TARS output and execute actions via PyAutoGUI."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import pyautogui

from .screenshot import get_screen_size

# Safety: don't move to (0,0) corner instantly
pyautogui.FAILSAFE = True
# Small pause between PyAutoGUI calls
pyautogui.PAUSE = 0.3


@dataclass
class ParsedAction:
    thought: str
    action_type: str
    params: dict


def _extract_coords(box_str: str) -> tuple[int, int]:
    """Extract (x, y) from '<|box_start|>(x,y)<|box_end|>' and convert to absolute pixels."""
    m = re.search(r"\((\d+)\s*,\s*(\d+)\)", box_str)
    if not m:
        raise ValueError(f"Cannot parse coordinates from: {box_str}")
    norm_x, norm_y = int(m.group(1)), int(m.group(2))
    sw, sh = get_screen_size()
    abs_x = round(sw * norm_x / 1000)
    abs_y = round(sh * norm_y / 1000)
    return abs_x, abs_y


def parse_response(text: str) -> ParsedAction:
    """Parse a UI-TARS response into a structured action.

    Expected format:
        Thought: <reasoning>
        Action: <action_call>
    """
    thought = ""
    action_line = ""

    for line in text.strip().splitlines():
        line = line.strip()
        if line.lower().startswith("thought:"):
            thought = line.split(":", 1)[1].strip()
        elif line.lower().startswith("action:"):
            action_line = line.split(":", 1)[1].strip()

    if not action_line:
        # Fallback: treat entire text as action if no prefix found
        action_line = text.strip().splitlines()[-1].strip()

    # Parse action call: name(params)
    m = re.match(r"(\w+)\((.*)\)$", action_line, re.DOTALL)
    if not m:
        return ParsedAction(thought=thought, action_type="unknown", params={"raw": action_line})

    action_type = m.group(1)
    params_str = m.group(2)

    params: dict = {}
    # Parse keyword arguments: key='value' or key="value" or key=number
    for km in re.finditer(r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|(\d+(?:\.\d+)?))", params_str):
        key = km.group(1)
        val = km.group(2) if km.group(2) is not None else km.group(3) if km.group(3) is not None else km.group(4)
        params[key] = val

    return ParsedAction(thought=thought, action_type=action_type, params=params)


def execute(action: ParsedAction) -> bool:
    """Execute a parsed action via PyAutoGUI. Returns True if the task is finished."""
    at = action.action_type

    if at == "finished":
        return True

    if at == "click":
        x, y = _extract_coords(action.params.get("start_box", ""))
        pyautogui.click(x, y)

    elif at == "left_double":
        x, y = _extract_coords(action.params.get("start_box", ""))
        pyautogui.doubleClick(x, y)

    elif at == "right_single":
        x, y = _extract_coords(action.params.get("start_box", ""))
        pyautogui.rightClick(x, y)

    elif at == "type":
        content = action.params.get("content", "")
        pyautogui.typewrite(content, interval=0.03) if content.isascii() else pyautogui.write(content)

    elif at == "hotkey":
        keys = action.params.get("key", "").split("+")
        pyautogui.hotkey(*[k.strip() for k in keys])

    elif at == "scroll":
        x, y = _extract_coords(action.params.get("start_box", "(500,500)"))
        direction = action.params.get("direction", "down")
        amount = int(action.params.get("amount", 3))
        clicks = amount if direction == "up" else -amount
        pyautogui.scroll(clicks, x=x, y=y)

    elif at == "drag":
        x1, y1 = _extract_coords(action.params.get("start_box", ""))
        x2, y2 = _extract_coords(action.params.get("end_box", ""))
        pyautogui.moveTo(x1, y1)
        pyautogui.drag(x2 - x1, y2 - y1, duration=0.5)

    elif at == "wait":
        secs = float(action.params.get("time", 2))
        time.sleep(secs)

    else:
        print(f"  [WARN] Unknown action type: {at}")

    return False
