package com.smartpool.auth.dto;

import lombok.Data;

@Data
public class LoginResponse {

    private String token;
    private long expiresIn;
    private UserView user;
}
