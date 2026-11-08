package com.smartpool.auth.dto;

import com.smartpool.user.SysUser;
import lombok.Data;

import java.util.List;

@Data
public class UserView {

    private Long id;
    private String username;
    private String displayName;
    private String role;
    private List<String> menus;

    public static UserView from(SysUser user) {
        UserView view = new UserView();
        view.id = user.getId();
        view.username = user.getUsername();
        view.displayName = user.getDisplayName();
        view.role = user.getRole();
        view.menus = menusOf(user.getRole());
        return view;
    }

    private static List<String> menusOf(String role) {
        if (role == null) {
            return List.of();
        }
        return switch (role) {
            case "SYS_ADMIN" -> List.of("monitor", "alerts", "replay", "zones", "dashboard",
                    "devices", "model", "demo", "users");
            case "ADMIN" -> List.of("monitor", "alerts", "replay", "zones", "dashboard",
                    "devices", "model", "demo");
            case "DEMO" -> List.of("monitor", "demo");
            default -> List.of("monitor", "alerts", "replay", "dashboard");
        };
    }
}
