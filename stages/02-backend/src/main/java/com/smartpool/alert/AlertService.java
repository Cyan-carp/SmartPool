package com.smartpool.alert;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartpool.alert.dto.AlertView;
import com.smartpool.audit.AuditService;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import com.smartpool.pool.Zone;
import com.smartpool.pool.ZoneMapper;
import com.smartpool.user.SysUser;
import com.smartpool.user.SysUserMapper;
import com.smartpool.ws.LiveSocketHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 告警域：风险事件入库、去重合并、状态机、超时升级、统计与导出。
 *
 * 状态机（契约）：
 *   OPEN -> ACKED -> DISPATCHED -> RESOLVED
 *   任意未关闭 -> FALSE_ALARM
 * 去重：同泳池 + 同目标 + 同区域，60 秒窗口内只保留一条活动告警。
 */
@Service
public class AlertService {

    private static final Logger log = LoggerFactory.getLogger(AlertService.class);

    private static final long DEDUP_WINDOW_SEC = 60;
    private static final long ESCALATE_AFTER_SEC = 30;
    private static final int LEVEL_RANK_NOTICE = 1;
    private static final int LEVEL_RANK_WEAK = 2;
    private static final int LEVEL_RANK_STRONG = 3;

    private final AlertMapper alertMapper;
    private final RiskEventMapper riskEventMapper;
    private final AlertActionMapper actionMapper;
    private final TrackSampleMapper trackSampleMapper;
    private final ZoneMapper zoneMapper;
    private final ZoneLocator zoneLocator;
    private final SysUserMapper userMapper;
    private final LiveSocketHandler socketHandler;
    private final AuditService auditService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AlertService(AlertMapper alertMapper,
                        RiskEventMapper riskEventMapper,
                        AlertActionMapper actionMapper,
                        TrackSampleMapper trackSampleMapper,
                        ZoneMapper zoneMapper,
                        ZoneLocator zoneLocator,
                        SysUserMapper userMapper,
                        LiveSocketHandler socketHandler,
                        AuditService auditService) {
        this.alertMapper = alertMapper;
        this.riskEventMapper = riskEventMapper;
        this.actionMapper = actionMapper;
        this.trackSampleMapper = trackSampleMapper;
        this.zoneMapper = zoneMapper;
        this.zoneLocator = zoneLocator;
        this.userMapper = userMapper;
        this.socketHandler = socketHandler;
        this.auditService = auditService;
    }

    // ---------- 入库与去重 ----------

    @Transactional
    public void ingest(JsonNode frames) {
        JsonNode targets = frames.path("targets");
        if (!targets.isArray()) {
            return;
        }
        long poolId = frames.path("poolId").asLong(1);
        for (JsonNode target : targets) {
            String level = target.path("level").asText("NORMAL");
            int rank = rank(level);
            if (rank < LEVEL_RANK_WEAK) {
                continue;
            }
            int trackNo = target.path("trackNo").asInt();
            JsonNode box = target.path("box");
            double cx = box.path("x").asDouble() + box.path("w").asDouble() / 2;
            double cy = box.path("y").asDouble() + box.path("h").asDouble() / 2;
            Zone zone = zoneLocator.locate(poolId, cx, cy);
            Long zoneId = zone == null ? null : zone.getId();
            double score = target.path("riskScore").asDouble(0);
            String reason = target.path("reason").asText("");

            // 锁存语义：只要该目标还有未确认（OPEN）的告警，就不再另开新单，
            // 只做等级/原因升级；人工确认之后才可能产生下一次告警。
            AlertEntity open = findOpenAlert(poolId, trackNo, zoneId);
            if (open != null) {
                if (rank > rank(open.getLevel())) {
                    open.setLevel(level);
                    open.setReason(reason);
                    open.setUpdatedAt(LocalDateTime.now());
                    alertMapper.updateById(open);
                    recordAction(open.getId(), "ESCALATE", null, "风险升级为 " + level);
                    push("alert.updated", view(open));
                }
                continue;
            }

            String bucket = String.valueOf(System.currentTimeMillis() / 1000 / DEDUP_WINDOW_SEC);
            String dedupKey = poolId + ":" + trackNo + ":" + (zoneId == null ? 0 : zoneId) + ":" + bucket;

            AlertEntity existing = alertMapper.selectOne(
                    Wrappers.<AlertEntity>lambdaQuery().eq(AlertEntity::getDedupKey, dedupKey));

            if (existing != null) {
                if (rank > rank(existing.getLevel())) {
                    existing.setLevel(level);
                    existing.setReason(reason);
                    existing.setUpdatedAt(LocalDateTime.now());
                    alertMapper.updateById(existing);
                    recordAction(existing.getId(), "ESCALATE", null, "风险升级为 " + level);
                    push("alert.updated", view(existing));
                }
                continue;
            }

            RiskEvent event = new RiskEvent();
            event.setPoolId(poolId);
            event.setTrackNo(trackNo);
            event.setRiskScore(score);
            event.setReason(reason);
            event.setEvidenceJson(writeJson(target.path("riskDetail")));
            event.setTriggeredAt(LocalDateTime.now());
            riskEventMapper.insert(event);

            AlertEntity alert = new AlertEntity();
            alert.setRiskEventId(event.getId());
            alert.setPoolId(poolId);
            alert.setTrackNo(trackNo);
            alert.setZoneId(zoneId);
            alert.setLevel(level);
            alert.setStatus("OPEN");
            alert.setReason(reason);
            alert.setDedupKey(dedupKey);
            alert.setTriggeredAt(event.getTriggeredAt());
            alert.setCreatedAt(LocalDateTime.now());
            alert.setUpdatedAt(LocalDateTime.now());
            alertMapper.insert(alert);

            recordAction(alert.getId(), "CREATE", null, "系统触发：" + reason);
            push("alert.created", view(alert));
            log.info("alert created id={} track={} level={} zone={}", alert.getId(), trackNo, level, zoneId);
        }
    }

