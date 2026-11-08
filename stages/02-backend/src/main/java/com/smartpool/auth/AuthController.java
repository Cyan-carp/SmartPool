package com.smartpool.auth;

import com.smartpool.auth.dto.LoginRequest;
import com.smartpool.auth.dto.LoginResponse;
import com.smartpool.auth.dto.UserView;
import com.smartpool.common.ApiResponse;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.ok(authService.login(request));
    }

    @GetMapping("/me")
    public ApiResponse<UserView> me(@AuthenticationPrincipal String username) {
        return ApiResponse.ok(authService.current(username));
    }

    @PostMapping("/logout")
    public ApiResponse<Map<String, Object>> logout() {
        // 无状态 JWT：前端清除本地 token 即完成登出
        return ApiResponse.ok(Map.of("closed", true));
    }
}
