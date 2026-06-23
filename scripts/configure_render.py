"""Push production env vars to Render via API (optional — blueprint sync handles most)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API = "https://api.render.com/v1"
SERVICE_NAME = "solar-path"


def _request(method: str, path: str, body: dict | None = None) -> dict:
    key = os.environ.get("RENDER_API_KEY", "").strip()
    if not key:
        print("Set RENDER_API_KEY in .env (Render → Account Settings → API Keys)")
        sys.exit(1)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def find_service_id() -> str:
    cursor = ""
    while True:
        q = f"?limit=50&name={SERVICE_NAME}"
        if cursor:
            q += f"&cursor={cursor}"
        payload = _request("GET", f"/services{q}")
        for item in payload:
            svc = item.get("service") or item
            if svc.get("name") == SERVICE_NAME:
                return svc["id"]
        cursor = payload[-1].get("cursor") if payload else ""
        if not cursor:
            break
    print(f"Service '{SERVICE_NAME}' not found on Render")
    sys.exit(1)


def set_env(service_id: str, key: str, value: str) -> None:
    _request("PUT", f"/services/{service_id}/env-vars/{key}", {"value": value})
    print(f"  set {key}")


def main() -> None:
    sid = find_service_id()
    print(f"Configuring service {SERVICE_NAME} ({sid})")
    mapping = {
        "SUPPORT_EMAIL": os.environ.get("SUPPORT_EMAIL", ""),
        "SMTP_FROM": os.environ.get("SMTP_FROM", ""),
        "BETA_ACCESS_PASSWORD": os.environ.get("BETA_ACCESS_PASSWORD", ""),
        "BETA_INVITE_TOKENS": os.environ.get("BETA_INVITE_TOKENS", ""),
        "DATABASE_URL": os.environ.get("DATABASE_URL", ""),
    }
    for key, value in mapping.items():
        if value:
            set_env(sid, key, value)
    print("Done. Trigger redeploy from Render dashboard if env changed.")


if __name__ == "__main__":
    main()
