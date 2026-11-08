package com.smartpool.live;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartpool.alert.RiskPipeline;
import com.smartpool.ws.LiveSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Map;

/**
 * 定时向推理服务取帧并广播。
 *
 * <p>设计要点：
 * <ul>
 *   <li>推送频率与缓存频率分离：帧推送默认 100ms（10Hz），Redis 快照默认 1s，避免高频写。</li>
 *   <li>推理不可用时冻结最后一帧并广播一次降级通知；恢复时补发恢复通知。</li>
 *   <li>首帧未就绪时不广播空数据，前端靠 /live/snapshot 与横幅感知。</li>
 * </ul>
 */
@Service
public class LiveFeedService {

    private static final Logger log = LoggerFactory.getLogger(LiveFeedService.class);
    private static final long POOL_ID = 1L;

    private final AiClient aiClient;
    private final LiveSocketHandler socketHandler;
    private final RiskPipeline riskPipeline;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Duration ttl;
    private final long redisCacheMs;

    private volatile JsonNode latest;
    private volatile long lastSuccessAt;
    private volatile boolean degraded;
    private volatile boolean paused;
    private volatile long lastRedisWriteAt;
    private long broadcastCount;
    private long errorCount;

    public LiveFeedService(AiClient aiClient,
                           LiveSocketHandler socketHandler,
                           RiskPipeline riskPipeline,
                           StringRedisTemplate redisTemplate,
                           @Value("${smartpool.live.snapshot-ttl-seconds:30}") long ttlSeconds,
                           @Value("${smartpool.live.redis-cache-ms:1000}") long redisCacheMs) {
        this.aiClient = aiClient;
        this.socketHandler = socketHandler;
        this.riskPipeline = riskPipeline;
        this.redisTemplate = redisTemplate;
        this.ttl = Duration.ofSeconds(ttlSeconds);
        this.redisCacheMs = redisCacheMs;
    }

    @Scheduled(fixedRateString = "${smartpool.live.push-interval-ms:100}")
    public void tick() {
        if (paused) {
            // 演示注入「推理中断」：冻结取帧，让前端感知数据延迟
            return;
        }
        try {
            JsonNode frames = aiClient.infer(POOL_ID);
            latest = frames;
            lastSuccessAt = System.currentTimeMillis();
            broadcastCount++;

            if (degraded) {
                degraded = false;
                socketHandler.broadcast("system.notice",
                        Map.of("level", "ok", "message", "推理服务已恢复"));
                log.info("ai service recovered");
            }

            cacheToRedis(frames);
            socketHandler.broadcast("frames", frames);
            riskPipeline.accept(frames);
        } catch (RuntimeException ex) {
            errorCount++;
            long silence = System.currentTimeMillis() - lastSuccessAt;
            if (!degraded && silence > 3000) {
                degraded = true;
                socketHandler.broadcast("system.notice",
                        Map.of("level", "degraded", "message", "推理服务不可用，画面已冻结"));
                log.warn("ai service degraded: {}", ex.getMessage());
            }
        }
    }

    private void cacheToRedis(JsonNode frames) {
        long now = System.currentTimeMillis();
        if (now - lastRedisWriteAt < redisCacheMs) {
            return;
        }
        lastRedisWriteAt = now;
        try {
            redisTemplate.opsForValue().set("smartpool:live:" + POOL_ID,
                    objectMapper.writeValueAsString(frames), ttl);
        } catch (RuntimeException | com.fasterxml.jackson.core.JsonProcessingException ex) {
            log.debug("redis cache skipped: {}", ex.getMessage());
        }
    }

    public JsonNode latest() {
        return latest;
    }

    public long lastSuccessAt() {
        return lastSuccessAt;
    }

    public boolean degraded() {
        return degraded;
    }

    /** 演示注入用：暂停/恢复取帧。 */
    public void pause(boolean value) {
        this.paused = value;
    }

    public boolean paused() {
        return paused;
    }

    public long broadcastCount() {
        return broadcastCount;
    }

    public long errorCount() {
        return errorCount;
    }
}
