package com.smartpool.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("model_param")
public class ModelParam {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String mode;
    private Double confidence;
    private Integer windowT;
    private String stride;
    private Double computeRatio;
    private LocalDateTime updatedAt;
}
