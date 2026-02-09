"""Ollama Vision client — sends screenshot + prompt to UI-TARS 1.5 7B."""

import json
import urllib.request
import urllib.error

MODEL = "0000/ui-tars-1.5-7b"
OLLAMA_URL = "http://localhost:11434"

SYSTEM_PROMPT = (
    "You are a GUI automation agent. You see a screenshot of a desktop. "
    "Based on the user's task, decide the next single action to perform.\n\n"
    "Respond in EXACTLY this format:\n"
    "Thought: <your reasoning>\n"
    "Action: <action>\n\n"
    "Available actions:\n"
    "- click(start_box='<|box_start|>(x,y)<|box_end|>')\n"
    "- left_double(start_box='<|box_start|>(x,y)<|box_end|>')\n"
    "- right_single(start_box='<|box_start|>(x,y)<|box_end|>')\n"
    "- type(content='text to type')\n"
    "- hotkey(key='ctrl+a')\n"
    "- scroll(start_box='<|box_start|>(x,y)<|box_end|>', direction='down', amount=3)\n"
    "- drag(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x2,y2)<|box_end|>')\n"
    "- wait(time=2)\n"
    "- finished(content='task completed')\n\n"
    "Coordinates are normalized to 0-1000 range for both x and y.\n"
    "Always output exactly ONE action per response."
)


def check_model_available() -> bool:
    """Check if the UI-TARS model is pulled in Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            names = [m["name"] for m in data.get("models", [])]
            return any(MODEL in n for n in names)
    except (urllib.error.URLError, OSError):
        return False


def check_ollama_running() -> bool:
    """Check if Ollama server is reachable."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def ask_vlm(screenshot_b64: str, task: str, history: list[dict] | None = None) -> str:
    """Send screenshot + task to UI-TARS via Ollama and return the response text.

    Args:
        screenshot_b64: Base64-encoded PNG screenshot.
        task: The task description / instruction for the agent.
        history: Optional list of previous messages for context.

    Returns:
        Raw text response from the model.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    messages.append({
        "role": "user",
        "content": task,
        "images": [screenshot_b64],
    })

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
        },
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
        return data["message"]["content"]
