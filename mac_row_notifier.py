#!/usr/bin/env python3
"""
Mac Script — OBS Row Complete Notifier
Watches OBS recordings folder. When a new .mkv or .mp4 appears (OBS stopped recording),
sends "Row Complete" UDP message to Jetson.

Usage:
    python3 mac_row_notifier.py
"""

import os
import socket
import time
from datetime import datetime
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
OBS_FOLDER = Path("/Users/Mac/Movies")
#Rs2 IP 
JETSON_IP = "192.169.43.107"
JETSON_PORT = 7000
CHECK_INTERVAL = 2  # seconds
# ──────────────────────────────────────────────────────────────────────────────


def get_current_files(folder: Path):
    return {
        f for f in folder.iterdir()
        if f.suffix.lower() in (".mp4", ".mkv", ".mov", ".flv")
    }


def send_to_jetson(message: str):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (JETSON_IP, JETSON_PORT))
        sock.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent to Jetson: {message}")
    except Exception as e:
        print(f"[ERROR] Could not send to Jetson: {e}")


def main():
    print(f"Watching OBS folder: {OBS_FOLDER}")
    print(f"Will notify Jetson at {JETSON_IP}:{JETSON_PORT}")
    print("Press Ctrl+C to stop\n")

    known_files = get_current_files(OBS_FOLDER)
    row_count = 0

    while True:
        time.sleep(CHECK_INTERVAL)
        current_files = get_current_files(OBS_FOLDER)
        new_files = current_files - known_files

        for new_file in new_files:
            row_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"Row Complete | Row: {row_count} | File: {new_file.name} | Time: {timestamp}"
            print(f"[{timestamp}] New recording detected: {new_file.name}")
            send_to_jetson(message)

        known_files = current_files


if __name__ == "__main__":
    main()
