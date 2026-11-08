package com.smartpool.alert;

import com.fasterxml.jackson.databind.JsonNode;
import com.smartpool.pool.Zone;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 电子围栏越界判定。
 *
 * 规则（演示口径）：
 * - 儿童进入深水区 / 禁入区，持续 8 秒 → 弱告警（可被 30 秒规则升级）
 * - 任何目标进入禁入区，持续 5 秒 → 弱告警
 * - 成人进入儿童区不告警（避免噪声）
 */
@Service
public class BoundaryGuard {

    private static final Logger log = LoggerFactory.getLogger(BoundaryGuard.class);

    private static final long CHILD_DEEP_SECONDS = 15;
    private static final long RESTRICTED_SECONDS = 5;
    private static final List<String> CHILD_FORBIDDEN = List.of("DEEP", "RESTRICTED");

    private final ZoneLocator zoneLocator;
    private final AlertService alertService;

    /** trackNo -> 当前区域与进入时间 */
    private final Map<Integer, TrackZoneState> states = new ConcurrentHashMap<>();

    public BoundaryGuard(ZoneLocator zoneLocator, AlertService alertService) {
        this.zoneLocator = zoneLocator;
        this.alertService = alertService;
    }

    public void check(JsonNode frames) {
        long poolId = frames.path("poolId").asLong(1);
        JsonNode targets = frames.path("targets");
        if (!targets.isArray()) {
            return;
        }
        long now = System.currentTimeMillis();
        for (JsonNode target : targets) {
            int trackNo = target.path("trackNo").asInt();
            String group = target.path("group").asText("ADULT");
            JsonNode box = target.path("box");
            double cx = box.path("x").asDouble() + box.path("w").asDouble() / 2;
            double cy = box.path("y").asDouble() + box.path("h").asDouble() / 2;
            Zone zone = zoneLocator.locate(poolId, cx, cy);

            TrackZoneState state = states.computeIfAbsent(trackNo, key -> new TrackZoneState());
            long zoneId = zone == null ? 0 : zone.getId();
            if (state.zoneId != zoneId) {
                state.zoneId = zoneId;
                state.since = now;
                state.alerted = false;
                continue;
            }
            if (zone == null || state.alerted) {
                continue;
            }
            long seconds = (now - state.since) / 1000;

            if ("RESTRICTED".equals(zone.getType()) && seconds >= RESTRICTED_SECONDS) {
                state.alerted = fire(poolId, trackNo, zone, group, seconds, "进入禁入区 " + seconds + "s");
            } else if ("CHILD".equals(group) && CHILD_FORBIDDEN.contains(zone.getType())
                    && seconds >= CHILD_DEEP_SECONDS) {
                state.alerted = fire(poolId, trackNo, zone, group, seconds, "儿童进入" + zone.getName() + " " + seconds + "s");
            }
        }
    }

    /** @return 是否已经产生过告警（用于抑制同一次越界的重复建单） */
    private boolean fire(long poolId, int trackNo, Zone zone, String group, long seconds, String reason) {
        try {
            boolean created = alertService.createBoundaryAlert(poolId, trackNo, zone.getId(), zone.getName(),
                    group, seconds, reason);
            if (created) {
                log.info("boundary alert track={} zone={} reason={}", trackNo, zone.getName(), reason);
            }
            return true;
        } catch (RuntimeException ex) {
            log.debug("boundary alert skipped: {}", ex.getMessage());
            return false;
        }
    }

    private static final class TrackZoneState {
        private long zoneId = -1;
        private long since = System.currentTimeMillis();
        private boolean alerted;
    }
}
