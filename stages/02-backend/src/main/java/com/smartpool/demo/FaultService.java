package com.smartpool.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import com.smartpool.live.LiveFeedService;
import com.smartpool.pool.Camera;
import com.smartpool.pool.CameraMapper;
import com.smartpool.ws.LiveSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * 演示用故障注入：摄像头离线、推理中断（冻结取帧）、推送风暴。
 * 只影响演示观感，不改业务数据。
 */
@Service
public class FaultService {

    private static final Logger log = LoggerFactory.getLogger(FaultService.class);
    private static final List<String> TYPES = List.of("CAMERA_OFFLINE", "INFER_DOWN", "WS_FLOOD");

    private final CameraMapper cameraMapper;
    private final LiveFeedService liveFeedService;
    private final LiveSocketHandler socketHandler;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    private final Map<String, Long> active = new ConcurrentHashMap<>();

    public FaultService(CameraMapper cameraMapper, LiveFeedService liveFeedService, LiveSocketHandler socketHandler) {
        this.cameraMapper = cameraMapper;
        this.liveFeedService = liveFeedService;
        this.socketHandler = socketHandler;
    }

    public Map<String, Object> apply(String type, long seconds, Long cameraId) {
        if (!TYPES.contains(type)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未知故障类型：" + type);
        }
        long duration = Math.max(5, Math.min(seconds, 300));
        long until = System.currentTimeMillis() + duration * 1000;
        active.put(type, until);

        switch (type) {
            case "CAMERA_OFFLINE" -> {
                long id = cameraId == null ? 3L : cameraId;
                Camera camera = cameraMapper.selectById(id);
                if (camera == null) {
                    throw new BizException(ErrorCode.NOT_FOUND, "摄像头不存在");
                }
                camera.setStatus("OFFLINE");
                cameraMapper.updateById(camera);
                socketHandler.broadcast("device.status", Map.of(
                        "deviceId", "camera-" + id, "online", false, "at", System.currentTimeMillis()));
                scheduler.schedule(() -> restoreCamera(id), duration, TimeUnit.SECONDS);
            }
            case "INFER_DOWN" -> {
                liveFeedService.pause(true);
                socketHandler.broadcast("system.notice", Map.of(
                        "level", "degraded", "message", "推理服务不可用（演示注入），画面已冻结"));
                scheduler.schedule(() -> {
                    liveFeedService.pause(false);
                    socketHandler.broadcast("system.notice", Map.of(
                            "level", "ok", "message", "推理服务已恢复（演示注入结束）"));
                }, duration, TimeUnit.SECONDS);
            }
            case "WS_FLOOD" -> {
                JsonNode latest = liveFeedService.latest();
                for (int i = 0; i < 20; i += 1) {
                    if (latest != null) {
                        socketHandler.broadcast("frames", latest);
                    }
                }
            }
            default -> { }
        }

        log.info("fault injected: {} for {}s", type, duration);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("type", type);
        body.put("seconds", duration);
        body.put("until", until);
        return body;
    }

    public List<Map<String, Object>> active() {
        long now = System.currentTimeMillis();
        List<Map<String, Object>> list = new ArrayList<>();
        active.entrySet().removeIf(entry -> entry.getValue() < now);
        active.forEach((type, until) -> {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("type", type);
            item.put("remainSec", Math.max(0, (until - now) / 1000));
            list.add(item);
        });
        return list;
    }

    public void clearAll() {
        active.clear();
        liveFeedService.pause(false);
        for (long id : List.of(1L, 2L, 3L, 4L)) {
            restoreCamera(id);
        }
    }

    private void restoreCamera(long id) {
        Camera camera = cameraMapper.selectById(id);
        if (camera == null) {
            return;
        }
        camera.setStatus("ONLINE");
        cameraMapper.updateById(camera);
        socketHandler.broadcast("device.status", Map.of(
                "deviceId", "camera-" + id, "online", true, "at", System.currentTimeMillis()));
    }
}
