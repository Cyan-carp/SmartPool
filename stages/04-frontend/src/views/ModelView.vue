<template>
  <div class="model">
    <div class="sp-panel">
      <div class="sp-panel__title">
        <span>模型信息</span>
        <span class="sp-badge sp-badge--mock">占位模式 · 未加载真实权重</span>
      </div>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="检测提供者">{{ info.provider || '-' }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ info.version || '-' }}</el-descriptions-item>
        <el-descriptions-item label="模型加载状态">
          {{ info.modelLoaded ? '已加载' : '未加载（占位）' }}
        </el-descriptions-item>
        <el-descriptions-item label="输入尺寸">{{ info.inputSize || '-' }}</el-descriptions-item>
        <el-descriptions-item label="类别">{{ (info.classes || []).join(' / ') }}</el-descriptions-item>
        <el-descriptions-item label="当前档位">{{ params.mode || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="hint sp-dim">{{ info.note }}</div>
    </div>

    <div class="row">
      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>分时域算力调度</span>
          <span class="sp-badge">算力占比为模拟值</span>
        </div>
        <div class="switcher">
          <el-radio-group v-model="draftMode" size="default">
            <el-radio-button value="PEAK">高峰档</el-radio-button>
            <el-radio-button value="OFFPEAK">低谷档</el-radio-button>
          </el-radio-group>
          <div class="switcher__auto">
            <span class="sp-dim">按营业时段自动切换</span>
            <el-switch v-model="draftAuto" />
          </div>
          <el-button type="primary" :loading="applying" @click="applyMode">应用并下发</el-button>
        </div>

        <el-table :data="paramRows" style="width: 100%; margin-top: 14px">
          <el-table-column prop="mode" label="档位" width="110">
            <template #default="{ row }">
              <span :class="{ 'is-current': row.mode === params.mode }">{{ row.mode === 'PEAK' ? '高峰' : '低谷' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度阈值" width="120" />
          <el-table-column prop="windowT" label="滑窗 T（秒）" width="120" />
          <el-table-column prop="stride" label="特征步长" width="110" />
          <el-table-column prop="computeRatio" label="算力占比（模拟）" />
        </el-table>

        <div class="hint sp-dim">
          真实方案为 Mamba-YOLO 的分时域自适应调度（关闭部分 LS Block、切换 PAFPN 层数）。
          演示版只展示参数与模拟指标，不宣称实测降幅。
        </div>
      </div>

      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>推理指标</span>
          <span class="sp-dim">延迟来自真实返回 · 算力占比为模拟</span>
        </div>
        <div ref="metricChartRef" class="chart" />
        <div class="summary">
          <div><span class="sp-dim">平均延迟</span><b>{{ avgLatency }} ms</b></div>
          <div><span class="sp-dim">采样点</span><b>{{ metrics.points.length }}</b></div>
          <div><span class="sp-dim">当前档位</span><b>{{ metrics.mode || '-' }}</b></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { fetchModelInfo, fetchModelMetrics, fetchModelParams, setModelMode } from '@/api'
import type { ModelMetrics } from '@/types/api'

const info = ref<Record<string, any>>({})
const params = reactive<{ mode: string; auto: boolean; templates: Record<string, any> }>({
  mode: 'PEAK',
  auto: true,
  templates: {}
})
const metrics = ref<ModelMetrics>({ mode: 'PEAK', windowMinutes: 30, points: [] })
const draftMode = ref('PEAK')
const draftAuto = ref(true)
const applying = ref(false)
const metricChartRef = ref<HTMLDivElement>()

let chart: echarts.ECharts | null = null
let timer = 0

const paramRows = computed(() =>
  Object.keys(params.templates).map((mode) => ({ mode, ...params.templates[mode] }))
)

const avgLatency = computed(() => {
  const points = metrics.value.points
  if (!points.length) {
    return 0
  }
  return Math.round(points.reduce((acc, item) => acc + item.latencyMs, 0) / points.length)
})

async function loadParams() {
  try {
    const data = (await fetchModelParams()) as any
    params.mode = data.mode
    params.auto = data.auto
    params.templates = data.templates || {}
    draftMode.value = data.mode
    draftAuto.value = data.auto
  } catch {
    /* 拦截器已提示 */
  }
}

async function loadMetrics() {
  try {
    metrics.value = await fetchModelMetrics(30)
    renderChart()
  } catch {
    /* 保持上次数据 */
  }
}

function renderChart() {
  if (!chart) {
    return
  }
  const points = metrics.value.points
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 12, top: 28, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis' },
    legend: { data: ['推理延迟', '算力占比'], textStyle: { color: '#9db2c4', fontSize: 11 }, top: 0 },
    xAxis: {
      type: 'category',
      data: points.map((item) => item.ts),
      axisLine: { lineStyle: { color: '#2a3f52' } },
      axisLabel: { color: '#9db2c4', fontSize: 10, interval: Math.max(0, Math.floor(points.length / 8)) }
    },
    yAxis: [
      { type: 'value', name: 'ms', nameTextStyle: { color: '#9db2c4', fontSize: 10 }, axisLabel: { color: '#9db2c4', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(58,82,102,0.6)' } } },
      { type: 'value', name: '占比', min: 0, max: 1, nameTextStyle: { color: '#9db2c4', fontSize: 10 }, axisLabel: { color: '#9db2c4', fontSize: 10 }, splitLine: { show: false } }
    ],
    series: [
      {
        name: '推理延迟',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: points.map((item) => item.latencyMs),
        lineStyle: { color: '#43b9f5', width: 2 },
        areaStyle: { color: 'rgba(67,185,245,0.14)' }
      },
      {
        name: '算力占比',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: points.map((item) => item.computeRatio),
        lineStyle: { color: '#e9c46a', width: 1.6, type: 'dashed' }
      }
    ]
  })
}

async function applyMode() {
  applying.value = true
  try {
    await setModelMode(draftMode.value, draftAuto.value)
    ElMessage.success(`已切换到${draftMode.value === 'PEAK' ? '高峰' : '低谷'}档`)
    await loadParams()
    await loadMetrics()
  } catch {
    /* 拦截器已提示 */
  } finally {
    applying.value = false
  }
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  await nextTick()
  if (metricChartRef.value) {
    chart = echarts.init(metricChartRef.value)
  }
  try {
    info.value = (await fetchModelInfo()) as any
  } catch {
    info.value = {}
  }
  await loadParams()
  await loadMetrics()
  timer = window.setInterval(loadMetrics, 10000)
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
.model {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.row {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 16px;
}

.switcher {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.switcher__auto {
  display: flex;
  align-items: center;
  gap: 8px;
}

.is-current {
  color: #36d1a6;
  font-weight: 600;
}

.chart {
  width: 100%;
  height: 230px;
}

.summary {
  display: flex;
  gap: 24px;
  margin-top: 10px;
  font-size: 13px;
}

.summary b {
  margin-left: 6px;
  color: var(--sp-text);
}

.hint {
  margin-top: 12px;
  line-height: 1.8;
}
</style>
