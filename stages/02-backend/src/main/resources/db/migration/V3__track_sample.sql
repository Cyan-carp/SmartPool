-- 轨迹采样：供事件回溯使用（与 track/track_point 并存，轨迹会话模型留给后续）
CREATE TABLE track_sample (
    id         BIGINT      NOT NULL AUTO_INCREMENT,
    pool_id    BIGINT      NOT NULL,
    track_no   INT         NOT NULL,
    ts         DATETIME(3) NOT NULL,
    x          DOUBLE      NOT NULL,
    y          DOUBLE      NOT NULL,
    posture    VARCHAR(24) NOT NULL,
    risk_score DOUBLE      NOT NULL,
    PRIMARY KEY (id),
    KEY idx_track_sample (pool_id, track_no, ts)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '目标轨迹采样（回溯用）';
