package com.smartpool.water;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("water_quality")
public class WaterQuality {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long poolId;
    private LocalDateTime ts;
    private Double temperature;
    private Double turbidity;
    private Double ph;
    private Double chlorine;
    private String exceeded;
}
