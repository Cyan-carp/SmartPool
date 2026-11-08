"""触发演示剧本（经后端 /demo 接口，需要隧道已建立）。

用法：
    python deploy/scripts/trigger.py drown_still
    python deploy/scripts/trigger.py normal
    python deploy/scripts/trigger.py reset
    python deploy/scripts/trigger.py clock 5
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:18080"


def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    action = sys.argv[1]
    token = call("POST", "/api/v1/auth/login", {"username": "manager", "password": "demo1234"})["data"]["token"]

    if action == "reset":
        result = call("POST", "/api/v1/demo/reset", None, token)
    elif action == "clock":
        speed = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
        result = call("POST", "/api/v1/demo/clock", {"speed": speed}, token)
    else:
        result = call("POST", f"/api/v1/demo/scenarios/{action}", None, token)

    print(json.dumps(result.get("data"), ensure_ascii=False))
    return 0 if result.get("code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
