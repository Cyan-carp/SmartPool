package com.smartpool.alert;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.smartpool.live.LiveFeedService;
import com.smartpool.pool.Zone;
import com.smartpool.pool.ZoneMapper;
import org.springframework.stereotype.Service;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 大屏的「待确认告警」面板：数据源是服务端的 OPEN 告警，不是浏览器缓存。
 * active=true 表示目标当前仍在报警，false 表示已恢复但尚未人工确认。
 */
@Service
public class AlertBoardService {

    private static final DateTimeFormatter ISO = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private final AlertMapper alertMapper;
    private final RiskEventMapper riskEventMapper;
    private final ZoneMapper zoneMapper;
    private final LiveFeedService liveFeedService;

    public AlertBoardService(AlertMapper alertMapper,
                             RiskEventMapper riskEventMapper,
                             ZoneMapper zoneMapper,
                             LiveFeedService liveFeedService) {
        this.alertMapper = alertMapper;
        this.riskEventMapper = riskEventMapper;
        this.zoneMapper = zoneMapper;
        this.liveFeedService = liveFeedService;
    }

    public List<Map<String, Object>> active(long poolId) {
        List<AlertEntity> alerts = alertMapper.selectList(Wrappers.<AlertEntity>lambdaQuery()
                .eq(AlertEntity::getPoolId, poolId)
                .eq(AlertEntity::getStatus, "OPEN")
                .orderByDesc(AlertEntity::getTriggeredAt)
                .last("LIMIT 50"));

        JsonNode frames = liveFeedService.latest();
        Map<Integer, JsonNode> risky = new HashMap<>();
        if (frames != null) {
            for (JsonNode target : frames.path("targets")) {
                if (!"NORMAL".equals(target.path("level").asText("NORMAL"))) {
                    risky.put(target.path("trackNo").asInt(), target);
                }
            }
        }

        List<Map<String, Object>> rows = new ArrayList<>();
        for (AlertEntity alert : alerts) {
            JsonNode target = risky.get(alert.getTrackNo());
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", alert.getId());
            item.put("trackNo", alert.getTrackNo());
            item.put("level", alert.getLevel());
            item.put("status", alert.getStatus());
            item.put("reason", alert.getReason());
            item.put("triggeredAt", alert.getTriggeredAt().format(ISO));
            item.put("active", target != null);
            item.put("zoneName", zoneName(alert.getZoneId()));
            item.put("riskScore", riskScore(alert.getRiskEventId()));
            item.put("posture", target == null ? null : target.path("posture").asText(null));
            rows.add(item);
        }
        return rows;
    }

    public long count(long poolId) {
        return alertMapper.selectCount(Wrappers.<AlertEntity>lambdaQuery()
                .eq(AlertEntity::getPoolId, poolId)
                .eq(AlertEntity::getStatus, "OPEN"));
    }

    private String zoneName(Long zoneId) {
        if (zoneId == null) {
            return null;
        }
        Zone zone = zoneMapper.selectById(zoneId);
        return zone == null ? null : zone.getName();
    }

    private Double riskScore(Long riskEventId) {
        if (riskEventId == null) {
            return null;
        }
        RiskEvent event = riskEventMapper.selectById(riskEventId);
        return event == null ? null : event.getRiskScore();
    }
}
