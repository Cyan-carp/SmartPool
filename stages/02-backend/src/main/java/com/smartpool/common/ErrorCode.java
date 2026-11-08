package com.smartpool.common;

/** 契约错误码，见 notes/…/03-架构设计/02-接口契约.md */
public enum ErrorCode {

    OK(0, "ok"),
    BAD_REQUEST(40001, "参数校验失败"),
    UNAUTHORIZED(40100, "未登录或登录已过期"),
    FORBIDDEN(40300, "当前角色无权访问"),
    NOT_FOUND(40400, "资源不存在"),
    CONFLICT(40900, "状态冲突"),
    TOO_MANY_REQUESTS(42900, "请求过于频繁"),
    INTERNAL_ERROR(50000, "服务内部错误"),
    DEPENDENCY_UNAVAILABLE(50300, "依赖服务不可用");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int code() {
        return code;
    }

    public String message() {
        return message;
    }
}
