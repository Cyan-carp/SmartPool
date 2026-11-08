package com.smartpool.model;

import com.smartpool.common.ApiResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 模型与算力档位。演示版模型空置，modelLoaded 恒为 false，
 * 页面必须展示「占位模式」，见工程规范 05。
 */
@RestController
@RequestMapping("/api/v1/model")
public class ModelController {

    private final String provider;
    private final ModelService modelService;

    public ModelController(@Value("${AI_DETECTOR_PROVIDER:mock}") String provider, ModelService modelService) {
        this.provider = provider;
        this.modelService = modelService;
    }

    @GetMapping("/info")
    public ApiResponse<Map<String, Object>> info() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("provider", provider);
        body.put("version", "mock-0.1.0");
        body.put("modelLoaded", false);
        body.put("placeholder", true);
        body.put("inputSize", "640x640");
        body.put("classes", java.util.List.of("swimmer", "drowning"));
        body.put("mode", modelService.currentMode());
        body.put("note", "演示版未加载真实 Mamba-YOLO 权重，检测结果由剧本引擎生成");
        return ApiResponse.ok(body);
    }

    @GetMapping("/params")
    public ApiResponse<Map<String, Object>> params() {
        return ApiResponse.ok(modelService.params());
    }

    @PostMapping("/mode")
    @PreAuthorize("hasAnyRole('ADMIN','SYS_ADMIN')")
    public ApiResponse<Map<String, Object>> setMode(@RequestBody Map<String, Object> body,
                                                    @AuthenticationPrincipal String username) {
        String mode = String.valueOf(body.getOrDefault("mode", "PEAK"));
        boolean auto = body.get("auto") == null || Boolean.parseBoolean(String.valueOf(body.get("auto")));
        return ApiResponse.ok(modelService.setMode(mode, auto, username));
    }

    @GetMapping("/metrics")
    public ApiResponse<Map<String, Object>> metrics(@RequestParam(defaultValue = "30") int minutes) {
        return ApiResponse.ok(modelService.metrics(minutes));
    }
}
