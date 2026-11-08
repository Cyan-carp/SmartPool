package com.smartpool.auth;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.smartpool.auth.dto.LoginRequest;
import com.smartpool.auth.dto.LoginResponse;
import com.smartpool.auth.dto.UserView;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import com.smartpool.security.JwtService;
import com.smartpool.user.SysUser;
import com.smartpool.user.SysUserMapper;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    private final SysUserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(SysUserMapper userMapper, PasswordEncoder passwordEncoder, JwtService jwtService) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    public LoginResponse login(LoginRequest request) {
        SysUser user = userMapper.selectOne(
                Wrappers.<SysUser>lambdaQuery().eq(SysUser::getUsername, request.getUsername()));
        if (user == null || !Boolean.TRUE.equals(user.getEnabled())) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "用户名或密码错误");
        }
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BizException(ErrorCode.UNAUTHORIZED, "用户名或密码错误");
        }
        LoginResponse response = new LoginResponse();
        response.setToken(jwtService.issue(user));
        response.setExpiresIn(jwtService.expireSeconds());
        response.setUser(UserView.from(user));
        return response;
    }

    public UserView current(String username) {
        SysUser user = userMapper.selectOne(
                Wrappers.<SysUser>lambdaQuery().eq(SysUser::getUsername, username));
        if (user == null) {
            throw new BizException(ErrorCode.UNAUTHORIZED);
        }
        return UserView.from(user);
    }
}
