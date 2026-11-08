package com.smartpool.alert;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Service;

/**
 * 每帧经过这里：轨迹始终采样，告警判定按 1 秒节流，
 * 避免 10 Hz 推送把数据库打成筛子。
 */
@Service
public class RiskPipeline {

    private static final int ALERT_EVERY_N_TICKS = 10;

    private final AlertService alertService;
    private final TrackSampler trackSampler;
    private final BoundaryGuard boundaryGuard;

    private long tick;

    public RiskPipeline(AlertService alertService, TrackSampler trackSampler, BoundaryGuard boundaryGuard) {
        this.alertService = alertService;
        this.trackSampler = trackSampler;
        this.boundaryGuard = boundaryGuard;
    }

    public void accept(JsonNode frames) {
        tick++;
        try {
            trackSampler.maybeSample(frames);
            if (tick % ALERT_EVERY_N_TICKS == 0) {
                alertService.ingest(frames);
                boundaryGuard.check(frames);
            }
        } catch (RuntimeException ex) {
            // 单帧处理失败不能中断推送
        }
    }
}
