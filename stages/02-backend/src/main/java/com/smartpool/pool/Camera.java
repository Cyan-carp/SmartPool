package com.smartpool.pool;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("camera")
public class Camera {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long poolId;

    private String name;

    /** OVERVIEW / UNDERWATER / LANE */
    private String position;

    /** ONLINE / OFFLINE / DEGRADED */
    private String status;

    private Double cleanliness;

    private Double sealScore;

    private Boolean powerOk;

    private LocalDateTime lastSeenAt;
}
