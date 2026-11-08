package com.smartpool.alert;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("risk_event")
public class RiskEvent {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long poolId;
    private Integer trackNo;
    private Double riskScore;
    private String reason;
    private String evidenceJson;
    private LocalDateTime triggeredAt;
}
