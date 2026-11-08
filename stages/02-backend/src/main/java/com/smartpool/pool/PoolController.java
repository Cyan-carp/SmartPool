package com.smartpool.pool;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.smartpool.common.ApiResponse;
import com.smartpool.common.BizException;
import com.smartpool.common.ErrorCode;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class PoolController {

    private final PoolMapper poolMapper;
    private final CameraMapper cameraMapper;
    private final ZoneMapper zoneMapper;

    public PoolController(PoolMapper poolMapper, CameraMapper cameraMapper, ZoneMapper zoneMapper) {
        this.poolMapper = poolMapper;
        this.cameraMapper = cameraMapper;
        this.zoneMapper = zoneMapper;
    }

    @GetMapping("/pools")
    public ApiResponse<List<Pool>> pools() {
        return ApiResponse.ok(poolMapper.selectList(null));
    }

    @GetMapping("/pools/{id}")
    public ApiResponse<Pool> pool(@PathVariable Long id) {
        Pool pool = poolMapper.selectById(id);
        if (pool == null) {
            throw new BizException(ErrorCode.NOT_FOUND, "泳池不存在");
        }
        return ApiResponse.ok(pool);
    }

    @GetMapping("/cameras")
    public ApiResponse<List<Camera>> cameras(@RequestParam(defaultValue = "1") Long poolId) {
        return ApiResponse.ok(cameraMapper.selectList(
                Wrappers.<Camera>lambdaQuery().eq(Camera::getPoolId, poolId).orderByAsc(Camera::getId)));
    }

    // 区域查询与维护统一在 ZoneController（/api/v1/zones）
}
