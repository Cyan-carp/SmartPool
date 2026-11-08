-- SmartPool 演示版基础表结构（M1）
-- 约定：主键 BIGINT AUTO_INCREMENT，软删用 deleted_at（时间戳，NULL 为未删）

CREATE TABLE sys_user (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    username     VARCHAR(64)  NOT NULL,
    password     VARCHAR(128) NOT NULL,
    display_name VARCHAR(64)  NOT NULL,
    role         VARCHAR(16)  NOT NULL COMMENT 'RESCUER/ADMIN/SYS_ADMIN/DEMO',
    enabled      TINYINT(1)   NOT NULL DEFAULT 1,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_sys_user_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '账号';

CREATE TABLE pool (
    id          BIGINT        NOT NULL AUTO_INCREMENT,
    name        VARCHAR(64)   NOT NULL,
    length_m    DECIMAL(6, 2) NOT NULL DEFAULT 25.00,
    width_m     DECIMAL(6, 2) NOT NULL DEFAULT 12.50,
    open_from   VARCHAR(8)    NOT NULL DEFAULT '06:00',
    open_to     VARCHAR(8)    NOT NULL DEFAULT '22:00',
    description VARCHAR(255)  NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '泳池';

CREATE TABLE camera (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    pool_id      BIGINT       NOT NULL,
    name         VARCHAR(64)  NOT NULL,
    position     VARCHAR(16)  NOT NULL DEFAULT 'OVERVIEW' COMMENT 'OVERVIEW/UNDERWATER/LANE',
    status       VARCHAR(16)  NOT NULL DEFAULT 'ONLINE' COMMENT 'ONLINE/OFFLINE/DEGRADED',
    cleanliness  DOUBLE       NOT NULL DEFAULT 0.95,
    seal_score   DOUBLE       NOT NULL DEFAULT 0.98,
    power_ok     TINYINT(1)   NOT NULL DEFAULT 1,
    last_seen_at DATETIME     NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_camera_pool (pool_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '摄像头';

CREATE TABLE zone (
    id             BIGINT      NOT NULL AUTO_INCREMENT,
    pool_id        BIGINT      NOT NULL,
    name           VARCHAR(64) NOT NULL,
    type           VARCHAR(16) NOT NULL COMMENT 'DEEP/SHALLOW/KIDS/LANE/RESTRICTED',
    polygon_json   TEXT        NOT NULL,
    allowed_groups VARCHAR(32) NOT NULL DEFAULT 'ALL' COMMENT 'ALL/ADULT/CHILD',
    enabled        TINYINT(1)  NOT NULL DEFAULT 1,
    created_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_zone_pool (pool_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '区域与电子围栏';

CREATE TABLE wristband (
    id            BIGINT      NOT NULL AUTO_INCREMENT,
    code          VARCHAR(32) NOT NULL,
    bind_track_no INT         NULL,
    battery       INT         NOT NULL DEFAULT 90,
    created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_wristband_code (code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '智能手环（合成）';

CREATE TABLE track (
    id         BIGINT      NOT NULL AUTO_INCREMENT,
    pool_id    BIGINT      NOT NULL,
    track_no   INT         NOT NULL,
    group_type VARCHAR(16) NOT NULL DEFAULT 'ADULT',
    started_at DATETIME    NOT NULL,
    ended_at   DATETIME    NULL,
    KEY idx_track_pool (pool_id, started_at),
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '目标轨迹会话';

CREATE TABLE track_point (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    track_id   BIGINT       NOT NULL,
    ts         DATETIME(3)  NOT NULL,
    x          DOUBLE       NOT NULL,
    y          DOUBLE       NOT NULL,
    posture    VARCHAR(24)  NOT NULL DEFAULT 'swimming',
    risk_score DOUBLE       NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_track_point (track_id, ts)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '轨迹采样';

CREATE TABLE risk_event (
    id            BIGINT       NOT NULL AUTO_INCREMENT,
    pool_id       BIGINT       NOT NULL,
    track_no      INT          NOT NULL,
    risk_score    DOUBLE       NOT NULL,
    reason        VARCHAR(255) NOT NULL,
    evidence_json TEXT         NULL,
    triggered_at  DATETIME(3)  NOT NULL,
    PRIMARY KEY (id),
    KEY idx_risk_event (pool_id, triggered_at),
    KEY idx_risk_track (track_no)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '风险事件';

CREATE TABLE alert (
    id            BIGINT       NOT NULL AUTO_INCREMENT,
    risk_event_id BIGINT       NULL,
    pool_id       BIGINT       NOT NULL,
    track_no      INT          NULL,
    zone_id       BIGINT       NULL,
    level         VARCHAR(16)  NOT NULL COMMENT 'NOTICE/WEAK/STRONG',
    status        VARCHAR(16)  NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN/ACKED/DISPATCHED/RESOLVED/FALSE_ALARM',
    reason        VARCHAR(255) NOT NULL,
    dedup_key     VARCHAR(96)  NOT NULL,
    triggered_at  DATETIME(3)  NOT NULL,
    first_ack_at  DATETIME(3)  NULL,
    closed_at     DATETIME(3)  NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_alert_dedup (dedup_key),
    KEY idx_alert_query (pool_id, status, triggered_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '告警';

CREATE TABLE alert_action (
    id          BIGINT       NOT NULL AUTO_INCREMENT,
    alert_id    BIGINT       NOT NULL,
    action      VARCHAR(24)  NOT NULL COMMENT 'ACK/DISPATCH/RESOLVE/FALSE_ALARM/ESCALATE',
    operator_id BIGINT       NULL,
    note        VARCHAR(255) NULL,
    at          DATETIME(3)  NOT NULL,
    PRIMARY KEY (id),
    KEY idx_alert_action (alert_id, at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '告警处置时间线';

CREATE TABLE event_clip (
    id            BIGINT      NOT NULL AUTO_INCREMENT,
    risk_event_id BIGINT      NOT NULL,
    window_start  DATETIME(3) NOT NULL,
    window_end    DATETIME(3) NOT NULL,
    payload_json  MEDIUMTEXT  NULL,
    created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_event_clip (risk_event_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '事件片段';

CREATE TABLE device (
    id           BIGINT      NOT NULL AUTO_INCREMENT,
    pool_id      BIGINT      NOT NULL,
    type         VARCHAR(24) NOT NULL COMMENT 'CAMERA/GATEWAY/SENSOR',
    name         VARCHAR(64) NOT NULL,
    status       VARCHAR(16) NOT NULL DEFAULT 'ONLINE',
    metrics_json TEXT        NULL,
    created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_device_pool (pool_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '设备';

CREATE TABLE maintenance_log (
    id          BIGINT      NOT NULL AUTO_INCREMENT,
    device_id   BIGINT      NOT NULL,
    type        VARCHAR(24) NOT NULL COMMENT 'CLEAN/SEAL_CHECK/REBOOT',
    operator_id BIGINT      NULL,
    note        VARCHAR(255) NULL,
    at          DATETIME(3) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_maintenance_device (device_id, at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '设备维护记录';

CREATE TABLE water_quality (
    id          BIGINT      NOT NULL AUTO_INCREMENT,
    pool_id     BIGINT      NOT NULL,
    ts          DATETIME(3) NOT NULL,
    temperature DOUBLE      NOT NULL,
    turbidity   DOUBLE      NOT NULL,
    ph          DOUBLE      NOT NULL,
    chlorine    DOUBLE      NOT NULL,
    exceeded    VARCHAR(64) NULL,
    PRIMARY KEY (id),
    KEY idx_water_quality (pool_id, ts)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '水质采样';

CREATE TABLE model_param (
    id            BIGINT      NOT NULL AUTO_INCREMENT,
    mode          VARCHAR(16) NOT NULL COMMENT 'PEAK/OFFPEAK',
    confidence    DOUBLE      NOT NULL,
    window_t      INT         NOT NULL,
    stride        VARCHAR(8)  NOT NULL,
    compute_ratio DOUBLE      NOT NULL,
    updated_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_model_param_mode (mode)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '算力档位参数';

CREATE TABLE model_metric (
    id            BIGINT      NOT NULL AUTO_INCREMENT,
    ts            DATETIME(3) NOT NULL,
    latency_ms    INT         NOT NULL,
    fps           DOUBLE      NOT NULL,
    compute_ratio DOUBLE      NOT NULL,
    PRIMARY KEY (id),
    KEY idx_model_metric_ts (ts)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '推理指标采样';

CREATE TABLE export_job (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    status       VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    format       VARCHAR(8)   NOT NULL DEFAULT 'CSV',
    file_path    VARCHAR(255) NULL,
    requested_by BIGINT       NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '导出任务';

CREATE TABLE audit_log (
    id          BIGINT      NOT NULL AUTO_INCREMENT,
    actor_id    BIGINT      NULL,
    action      VARCHAR(48) NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    target_id   VARCHAR(64) NULL,
    detail_json TEXT        NULL,
    created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_audit_actor (actor_id, created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '审计日志';

CREATE TABLE demo_scenario_run (
    id           BIGINT      NOT NULL AUTO_INCREMENT,
    scenario_key VARCHAR(32) NOT NULL,
    run_id       VARCHAR(64) NOT NULL,
    started_at   DATETIME(3) NOT NULL,
    result       VARCHAR(255) NULL,
    PRIMARY KEY (id),
    KEY idx_demo_run (scenario_key, started_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '剧本执行记录';
