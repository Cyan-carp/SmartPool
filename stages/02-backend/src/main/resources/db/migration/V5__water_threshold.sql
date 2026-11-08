-- 水质阈值配置（单泳池一条，M5 引入）
CREATE TABLE water_threshold (
    id              BIGINT NOT NULL AUTO_INCREMENT,
    pool_id         BIGINT NOT NULL,
    turbidity_max   DOUBLE NOT NULL DEFAULT 5.00,
    ph_min          DOUBLE NOT NULL DEFAULT 6.80,
    ph_max          DOUBLE NOT NULL DEFAULT 8.00,
    temperature_min DOUBLE NOT NULL DEFAULT 25.00,
    temperature_max DOUBLE NOT NULL DEFAULT 29.00,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_water_threshold_pool (pool_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT '水质阈值';

INSERT INTO water_threshold (pool_id, turbidity_max, ph_min, ph_max, temperature_min, temperature_max)
VALUES (1, 5.00, 6.80, 8.00, 25.00, 29.00);