    /** 未确认的告警（锁存源）：同池 + 同目标 + 同区域。 */
    public AlertEntity findOpenAlert(long poolId, int trackNo, Long zoneId) {
        return alertMapper.selectOne(Wrappers.<AlertEntity>lambdaQuery()
                .eq(AlertEntity::getPoolId, poolId)
                .eq(AlertEntity::getTrackNo, trackNo)
                .eq(zoneId != null, AlertEntity::getZoneId, zoneId)
                .isNull(zoneId == null, AlertEntity::getZoneId)
                .eq(AlertEntity::getStatus, "OPEN")
                .orderByAsc(AlertEntity::getTriggeredAt)
                .last("LIMIT 1"));
    }

    /** 越界告警：未确认告警存在时不重复建单；否则按 60 秒窗口去重。 */
    @Transactional
    public boolean createBoundaryAlert(long poolId, int trackNo, Long zoneId, String zoneName,
                                       String group, long seconds, String reason) {
        if (findOpenAlert(poolId, trackNo, zoneId) != null) {
            return false;
        }
        String bucket = String.valueOf(System.currentTimeMillis() / 1000 / DEDUP_WINDOW_SEC);
        String dedupKey = poolId + ":" + trackNo + ":" + (zoneId == null ? 0 : zoneId) + ":B" + bucket;
        if (alertMapper.selectCount(Wrappers.<AlertEntity>lambdaQuery()
                .eq(AlertEntity::getDedupKey, dedupKey)) > 0) {
            return false;
        }

        RiskEvent event = new RiskEvent();
        event.setPoolId(poolId);
        event.setTrackNo(trackNo);
        event.setRiskScore(0.62);
        event.setReason(reason);
        event.setEvidenceJson("{\"group\":\"" + group + "\",\"zone\":\"" + zoneName
                + "\",\"durationSec\":" + seconds + ",\"placeholder\":true}");
        event.setTriggeredAt(LocalDateTime.now());
        riskEventMapper.insert(event);

        AlertEntity alert = new AlertEntity();
        alert.setRiskEventId(event.getId());
        alert.setPoolId(poolId);
        alert.setTrackNo(trackNo);
        alert.setZoneId(zoneId);
        alert.setLevel("WEAK");
        alert.setStatus("OPEN");
        alert.setReason(reason);
        alert.setDedupKey(dedupKey);
        alert.setTriggeredAt(event.getTriggeredAt());
        alert.setCreatedAt(LocalDateTime.now());
        alert.setUpdatedAt(LocalDateTime.now());
        alertMapper.insert(alert);

        recordAction(alert.getId(), "CREATE", null, "围栏触发：" + reason);
        push("alert.created", view(alert));
        return true;
    }

    // ---------- 状态机 ----------

    @Transactional
    public AlertView ack(Long alertId, String username, String note) {
        AlertEntity alert = require(alertId);
        requireStatus(alert, "OPEN", "只有待确认的告警可以确认");
        alert.setStatus("ACKED");
        alert.setFirstAckAt(LocalDateTime.now());
        alert.setUpdatedAt(LocalDateTime.now());
        alertMapper.updateById(alert);
        recordAction(alertId, "ACK", userId(username), note);
        audit(username, "ALERT_ACK", alertId, note);
        push("alert.updated", view(alert));
        return view(alert);
    }

