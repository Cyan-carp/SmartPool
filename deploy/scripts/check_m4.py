"""M4 验收：围栏 CRUD、手环绑定、看板聚合。

用法：python deploy/scripts/check_m4.py
"""

from __future__ import annotations

import json
import urllib.error
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

    zones = call("GET", "/api/v1/zones?poolId=1", token=token)["data"]
    types = [zone["type"] for zone in zones]
    print(f"[1] zones         -> {len(zones)} 个：{', '.join(z['name'] for z in zones)}")
    if "POOL" not in types:
        failures.append("缺少全池兜底区域（V4 未生效？）")

    pool_zone = next((zone for zone in zones if zone["type"] == "POOL"), None)
    if pool_zone:
        code = 0
        try:
            call("DELETE", f"/api/v1/zones/{pool_zone['id']}", token=token)
        except urllib.error.HTTPError as ex:
            code = ex.code
        print(f"[2] delete POOL   -> HTTP {code}（预期 409）")
        if code != 409:
            failures.append("全池区域没有被保护")

    target = next((zone for zone in zones if zone["type"] == "DEEP"), zones[0])
    updated = call("PUT", f"/api/v1/zones/{target['id']}", {
        "name": target["name"],
        "type": target["type"],
        "allowedGroups": target["allowedGroups"],
        "enabled": target["enabled"],
        "polygonJson": target["polygonJson"]
    }, token)["data"]
    print(f"[3] update zone   -> id={updated['id']} name={updated['name']}")

    created = call("POST", "/api/v1/zones", {
        "poolId": 1,
        "name": "验收临时区",
        "type": "RESTRICTED",
        "allowedGroups": "ALL",
        "enabled": True,
        "polygonJson": json.dumps({"points": [
            {"x": 0.02, "y": 0.02}, {"x": 0.10, "y": 0.02},
            {"x": 0.10, "y": 0.10}, {"x": 0.02, "y": 0.10}
        ], "version": 1})
    }, token)["data"]
    print(f"[4] create zone   -> id={created['id']} type={created['type']}")
    call("DELETE", f"/api/v1/zones/{created['id']}", token=token)
    print("[5] delete temp   -> ok")

    bands = call("GET", "/api/v1/wristbands", token=token)["data"]
    print(f"[6] wristbands    -> total={bands['total']} bound={bands['bound']}")
    if bands["total"] == 0:
        failures.append("手环列表为空")

    free_band = next((band for band in bands["list"] if not band.get("bindTrackNo")), None)
    used = [band["bindTrackNo"] for band in bands["list"] if band.get("bindTrackNo")]
    free_track = (max(used) + 1) if used else 1
    if free_band:
        bound_band = call("POST", f"/api/v1/wristbands/{free_band['code']}/bind",
                          {"trackNo": free_track}, token)["data"]
        print(f"[7] bind          -> {bound_band['code']} -> #{bound_band['bindTrackNo']}")
        unbound = call("POST", f"/api/v1/wristbands/{free_band['code']}/unbind", None, token)["data"]
        print(f"[8] unbind        -> bindTrackNo={unbound.get('bindTrackNo')}")
        if unbound.get("bindTrackNo"):
            failures.append("解绑后仍保留绑定关系")

    heatmap = call("GET", "/api/v1/stats/heatmap?poolId=1&minutes=30", token=token)["data"]
    filled = sum(1 for row in heatmap["grid"] for value in row if value > 0)
    print(f"[9] heatmap       -> {heatmap['rows']}x{heatmap['cols']} 格，非零 {filled} 格，峰值 {heatmap['max']}")
    if filled == 0:
        failures.append("热力图没有数据（轨迹采样是否在跑？）")

    trend = call("GET", "/api/v1/stats/trend?poolId=1&minutes=30", token=token)["data"]
    print(f"[10] trend        -> {len(trend['points'])} 个分钟点")
    if not trend["points"]:
        failures.append("趋势数据为空")

    crowd = call("GET", "/api/v1/stats/crowd?poolId=1&hours=6", token=token)["data"]
    print(f"[11] crowd        -> {len(crowd['bars'])} 个小时桶")
    if not crowd["bars"]:
        failures.append("峰谷数据为空")

    print()
    if failures:
        print("结果：未通过")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("结果：通过（M4 围栏·手环·看板）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
