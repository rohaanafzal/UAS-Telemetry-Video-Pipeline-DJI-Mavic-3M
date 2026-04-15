#!/usr/bin/env python3
"""
Jetson Script — Row Complete Receiver
Listens for UDP messages from Mac.
Saves each message with timestamp to a log file in ~/Rohaan-Testing-Signal/

Usage:
    python3 jetson_receiver.py
"""

import socket
from datetime import datetime
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
LISTEN_PORT = 7000
SAVE_FOLDER = Path.home() / "Rohaan-Testing-Signal"
# ──────────────────────────────────────────────────────────────────────────────


def main():
    SAVE_FOLDER.mkdir(parents=True, exist_ok=True)
    log_file = SAVE_FOLDER / f"log_{datetime.now().strftime('%Y%m%d')}.txt"

    print(f"Listening on UDP port {LISTEN_PORT}")
    print(f"Saving messages to: {log_file}")
    print("Press Ctrl+C to stop\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LISTEN_PORT))

    while True:
        data, addr = sock.recvfrom(4096)
        message = data.decode(errors="replace").strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] FROM {addr[0]} | {message}\n"

        print(log_entry.strip())

        with open(log_file, "a") as f:
            f.write(log_entry)


if __name__ == "__main__":
    main()
