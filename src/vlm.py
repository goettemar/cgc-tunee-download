"""Ollama Vision client — sends screenshot + prompt to UI-TARS 1.5 7B."""

import json
import urllib.request
import urllib.error

MODEL = "0000/ui-tars-1.5-7b"
OLLAMA_URL = "http://localhost:11434"

# Native UI-TARS system prompt — do NOT override with custom instructions,
# the model was trained with this exact prompt.
SYSTEM_PROMPT = (
    "You are a GUI agent. You are given a task and your action history, "
    "with screenshots. You need to perform the next action to complete the task."
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


def ask_vlm(screenshot_b64: str, task: str, action_history: list[str] | None = None) -> str:
    """Send screenshot + task to UI-TARS via Ollama and return the response text.

    Args:
        screenshot_b64: Base64-encoded PNG screenshot.
        task: The task description / instruction for the agent.
        action_history: Optional list of previous Thought+Action strings.

    Returns:
        Raw text response from the model.
    """
    # Build user content in UI-TARS native format
    user_content = f"Task: {task}"
    if action_history:
        user_content += "\n\nAction History:\n" + "\n".join(action_history)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": user_content,
            "images": [screenshot_b64],
        },
    ]

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
