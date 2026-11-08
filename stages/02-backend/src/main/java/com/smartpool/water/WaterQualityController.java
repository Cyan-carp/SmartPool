package com.smartpool.water;

import com.smartpool.audit.AuditService;
import com.smartpool.common.ApiResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/water-quality")
public class WaterQualityController {

    private final WaterService waterService;
    private final AuditService auditService;

    public WaterQualityController(WaterService waterService, AuditService auditService) {
        this.waterService = waterService;
        this.auditService = auditService;
    }

    @GetMapping("/latest")
    public ApiResponse<Map<String, Object>> latest(@RequestParam(defaultValue = "1") long poolId) {
        return ApiResponse.ok(waterService.latest(poolId));
    }

    @GetMapping("/history")
    public ApiResponse<Map<String, Object>> history(@RequestParam(defaultValue = "1") long poolId,
                                                    @RequestParam(defaultValue = "60") int minutes) {
        return ApiResponse.ok(waterService.history(poolId, minutes));
    }

    @PutMapping("/thresholds")
    @PreAuthorize("hasAnyRole('ADMIN','SYS_ADMIN')")
    public ApiResponse<WaterThreshold> updateThresholds(@RequestBody Map<String, Object> body) {
        long poolId = body.get("poolId") == null ? 1L : Long.parseLong(String.valueOf(body.get("poolId")));
        WaterThreshold threshold = waterService.updateThreshold(poolId, body);
        auditService.record(null, "WATER_THRESHOLD_UPDATE", "POOL", String.valueOf(poolId),
                Map.of("turbidityMax", threshold.getTurbidityMax(),
                        "phMin", threshold.getPhMin(),
                        "phMax", threshold.getPhMax()));
        return ApiResponse.ok(threshold);
    }
}
