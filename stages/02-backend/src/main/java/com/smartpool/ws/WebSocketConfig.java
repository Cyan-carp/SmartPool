package com.smartpool.ws;

import com.smartpool.security.JwtService;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.server.HandshakeInterceptor;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.Map;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final LiveSocketHandler liveSocketHandler;
    private final JwtService jwtService;

    public WebSocketConfig(LiveSocketHandler liveSocketHandler, JwtService jwtService) {
        this.liveSocketHandler = liveSocketHandler;
        this.jwtService = jwtService;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(liveSocketHandler, "/ws/live")
                .addInterceptors(tokenInterceptor())
                .setAllowedOriginPatterns("*");
    }

    private HandshakeInterceptor tokenInterceptor() {
        return new HandshakeInterceptor() {
            @Override
            public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                           WebSocketHandler wsHandler, Map<String, Object> attributes) {
                String token = UriComponentsBuilder.fromUri(request.getURI()).build()
                        .getQueryParams().getFirst("token");
                if (token == null || token.isBlank()) {
                    return false;
                }
                try {
                    jwtService.parse(token);
                    return true;
                } catch (RuntimeException ex) {
                    return false;
                }
            }

            @Override
            public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                       WebSocketHandler wsHandler, Exception exception) {
                // no-op
            }
        };
    }
}
