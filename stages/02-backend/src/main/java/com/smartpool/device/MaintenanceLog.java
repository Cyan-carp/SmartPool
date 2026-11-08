package com.smartpool.device;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("maintenance_log")
public class MaintenanceLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long deviceId;
    private String type;
    private Long operatorId;
    private String note;
    private LocalDateTime at;
}
