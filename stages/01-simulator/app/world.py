"""泳池世界状态：游客运动、姿态、手环生理、水质与剧本注入。

坐标一律归一化到 0..1（原点左上），与前端画布和检测框共用同一坐标系。
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

POOL_LENGTH_M = 25.0
POOL_WIDTH_M = 12.5

NORMAL_POSTURES = ["swimming", "swimming", "swimming", "floating", "treading", "standing"]

SCENARIOS = {
    "normal": {"label": "正常游泳", "duration": 0},
    "drown_still": {"label": "静止下沉", "duration": 90},
    "zone_intrude": {"label": "儿童进入深水区", "duration": 90},
    "night_intrude": {"label": "营业外闯入", "duration": 60},
    "water_poor": {"label": "水质超标", "duration": 120},
}


@dataclass
class Swimmer:
    track_no: int
    x: float
    y: float
    vx: float
    vy: float
    posture: str = "swimming"
    group: str = "ADULT"
    heart_rate: float = 96.0
    spo2: float = 98.0
    still_sec: float = 0.0
    under_water_sec: float = 0.0
    forced: str | None = None
    forced_until: float = 0.0
    wristband: str | None = None

    def box(self) -> dict:
        w = 0.055 if self.group == "ADULT" else 0.038
        h = 0.075 if self.group == "ADULT" else 0.052
        return {"x": round(max(0.0, self.x - w / 2), 4),
                "y": round(max(0.0, self.y - h / 2), 4),
                "w": w, "h": h}


@dataclass
class World:
    seed: int = 2026
    swimmer_count: int = 8
    clock_speed: float = 1.0
    started_at: float = field(default_factory=time.time)
    last_tick: float = field(default_factory=time.time)
    seq: int = 0
    active_scenario: str = "normal"
    scenario_until: float = 0.0
    swimmers: list[Swimmer] = field(default_factory=list)
    water: dict = field(default_factory=lambda: {
        "temperature": 27.2, "turbidity": 0.8, "ph": 7.4, "chlorine": 0.6,
    })
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self.reset(self.seed, self.swimmer_count)

    # ---------- 生命周期 ----------

    def reset(self, seed: int | None = None, count: int | None = None) -> None:
        if seed is not None:
            self.seed = seed
        if count is not None:
            self.swimmer_count = max(2, min(count, 30))
        self._rng = random.Random(self.seed)
        self.started_at = time.time()
        self.last_tick = self.started_at
        self.seq = 0
        self.active_scenario = "normal"
        self.scenario_until = 0.0
        self.swimmers = []
        for index in range(1, self.swimmer_count + 1):
            group = "CHILD" if index % 4 == 0 else "ADULT"
            self.swimmers.append(Swimmer(
                track_no=index,
                x=self._rng.uniform(0.08, 0.92),
                y=self._rng.uniform(0.12, 0.88),
                vx=self._rng.uniform(-0.02, 0.02),
                vy=self._rng.uniform(-0.012, 0.012),
                posture=self._rng.choice(NORMAL_POSTURES),
                group=group,
                heart_rate=self._rng.uniform(88, 108) if group == "ADULT" else self._rng.uniform(104, 122),
                spo2=self._rng.uniform(97, 99),
                wristband=f"WB-{index:04d}" if index <= 4 else None,
            ))

    # ---------- 时钟推进 ----------

    def tick(self) -> None:
        now = time.time()
        elapsed = min(now - self.last_tick, 2.0) * self.clock_speed
        self.last_tick = now
        if elapsed <= 0:
            return
        self.seq += 1

        if self.active_scenario != "normal" and now > self.scenario_until:
            self.clear_scenario()

        for swimmer in self.swimmers:
            self._step(swimmer, elapsed)

        self._step_water(elapsed)

    def _step(self, swimmer: Swimmer, dt: float) -> None:
        if swimmer.forced_until and time.time() > swimmer.forced_until:
            # 剧本结束时把姿态复位，避免目标继续保持「水下静止」姿态
            swimmer.forced = None
            swimmer.forced_until = 0.0
            swimmer.posture = "swimming"
            swimmer.still_sec = 0.0

        if swimmer.forced == "underwater_still":
            swimmer.posture = "underwater_still"
            swimmer.vx *= 0.90
            swimmer.vy *= 0.90
            swimmer.still_sec += dt
            swimmer.under_water_sec += dt
            swimmer.heart_rate = max(60.0, swimmer.heart_rate - 0.2 * dt) if swimmer.still_sec > 12 \
                else swimmer.heart_rate
        elif swimmer.forced == "intrude_deep":
            swimmer.posture = "swimming"
            target_x = 0.78
            swimmer.vx = 0.10 if swimmer.x < target_x else 0.0
            swimmer.vy = 0.0
            swimmer.under_water_sec = 0.0
        else:
            if self._rng.random() < 0.01:
                swimmer.posture = self._rng.choice(NORMAL_POSTURES)
            if self._rng.random() < 0.05:
                swimmer.vx += self._rng.uniform(-0.006, 0.006)
                swimmer.vy += self._rng.uniform(-0.004, 0.004)
            swimmer.vx = max(-0.035, min(0.035, swimmer.vx))
            swimmer.vy = max(-0.022, min(0.022, swimmer.vy))
            if swimmer.posture in ("standing", "floating"):
                swimmer.vx *= 0.5
                swimmer.vy *= 0.5
                swimmer.still_sec += dt
            else:
                swimmer.still_sec = max(0.0, swimmer.still_sec - dt)
            swimmer.under_water_sec = 0.0
            swimmer.heart_rate += self._rng.uniform(-0.6, 0.6)

        # 边界反弹
        if swimmer.x < 0.04 or swimmer.x > 0.96:
            swimmer.vx = -swimmer.vx
            swimmer.x = max(0.04, min(0.96, swimmer.x))
        if swimmer.y < 0.06 or swimmer.y > 0.94:
            swimmer.vy = -swimmer.vy
            swimmer.y = max(0.06, min(0.94, swimmer.y))

        swimmer.x = max(0.02, min(0.98, swimmer.x + swimmer.vx * dt))
        swimmer.y = max(0.03, min(0.97, swimmer.y + swimmer.vy * dt))
        swimmer.heart_rate = max(55.0, min(170.0, swimmer.heart_rate))
        swimmer.spo2 = max(88.0, min(100.0, swimmer.spo2 - (0.05 * dt if swimmer.under_water_sec > 20 else 0)))

    def _step_water(self, dt: float) -> None:
        self.water["temperature"] += self._rng.uniform(-0.01, 0.01) * dt
        if self.active_scenario == "water_poor":
            self.water["turbidity"] += 0.09 * dt
        else:
            self.water["turbidity"] += (0.8 - self.water["turbidity"]) * 0.02 * dt
        self.water["ph"] += self._rng.uniform(-0.005, 0.005) * dt
        self.water["chlorine"] += self._rng.uniform(-0.004, 0.004) * dt
        self.water["temperature"] = round(max(24.0, min(31.0, self.water["temperature"])), 2)
        self.water["turbidity"] = round(max(0.2, min(9.0, self.water["turbidity"])), 2)
        self.water["ph"] = round(max(6.5, min(8.5, self.water["ph"])), 2)
        self.water["chlorine"] = round(max(0.1, min(1.5, self.water["chlorine"])), 2)

    # ---------- 剧本 ----------

    def trigger(self, key: str) -> dict:
        if key not in SCENARIOS:
            raise KeyError(key)
        now = time.time()
        self.active_scenario = key
        self.scenario_until = now + SCENARIOS[key]["duration"]
        detail: dict = {"scenario": key}

        if key == "drown_still":
            target = self.swimmers[min(len(self.swimmers), 7) - 1]
            target.forced = "underwater_still"
            target.forced_until = self.scenario_until
            detail["target"] = target.track_no
        elif key == "zone_intrude":
            child = next((s for s in self.swimmers if s.group == "CHILD"), self.swimmers[0])
            child.forced = "intrude_deep"
            child.forced_until = self.scenario_until
            detail["target"] = child.track_no
        elif key == "water_poor":
            self.water["turbidity"] = max(self.water["turbidity"], 5.2)
        return detail

    def clear_scenario(self) -> None:
        self.active_scenario = "normal"
        self.scenario_until = 0.0
        for swimmer in self.swimmers:
            if swimmer.forced:
                swimmer.posture = "swimming"
                swimmer.still_sec = 0.0
            swimmer.forced = None
            swimmer.forced_until = 0.0

    # ---------- 输出 ----------

    def snapshot(self, pool_id: int) -> dict:
        self.tick()
        targets = []
        for swimmer in self.swimmers:
            targets.append({
                "trackNo": swimmer.track_no,
                "box": swimmer.box(),
                "point": {"x": round(swimmer.x, 4), "y": round(swimmer.y, 4)},
                "posture": swimmer.posture,
                "group": swimmer.group,
                "wristband": swimmer.wristband,
                "wristbandData": {
                    "code": swimmer.wristband,
                    "heartRate": round(swimmer.heart_rate, 1),
                    "spo2": round(swimmer.spo2, 1),
                    "stillSec": round(swimmer.still_sec, 1),
                } if swimmer.wristband else None,
                "synthetic": True,
            })
        return {
            "poolId": pool_id,
            "seq": self.seq,
            "simTime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "clockSpeed": self.clock_speed,
            "scenario": self.active_scenario,
            "targets": targets,
            "counts": {
                "total": len(targets),
                "adult": sum(1 for t in targets if t["group"] == "ADULT"),
                "child": sum(1 for t in targets if t["group"] == "CHILD"),
            },
            "water": dict(self.water),
            "synthetic": True,
        }

    def status(self) -> dict:
        return {
            "seed": self.seed,
            "swimmers": len(self.swimmers),
            "clockSpeed": self.clock_speed,
            "scenario": self.active_scenario,
            "seq": self.seq,
            "water": dict(self.water),
            "scenarios": [{"key": k, "label": v["label"], "duration": v["duration"]}
                          for k, v in SCENARIOS.items()],
        }
