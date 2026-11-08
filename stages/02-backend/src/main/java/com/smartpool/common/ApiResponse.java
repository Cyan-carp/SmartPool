package com.smartpool.common;

import lombok.Data;

/**
 * 统一响应包络：{ code, message, data, traceId }
 */
@Data
public class ApiResponse<T> {

    private int code;
    private String message;
    private T data;
    private String traceId;

    public static <T> ApiResponse<T> ok(T data) {
        ApiResponse<T> body = new ApiResponse<>();
        body.code = 0;
        body.message = "ok";
        body.data = data;
        body.traceId = TraceIdHolder.current();
        return body;
    }

    public static <T> ApiResponse<T> fail(int code, String message) {
        ApiResponse<T> body = new ApiResponse<>();
        body.code = code;
        body.message = message;
        body.traceId = TraceIdHolder.current();
        return body;
    }
}
