"""验收：告警锁存服务端化。

验证点：
1. 触发剧本后 /alerts/active 出现未确认告警，且同一目标只有一条；
2. 告警在库里是 OPEN，服务端可见（不是浏览器 localStorage）；
3. 人工确认后从 active 列表消失，但历史记录仍在（状态 ACKED）。

用法：python deploy/scripts/check_latch.py
"""

from __future__ import annotations

import json
import time
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
    failures: list[str] = []
    token = call("POST", "/api/v1/auth/login", {"username": "manager", "password": "demo1234"})["data"]["token"]

    call("POST", "/api/v1/demo/reset?seed=2026&swimmerCount=8&clearAlerts=true", None, token)
    empty = call("GET", "/api/v1/alerts/active?poolId=1", token=token)["data"]
    print(f"[1] active(before) -> total={empty['total']}")
    if empty["list"]:
        failures.append("重置后仍有未确认告警")

    call("POST", "/api/v1/demo/scenarios/drown_still", None, token)
    rows: list[dict] = []
    # 等到出现「仍在报警」的目标（越界告警可能先出现且已恢复，不算通过）
    for _ in range(30):
        time.sleep(3)
        rows = call("GET", "/api/v1/alerts/active?poolId=1", token=token)["data"]["list"]
        if any(row["active"] for row in rows):
            break

    print(f"[2] active(after)  -> {len(rows)} 条")
    for row in rows:
        print(f"    id={row['id']} track=#{row['trackNo']} level={row['level']} "
              f"active={row['active']} zone={row.get('zoneName')} reason={row['reason']}")
    if not rows:
        print("结果：未通过（等了 72 秒仍没有未确认告警）")
        return 1

    tracks = [row["trackNo"] for row in rows]
    if len(tracks) != len(set(tracks)):
        failures.append("同一目标存在多条未确认告警（锁存未生效）")
    if not any(row["active"] for row in rows):
        failures.append("剧本期间没有 active=true 的告警")

    target = rows[0]
    listed = call("GET", "/api/v1/alerts?status=OPEN&page=1&size=20", token=token)["data"]
    print(f"[3] server list    -> OPEN 告警 {listed['total']} 条（与 active 对应）")
    if listed["total"] == 0:
        failures.append("服务端没有 OPEN 告警记录")

    call("POST", f"/api/v1/alerts/{target['id']}/ack", {"note": "锁存验收：值班确认"}, token)
    after_ack = call("GET", "/api/v1/alerts/active?poolId=1", token=token)["data"]
    print(f"[4] active(acked)  -> total={after_ack['total']}")
    remaining = [row for row in after_ack["list"] if row["id"] == target["id"]]
    if remaining:
        failures.append("确认后告警仍在 active 列表")

    history = call("GET", f"/api/v1/alerts/{target['id']}", token=token)["data"]
    print(f"[5] history        -> status={history['alert']['status']} "
          f"actions={len(history['actions'])}")
    if history["alert"]["status"] != "ACKED":
        failures.append("确认后历史状态不是 ACKED")
    if len(history["actions"]) < 2:
        failures.append("处置时间线缺少确认记录")

    print()
    if failures:
        print("结果：未通过")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("结果：通过（告警锁存在服务端，确认后留痕）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
