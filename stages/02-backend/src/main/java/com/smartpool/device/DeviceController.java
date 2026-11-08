package com.smartpool.device;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartpool.audit.AuditService;
import com.smartpool.common.ApiResponse;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import com.smartpool.pool.Camera;
import com.smartpool.pool.CameraMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 设备健康：摄像头与传感器统一成一张列表。
 * 设备标识用 `camera-<id>` / `device-<id>`，避免两张表主键冲突。
 */
@RestController
@RequestMapping("/api/v1/devices")
public class DeviceController {

    private final CameraMapper cameraMapper;
    private final DeviceMapper deviceMapper;
    private final MaintenanceLogMapper maintenanceMapper;
    private final AuditService auditService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public DeviceController(CameraMapper cameraMapper,
                            DeviceMapper deviceMapper,
                            MaintenanceLogMapper maintenanceMapper,
                            AuditService auditService) {
        this.cameraMapper = cameraMapper;
        this.deviceMapper = deviceMapper;
        this.maintenanceMapper = maintenanceMapper;
        this.auditService = auditService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(@RequestParam(defaultValue = "1") Long poolId,
                                                 @RequestParam(required = false) String type) {
        List<Map<String, Object>> items = new ArrayList<>();

        if (type == null || type.isBlank() || "CAMERA".equals(type)) {
            List<Camera> cameras = cameraMapper.selectList(Wrappers.<Camera>lambdaQuery()
                    .eq(Camera::getPoolId, poolId).orderByAsc(Camera::getId));
            for (Camera camera : cameras) {
                Map<String, Object> metrics = new LinkedHashMap<>();
                metrics.put("cleanliness", camera.getCleanliness());
                metrics.put("sealScore", camera.getSealScore());
                metrics.put("powerOk", camera.getPowerOk());
                metrics.put("position", camera.getPosition());
                items.add(item("camera-" + camera.getId(), camera.getId(), "CAMERA",
                        camera.getName(), camera.getStatus(), metrics));
            }
        }

        if (type == null || type.isBlank() || !"CAMERA".equals(type)) {
            List<Device> devices = deviceMapper.selectList(Wrappers.<Device>lambdaQuery()
                    .eq(Device::getPoolId, poolId).orderByAsc(Device::getId));
            for (Device device : devices) {
                if (type != null && !type.isBlank() && !type.equals(device.getType())) {
                    continue;
                }
                items.add(item("device-" + device.getId(), device.getId(), device.getType(),
                        device.getName(), device.getStatus(), parse(device.getMetricsJson())));
            }
        }

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("items", items);
        body.put("total", items.size());
        body.put("online", items.stream().filter(it -> "ONLINE".equals(it.get("status"))).count());
        return ApiResponse.ok(body);
    }

    @GetMapping("/{key}/maintenance")
    public ApiResponse<List<MaintenanceLog>> history(@PathVariable String key) {
        long rawId = rawId(key);
        return ApiResponse.ok(maintenanceMapper.selectList(Wrappers.<MaintenanceLog>lambdaQuery()
                .eq(MaintenanceLog::getDeviceId, rawId)
                .orderByDesc(MaintenanceLog::getAt)
                .last("LIMIT 20")));
    }

    @PostMapping("/{key}/maintenance")
    public ApiResponse<MaintenanceLog> maintain(@PathVariable String key, @RequestBody Map<String, Object> body) {
        long rawId = rawId(key);
        String type = String.valueOf(body.getOrDefault("type", "CLEAN"));
        if (!List.of("CLEAN", "SEAL_CHECK", "REBOOT", "POWER_CHECK").contains(type)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "维护类型不合法：" + type);
        }
        MaintenanceLog log = new MaintenanceLog();
        log.setDeviceId(rawId);
        log.setType(type);
        log.setNote(body.get("note") == null ? null : String.valueOf(body.get("note")));
        log.setAt(LocalDateTime.now());
        maintenanceMapper.insert(log);

        // 维护后清洗类指标回升（模拟）
        if (key.startsWith("camera-")) {
            Camera camera = cameraMapper.selectById(rawId);
            if (camera != null) {
                if ("CLEAN".equals(type)) {
                    camera.setCleanliness(0.99);
                } else if ("SEAL_CHECK".equals(type)) {
                    camera.setSealScore(0.99);
                } else if ("REBOOT".equals(type)) {
                    camera.setStatus("ONLINE");
                }
                cameraMapper.updateById(camera);
            }
        }
        auditService.record(null, "DEVICE_MAINTENANCE", "DEVICE", key, Map.of("type", type));
        return ApiResponse.ok(log);
    }

    private Map<String, Object> item(String key, Long id, String type, String name,
                                     String status, Map<String, Object> metrics) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("key", key);
        item.put("id", id);
        item.put("type", type);
        item.put("name", name);
        item.put("status", status);
        item.put("metrics", metrics);
        item.put("placeholder", true);
        return item;
    }

    private Map<String, Object> parse(String json) {
        Map<String, Object> metrics = new LinkedHashMap<>();
        if (json == null || json.isBlank()) {
            return metrics;
        }
        try {
            JsonNode node = objectMapper.readTree(json);
            node.fields().forEachRemaining(entry -> metrics.put(entry.getKey(), entry.getValue().asText()));
        } catch (Exception ignored) {
            // 坏数据按空指标处理
        }
        return metrics;
    }

    private long rawId(String key) {
        int index = key.indexOf('-');
        if (index < 0) {
            throw new BizException(ErrorCode.BAD_REQUEST, "设备标识不合法");
        }
        try {
            return Long.parseLong(key.substring(index + 1));
        } catch (NumberFormatException ex) {
            throw new BizException(ErrorCode.BAD_REQUEST, "设备标识不合法");
        }
    }
}
