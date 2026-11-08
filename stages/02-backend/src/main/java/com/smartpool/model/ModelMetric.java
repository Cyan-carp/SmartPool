package com.smartpool.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("model_metric")
public class ModelMetric {

    @TableId(type = IdType.AUTO)
    private Long id;

    private LocalDateTime ts;
    private Integer latencyMs;
    private Double fps;
    private Double computeRatio;
}
