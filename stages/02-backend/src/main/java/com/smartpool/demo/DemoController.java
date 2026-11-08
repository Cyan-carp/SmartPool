package com.smartpool.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.smartpool.alert.AlertService;
import com.smartpool.common.ApiResponse;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import com.smartpool.live.AiClient;
import com.smartpool.live.LiveFeedService;
import com.smartpool.model.ModelService;
import com.smartpool.pool.Camera;
import com.smartpool.pool.CameraMapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.smartpool.water.WaterService;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 演示控制：剧本注入、时钟倍速、重置、故障注入与状态汇总。
 * 契约见接口契约 2.7；M6 补齐故障注入与状态面板。
 */
@RestController
@RequestMapping("/api/v1/demo")
@PreAuthorize("hasAnyRole('ADMIN','SYS_ADMIN','DEMO')")
public class DemoController {

    private static final List<String> SCENARIOS = List.of(
            "normal", "drown_still", "zone_intrude", "night_intrude", "water_poor");

    private final SimulatorGateway gateway;
    private final FaultService faultService;
    private final AiClient aiClient;
    private final LiveFeedService liveFeedService;
    private final AlertService alertService;
    private final ModelService modelService;
    private final WaterService waterService;
    private final CameraMapper cameraMapper;

    public DemoController(SimulatorGateway gateway,
                          FaultService faultService,
                          AiClient aiClient,
                          LiveFeedService liveFeedService,
                          AlertService alertService,
                          ModelService modelService,
                          WaterService waterService,
                          CameraMapper cameraMapper) {
        this.gateway = gateway;
        this.faultService = faultService;
        this.aiClient = aiClient;
        this.liveFeedService = liveFeedService;
        this.alertService = alertService;
        this.modelService = modelService;
        this.waterService = waterService;
        this.cameraMapper = cameraMapper;
    }

    @GetMapping("/scenarios")
    public ApiResponse<JsonNode> scenarios() {
        return ApiResponse.ok(gateway.get("/sim/scenarios"));
    }

    @PostMapping("/scenarios/{key}")
    public ApiResponse<JsonNode> trigger(@PathVariable String key) {
        if (!SCENARIOS.contains(key)) {
            throw new BizException(ErrorCode.BAD_REQUEST, "未知剧本：" + key);
        }
        return ApiResponse.ok(gateway.post("/sim/scenario/" + key));
    }

    @PostMapping("/clock")
    public ApiResponse<JsonNode> clock(@RequestBody Map<String, Object> body) {
        double speed = Double.parseDouble(String.valueOf(body.getOrDefault("speed", 1)));
        return ApiResponse.ok(gateway.postJson("/sim/clock", Map.of("speed", speed)));
    }

    @PostMapping("/reset")
    public ApiResponse<Map<String, Object>> reset(@RequestParam(defaultValue = "2026") int seed,
                                                  @RequestParam(defaultValue = "8") int swimmerCount,
                                                  @RequestParam(defaultValue = "false") boolean clearAlerts) {
        gateway.post("/sim/scenario/normal");
        JsonNode seeded = gateway.postJson("/sim/seed?seed=" + seed + "&swimmerCount=" + swimmerCount, null);
        gateway.resetAi();
        faultService.clearAll();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("seed", seed);
        body.put("swimmerCount", swimmerCount);
        body.put("scenario", seeded.path("scenario").asText("normal"));
        body.put("reset", true);
        if (clearAlerts) {
            body.put("cleared", alertService.clearAll());
        }
        return ApiResponse.ok(body);
    }

    // ---------- 故障注入 ----------

    @PostMapping("/faults")
    public ApiResponse<Map<String, Object>> injectFault(@RequestBody Map<String, Object> body) {
        String type = String.valueOf(body.getOrDefault("type", "INFER_DOWN"));
        long seconds = body.get("seconds") == null ? 20 : Long.parseLong(String.valueOf(body.get("seconds")));
        Long cameraId = body.get("cameraId") == null ? null : Long.parseLong(String.valueOf(body.get("cameraId")));
        return ApiResponse.ok(faultService.apply(type, seconds, cameraId));
    }

    @GetMapping("/faults")
    public ApiResponse<List<Map<String, Object>>> activeFaults() {
        return ApiResponse.ok(faultService.active());
    }

    @PostMapping("/faults/clear")
    public ApiResponse<Map<String, Object>> clearFaults() {
        faultService.clearAll();
        return ApiResponse.ok(Map.of("cleared", true));
    }

    // ---------- 状态汇总 ----------

    /** 演示前的自检面板：一次拿齐各子系统状态。 */
    @GetMapping("/status")
    public ApiResponse<Map<String, Object>> status() {
        Map<String, Object> body = new LinkedHashMap<>();

        boolean aiOk = true;
        try {
            JsonNode health = aiClient.health();
            aiOk = health.path("ok").asBoolean(true);
            body.put("provider", health.path("provider").asText("mock"));
            body.put("modelLoaded", health.path("modelLoaded").asBoolean(false));
        } catch (RuntimeException ex) {
            aiOk = false;
        }
        body.put("aiOk", aiOk);
        body.put("framesPaused", liveFeedService.paused());
        body.put("dataDelayMs", liveFeedService.lastSuccessAt() == 0
                ? -1 : System.currentTimeMillis() - liveFeedService.lastSuccessAt());
        body.put("framesPushed", liveFeedService.broadcastCount());
        body.put("framesFailed", liveFeedService.errorCount());
        body.put("mode", modelService.currentMode());

        JsonNode frames = liveFeedService.latest();
        body.put("scenario", frames == null ? "unknown" : frames.path("scenario").asText("unknown"));
        body.put("targets", frames == null ? 0 : frames.path("targets").size());

        List<Camera> cameras = cameraMapper.selectList(Wrappers.<Camera>lambdaQuery().eq(Camera::getPoolId, 1L));
        long online = cameras.stream().filter(item -> "ONLINE".equals(item.getStatus())).count();
        body.put("camerasOnline", online);
        body.put("camerasTotal", cameras.size());

        waterService.latest(1).forEach((key, value) -> {
            if ("exceeded".equals(key)) {
                body.put("waterExceeded", value);
            }
        });
        body.put("openAlerts", alertService.list("OPEN", null, 1L, 1, 1).get("total"));
        body.put("activeFaults", faultService.active());
        body.put("placeholder", true);
        return ApiResponse.ok(body);
    }
}
