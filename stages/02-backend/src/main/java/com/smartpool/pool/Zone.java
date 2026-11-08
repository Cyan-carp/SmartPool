package com.smartpool.pool;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("zone")
public class Zone {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long poolId;

    private String name;

    /** DEEP / SHALLOW / KIDS / LANE / RESTRICTED */
    private String type;

    /** 归一化多边形，形如 {"points":[{"x":0.1,"y":0.2}],"version":1} */
    private String polygonJson;

    /** CHILD / ADULT / ALL */
    private String allowedGroups;

    private Boolean enabled;
}
