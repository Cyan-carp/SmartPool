<template>
  <div class="devices">
    <div class="sp-panel">
      <div class="sp-panel__title">
        <span>水质监测（模拟传感器）</span>
        <span class="sp-badge" :class="{ 'sp-badge--live': water?.exceeded.length === 0 }">
          {{ water?.exceeded.length ? '存在超标项' : '指标正常' }}
        </span>
      </div>

      <div class="metrics">
        <div class="metric" :class="{ 'metric--bad': exceeded('TEMPERATURE') }">
          <div class="metric__value">{{ water?.temperature ?? '-' }}<small>℃</small></div>
          <div class="metric__label">水温</div>
        </div>
        <div class="metric" :class="{ 'metric--bad': exceeded('TURBIDITY') }">
          <div class="metric__value">{{ water?.turbidity ?? '-' }}<small>NTU</small></div>
          <div class="metric__label">浑浊度</div>
        </div>
        <div class="metric" :class="{ 'metric--bad': exceeded('PH') }">
          <div class="metric__value">{{ water?.ph ?? '-' }}</div>
          <div class="metric__label">pH</div>
        </div>
        <div class="metric">
          <div class="metric__value">{{ water?.chlorine ?? '-' }}<small>mg/L</small></div>
          <div class="metric__label">余氯</div>
        </div>
        <div class="metric metric--action">
          <el-button size="small" @click="thresholdDialog = true">修改阈值</el-button>
          <div class="metric__label">
            浑浊度 ≤ {{ water?.threshold?.turbidityMax ?? 5 }} · pH {{ water?.threshold?.phMin ?? 6.8 }}–{{ water?.threshold?.phMax ?? 8 }}
          </div>
        </div>
      </div>

      <div ref="waterChartRef" class="chart" />

      <div class="hint sp-dim">
        浑浊度超标时监控大屏提示「检测精度可能下降」，并建议清洁维护；曲线为每 10 秒采样一次，保留 24 小时。
      </div>
    </div>

    <div class="sp-panel">
      <div class="sp-panel__title">
        <span>设备健康</span>
        <span class="sp-dim">在线 {{ deviceOnline }} / {{ devices.length }}</span>
      </div>
      <div class="device-grid">
        <div v-for="item in devices" :key="item.key" class="device">
          <div class="device__head">
            <div>
              <div class="device__name">{{ item.name }}</div>
              <div class="sp-dim">{{ typeLabel(item.type) }}</div>
            </div>
            <el-tag size="small" :type="item.status === 'ONLINE' ? 'success' : 'info'">{{ item.status }}</el-tag>
          </div>

          <template v-if="item.type === 'CAMERA'">
            <div class="indicator">
              <span>镜头清洁度</span>
              <div class="indicator__bar"><i :style="{ width: pct(item.metrics.cleanliness) }" /></div>
              <b>{{ num(item.metrics.cleanliness) }}</b>
            </div>
            <div class="indicator">
              <span>防水密封</span>
              <div class="indicator__bar"><i :style="{ width: pct(item.metrics.sealScore) }" /></div>
              <b>{{ num(item.metrics.sealScore) }}</b>
            </div>
            <div class="indicator">
              <span>供电状态</span>
              <b :style="{ color: item.metrics.powerOk ? '#36d1a6' : '#ff6b72' }">
                {{ item.metrics.powerOk ? '正常' : '异常' }}
              </b>
            </div>
          </template>
          <div v-else class="chips">
            <span v-for="(value, key) in item.metrics" :key="key" class="chip">{{ key }}: {{ value }}</span>
          </div>

          <div class="device__foot">
            <el-button size="small" link type="primary" @click="openMaintenance(item)">登记维护</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="thresholdDialog" title="水质阈值" width="420px">
      <el-form label-width="90px" size="small">
        <el-form-item label="浑浊度上限"><el-input-number v-model="form.turbidityMax" :min="0.5" :max="20" :step="0.5" /></el-form-item>
        <el-form-item label="pH 下限"><el-input-number v-model="form.phMin" :min="5" :max="9" :step="0.1" /></el-form-item>
        <el-form-item label="pH 上限"><el-input-number v-model="form.phMax" :min="5" :max="9" :step="0.1" /></el-form-item>
        <el-form-item label="水温下限"><el-input-number v-model="form.temperatureMin" :min="15" :max="35" :step="0.5" /></el-form-item>
        <el-form-item label="水温上限"><el-input-number v-model="form.temperatureMax" :min="15" :max="40" :step="0.5" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="thresholdDialog = false">取消</el-button>
        <el-button type="primary" @click="saveThreshold">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="maintenanceDialog" :title="`登记维护 · ${currentDevice?.name || ''}`" width="420px">
      <el-form label-width="90px" size="small">
        <el-form-item label="维护类型">
          <el-select v-model="maintenance.type" style="width: 100%">
            <el-option label="清洁镜头" value="CLEAN" />
            <el-option label="密封检查" value="SEAL_CHECK" />
            <el-option label="重启设备" value="REBOOT" />
            <el-option label="供电检查" value="POWER_CHECK" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="maintenance.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <div class="sp-dim">维护记录会写入审计；清洁 / 密封检查后对应指标回升（模拟）。</div>
      <template #footer>
        <el-button @click="maintenanceDialog = false">取消</el-button>
        <el-button type="primary" @click="submitMaintenance">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import {
  fetchDevices,
  fetchWaterHistory,
  fetchWaterLatest,
  postMaintenance,
  updateWaterThreshold
} from '@/api'
import type { DeviceItem, WaterHistory, WaterLatest } from '@/types/api'

