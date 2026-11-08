package com.smartpool.alert;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/** 每秒为目标落一条轨迹采样，供事件回溯使用。 */
@Service
public class TrackSampler {

    private final TrackSampleMapper mapper;

    private volatile long lastSampleAt;
    private volatile long lastPruneAt;

    public TrackSampler(TrackSampleMapper mapper) {
        this.mapper = mapper;
    }

    public void maybeSample(JsonNode frames) {
        long now = System.currentTimeMillis();
        if (now - lastSampleAt < 1000) {
            return;
        }
        lastSampleAt = now;
        JsonNode targets = frames.path("targets");
        if (!targets.isArray()) {
            return;
        }
        long poolId = frames.path("poolId").asLong(1);
        LocalDateTime ts = LocalDateTime.now();
        for (JsonNode target : targets) {
            JsonNode box = target.path("box");
            TrackSample sample = new TrackSample();
            sample.setPoolId(poolId);
            sample.setTrackNo(target.path("trackNo").asInt());
            sample.setTs(ts);
            sample.setX(box.path("x").asDouble() + box.path("w").asDouble() / 2);
            sample.setY(box.path("y").asDouble() + box.path("h").asDouble() / 2);
            sample.setPosture(target.path("posture").asText("unknown"));
            sample.setRiskScore(target.path("riskScore").asDouble(0));
            mapper.insert(sample);
        }
        prune(now);
    }

    /** 演示只保留 30 分钟，避免长跑把磁盘写满。 */
    private void prune(long now) {
        if (now - lastPruneAt < 300_000) {
            return;
        }
        lastPruneAt = now;
        mapper.delete(Wrappers.<TrackSample>lambdaQuery()
                .lt(TrackSample::getTs, LocalDateTime.now().minusMinutes(30)));
    }
}
