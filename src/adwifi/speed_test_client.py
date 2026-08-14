from typing import Any

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib # type: ignore

import json
import subprocess


class SpeedTestError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(message)

async def process_line(line: str) -> dict | None:
    data = json.loads(line)
    type = data.get('type')

    if type == "ping":
        ping = data["ping"]["latency"]
        return {"ping": ping}

    elif type == "download":
        download = data["download"]["bandwidth"] * 8 / 1000000
        return {"download": download}

    elif type == "upload":
        upload = data["upload"]["bandwidth"] * 8 / 1000000
        return {"upload": upload}

    elif type == "result":
        ping = data["ping"]["latency"]
        download = data["download"]["bandwidth"] * 8 / 1000000
        upload = data["upload"]["bandwidth"] * 8 / 1000000
        return {"ping": ping, "download": download, "upload": upload}

    return None

async def run_speed_test(end_callback, update_callback) -> None:    
    try:

        process = subprocess.Popen(
            ["speedtest", "--format=jsonl"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # read line by line
        assert process.stdout is not None
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if not line: continue

            try:
                result = await process_line(line)

                if result is not None:
                    GLib.idle_add(update_callback, result)

            except json.JSONDecodeError:
                continue

        GLib.idle_add(end_callback)

        process.stdout.close()
        process.wait()

    except Exception:
        raise SpeedTestError("Failed to query connection data")