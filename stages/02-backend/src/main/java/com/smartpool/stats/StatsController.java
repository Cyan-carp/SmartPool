package com.smartpool.stats;

import com.smartpool.alert.AlertService;
import com.smartpool.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/stats")
public class StatsController {

    private final AlertService alertService;
    private final StatsQueryService statsQueryService;

    public StatsController(AlertService alertService, StatsQueryService statsQueryService) {
        this.alertService = alertService;
        this.statsQueryService = statsQueryService;
    }

    @GetMapping("/overview")
    public ApiResponse<Map<String, Object>> overview(@RequestParam(defaultValue = "24") int hours) {
        return ApiResponse.ok(alertService.stats(hours));
    }

    @GetMapping("/heatmap")
    public ApiResponse<Map<String, Object>> heatmap(@RequestParam(defaultValue = "1") long poolId,
                                                    @RequestParam(defaultValue = "30") int minutes) {
        return ApiResponse.ok(statsQueryService.heatmap(poolId, Math.min(minutes, 720)));
    }

    @GetMapping("/trend")
    public ApiResponse<Map<String, Object>> trend(@RequestParam(defaultValue = "1") long poolId,
                                                  @RequestParam(defaultValue = "30") int minutes) {
        return ApiResponse.ok(statsQueryService.trend(poolId, Math.min(minutes, 720)));
    }

    @GetMapping("/crowd")
    public ApiResponse<Map<String, Object>> crowd(@RequestParam(defaultValue = "1") long poolId,
                                                  @RequestParam(defaultValue = "6") int hours) {
        return ApiResponse.ok(statsQueryService.crowd(poolId, Math.min(hours, 24)));
    }
}