const TYPE_LABEL: Record<string, string> = { CAMERA: '摄像头', SENSOR: '传感器', GATEWAY: '网关' }

const devices = ref<DeviceItem[]>([])
const water = ref<WaterLatest | null>(null)
const history = ref<WaterHistory | null>(null)
const thresholdDialog = ref(false)
const maintenanceDialog = ref(false)
const currentDevice = ref<DeviceItem | null>(null)
const waterChartRef = ref<HTMLDivElement>()

const form = reactive({ turbidityMax: 5, phMin: 6.8, phMax: 8, temperatureMin: 25, temperatureMax: 29 })
const maintenance = reactive({ type: 'CLEAN', note: '' })

let chart: echarts.ECharts | null = null
let timer = 0

const deviceOnline = computed(() => devices.value.filter((item) => item.status === 'ONLINE').length)

function typeLabel(type: string) {
  return TYPE_LABEL[type] || type
}

function num(value: unknown) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toFixed(2) : '-'
}

function pct(value: unknown) {
  const parsed = Number(value)
  return `${Math.round((Number.isFinite(parsed) ? parsed : 0) * 100)}%`
}

function exceeded(key: string) {
  return water.value?.exceeded.includes(key) ?? false
}

async function loadWater() {
  try {
    water.value = await fetchWaterLatest(1)
    if (water.value?.threshold) {
      Object.assign(form, {
        turbidityMax: water.value.threshold.turbidityMax,
        phMin: water.value.threshold.phMin,
        phMax: water.value.threshold.phMax,
        temperatureMin: water.value.threshold.temperatureMin,
        temperatureMax: water.value.threshold.temperatureMax
      })
    }
  } catch {
    water.value = null
  }
  try {
    history.value = await fetchWaterHistory(1, 60)
    renderChart()
  } catch {
    history.value = null
  }
}

