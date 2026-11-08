"""风险打分（规则 + 时序累计，占位实现）。

真实方案为 DeepSORT 轨迹 + Temporal Transformer 滑窗分类，
本实现保留同样的输入输出形状：目标 -> 0..1 风险分 + 人类可读原因。

静止时长优先用检测框位移计算（不依赖手环），手环数据只做加权，
这样没有佩戴手环的目标同样能升级到强告警。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

LEVELS = ("NORMAL", "NOTICE", "WEAK", "STRONG")

# 位移阈值（归一化坐标/秒）：低于该速度视为静止
STILL_SPEED = 0.004
# 位置平滑系数：抑制检测框抖动带来的伪速度
EMA_ALPHA = 0.25


@dataclass
class TrackState:
    under_water_sec: float = 0.0
    still_sec: float = 0.0
    ema_x: float | None = None
    ema_y: float | None = None
    last_level: str = "NORMAL"


@dataclass
class RiskResult:
    score: float
    level: str
    reason: str
    detail: dict = field(default_factory=dict)


class RiskScorer:
    """阈值口径见工程规范 05「阈值与参数口径」。"""

    STRONG = 0.80
    WEAK = 0.55
    NOTICE = 0.35
    UNDER_WATER_FULL = 25.0
    STILL_FULL = 20.0

    def __init__(self) -> None:
        self._state: dict[int, TrackState] = {}

    def reset(self) -> None:
        self._state.clear()

    def score(self, detection, dt: float) -> RiskResult:
        state = self._state.setdefault(detection.track_no, TrackState())
        posture = detection.posture
        wristband = detection.wristband_data or {}

        # 1) 头部未出水累计
        if posture == "underwater_still":
            state.under_water_sec += dt
        else:
            state.under_water_sec = max(0.0, state.under_water_sec - dt * 1.5)

        # 2) 静止累计：框中心做指数平滑后再求速度，手环静止时长取较大值
        center_x = detection.box.get("x", 0.0) + detection.box.get("w", 0.0) / 2
        center_y = detection.box.get("y", 0.0) + detection.box.get("h", 0.0) / 2
        speed = 0.0
        if state.ema_x is None or state.ema_y is None:
            state.ema_x, state.ema_y = center_x, center_y
        else:
            previous_x, previous_y = state.ema_x, state.ema_y
            state.ema_x = EMA_ALPHA * center_x + (1 - EMA_ALPHA) * previous_x
            state.ema_y = EMA_ALPHA * center_y + (1 - EMA_ALPHA) * previous_y
            if dt > 0:
                speed = math.hypot(state.ema_x - previous_x, state.ema_y - previous_y) / dt

        wristband_still = float(wristband.get("stillSec") or 0.0)
        if posture in ("underwater_still", "floating"):
            if speed < STILL_SPEED:
                state.still_sec += dt
            else:
                state.still_sec = max(0.0, state.still_sec - dt)
            state.still_sec = max(state.still_sec, wristband_still)
        else:
            # 站立/踩水属于正常行为，不累积静止
            state.still_sec = max(0.0, state.still_sec - dt * 2)

        score = 0.10
        reasons: list[str] = []

        water_part = 0.45 * min(1.0, state.under_water_sec / self.UNDER_WATER_FULL)
        if water_part > 0:
            score += water_part
            reasons.append(f"头部未出水 {state.under_water_sec:.0f}s")

        still_part = 0.30 * min(1.0, state.still_sec / self.STILL_FULL)
        if still_part > 0:
            score += still_part
            reasons.append(f"静止 {state.still_sec:.0f}s")

        heart_rate = float(wristband.get("heartRate") or 0.0)
        spo2 = float(wristband.get("spo2") or 100.0)
        if heart_rate and (heart_rate > 140 or heart_rate < 70):
            score += 0.08
            reasons.append(f"心率异常 {heart_rate:.0f}")
        if spo2 < 95:
            score += 0.09
            reasons.append(f"血氧偏低 {spo2:.0f}%")

        score = round(min(0.99, score), 3)
        if score >= self.STRONG:
            level = "STRONG"
        elif score >= self.WEAK:
            level = "WEAK"
        elif score >= self.NOTICE:
            level = "NOTICE"
        else:
            level = "NORMAL"

        state.last_level = level
        reason = "；".join(reasons) if reasons else "正常游泳"
        return RiskResult(score=score, level=level, reason=reason, detail={
            "underWaterSec": round(state.under_water_sec, 1),
            "stillSec": round(state.still_sec, 1),
            "speed": round(speed, 4),
            "heartRate": heart_rate or None,
            "spo2": spo2,
        })
