package com.smartpool.pool;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;

@Data
@TableName("pool")
public class Pool {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private BigDecimal lengthM;

    private BigDecimal widthM;

    private String openFrom;

    private String openTo;

    private String description;
}
