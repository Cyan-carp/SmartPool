-- 兜底池区：覆盖整池，保证任何目标都有归属（细节区域优先命中）
INSERT INTO zone (pool_id, name, type, polygon_json, allowed_groups, enabled)
SELECT 1, '全池', 'POOL',
       '{"points":[{"x":0.0,"y":0.0},{"x":1.0,"y":0.0},{"x":1.0,"y":1.0},{"x":0.0,"y":1.0}],"version":1}',
       'ALL', 1
WHERE NOT EXISTS (SELECT 1 FROM zone WHERE pool_id = 1 AND type = 'POOL');
