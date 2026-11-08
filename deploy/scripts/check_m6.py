"""M6 验收：演示状态自检、故障注入与恢复、重置一致性。

用法：python deploy/scripts/check_m6.py
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
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def snapshot_tracks(token: str) -> set[int]:
    data = call("GET", "/api/v1/live/snapshot?poolId=1", token=token)["data"]["snapshot"]
    return {item["trackNo"] for item in data["targets"]}


def main() -> int:
    failures: list[str] = []
    token = call("POST", "/api/v1/auth/login", {"username": "manager", "password": "demo1234"})["data"]["token"]

    status = call("GET", "/api/v1/demo/status", token=token)["data"]
    print(f"[1] status        -> aiOk={status['aiOk']} mode={status['mode']} targets={status['targets']} "
          f"cameras={status['camerasOnline']}/{status['camerasTotal']} openAlerts={status['openAlerts']}")
    if not status["aiOk"]:
        failures.append("推理服务不可用")

    call("POST", "/api/v1/demo/faults", {"type": "INFER_DOWN", "seconds": 8}, token)
    time.sleep(4)
    during = call("GET", "/api/v1/demo/status", token=token)["data"]
    print(f"[2] infer down    -> paused={during['framesPaused']} delay={during['dataDelayMs']}ms")
    if not during["framesPaused"]:
        failures.append("推理中断没有冻结取帧")
    time.sleep(8)
    after = call("GET", "/api/v1/demo/status", token=token)["data"]
    print(f"[3] auto recover  -> paused={after['framesPaused']} delay={after['dataDelayMs']}ms")
    if after["framesPaused"]:
        failures.append("推理中断没有自动恢复")

    call("POST", "/api/v1/demo/faults", {"type": "CAMERA_OFFLINE", "seconds": 6, "cameraId": 3}, token)
    time.sleep(1)
    devices = call("GET", "/api/v1/devices?poolId=1", token=token)["data"]
    camera = next((item for item in devices["items"] if item["key"] == "camera-3"), None)
    print(f"[4] camera offline-> status={camera['status']} online={devices['online']}")
    if camera["status"] != "OFFLINE":
        failures.append("摄像头离线未生效")
    time.sleep(7)
    restored = call("GET", "/api/v1/devices?poolId=1", token=token)["data"]
    camera = next((item for item in restored["items"] if item["key"] == "camera-3"), None)
    print(f"[5] camera back   -> status={camera['status']}")
    if camera["status"] != "ONLINE":
        failures.append("摄像头没有自动恢复")

    call("POST", "/api/v1/demo/faults", {"type": "WS_FLOOD", "seconds": 5}, token)
    print("[6] ws flood      -> 已注入（20 帧突发）")

    call("POST", "/api/v1/demo/reset?seed=2026&swimmerCount=8", None, token)
    time.sleep(3)
    first = snapshot_tracks(token)
    call("POST", "/api/v1/demo/reset?seed=2026&swimmerCount=8", None, token)
    time.sleep(3)
    second = snapshot_tracks(token)
    print(f"[7] reset x2      -> 轨迹集合一致={first == second}（{sorted(first)}）")
    if first != second:
        failures.append("两次重置后的目标集合不一致")

    final = call("GET", "/api/v1/demo/status", token=token)["data"]
    print(f"[8] final status  -> scenario={final['scenario']} openFaults={len(final['activeFaults'])}")
    if final["activeFaults"]:
        failures.append("重置后仍有未恢复的故障")

    print()
    if failures:
        print("结果：未通过")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("结果：通过（M6 演示控制与重置一致性）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
