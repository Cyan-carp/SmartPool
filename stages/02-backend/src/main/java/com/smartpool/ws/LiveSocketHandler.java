package com.smartpool.ws;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArraySet;

/** 实时通道：只做推送，不做查询。 */
@Component
public class LiveSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(LiveSocketHandler.class);

    private final Set<WebSocketSession> sessions = new CopyOnWriteArraySet<>();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws IOException {
        sessions.add(session);
        log.info("ws connected: {} total={}", session.getId(), sessions.size());
        session.sendMessage(new TextMessage(wrap("system.notice",
                Map.of("level", "info", "message", "实时通道已连接（占位模型模式）"))));
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session);
        log.info("ws closed: {} total={} status={}", session.getId(), sessions.size(), status);
    }

    public void broadcast(String type, Object payload) {
        if (sessions.isEmpty()) {
            return;
        }
        String text = wrap(type, payload);
        for (WebSocketSession session : sessions) {
            if (!session.isOpen()) {
                sessions.remove(session);
                continue;
            }
            try {
                synchronized (session) {
                    session.sendMessage(new TextMessage(text));
                }
            } catch (IOException ex) {
                log.debug("ws send failed: {}", session.getId());
                sessions.remove(session);
            }
        }
    }

    public int onlineCount() {
        return sessions.size();
    }

    private String wrap(String type, Object payload) {
        try {
            return objectMapper.writeValueAsString(Map.of(
                    "type", type,
                    "ts", OffsetDateTime.now().toString(),
                    "payload", payload));
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            return "{\"type\":\"system.notice\",\"payload\":{\"level\":\"error\",\"message\":\"序列化失败\"}}";
        }
    }
}
