package com.smartpool.user;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/**
 * 种子用户口令初始化：V2 迁移中写入的是明文口令（仅演示种子），
 * 启动时统一升级为 BCrypt，避免明文长期留在库里。
 */
@Component
public class UserInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(UserInitializer.class);

    private final SysUserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    public UserInitializer(SysUserMapper userMapper, PasswordEncoder passwordEncoder) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) {
        var users = userMapper.selectList(null);
        int upgraded = 0;
        for (SysUser user : users) {
            String pwd = user.getPassword();
            if (pwd != null && !pwd.startsWith("$2")) {
                user.setPassword(passwordEncoder.encode(pwd));
                userMapper.updateById(user);
                upgraded++;
            }
        }
        if (upgraded > 0) {
            log.info("种子用户口令已升级为 BCrypt，共 {} 个", upgraded);
        }
    }
}
