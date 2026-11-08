"""M5 验收：设备健康与维护、水质阈值与超标、算力档位与指标。

用法：python deploy/scripts/check_m5.py
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

    devices = call("GET", "/api/v1/devices?poolId=1", token=token)["data"]
    print(f"[1] devices       -> total={devices['total']} online={devices['online']}")
    if devices["total"] < 4:
        failures.append("设备数量异常")

    camera = next((item for item in devices["items"] if item["type"] == "CAMERA"), None)
    if camera:
        before = camera["metrics"].get("cleanliness")
        call("POST", f"/api/v1/devices/{camera['key']}/maintenance",
             {"type": "CLEAN", "note": "验收：清洁镜头"}, token)
        after = call("GET", "/api/v1/devices?poolId=1", token=token)["data"]["items"]
        current = next((item for item in after if item["key"] == camera["key"]), None)
        print(f"[2] maintenance   -> {camera['key']} 清洁度 {before} -> {current['metrics'].get('cleanliness')}")

    latest = call("GET", "/api/v1/water-quality/latest?poolId=1", token=token)["data"]
    print(f"[3] water latest  -> 浑浊度={latest.get('turbidity')} pH={latest.get('ph')} "
          f"水温={latest.get('temperature')} 超标={latest.get('exceeded')}")
    if "threshold" not in latest:
        failures.append("水质缺少阈值信息")

    history = call("GET", "/api/v1/water-quality/history?poolId=1&minutes=60", token=token)["data"]
    if not history["points"]:
        print("    ... 等待采样（每 10 秒一次）")
        time.sleep(12)
        history = call("GET", "/api/v1/water-quality/history?poolId=1&minutes=60", token=token)["data"]
    print(f"[4] water history -> {len(history['points'])} 个采样点")
    if not history["points"]:
        failures.append("水质曲线没有采样点")

    updated = call("PUT", "/api/v1/water-quality/thresholds",
                   {"poolId": 1, "turbidityMax": 6.5, "phMin": 6.8, "phMax": 8.0}, token)["data"]
    print(f"[5] threshold     -> turbidityMax={updated['turbidityMax']} ph={updated['phMin']}~{updated['phMax']}")
    if float(updated["turbidityMax"]) != 6.5:
        failures.append("阈值保存未生效")

    params = call("GET", "/api/v1/model/params", token=token)["data"]
    print(f"[6] model params  -> mode={params['mode']} 模板={list(params['templates'].keys())}")
    if len(params["templates"]) < 2:
        failures.append("档位模板不足两个")

    switched = call("POST", "/api/v1/model/mode", {"mode": "OFFPEAK", "auto": False}, token)["data"]
    print(f"[7] switch mode   -> {switched['mode']} auto={switched['auto']}")
    confirmed = call("GET", "/api/v1/model/params", token=token)["data"]
    if confirmed["mode"] != "OFFPEAK":
        failures.append("档位切换未持久化")

    metrics = call("GET", "/api/v1/model/metrics?minutes=30", token=token)["data"]
    if not metrics["points"]:
        print("    ... 等待指标采样（每 10 秒一次）")
        time.sleep(12)
        metrics = call("GET", "/api/v1/model/metrics?minutes=30", token=token)["data"]
    print(f"[8] model metrics -> {len(metrics['points'])} 个采样点，mode={metrics['mode']}")
    if not metrics["points"]:
        failures.append("指标曲线没有采样点")

    call("POST", "/api/v1/demo/scenarios/water_poor", None, token)
    time.sleep(14)
    poor = call("GET", "/api/v1/water-quality/latest?poolId=1", token=token)["data"]
    print(f"[9] water_poor    -> 浑浊度={poor.get('turbidity')} 超标={poor.get('exceeded')}")
    if "TURBIDITY" not in poor.get("exceeded", []):
        failures.append("浑浊度超标没有被识别")

    call("POST", "/api/v1/demo/scenarios/normal", None, token)
    call("PUT", "/api/v1/water-quality/thresholds", {"poolId": 1, "turbidityMax": 5.0}, token)
    call("POST", "/api/v1/model/mode", {"mode": "PEAK", "auto": True}, token)
    print("[10] restore      -> 阈值与档位已还原")

    print()
    if failures:
        print("结果：未通过")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("结果：通过（M5 设备水质与算力调度）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
