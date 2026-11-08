package com.smartpool.common;

import org.slf4j.MDC;

import java.util.UUID;

/** 请求级 traceId，写入 MDC 与响应头，便于日志对账。 */
public final class TraceIdHolder {

    public static final String KEY = "traceId";

    private TraceIdHolder() {
    }

    public static String start() {
        String traceId = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        MDC.put(KEY, traceId);
        return traceId;
    }

    public static String current() {
        String value = MDC.get(KEY);
        return value == null ? "" : value;
    }

    public static void clear() {
        MDC.remove(KEY);
    }
}
