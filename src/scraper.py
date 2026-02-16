"""Scrape song list from tunee.ai via Chrome DevTools Protocol.

Connects to Chrome's debugging port and executes JavaScript to extract
all song names and durations from the currently open project page.
"""

from __future__ import annotations

import json

import requests
import websocket

CDP_URL = "http://127.0.0.1:9222"

# JavaScript to extract ALL songs from the tunee.ai DOM in page order.
# All song elements exist in the DOM at once (no lazy loading).
_JS_GET_ALL_SONGS = r"""
var results = [];
var timeRegex = /^\d{2}:\d{2}$/;
var all = document.querySelectorAll('*');
for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var t = el.textContent ? el.textContent.trim() : '';
    if (t && timeRegex.test(t) && el.childNodes.length === 1) {
        var rect = el.getBoundingClientRect();
        if (rect.left > 400) continue;

        var duration = t;
        var container = el.parentElement;

        for (var j = 0; j < 4 && container; j++) {
            var cRect = container.getBoundingClientRect();
            if (cRect.height > 40 && cRect.height < 150) {
                var textNodes = container.querySelectorAll('span, div, p, a');
                for (var k = 0; k < textNodes.length; k++) {
                    var node = textNodes[k];
                    var nodeText = node.textContent ? node.textContent.trim() : '';
                    if (nodeText &&
                        nodeText.length > 2 &&
                        nodeText.length < 80 &&
                        !timeRegex.test(nodeText) &&
                        ['All Music', 'Favorites', 'All', 'Share', 'Home'].indexOf(nodeText) === -1 &&
                        nodeText.indexOf('\n') === -1 &&
                        node.childNodes.length <= 2) {
                        results.push({ name: nodeText, duration: duration, y: rect.top });
                        break;
                    }
                }
                break;
            }
            container = container.parentElement;
        }
    }
}
results;
"""


def _get_ws_url() -> str:
    """Get the WebSocket debugger URL of the first Chrome tab."""
    r = requests.get(f"{CDP_URL}/json", timeout=5)
    r.raise_for_status()
    tabs = r.json()
    for tab in tabs:
        if tab.get("type") == "page" and "tunee" in tab.get("url", "").lower():
            return tab["webSocketDebuggerUrl"]
    for tab in tabs:
        if tab.get("type") == "page":
            return tab["webSocketDebuggerUrl"]
    raise ConnectionError("Keine Chrome-Tabs gefunden")


def _cdp_evaluate(ws: websocket.WebSocket, expression: str, msg_id: int):
    """Execute JavaScript via CDP Runtime.evaluate and return the result."""
    ws.send(
        json.dumps(
            {
                "id": msg_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expression,
                    "returnByValue": True,
                },
            }
        )
    )
    while True:
        resp = json.loads(ws.recv())
        if resp.get("id") == msg_id:
            if "error" in resp:
                raise RuntimeError(resp["error"].get("message", str(resp["error"])))
            result = resp.get("result", {}).get("result", {})
            return result.get("value")


def get_song_list() -> list[dict]:
    """Scrape all songs from the tunee.ai project page.

    Returns list of {"name": str, "duration": str} dicts in page order.
    Requires Chrome to be running with --remote-debugging-port=9222.
    """
    ws_url = _get_ws_url()
    ws = websocket.create_connection(ws_url, timeout=10)

    try:
        songs = _cdp_evaluate(ws, _JS_GET_ALL_SONGS, 1) or []
        # Sort by Y position (page order) and strip the y field
        songs.sort(key=lambda s: s.get("y", 0))
        return [{"name": s["name"], "duration": s["duration"]} for s in songs]
    finally:
        ws.close()
