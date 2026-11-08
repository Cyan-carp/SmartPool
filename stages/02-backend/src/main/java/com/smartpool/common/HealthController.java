package com.smartpool.common;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class HealthController {

    private final String provider;

    public HealthController(@Value("${AI_DETECTOR_PROVIDER:mock}") String provider) {
        this.provider = provider;
    }

    @GetMapping("/api/health")
    public ApiResponse<Map<String, Object>> health() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "UP");
        body.put("service", "smartpool-backend");
        body.put("version", "0.1.0");
        body.put("detectorProvider", provider);
        body.put("modelLoaded", false);
        body.put("time", OffsetDateTime.now().toString());
        return ApiResponse.ok(body);
    }
}
