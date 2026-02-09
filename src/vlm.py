"""Ollama Vision client — sends screenshot + prompt to UI-TARS 1.5 7B."""

import json
import urllib.request
import urllib.error

MODEL = "ui-tars-gui"
OLLAMA_URL = "http://localhost:11434"


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


def ask_vlm(screenshot_b64: str, task: str, action_history: list[str] | None = None) -> str:
    """Send screenshot + task to UI-TARS via Ollama /api/generate endpoint.

    The Ollama model has TEMPLATE={{ .Prompt }} and a built-in SYSTEM message,
    so we use the raw generate API instead of chat to avoid double-wrapping.

    Args:
        screenshot_b64: Base64-encoded PNG screenshot.
        task: The task description / instruction for the agent.
        action_history: Optional list of previous Thought+Action strings.

    Returns:
        Raw text response from the model.
    """
    prompt = f"Task: {task}"
    if action_history:
        prompt += "\n\nAction History:\n" + "\n".join(action_history)

    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "images": [screenshot_b64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 256,
        },
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
        return data["response"]
