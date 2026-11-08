package com.smartpool.stats;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 基于 track_sample 的看板聚合查询。 */
@Service
public class StatsQueryService {

    private static final int GRID_COLS = 24;
    private static final int GRID_ROWS = 16;

    private final JdbcTemplate jdbcTemplate;

    public StatsQueryService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Map<String, Object> heatmap(long poolId, int minutes) {
        Timestamp from = Timestamp.valueOf(LocalDateTime.now().minusMinutes(Math.max(1, minutes)));
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT LEAST(?, FLOOR(x * ?)) AS gx, LEAST(?, FLOOR(y * ?)) AS gy, COUNT(*) AS c "
                        + "FROM track_sample WHERE pool_id = ? AND ts >= ? GROUP BY gx, gy",
                GRID_COLS - 1, GRID_COLS, GRID_ROWS - 1, GRID_ROWS, poolId, from);

        int[][] matrix = new int[GRID_ROWS][GRID_COLS];
        int max = 0;
        for (Map<String, Object> row : rows) {
            int gx = ((Number) row.get("gx")).intValue();
            int gy = ((Number) row.get("gy")).intValue();
            int count = ((Number) row.get("c")).intValue();
            matrix[gy][gx] = count;
            max = Math.max(max, count);
        }

        List<List<Integer>> grid = new ArrayList<>();
        for (int y = 0; y < GRID_ROWS; y += 1) {
            List<Integer> line = new ArrayList<>();
            for (int x = 0; x < GRID_COLS; x += 1) {
                line.add(matrix[y][x]);
            }
            grid.add(line);
        }

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("cols", GRID_COLS);
        body.put("rows", GRID_ROWS);
        body.put("max", max);
        body.put("windowMinutes", minutes);
        body.put("grid", grid);
        return body;
    }

    public Map<String, Object> trend(long poolId, int minutes) {
        Timestamp from = Timestamp.valueOf(LocalDateTime.now().minusMinutes(Math.max(1, minutes)));
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT DATE_FORMAT(ts, '%H:%i') AS t, ROUND(AVG(risk_score), 3) AS avgRisk, "
                        + "SUM(CASE WHEN risk_score >= 0.55 THEN 1 ELSE 0 END) AS riskCnt "
                        + "FROM track_sample WHERE pool_id = ? AND ts >= ? GROUP BY t ORDER BY t",
                poolId, from);

        List<Map<String, Object>> points = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("time", row.get("t"));
            point.put("avgRisk", row.get("avgRisk"));
            point.put("riskCount", row.get("riskCnt"));
            points.add(point);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("points", points);
        body.put("windowMinutes", minutes);
        return body;
    }

    public Map<String, Object> crowd(long poolId, int hours) {
        Timestamp from = Timestamp.valueOf(LocalDateTime.now().minusHours(Math.max(1, hours)));
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT DATE_FORMAT(ts, '%H:00') AS h, DATE_FORMAT(ts, '%H:%i') AS m, "
                        + "COUNT(DISTINCT track_no) AS c "
                        + "FROM track_sample WHERE pool_id = ? AND ts >= ? GROUP BY h, m ORDER BY h, m",
                poolId, from);

        Map<String, Integer> peaks = new HashMap<>();
        for (Map<String, Object> row : rows) {
            String hour = String.valueOf(row.get("h"));
            int count = ((Number) row.get("c")).intValue();
            peaks.merge(hour, count, Math::max);
        }

        List<Map<String, Object>> bars = new ArrayList<>();
        peaks.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .forEach(entry -> {
                    Map<String, Object> bar = new LinkedHashMap<>();
                    bar.put("hour", entry.getKey());
                    bar.put("peak", entry.getValue());
                    bars.add(bar);
                });

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("bars", bars);
        body.put("windowHours", hours);
        return body;
    }
}
