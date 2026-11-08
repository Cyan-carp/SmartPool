"""M3 告警闭环验收：列表 -> 确认 -> 派单 -> 解除 -> 详情 -> 统计 -> 导出。

前置：已触发剧本并产生至少一条告警（见 README 的演示步骤）。
用法：python deploy/scripts/check_alerts.py
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
    failures: list[str] = []

    token = call("POST", "/api/v1/auth/login", {"username": "manager", "password": "demo1234"})["data"]["token"]

    listing = call("GET", "/api/v1/alerts?page=1&size=20", token=token)["data"]
    alerts = listing["list"]
    print(f"[1] alerts        -> total={listing['total']} 本页 {len(alerts)} 条")
    if not alerts:
        print("结果：未通过（没有任何告警，请先触发剧本）")
        return 1

    open_alert = next((item for item in alerts if item["status"] == "OPEN"), None)
    target = open_alert or alerts[0]
    alert_id = target["id"]
    print(f"[2] pick          -> id={alert_id} level={target['level']} status={target['status']} track=#{target['trackNo']}")

    if open_alert:
        acked = call("POST", f"/api/v1/alerts/{alert_id}/ack", {"note": "冒烟：值班台确认"}, token)["data"]
        print(f"[3] ack           -> status={acked['status']}")
        dispatched = call("POST", f"/api/v1/alerts/{alert_id}/dispatch",
                          {"assignee": "现场救生员", "note": "冒烟：派单"}, token)["data"]
        print(f"[4] dispatch      -> status={dispatched['status']}")
        resolved = call("POST", f"/api/v1/alerts/{alert_id}/resolve",
                        {"result": "RESCUED", "note": "冒烟：已施救"}, token)["data"]
        print(f"[5] resolve       -> status={resolved['status']} closedAt={resolved['closedAt']}")
        if resolved["status"] != "RESOLVED":
            failures.append("解除后状态不是 RESOLVED")

        invalid = 0
        try:
            call("POST", f"/api/v1/alerts/{alert_id}/ack", {"note": "重复确认"}, token)
        except urllib.error.HTTPError as ex:
            invalid = ex.code
        print(f"[6] re-ack        -> HTTP {invalid}（预期 409）")
        if invalid != 409:
            failures.append("重复确认没有被状态机拦住")

    detail = call("GET", f"/api/v1/alerts/{alert_id}", token=token)["data"]
    actions = detail["actions"]
    points = detail["clip"]["points"]
    print(f"[7] detail        -> actions={len(actions)} clipPoints={len(points)} zone={detail['alert'].get('zoneName')}")
    if len(actions) < 2:
        failures.append("处置时间线动作过少")
    if not points:
        failures.append("事件片段没有轨迹采样")

    stats = call("GET", "/api/v1/stats/overview?hours=24", token=token)["data"]
    print(f"[8] stats         -> total={stats['total']} open={stats['open']} resolved={stats['resolved']} "
          f"falseRate={stats['falseAlarmRate']}% avgAck={stats['avgAckSeconds']}s")

    request = urllib.request.Request(BASE + "/api/v1/alerts/export.csv?hours=24", method="GET")
    request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=15) as response:
        csv_text = response.read().decode("utf-8-sig")
    lines = [line for line in csv_text.splitlines() if line.strip()]
    print(f"[9] export.csv    -> {len(lines)} 行（含表头）")
    if len(lines) < 2 or not lines[0].startswith("告警ID"):
        failures.append("CSV 导出内容异常")

    print()
    if failures:
        print("结果：未通过")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("结果：通过（M3 告警闭环）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
