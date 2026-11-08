-- 演示种子数据（M1）
-- 注意：口令此处为明文占位，应用启动时由 UserInitializer 统一升级为 BCrypt。

INSERT INTO sys_user (username, password, display_name, role, enabled) VALUES
('lifeguard', 'demo1234', '值班救生员', 'RESCUER', 1),
('manager',   'demo1234', '泳池管理员', 'ADMIN', 1),
('sysadmin',  'demo1234', '系统管理员', 'SYS_ADMIN', 1),
('demo',      'demo1234', '演示操作员', 'DEMO', 1);

INSERT INTO pool (id, name, length_m, width_m, open_from, open_to, description) VALUES
(1, '标准训练池 A', 25.00, 12.50, '06:00', '22:00', '演示用 25 米标准池，含深水区/浅水区/儿童区');

INSERT INTO camera (id, pool_id, name, position, status) VALUES
(1, 1, 'CAM-01 全景', 'OVERVIEW', 'ONLINE'),
(2, 1, 'CAM-02 深水区', 'LANE', 'ONLINE'),
(3, 1, 'CAM-03 水下', 'UNDERWATER', 'ONLINE'),
(4, 1, 'CAM-04 儿童区', 'LANE', 'ONLINE');

INSERT INTO zone (pool_id, name, type, polygon_json, allowed_groups, enabled) VALUES
(1, '深水区', 'DEEP', '{"points":[{"x":0.52,"y":0.08},{"x":0.95,"y":0.08},{"x":0.95,"y":0.92},{"x":0.52,"y":0.92}],"version":1}', 'ADULT', 1),
(1, '浅水区', 'SHALLOW', '{"points":[{"x":0.05,"y":0.08},{"x":0.50,"y":0.08},{"x":0.50,"y":0.92},{"x":0.05,"y":0.92}],"version":1}', 'ALL', 1),
(1, '儿童区', 'KIDS', '{"points":[{"x":0.05,"y":0.60},{"x":0.30,"y":0.60},{"x":0.30,"y":0.92},{"x":0.05,"y":0.92}],"version":1}', 'CHILD', 1);

INSERT INTO wristband (code, bind_track_no, battery) VALUES
('WB-0001', 1, 92), ('WB-0002', 2, 88), ('WB-0003', NULL, 76), ('WB-0004', NULL, 95);

INSERT INTO model_param (mode, confidence, window_t, stride, compute_ratio) VALUES
('PEAK',    0.70, 30, '1x1', 1.00),
('OFFPEAK', 0.85, 60, '2x2', 0.68);

INSERT INTO device (pool_id, type, name, status, metrics_json) VALUES
(1, 'SENSOR', '水质传感器 WQ-01', 'ONLINE', '{"temperature":27.0,"turbidity":0.8,"ph":7.4,"chlorine":0.6}'),
(1, 'GATEWAY', '手环网关 GW-01', 'ONLINE', '{"connected":true,"devices":4}');
