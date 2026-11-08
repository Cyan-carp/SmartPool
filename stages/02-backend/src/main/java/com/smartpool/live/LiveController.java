package com.smartpool.live;

import com.fasterxml.jackson.databind.JsonNode;
import com.smartpool.common.ApiResponse;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import com.smartpool.ws.LiveSocketHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/live")
public class LiveController {

    private final LiveFeedService liveFeedService;
    private final LiveSocketHandler socketHandler;

    public LiveController(LiveFeedService liveFeedService, LiveSocketHandler socketHandler) {
        this.liveFeedService = liveFeedService;
        this.socketHandler = socketHandler;
    }

    @GetMapping("/snapshot")
    public ApiResponse<Map<String, Object>> snapshot(@RequestParam(defaultValue = "1") Long poolId) {
        JsonNode latest = liveFeedService.latest();
        if (latest == null) {
            throw new BizException(ErrorCode.DEPENDENCY_UNAVAILABLE, "实时快照尚未就绪");
        }
        long delay = System.currentTimeMillis() - liveFeedService.lastSuccessAt();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("poolId", poolId);
        body.put("snapshot", latest);
        body.put("serverTime", OffsetDateTime.now().toString());
        body.put("wsOnline", socketHandler.onlineCount());
        body.put("dataDelayMs", delay);
        body.put("degraded", liveFeedService.degraded());
        body.put("pushedFrames", liveFeedService.broadcastCount());
        body.put("failedFrames", liveFeedService.errorCount());
        return ApiResponse.ok(body);
    }
}