    @Transactional
    public AlertView dispatch(Long alertId, String username, String assignee, String note) {
        AlertEntity alert = require(alertId);
        requireStatus(alert, "ACKED", "只有已确认的告警可以派单");
        alert.setStatus("DISPATCHED");
        alert.setUpdatedAt(LocalDateTime.now());
        alertMapper.updateById(alert);
        recordAction(alertId, "DISPATCH", userId(username),
                "指派给 " + (assignee == null || assignee.isBlank() ? "现场救生员" : assignee) + "；" + nullSafe(note));
        audit(username, "ALERT_DISPATCH", alertId, note);
        push("alert.updated", view(alert));
        return view(alert);
    }

    @Transactional
    public AlertView resolve(Long alertId, String username, String result, String note) {
        AlertEntity alert = require(alertId);
        if (!"ACKED".equals(alert.getStatus()) && !"DISPATCHED".equals(alert.getStatus())) {
            throw new BizException(ErrorCode.CONFLICT, "告警需先确认或派单才能解除");
        }
        alert.setStatus("RESOLVED");
        alert.setClosedAt(LocalDateTime.now());
        alert.setUpdatedAt(LocalDateTime.now());
        alertMapper.updateById(alert);
        recordAction(alertId, "RESOLVE", userId(username), resultLabel(result) + "；" + nullSafe(note));
        audit(username, "ALERT_RESOLVE", alertId, note);
        push("alert.updated", view(alert));
        return view(alert);
    }

    @Transactional
    public AlertView markFalseAlarm(Long alertId, String username, String note) {
        AlertEntity alert = require(alertId);
        if (alert.getClosedAt() != null) {
            throw new BizException(ErrorCode.CONFLICT, "告警已关闭");
        }
        alert.setStatus("FALSE_ALARM");
        alert.setClosedAt(LocalDateTime.now());
        alert.setUpdatedAt(LocalDateTime.now());
        alertMapper.updateById(alert);
        recordAction(alertId, "FALSE_ALARM", userId(username), nullSafe(note));
        audit(username, "ALERT_FALSE_ALARM", alertId, note);
        push("alert.updated", view(alert));
        return view(alert);
    }

    /** 超时升级：未处置的弱告警 30 秒后升为强告警。 */
    @Scheduled(fixedRate = 5000)
    @Transactional
    public void escalateExpired() {
        LocalDateTime threshold = LocalDateTime.now().minusSeconds(ESCALATE_AFTER_SEC);
        List<AlertEntity> candidates = alertMapper.selectList(Wrappers.<AlertEntity>lambdaQuery()
                .eq(AlertEntity::getStatus, "OPEN")
                .eq(AlertEntity::getLevel, "WEAK")
                .le(AlertEntity::getTriggeredAt, threshold));
        for (AlertEntity alert : candidates) {
            alert.setLevel("STRONG");
            alert.setUpdatedAt(LocalDateTime.now());
            alertMapper.updateById(alert);
            recordAction(alert.getId(), "ESCALATE", null, "超过 30 秒未处置，自动升级为强告警");
            push("alert.updated", view(alert));
            log.info("alert escalated id={}", alert.getId());
        }
    }

    // ---------- 查询 ----------

