"""模拟数据源服务（8010）。

仅负责生成「世界」：游客位置与姿态、手环生理、水质、剧本。
不判定风险（推理服务做），不写业务库（后端做）。
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .world import SCENARIOS, World

app = FastAPI(title="SmartPool Simulator", version="0.1.0")
world = World()


class ClockRequest(BaseModel):
    speed: float = Field(default=1.0, ge=0.5, le=20.0)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "smartpool-simulator",
        "version": "0.1.0",
        "seed": world.seed,
        "swimmers": len(world.swimmers),
        "synthetic": True,
    }


@app.get("/sim/snapshot")
def snapshot(poolId: int = 1) -> dict:
    return world.snapshot(poolId)


@app.get("/sim/status")
def status() -> dict:
    return world.status()


@app.get("/sim/scenarios")
def scenarios() -> list[dict]:
    return [{"key": k, "label": v["label"], "duration": v["duration"]} for k, v in SCENARIOS.items()]


# 注意：具体路径必须声明在通配路径之前，否则 "normal" 会被 {key} 吃掉
@app.post("/sim/scenario/normal")
def clear() -> dict:
    world.clear_scenario()
    return {"scenario": "normal"}


@app.post("/sim/scenario/{key}")
def trigger(key: str) -> dict:
    try:
        detail = world.trigger(key)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知剧本: {key}")
    return {**detail, "activeUntilSec": round(max(0.0, world.scenario_until - world.started_at), 1)}


@app.post("/sim/clock")
def set_clock(body: ClockRequest) -> dict:
    world.clock_speed = body.speed
    return {"clockSpeed": world.clock_speed}


@app.post("/sim/seed")
def reseed(seed: int = 2026, swimmerCount: int | None = None) -> dict:
    world.reset(seed, swimmerCount)
    return world.status()
