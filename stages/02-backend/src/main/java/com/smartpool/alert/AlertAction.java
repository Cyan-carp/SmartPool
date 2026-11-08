package com.smartpool.alert;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("alert_action")
public class AlertAction {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long alertId;
    /** ACK / DISPATCH / RESOLVE / FALSE_ALARM / ESCALATE */
    private String action;
    private Long operatorId;
    private String note;
    private LocalDateTime at;
}
