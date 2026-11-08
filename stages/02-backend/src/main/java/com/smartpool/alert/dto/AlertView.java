package com.smartpool.alert.dto;

import com.smartpool.alert.AlertEntity;
import lombok.Data;

import java.time.Duration;
import java.time.LocalDateTime;

@Data
public class AlertView {

    private Long id;
    private Long poolId;
    private Long zoneId;
    private String zoneName;
    private Integer trackNo;
    private String level;
    private String status;
    private String reason;
    private Double riskScore;
    private LocalDateTime triggeredAt;
    private LocalDateTime firstAckAt;
    private LocalDateTime closedAt;
    private Long ageSec;

    public static AlertView from(AlertEntity alert, String zoneName, Double riskScore) {
        AlertView view = new AlertView();
        view.id = alert.getId();
        view.poolId = alert.getPoolId();
        view.zoneId = alert.getZoneId();
        view.zoneName = zoneName;
        view.trackNo = alert.getTrackNo();
        view.level = alert.getLevel();
        view.status = alert.getStatus();
        view.reason = alert.getReason();
        view.riskScore = riskScore;
        view.triggeredAt = alert.getTriggeredAt();
        view.firstAckAt = alert.getFirstAckAt();
        view.closedAt = alert.getClosedAt();
        LocalDateTime end = alert.getClosedAt() != null ? alert.getClosedAt() : LocalDateTime.now();
        view.ageSec = Math.max(0, Duration.between(alert.getTriggeredAt(), end).getSeconds());
        return view;
    }
}
