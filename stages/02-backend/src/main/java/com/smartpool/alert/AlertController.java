package com.smartpool.alert;

import com.smartpool.alert.dto.AlertActionRequest;
import com.smartpool.alert.dto.AlertView;
import com.smartpool.common.ApiResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/alerts")
public class AlertController {

    private final AlertService alertService;
    private final AlertBoardService boardService;

    public AlertController(AlertService alertService, AlertBoardService boardService) {
        this.alertService = alertService;
        this.boardService = boardService;
    }

    /** 大屏锁存源：未确认告警（含「已恢复待确认」）。 */
    @GetMapping("/active")
    public ApiResponse<Map<String, Object>> active(@RequestParam(defaultValue = "1") long poolId) {
        java.util.List<Map<String, Object>> rows = boardService.active(poolId);
        Map<String, Object> body = new java.util.LinkedHashMap<>();
        body.put("list", rows);
        body.put("total", boardService.count(poolId));
        return ApiResponse.ok(body);
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(@RequestParam(required = false) String status,
                                                 @RequestParam(required = false) String level,
                                                 @RequestParam(required = false) Long poolId,
                                                 @RequestParam(defaultValue = "1") int page,
                                                 @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.ok(alertService.list(status, level, poolId, page, Math.min(size, 100)));
    }

    @GetMapping("/{id}")
    public ApiResponse<Map<String, Object>> detail(@PathVariable Long id) {
        return ApiResponse.ok(alertService.detail(id));
    }

    @PostMapping("/{id}/ack")
    public ApiResponse<AlertView> ack(@PathVariable Long id,
                                      @RequestBody(required = false) AlertActionRequest request,
                                      @AuthenticationPrincipal String username) {
        return ApiResponse.ok(alertService.ack(id, username, request == null ? null : request.getNote()));
    }

    @PostMapping("/{id}/dispatch")
    public ApiResponse<AlertView> dispatch(@PathVariable Long id,
                                           @RequestBody(required = false) AlertActionRequest request,
                                           @AuthenticationPrincipal String username) {
        return ApiResponse.ok(alertService.dispatch(id, username,
                request == null ? null : request.getAssignee(),
                request == null ? null : request.getNote()));
    }

    @PostMapping("/{id}/resolve")
    public ApiResponse<AlertView> resolve(@PathVariable Long id,
                                          @RequestBody(required = false) AlertActionRequest request,
                                          @AuthenticationPrincipal String username) {
        return ApiResponse.ok(alertService.resolve(id, username,
                request == null ? null : request.getResult(),
                request == null ? null : request.getNote()));
    }

    @PostMapping("/{id}/false-alarm")
    public ApiResponse<AlertView> falseAlarm(@PathVariable Long id,
                                             @RequestBody(required = false) AlertActionRequest request,
                                             @AuthenticationPrincipal String username) {
        return ApiResponse.ok(alertService.markFalseAlarm(id, username,
                request == null ? null : request.getNote()));
    }

    @GetMapping("/export.csv")
    public ResponseEntity<byte[]> export(@RequestParam(required = false) String status,
                                         @RequestParam(defaultValue = "24") int hours) {
        String csv = alertService.exportCsv(status, hours);
        byte[] body = ("\uFEFF" + csv).getBytes(StandardCharsets.UTF_8);
        String filename = "alerts-" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss")) + ".csv";
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentType(new MediaType("text", "csv", StandardCharsets.UTF_8))
                .body(body);
    }
}
