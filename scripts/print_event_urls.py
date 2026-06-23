"""Print URLs for event-day testing on local WiFi."""

from __future__ import annotations

import os
import socket

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main() -> None:
    port = os.environ.get("PORT", "5000")
    ip = local_ip()
    base = f"http://{ip}:{port}"
    invite = (os.environ.get("BETA_INVITE_TOKENS") or "").split(",")[0].strip()
    password = os.environ.get("BETA_ACCESS_PASSWORD", "")

    print()
    print("=" * 50)
    print("  Solar Path — EVENT MODE")
    print("=" * 50)
    print()
    print(f"  Same WiFi (share QR or type on phones):")
    print(f"    {base}/")
    if invite:
        print(f"    {base}/?invite={invite}")
    print()
    print(f"  Calculator (main demo flow):")
    print(f"    {base}/calculator")
    print()
    if password:
        print(f"  Beta password (if invite link not used): {password}")
    else:
        print("  Beta gate: OFF (no BETA_ACCESS_PASSWORD set)")
    print()
    print("  Tips:")
    print("  - Laptop plugged in, stay on same WiFi as guests")
    print("  - Allow Python through Windows Firewall if phones cannot connect")
    print("  - Press Ctrl+C in this window to stop the server")
    print()


if __name__ == "__main__":
    main()
