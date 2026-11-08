package com.smartpool.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

/** 审计：告警处置、围栏修改、参数变更、导出都写一条。 */
@Service
public class AuditService {

    private static final Logger log = LoggerFactory.getLogger(AuditService.class);

    private final AuditLogMapper mapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AuditService(AuditLogMapper mapper) {
        this.mapper = mapper;
    }

    public void record(Long actorId, String action, String targetType, String targetId, Map<String, Object> detail) {
        AuditLog entry = new AuditLog();
        entry.setActorId(actorId);
        entry.setAction(action);
        entry.setTargetType(targetType);
        entry.setTargetId(targetId);
        entry.setCreatedAt(LocalDateTime.now());
        try {
            entry.setDetailJson(detail == null ? null : objectMapper.writeValueAsString(detail));
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            entry.setDetailJson(null);
        }
        try {
            mapper.insert(entry);
        } catch (RuntimeException ex) {
            // 审计失败不阻断业务，但必须留日志
            log.error("audit write failed: action={} target={}", action, targetId, ex);
        }
    }
}
