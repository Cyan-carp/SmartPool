package com.smartpool.alert;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("alert")
public class AlertEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long riskEventId;
    private Long poolId;
    private Integer trackNo;
    private Long zoneId;
    /** NOTICE / WEAK / STRONG */
    private String level;
    /** OPEN / ACKED / DISPATCHED / RESOLVED / FALSE_ALARM */
    private String status;
    private String reason;
    private String dedupKey;
    private LocalDateTime triggeredAt;
    private LocalDateTime firstAckAt;
    private LocalDateTime closedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
