package com.smartpool.alert;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartpool.pool.Zone;
import com.smartpool.pool.ZoneMapper;
import org.springframework.stereotype.Component;

import java.util.List;

/** 判断目标位置落在哪个区域（射线法，坐标为归一化值）。 */
@Component
public class ZoneLocator {

    private final ZoneMapper zoneMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    private volatile List<Zone> cache = List.of();
    private volatile long cacheAt;

    public ZoneLocator(ZoneMapper zoneMapper) {
        this.zoneMapper = zoneMapper;
    }

    public Zone locate(long poolId, double x, double y) {
        for (Zone zone : zones(poolId)) {
            if (Boolean.FALSE.equals(zone.getEnabled())) {
                continue;
            }
            if (contains(zone.getPolygonJson(), x, y)) {
                return zone;
            }
        }
        return null;
    }

    /** 区域被修改或删除后立刻失效，避免继续用旧多边形判定。 */
    public void invalidate() {
        cacheAt = 0;
        cache = List.of();
    }

    private List<Zone> zones(long poolId) {
        long now = System.currentTimeMillis();
        if (now - cacheAt > 30_000 || cache.isEmpty()) {
            cache = zoneMapper.selectList(Wrappers.<Zone>lambdaQuery()
                    .eq(Zone::getPoolId, poolId).orderByAsc(Zone::getId));
            cacheAt = now;
        }
        return cache;
    }

    private boolean contains(String polygonJson, double x, double y) {
        try {
            JsonNode points = objectMapper.readTree(polygonJson).path("points");
            int size = points.size();
            if (size < 3) {
                return false;
            }
            boolean inside = false;
            for (int i = 0, j = size - 1; i < size; j = i++) {
                double xi = points.get(i).path("x").asDouble();
                double yi = points.get(i).path("y").asDouble();
                double xj = points.get(j).path("x").asDouble();
                double yj = points.get(j).path("y").asDouble();
                boolean intersects = ((yi > y) != (yj > y))
                        && (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi);
                if (intersects) {
                    inside = !inside;
                }
            }
            return inside;
        } catch (Exception ex) {
            return false;
        }
    }
}
