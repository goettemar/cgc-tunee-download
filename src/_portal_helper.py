#!/usr/bin/env python3
"""Persistent screenshot helper — communicates via stdin/stdout.

Keeps the D-Bus connection alive between calls to avoid repeated
gi import and bus setup overhead. Runs with system python3 for gi access.

Protocol: read output path from stdin, take screenshot, write "OK" or "FAIL" to stdout.
"""

import os
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib  # noqa: E402


def take_screenshot(dest_path: str) -> bool:
    """Take a screenshot via XDG Portal, save to dest_path. Returns True on success."""
    result_uri = [None]
    loop = GLib.MainLoop()

    def on_response(conn, sender, path, iface, signal, params, _):
        response, results = params.unpack()
        if response == 0:
            result_uri[0] = results.get("uri", "")
        loop.quit()

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    sub_id = bus.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        None,
        None,
        Gio.DBusSignalFlags.NO_MATCH_RULE,
        on_response,
        None,
    )

    bus.call_sync(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Screenshot",
        "Screenshot",
        GLib.Variant(
            "(sa{sv})",
            (
                "",
                {
                    "interactive": GLib.Variant("b", False),
                },
            ),
        ),
        GLib.VariantType("(o)"),
        Gio.DBusCallFlags.NONE,
        5000,
        None,
    )

    GLib.timeout_add(5000, lambda: (loop.quit(), False)[1])
    loop.run()
    bus.signal_unsubscribe(sub_id)

    if result_uri[0] and result_uri[0].startswith("file://"):
        src = result_uri[0][7:]
        try:
            os.rename(src, dest_path)
        except OSError:
            import shutil

            shutil.move(src, dest_path)
        return True
    return False


def main():
    # Signal readiness
    sys.stdout.write("READY\n")
    sys.stdout.flush()

    for line in sys.stdin:
        dest_path = line.strip()
        if not dest_path or dest_path == "QUIT":
            break
        try:
            ok = take_screenshot(dest_path)
            sys.stdout.write("OK\n" if ok else "FAIL\n")
        except Exception as e:
            sys.stdout.write(f"FAIL:{e}\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