    public Map<String, Object> list(String status, String level, Long poolId, int page, int size) {
        LambdaQueryWrapper<AlertEntity> wrapper = Wrappers.<AlertEntity>lambdaQuery()
                .eq(poolId != null, AlertEntity::getPoolId, poolId)
                .eq(status != null && !status.isBlank(), AlertEntity::getStatus, status)
                .eq(level != null && !level.isBlank(), AlertEntity::getLevel, level);

        long total = alertMapper.selectCount(wrapper);
        int offset = Math.max(0, (page - 1) * size);
        List<AlertEntity> rows = alertMapper.selectList(wrapper
                .orderByDesc(AlertEntity::getTriggeredAt)
                .last("LIMIT " + offset + "," + size));

        List<AlertView> views = new ArrayList<>();
        for (AlertEntity alert : rows) {
            views.add(view(alert));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("list", views);
        body.put("total", total);
        body.put("page", page);
        body.put("size", size);
        return body;
    }

    public Map<String, Object> detail(Long alertId) {
        AlertEntity alert = require(alertId);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("alert", view(alert));

        List<AlertAction> actions = actionMapper.selectList(Wrappers.<AlertAction>lambdaQuery()
                .eq(AlertAction::getAlertId, alertId).orderByAsc(AlertAction::getAt));
        body.put("actions", actions);

        RiskEvent event = alert.getRiskEventId() == null ? null : riskEventMapper.selectById(alert.getRiskEventId());
        body.put("riskEvent", event);
        body.put("clip", clip(alert));
        return body;
    }

    /** 事件片段：告警前后各 20 秒的轨迹与风险曲线。 */
    public Map<String, Object> clip(AlertEntity alert) {
        LocalDateTime from = alert.getTriggeredAt().minusSeconds(20);
        LocalDateTime to = alert.getTriggeredAt().plusSeconds(20);
        List<TrackSample> samples = alert.getTrackNo() == null ? List.of()
                : trackSampleList(alert.getPoolId(), alert.getTrackNo(), from, to);

        List<Map<String, Object>> points = new ArrayList<>();
        for (TrackSample sample : samples) {
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("ts", sample.getTs().toString());
            point.put("x", sample.getX());
            point.put("y", sample.getY());
            point.put("posture", sample.getPosture());
            point.put("riskScore", sample.getRiskScore());
            points.add(point);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("windowFrom", from.toString());
        body.put("windowTo", to.toString());
        body.put("points", points);
        return body;
    }

    private List<TrackSample> trackSampleList(long poolId, int trackNo, LocalDateTime from, LocalDateTime to) {
        return trackSampleMapper.selectList(Wrappers.<TrackSample>lambdaQuery()
                .eq(TrackSample::getPoolId, poolId)
                .eq(TrackSample::getTrackNo, trackNo)
                .between(TrackSample::getTs, from, to)
                .orderByAsc(TrackSample::getTs));
    }

    /** 演示重置：清空告警、处置记录与风险事件（不影响区域与设备）。 */
    @Transactional
    public Map<String, Object> clearAll() {
        long actions = actionMapper.selectCount(null);
        long alerts = alertMapper.selectCount(null);
        long risks = riskEventMapper.selectCount(null);
        actionMapper.delete(null);
        alertMapper.delete(null);
        riskEventMapper.delete(null);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("alerts", alerts);
        body.put("actions", actions);
        body.put("riskEvents", risks);
        return body;
    }

    /** 某区域下未关闭的告警数（删除区域前校验）。 */
    public long countActiveByZone(Long zoneId) {
        return alertMapper.selectCount(Wrappers.<AlertEntity>lambdaQuery()
                .eq(AlertEntity::getZoneId, zoneId)
                .in(AlertEntity::getStatus, List.of("OPEN", "ACKED", "DISPATCHED")));
    }

    public Map<String, Object> stats(int hours) {
        LocalDateTime from = LocalDateTime.now().minusHours(Math.max(1, hours));
        List<AlertEntity> alerts = alertMapper.selectList(Wrappers.<AlertEntity>lambdaQuery()
                .ge(AlertEntity::getTriggeredAt, from));

        int open = 0;
        int acked = 0;
        int dispatched = 0;
        int resolved = 0;
        int falseAlarm = 0;
        int strong = 0;
        int weak = 0;
        long ackSecondsTotal = 0;
        int ackCount = 0;

        for (AlertEntity alert : alerts) {
            switch (alert.getStatus()) {
                case "OPEN" -> open++;
                case "ACKED" -> acked++;
                case "DISPATCHED" -> dispatched++;
                case "RESOLVED" -> resolved++;
                case "FALSE_ALARM" -> falseAlarm++;
                default -> { }
            }
            if ("STRONG".equals(alert.getLevel())) {
                strong++;
            } else if ("WEAK".equals(alert.getLevel())) {
                weak++;
            }
            if (alert.getFirstAckAt() != null) {
                ackSecondsTotal += Duration.between(alert.getTriggeredAt(), alert.getFirstAckAt()).getSeconds();
                ackCount++;
            }
        }

        int closed = resolved + falseAlarm;
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("hours", hours);
        body.put("total", alerts.size());
        body.put("open", open);
        body.put("acked", acked);
        body.put("dispatched", dispatched);
        body.put("resolved", resolved);
        body.put("falseAlarm", falseAlarm);
        body.put("strong", strong);
        body.put("weak", weak);
        body.put("avgAckSeconds", ackCount == 0 ? 0 : ackSecondsTotal / ackCount);
        body.put("falseAlarmRate", closed == 0 ? 0 : Math.round(falseAlarm * 1000.0 / closed) / 10.0);
        return body;
    }

    public String exportCsv(String status, int hours) {
        LocalDateTime from = LocalDateTime.now().minusHours(Math.max(1, hours));
        List<AlertEntity> rows = alertMapper.selectList(Wrappers.<AlertEntity>lambdaQuery()
                .ge(AlertEntity::getTriggeredAt, from)
                .eq(status != null && !status.isBlank(), AlertEntity::getStatus, status)
                .orderByDesc(AlertEntity::getTriggeredAt)
                .last("LIMIT 5000"));

        StringBuilder builder = new StringBuilder();
        builder.append("告警ID,时间,泳池,目标编号,区域,等级,状态,原因,风险分,首次确认,关闭时间\n");
        for (AlertEntity alert : rows) {
            AlertView view = view(alert);
            builder.append(alert.getId()).append(',')
                    .append(alert.getTriggeredAt()).append(',')
                    .append(alert.getPoolId()).append(',')
                    .append(alert.getTrackNo() == null ? "" : alert.getTrackNo()).append(',')
                    .append(csv(view.getZoneName())).append(',')
                    .append(alert.getLevel()).append(',')
                    .append(alert.getStatus()).append(',')
                    .append(csv(alert.getReason())).append(',')
                    .append(view.getRiskScore() == null ? "" : view.getRiskScore()).append(',')
                    .append(alert.getFirstAckAt() == null ? "" : alert.getFirstAckAt()).append(',')
                    .append(alert.getClosedAt() == null ? "" : alert.getClosedAt()).append('\n');
        }
        return builder.toString();
    }

    // ---------- 工具 ----------

    private AlertEntity require(Long alertId) {
        AlertEntity alert = alertMapper.selectById(alertId);
        if (alert == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "告警不存在");
        }
        return alert;
    }

    private void requireStatus(AlertEntity alert, String expected, String message) {
        if (!expected.equals(alert.getStatus())) {
            throw new BizException(ErrorCode.CONFLICT, message);
        }
    }

    private void recordAction(Long alertId, String action, Long operatorId, String note) {
        AlertAction entry = new AlertAction();
        entry.setAlertId(alertId);
        entry.setAction(action);
        entry.setOperatorId(operatorId);
        entry.setNote(note);
        entry.setAt(LocalDateTime.now());
        actionMapper.insert(entry);
    }

    private AlertView view(AlertEntity alert) {
        String zoneName = null;
        if (alert.getZoneId() != null) {
            Zone zone = zoneMapper.selectById(alert.getZoneId());
            zoneName = zone == null ? null : zone.getName();
        }
        Double score = null;
        if (alert.getRiskEventId() != null) {
            RiskEvent event = riskEventMapper.selectById(alert.getRiskEventId());
            score = event == null ? null : event.getRiskScore();
        }
        return AlertView.from(alert, zoneName, score);
    }

    private void push(String type, Object payload) {
        try {
            socketHandler.broadcast(type, payload);
        } catch (RuntimeException ex) {
            log.debug("ws push failed: {}", ex.getMessage());
        }
    }

    private void audit(String username, String action, Long alertId, String note) {
        auditService.record(userId(username), action, "ALERT", String.valueOf(alertId),
                Map.of("note", nullSafe(note)));
    }

    private Long userId(String username) {
        if (username == null) {
            return null;
        }
        SysUser user = userMapper.selectOne(Wrappers.<SysUser>lambdaQuery().eq(SysUser::getUsername, username));
        return user == null ? null : user.getId();
    }

    private int rank(String level) {
        return switch (level) {
            case "STRONG" -> LEVEL_RANK_STRONG;
            case "WEAK" -> LEVEL_RANK_WEAK;
            case "NOTICE" -> LEVEL_RANK_NOTICE;
            default -> 0;
        };
    }

    private String resultLabel(String result) {
        if (result == null) {
            return "处置完成";
        }
        return switch (result) {
            case "RESCUED" -> "已施救";
            case "SELF_RECOVERED" -> "自行恢复";
            case "FALSE_ALARM" -> "误报";
            default -> result;
        };
    }

    private String nullSafe(String value) {
        return value == null ? "" : value;
    }

    private String csv(String value) {
        if (value == null) {
            return "";
        }
        return '"' + value.replace("\"", "\"\"") + '"';
    }

    private String writeJson(JsonNode node) {
        try {
            return node == null || node.isMissingNode() ? null : objectMapper.writeValueAsString(node);
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            return null;
        }
    }
}
