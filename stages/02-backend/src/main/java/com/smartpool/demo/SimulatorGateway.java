package com.smartpool.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/** 后端到模拟数据源的内部通道（仅演示控制使用）。 */
@Component
public class SimulatorGateway {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String baseUrl;
    private final String aiBaseUrl;

    public SimulatorGateway(@Value("${smartpool.simulator.base-url}") String baseUrl,
                            @Value("${smartpool.ai.base-url}") String aiBaseUrl) {
        this.baseUrl = baseUrl;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout((int) Duration.ofSeconds(2).toMillis());
        factory.setReadTimeout((int) Duration.ofSeconds(3).toMillis());
        this.restTemplate = new RestTemplate(factory);
        this.aiBaseUrl = aiBaseUrl;
    }

    public JsonNode get(String path) {
        return read(() -> restTemplate.getForObject(baseUrl + path, String.class));
    }

    public JsonNode post(String path) {
        return read(() -> restTemplate.postForObject(baseUrl + path, null, String.class));
    }

    public JsonNode postJson(String path, Object body) {
        return read(() -> restTemplate.postForObject(baseUrl + path, body, String.class));
    }

    public void resetAi() {
        try {
            restTemplate.postForObject(aiBaseUrl + "/reset", null, String.class);
        } catch (RestClientException ex) {
            throw new BizException(ErrorCode.DEPENDENCY_UNAVAILABLE, "推理服务不可用");
        }
    }

    private JsonNode read(Supplier supplier) {
        try {
            String body = supplier.get();
            return body == null ? objectMapper.createObjectNode() : objectMapper.readTree(body);
        } catch (RestClientException | com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new BizException(ErrorCode.DEPENDENCY_UNAVAILABLE, "模拟数据源不可用");
        }
    }

    @FunctionalInterface
    private interface Supplier {
        String get();
    }
}
