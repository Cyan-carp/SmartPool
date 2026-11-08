package com.smartpool.water;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("water_threshold")
public class WaterThreshold {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long poolId;
    private Double turbidityMax;
    private Double phMin;
    private Double phMax;
    private Double temperatureMin;
    private Double temperatureMax;
    private LocalDateTime updatedAt;
}
