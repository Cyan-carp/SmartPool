package com.smartpool.wristband;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("wristband")
public class Wristband {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String code;
    private Integer bindTrackNo;
    private Integer battery;
    private LocalDateTime createdAt;
}
