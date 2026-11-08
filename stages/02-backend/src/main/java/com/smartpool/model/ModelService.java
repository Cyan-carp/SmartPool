package com.smartpool.model;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.smartpool.audit.AuditService;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import com.smartpool.live.AiClient;
import com.smartpool.live.LiveFeedService;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * 算力档位：参数模板存在 model_param，当前档位存在 Redis，切换时同步下发推理服务。
 * 指标曲线里的延迟来自推理服务真实返回，算力占比是**模拟值**。
 */
@Service
public class ModelService {

    private static final String MODE_KEY = "smartpool:model:mode";
    private static final String AUTO_KEY = "smartpool:model:auto";

    private final ModelParamMapper paramMapper;
    private final ModelMetricMapper metricMapper;
    private final StringRedisTemplate redisTemplate;
    private final AiClient aiClient;
    private final LiveFeedService liveFeedService;
    private final AuditService auditService;

    public ModelService(ModelParamMapper paramMapper,
                        ModelMetricMapper metricMapper,
                        StringRedisTemplate redisTemplate,
                        AiClient aiClient,
                        LiveFeedService liveFeedService,
                        AuditService auditService) {
        this.paramMapper = paramMapper;
        this.metricMapper = metricMapper;
        this.redisTemplate = redisTemplate;
        this.aiClient = aiClient;
        this.liveFeedService = liveFeedService;
        this.auditService = auditService;
    }

    public String currentMode() {
        String mode = redisTemplate.opsForValue().get(MODE_KEY);
        return mode == null ? "PEAK" : mode;
    }

    public boolean auto() {
        return !"false".equals(redisTemplate.opsForValue().get(AUTO_KEY));
    }

    public Map<String, Object> params() {
        List<ModelParam> rows = paramMapper.selectList(Wrappers.<ModelParam>lambdaQuery().orderByAsc(ModelParam::getId));
        Map<String, Object> templates = new LinkedHashMap<>();
        for (ModelParam row : rows) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("confidence", row.getConfidence());
            item.put("windowT", row.getWindowT());
            item.put("stride", row.getStride());
            item.put("computeRatio", row.getComputeRatio());
            templates.put(row.getMode(), item);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("mode", currentMode());
        body.put("auto", auto());
        body.put("templates", templates);
        body.put("placeholder", true);
        body.put("note", "算力占比为模拟值，非实测");
        return body;
    }

    public Map<String, Object> setMode(String mode, boolean auto, String username) {
        if (!List.of("PEAK", "OFFPEAK").contains(mode)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "档位不合法：" + mode);
        }
        redisTemplate.opsForValue().set(MODE_KEY, mode);
        redisTemplate.opsForValue().set(AUTO_KEY, String.valueOf(auto));
        aiClient.setMode(mode);
        auditService.record(null, "MODEL_MODE", "MODEL", mode, Map.of("auto", auto,
                "operator", username == null ? "" : username));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("mode", mode);
        body.put("auto", auto);
        body.put("params", params().get("templates") instanceof Map<?, ?> map ? map.get(mode) : null);
        body.put("placeholder", true);
        return body;
    }

    public Map<String, Object> metrics(int minutes) {
        List<ModelMetric> rows = metricMapper.selectList(Wrappers.<ModelMetric>lambdaQuery()
                .ge(ModelMetric::getTs, LocalDateTime.now().minusMinutes(Math.max(5, minutes)))
                .orderByAsc(ModelMetric::getTs));

        List<Map<String, Object>> points = new ArrayList<>();
        for (ModelMetric row : rows) {
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("ts", row.getTs().toString().substring(11, 19));
            point.put("latencyMs", row.getLatencyMs());
            point.put("fps", row.getFps());
            point.put("computeRatio", row.getComputeRatio());
            points.add(point);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("points", points);
        body.put("mode", currentMode());
        body.put("windowMinutes", minutes);
        body.put("placeholder", true);
        body.put("note", "算力占比为模拟值；延迟来自推理服务返回");
        return body;
    }

    /** 每 10 秒采一次指标：延迟取真实推理耗时，算力占比按档位模板加抖动（模拟）。 */
    @Scheduled(fixedRate = 10_000)
    public void sample() {
        JsonNode frames = liveFeedService.latest();
        if (frames == null) {
            return;
        }
        String mode = currentMode();
        double baseline = "OFFPEAK".equals(mode) ? 0.68 : 1.0;
        double jitter = ThreadLocalRandom.current().nextDouble(-0.03, 0.03);

        ModelMetric metric = new ModelMetric();
        metric.setTs(LocalDateTime.now());
        metric.setLatencyMs(Math.max(1, frames.path("inferMs").asInt(10)));
        metric.setFps(10.0);
        metric.setComputeRatio(Math.round(Math.min(1.0, baseline + jitter) * 1000) / 1000.0);
        metricMapper.insert(metric);

        prune();
    }

    private void prune() {
        if (ThreadLocalRandom.current().nextInt(60) != 0) {
            return;
        }
        metricMapper.delete(Wrappers.<ModelMetric>lambdaQuery()
                .lt(ModelMetric::getTs, LocalDateTime.now().minusHours(24)));
    }

    public Duration retention() {
        return Duration.ofHours(24);
    }
}