function renderChart() {
  if (!chart || !history.value) {
    return
  }
  const points = history.value.points
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 12, top: 28, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis' },
    legend: { data: ['浑浊度', '水温', 'pH'], textStyle: { color: '#9db2c4', fontSize: 11 }, top: 0 },
    xAxis: {
      type: 'category',
      data: points.map((item) => item.ts.slice(11, 19)),
      axisLine: { lineStyle: { color: '#2a3f52' } },
      axisLabel: { color: '#9db2c4', fontSize: 10, interval: Math.max(0, Math.floor(points.length / 8)) }
    },
    yAxis: [
      { type: 'value', name: 'NTU / ℃', nameTextStyle: { color: '#9db2c4', fontSize: 10 }, axisLabel: { color: '#9db2c4', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(58,82,102,0.6)' } } },
      { type: 'value', name: 'pH', min: 6, max: 9, nameTextStyle: { color: '#9db2c4', fontSize: 10 }, axisLabel: { color: '#9db2c4', fontSize: 10 }, splitLine: { show: false } }
    ],
    series: [
      { name: '浑浊度', type: 'line', smooth: true, showSymbol: false, data: points.map((item) => item.turbidity), lineStyle: { color: '#f5a25c', width: 2 } },
      { name: '水温', type: 'line', smooth: true, showSymbol: false, data: points.map((item) => item.temperature), lineStyle: { color: '#43b9f5', width: 1.6 } },
      { name: 'pH', type: 'line', yAxisIndex: 1, smooth: true, showSymbol: false, data: points.map((item) => item.ph), lineStyle: { color: '#36d1a6', width: 1.6 } }
    ]
  })
}

async function saveThreshold() {
  try {
    await updateWaterThreshold({ poolId: 1, ...form })
    ElMessage.success('阈值已保存')
    thresholdDialog.value = false
    await loadWater()
  } catch {
    /* 拦截器已提示 */
  }
}

async function loadDevices() {
  try {
    const data = await fetchDevices(1)
    devices.value = data.items
  } catch {
    devices.value = []
  }
}

function openMaintenance(item: DeviceItem) {
  currentDevice.value = item
  maintenance.type = 'CLEAN'
  maintenance.note = ''
  maintenanceDialog.value = true
}

async function submitMaintenance() {
  if (!currentDevice.value) {
    return
  }
  try {
    await postMaintenance(currentDevice.value.key, maintenance.type, maintenance.note)
    ElMessage.success('维护已登记')
    maintenanceDialog.value = false
    await loadDevices()
  } catch {
    /* 拦截器已提示 */
  }
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  if (waterChartRef.value) {
    chart = echarts.init(waterChartRef.value)
  }
  await Promise.all([loadWater(), loadDevices()])
  timer = window.setInterval(loadWater, 5000)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.devices {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric {
  background: var(--sp-panel-2);
  border-radius: 10px;
  padding: 14px;
  border: 1px solid transparent;
}

.metric--bad {
  border-color: rgba(255, 107, 114, 0.5);
  background: rgba(255, 107, 114, 0.08);
}

.metric--action {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.metric__value {
  font-size: 26px;
  font-weight: 600;
}

.metric__value small {
  font-size: 11px;
  color: var(--sp-text-dim);
  margin-left: 2px;
}

.metric__label {
  font-size: 12px;
  color: var(--sp-text-dim);
  margin-top: 4px;
}

.chart {
  width: 100%;
  height: 240px;
  margin-top: 12px;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.device {
  background: var(--sp-panel-2);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.device__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.device__name {
  font-size: 14px;
  font-weight: 600;
}

.indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--sp-text-dim);
}

.indicator__bar {
  flex: 1;
  height: 6px;
  background: rgba(125, 195, 240, .14);
  border-radius: 999px;
  overflow: hidden;
}

.indicator__bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #43b9f5, #36d1a6);
  border-radius: 999px;
}

.indicator b {
  width: 42px;
  text-align: right;
  color: var(--sp-text);
  font-weight: 500;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(67, 185, 245, 0.12);
  color: #9db2c4;
}

.device__foot {
  display: flex;
  justify-content: flex-end;
}

.hint {
  margin-top: 10px;
  line-height: 1.8;
}

</style>
