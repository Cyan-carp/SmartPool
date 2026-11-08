"""验证降级/恢复状态：读取 /live/snapshot 的 degraded 与 dataDelayMs。

用法：
    python deploy/scripts/check_degrade.py degraded    # 期望降级
    python deploy/scripts/check_degrade.py ok          # 期望正常
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:18080"
EXPECT = sys.argv[1] if len(sys.argv) > 1 else "ok"


def call(path: str, body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method="POST" if body is not None else "GET")
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    token = call("/api/v1/auth/login", {"username": "manager", "password": "demo1234"})["data"]["token"]
    data = call("/api/v1/live/snapshot?poolId=1", token=token)["data"]
    degraded = bool(data.get("degraded"))
    delay = int(data.get("dataDelayMs") or 0)
    failed = int(data.get("failedFrames") or 0)
    print(f"degraded={degraded} dataDelayMs={delay} failedFrames={failed} pushed={data.get('pushedFrames')}")

    if EXPECT == "degraded" and not degraded:
        print("结果：未通过（期望降级，实际正常）")
        return 1
    if EXPECT == "ok" and degraded:
        print("结果：未通过（期望恢复，实际仍降级）")
        return 1
    print(f"结果：通过（{EXPECT}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
