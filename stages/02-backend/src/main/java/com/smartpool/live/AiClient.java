package com.smartpool.live;

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

/**
 * 推理服务客户端：后端只消费结构化结果，不感知模型实现。
 * 契约见 notes/…/03-架构设计/02-接口契约.md 第四节。
 */
@Component
public class AiClient {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String baseUrl;

    public AiClient(@Value("${smartpool.ai.base-url}") String baseUrl) {
        this.baseUrl = baseUrl;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout((int) Duration.ofSeconds(2).toMillis());
        factory.setReadTimeout((int) Duration.ofSeconds(3).toMillis());
        this.restTemplate = new RestTemplate(factory);
    }

    public JsonNode infer(long poolId) {
        try {
            String body = restTemplate.postForObject(baseUrl + "/infer?poolId=" + poolId, null, String.class);
            return objectMapper.readTree(body);
        } catch (RestClientException | com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new BizException(ErrorCode.DEPENDENCY_UNAVAILABLE, "推理服务不可用");
        }
    }

    /** 下发档位与参数模板到推理服务。 */
    public JsonNode setMode(String mode) {
        try {
            String body = restTemplate.postForObject(baseUrl + "/mode",
                    java.util.Map.of("mode", mode, "auto", true), String.class);
            return objectMapper.readTree(body);
        } catch (RestClientException | com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new BizException(ErrorCode.DEPENDENCY_UNAVAILABLE, "推理服务不可用");
        }
    }

    public JsonNode health() {
        try {
            String body = restTemplate.getForObject(baseUrl + "/health", String.class);
            return objectMapper.readTree(body);
        } catch (RestClientException | com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new BizException(ErrorCode.DEPENDENCY_UNAVAILABLE, "推理服务不可用");
        }
    }
}
