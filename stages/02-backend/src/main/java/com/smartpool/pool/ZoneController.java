package com.smartpool.pool;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.smartpool.alert.AlertService;
import com.smartpool.audit.AuditService;
import com.smartpool.alert.ZoneLocator;
import com.smartpool.common.ApiResponse;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/zones")
public class ZoneController {

    private static final List<String> TYPES = List.of("DEEP", "SHALLOW", "KIDS", "LANE", "RESTRICTED", "POOL");
    private static final List<String> GROUPS = List.of("ALL", "ADULT", "CHILD");

    private final ZoneMapper zoneMapper;
    private final ZoneLocator zoneLocator;
    private final AlertService alertService;
    private final AuditService auditService;

    public ZoneController(ZoneMapper zoneMapper, ZoneLocator zoneLocator,
                          AlertService alertService, AuditService auditService) {
        this.zoneMapper = zoneMapper;
        this.zoneLocator = zoneLocator;
        this.alertService = alertService;
        this.auditService = auditService;
    }

    @GetMapping
    public ApiResponse<List<Zone>> list(@RequestParam(defaultValue = "1") Long poolId) {
        return ApiResponse.ok(zoneMapper.selectList(Wrappers.<Zone>lambdaQuery()
                .eq(Zone::getPoolId, poolId).orderByAsc(Zone::getId)));
    }

    @PostMapping
    public ApiResponse<Zone> create(@RequestBody Zone body, @AuthenticationPrincipal String username) {
        validate(body, true);
        body.setId(null);
        body.setEnabled(body.getEnabled() == null || body.getEnabled());
        zoneMapper.insert(body);
        zoneLocator.invalidate();
        auditService.record(null, "ZONE_CREATE", "ZONE", String.valueOf(body.getId()),
                Map.of("name", body.getName(), "type", body.getType()));
        return ApiResponse.ok(body);
    }

    @PutMapping("/{id}")
    public ApiResponse<Zone> update(@PathVariable Long id, @RequestBody Zone body,
                                    @AuthenticationPrincipal String username) {
        Zone existing = zoneMapper.selectById(id);
        if (existing == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "区域不存在");
        }
        validate(body, false);
        existing.setName(body.getName());
        existing.setType(body.getType());
        existing.setPolygonJson(body.getPolygonJson());
        existing.setAllowedGroups(body.getAllowedGroups());
        existing.setEnabled(body.getEnabled() == null ? existing.getEnabled() : body.getEnabled());
        zoneMapper.updateById(existing);
        zoneLocator.invalidate();
        auditService.record(null, "ZONE_UPDATE", "ZONE", String.valueOf(id),
                Map.of("name", existing.getName(), "type", existing.getType()));
        return ApiResponse.ok(existing);
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Map<String, Object>> delete(@PathVariable Long id) {
        Zone existing = zoneMapper.selectById(id);
        if (existing == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "区域不存在");
        }
        if ("POOL".equals(existing.getType())) {
            throw new BizException(ErrorCode.CONFLICT, "全池兜底区域不可删除");
        }
        long active = alertService.countActiveByZone(id);
        if (active > 0) {
            throw new BizException(ErrorCode.CONFLICT, "该区域仍有未关闭告警，暂不能删除");
        }
        zoneMapper.deleteById(id);
        zoneLocator.invalidate();
        auditService.record(null, "ZONE_DELETE", "ZONE", String.valueOf(id), Map.of("name", existing.getName()));
        return ApiResponse.ok(Map.of("deleted", true));
    }

    private void validate(Zone body, boolean requirePoolId) {
        if (body.getName() == null || body.getName().isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "区域名称不能为空");
        }
        if (!TYPES.contains(body.getType())) {
            throw new BizException(ErrorCode.BAD_REQUEST, "区域类型不合法：" + body.getType());
        }
        if (body.getAllowedGroups() == null || !GROUPS.contains(body.getAllowedGroups())) {
            throw new BizException(ErrorCode.BAD_REQUEST, "适宜人群不合法");
        }
        if (body.getPolygonJson() == null || body.getPolygonJson().isBlank()) {
            throw new BizException(ErrorCode.BAD_REQUEST, "缺少多边形坐标");
        }
        if (requirePoolId && body.getPoolId() == null) {
            throw new BizException(ErrorCode.BAD_REQUEST, "缺少泳池 ID");
        }
    }
}
