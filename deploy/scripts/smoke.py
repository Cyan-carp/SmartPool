"""M1 冒烟测试：登录 -> 实时快照 -> 关键接口。

用法：
    python deploy/scripts/smoke.py [base_url]

默认 base_url = http://127.0.0.1:18080（需要先起 SSH 隧道）。
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:18080"


def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    failures: list[str] = []

    health = call("GET", "/api/health")
    print(f"[1] health        -> code={health['code']} provider={health['data']['detectorProvider']} modelLoaded={health['data']['modelLoaded']}")
    if health.get("code") != 0 or health["data"].get("modelLoaded"):
        failures.append("health 接口返回异常或模型状态不是占位")

    login = call("POST", "/api/v1/auth/login", {"username": "manager", "password": "demo1234"})
    token = login["data"]["token"]
    user = login["data"]["user"]
    print(f"[2] login         -> user={user['username']} role={user['role']} menus={len(user['menus'])}")
    if not token:
        failures.append("登录未返回 token")

    me = call("GET", "/api/v1/auth/me", token=token)
    print(f"[3] auth/me       -> {me['data']['displayName']}")

    pools = call("GET", "/api/v1/pools", token=token)
    print(f"[4] pools         -> {len(pools['data'])} 个：{pools['data'][0]['name'] if pools['data'] else '-'}")

    zones = call("GET", "/api/v1/zones?poolId=1", token=token)
    print(f"[5] zones         -> {len(zones['data'])} 个")

    snapshot = call("GET", "/api/v1/live/snapshot?poolId=1", token=token)
    frames = snapshot["data"]["snapshot"]
    print(f"[6] live/snapshot -> targets={len(frames['targets'])} seq={frames['seq']} placeholder={frames['placeholder']} inferMs={frames['inferMs']}")
    if not frames["targets"]:
        failures.append("实时快照没有目标")

    alerts = call("GET", "/api/v1/alerts", token=token)
    print(f"[7] alerts        -> total={alerts['data']['total']}（M1 预期为 0）")

    model = call("GET", "/api/v1/model/info", token=token)
    print(f"[8] model/info    -> provider={model['data']['provider']} placeholder={model['data']['placeholder']}")

    unauthorized = 0
    try:
        call("GET", "/api/v1/pools")
    except urllib.error.HTTPError as ex:
        unauthorized = ex.code
    print(f"[9] no-token      -> HTTP {unauthorized}（预期 401）")
    if unauthorized != 401:
        failures.append("未带 token 的请求没有被拒绝")

    print()
    if failures:
        print("结果：未通过")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("结果：通过（M1 冒烟）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
