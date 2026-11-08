package com.smartpool.water;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.smartpool.live.LiveFeedService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class WaterService {

    private static final long POOL_ID = 1L;

    private final WaterQualityMapper qualityMapper;
    private final WaterThresholdMapper thresholdMapper;
    private final LiveFeedService liveFeedService;

    public WaterService(WaterQualityMapper qualityMapper,
                        WaterThresholdMapper thresholdMapper,
                        LiveFeedService liveFeedService) {
        this.qualityMapper = qualityMapper;
        this.thresholdMapper = thresholdMapper;
        this.liveFeedService = liveFeedService;
    }

    public WaterThreshold threshold(long poolId) {
        WaterThreshold threshold = thresholdMapper.selectOne(
                Wrappers.<WaterThreshold>lambdaQuery().eq(WaterThreshold::getPoolId, poolId));
        if (threshold == null) {
            threshold = new WaterThreshold();
            threshold.setPoolId(poolId);
            threshold.setTurbidityMax(5.0);
            threshold.setPhMin(6.8);
            threshold.setPhMax(8.0);
            threshold.setTemperatureMin(25.0);
            threshold.setTemperatureMax(29.0);
            thresholdMapper.insert(threshold);
        }
        return threshold;
    }

    public Map<String, Object> latest(long poolId) {
        WaterThreshold threshold = threshold(poolId);
        JsonNode frames = liveFeedService.latest();
        Map<String, Object> item = new LinkedHashMap<>();
        if (frames != null && frames.has("water")) {
            JsonNode water = frames.path("water");
            item.put("temperature", water.path("temperature").asDouble());
            item.put("turbidity", water.path("turbidity").asDouble());
            item.put("ph", water.path("ph").asDouble());
            item.put("chlorine", water.path("chlorine").asDouble());
            item.put("source", "live");
        } else {
            WaterQuality last = qualityMapper.selectOne(Wrappers.<WaterQuality>lambdaQuery()
                    .eq(WaterQuality::getPoolId, poolId)
                    .orderByDesc(WaterQuality::getTs).last("LIMIT 1"));
            if (last != null) {
                item.put("temperature", last.getTemperature());
                item.put("turbidity", last.getTurbidity());
                item.put("ph", last.getPh());
                item.put("chlorine", last.getChlorine());
            }
            item.put("source", "history");
        }
        item.put("exceeded", evaluate(item, threshold));
        item.put("threshold", threshold);
        item.put("placeholder", true);
        return item;
    }

    public Map<String, Object> history(long poolId, int minutes) {
        List<WaterQuality> rows = qualityMapper.selectList(Wrappers.<WaterQuality>lambdaQuery()
                .eq(WaterQuality::getPoolId, poolId)
                .ge(WaterQuality::getTs, LocalDateTime.now().minusMinutes(Math.max(5, minutes)))
                .orderByAsc(WaterQuality::getTs));

        List<Map<String, Object>> points = new ArrayList<>();
        for (WaterQuality row : rows) {
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("ts", row.getTs().toString());
            point.put("temperature", row.getTemperature());
            point.put("turbidity", row.getTurbidity());
            point.put("ph", row.getPh());
            point.put("chlorine", row.getChlorine());
            points.add(point);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("points", points);
        body.put("windowMinutes", minutes);
        body.put("threshold", threshold(poolId));
        return body;
    }

    public WaterThreshold updateThreshold(long poolId, Map<String, Object> body) {
        WaterThreshold threshold = threshold(poolId);
        if (body.get("turbidityMax") != null) {
            threshold.setTurbidityMax(asDouble(body.get("turbidityMax")));
        }
        if (body.get("phMin") != null) {
            threshold.setPhMin(asDouble(body.get("phMin")));
        }
        if (body.get("phMax") != null) {
            threshold.setPhMax(asDouble(body.get("phMax")));
        }
        if (body.get("temperatureMin") != null) {
            threshold.setTemperatureMin(asDouble(body.get("temperatureMin")));
        }
        if (body.get("temperatureMax") != null) {
            threshold.setTemperatureMax(asDouble(body.get("temperatureMax")));
        }
        thresholdMapper.updateById(threshold);
        return threshold;
    }

    /** 超标项：用于大屏提示「检测精度可能下降」。 */
    public List<String> evaluate(Map<String, Object> item, WaterThreshold threshold) {
        List<String> exceeded = new ArrayList<>();
        double turbidity = asDouble(item.getOrDefault("turbidity", 0));
        double ph = asDouble(item.getOrDefault("ph", 7));
        double temperature = asDouble(item.getOrDefault("temperature", 27));
        if (turbidity > threshold.getTurbidityMax()) {
            exceeded.add("TURBIDITY");
        }
        if (ph < threshold.getPhMin() || ph > threshold.getPhMax()) {
            exceeded.add("PH");
        }
        if (temperature < threshold.getTemperatureMin() || temperature > threshold.getTemperatureMax()) {
            exceeded.add("TEMPERATURE");
        }
        return exceeded;
    }

    public void sample(long poolId) {
        JsonNode frames = liveFeedService.latest();
        if (frames == null || !frames.has("water")) {
            return;
        }
        JsonNode water = frames.path("water");
        WaterQuality row = new WaterQuality();
        row.setPoolId(poolId);
        row.setTs(LocalDateTime.now());
        row.setTemperature(water.path("temperature").asDouble());
        row.setTurbidity(water.path("turbidity").asDouble());
        row.setPh(water.path("ph").asDouble());
        row.setChlorine(water.path("chlorine").asDouble());

        Map<String, Object> plain = new LinkedHashMap<>();
        plain.put("turbidity", row.getTurbidity());
        plain.put("ph", row.getPh());
        plain.put("temperature", row.getTemperature());
        List<String> exceeded = evaluate(plain, threshold(poolId));
        row.setExceeded(String.join(",", exceeded));
        qualityMapper.insert(row);
    }

    public long defaultPool() {
        return POOL_ID;
    }

    private double asDouble(Object value) {
        return value == null ? 0 : Double.parseDouble(String.valueOf(value));
    }
}
