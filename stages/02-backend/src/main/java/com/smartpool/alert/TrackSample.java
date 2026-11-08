package com.smartpool.alert;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("track_sample")
public class TrackSample {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long poolId;
    private Integer trackNo;
    private LocalDateTime ts;
    private Double x;
    private Double y;
    private String posture;
    private Double riskScore;
}
