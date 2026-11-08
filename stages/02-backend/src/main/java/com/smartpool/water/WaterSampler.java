package com.smartpool.water;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/** 每 10 秒采一次水质，保留 24 小时；演示数据来自模拟源。 */
@Service
public class WaterSampler {

    private final WaterService waterService;
    private final WaterQualityMapper mapper;

    private long lastPruneAt;

    public WaterSampler(WaterService waterService, WaterQualityMapper mapper) {
        this.waterService = waterService;
        this.mapper = mapper;
    }

    @Scheduled(fixedRate = 10_000)
    public void tick() {
        try {
            waterService.sample(waterService.defaultPool());
            prune();
        } catch (RuntimeException ex) {
            // 采样失败不影响主链路
        }
    }

    private void prune() {
        long now = System.currentTimeMillis();
        if (now - lastPruneAt < 1_800_000) {
            return;
        }
        lastPruneAt = now;
        mapper.delete(Wrappers.<WaterQuality>lambdaQuery()
                .lt(WaterQuality::getTs, LocalDateTime.now().minusHours(24)));
    }
}
