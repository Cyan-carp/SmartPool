package com.smartpool.wristband;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.smartpool.audit.AuditService;
import com.smartpool.common.ApiResponse;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/wristbands")
public class WristbandController {

    private final WristbandMapper mapper;
    private final AuditService auditService;

    public WristbandController(WristbandMapper mapper, AuditService auditService) {
        this.mapper = mapper;
        this.auditService = auditService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list() {
        List<Wristband> rows = mapper.selectList(Wrappers.<Wristband>lambdaQuery().orderByAsc(Wristband::getCode));
        long bound = rows.stream().filter(item -> item.getBindTrackNo() != null).count();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("list", rows);
        body.put("total", rows.size());
        body.put("bound", bound);
        return ApiResponse.ok(body);
    }

    @PostMapping("/{code}/bind")
    public ApiResponse<Wristband> bind(@PathVariable String code, @RequestBody Map<String, Object> body) {
        Wristband band = require(code);
        Integer trackNo = body.get("trackNo") == null ? null : Integer.valueOf(String.valueOf(body.get("trackNo")));
        if (trackNo == null || trackNo <= 0) {
            throw new BizException(ErrorCode.BAD_REQUEST, "缺少目标编号");
        }
        long occupied = mapper.selectCount(Wrappers.<Wristband>lambdaQuery()
                .eq(Wristband::getBindTrackNo, trackNo)
                .ne(Wristband::getCode, code));
        if (occupied > 0) {
            throw new BizException(ErrorCode.CONFLICT, "该目标已绑定其它手环");
        }
        band.setBindTrackNo(trackNo);
        mapper.updateById(band);
        auditService.record(null, "WRISTBAND_BIND", "WRISTBAND", code, Map.of("trackNo", trackNo));
        return ApiResponse.ok(band);
    }

    @PostMapping("/{code}/unbind")
    public ApiResponse<Wristband> unbind(@PathVariable String code) {
        require(code);
        // MyBatis-Plus 的 updateById 默认忽略 null 字段，解绑必须显式 set null
        mapper.update(null, Wrappers.<Wristband>lambdaUpdate()
                .set(Wristband::getBindTrackNo, null)
                .eq(Wristband::getCode, code));
        Wristband updated = require(code);
        auditService.record(null, "WRISTBAND_UNBIND", "WRISTBAND", code, Map.of());
        return ApiResponse.ok(updated);
    }

    private Wristband require(String code) {
        Wristband band = mapper.selectOne(Wrappers.<Wristband>lambdaQuery().eq(Wristband::getCode, code));
        if (band == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "手环不存在");
        }
        return band;
    }
}
