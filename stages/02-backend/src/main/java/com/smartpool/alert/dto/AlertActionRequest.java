package com.smartpool.alert.dto;

import lombok.Data;

@Data
public class AlertActionRequest {

    private String note;
    private String assignee;
    /** RESCUED / SELF_RECOVERED / FALSE_ALARM */
    private String result;
}
