<template>
  <div class="dashboard">
    <div class="sp-panel">
      <div class="sp-panel__title">
        <span>运行概览（近 24 小时）</span>
        <span class="sp-badge">{{ updatedAt || '加载中' }}</span>
      </div>
      <div class="cards">
        <div class="card">
          <div class="card__value">{{ stats?.total ?? 0 }}</div>
          <div class="card__label">告警总数</div>
        </div>
        <div class="card">
          <div class="card__value" style="color: #ff6b72">{{ stats?.open ?? 0 }}</div>
          <div class="card__label">待确认</div>
        </div>
        <div class="card">
          <div class="card__value" style="color: #e9c46a">{{ stats?.acked ?? 0 }}</div>
          <div class="card__label">已确认</div>
        </div>
        <div class="card">
          <div class="card__value" style="color: #36d1a6">{{ stats?.resolved ?? 0 }}</div>
          <div class="card__label">已解除</div>
        </div>
        <div class="card">
          <div class="card__value">{{ stats?.avgAckSeconds ?? 0 }}<small>s</small></div>
          <div class="card__label">平均响应</div>
        </div>
        <div class="card">
          <div class="card__value" :style="{ color: (stats?.falseAlarmRate ?? 0) > 20 ? '#f5a25c' : undefined }">
            {{ stats?.falseAlarmRate ?? 0 }}<small>%</small>
          </div>
          <div class="card__label">误报率</div>
        </div>
      </div>
    </div>

    <div class="charts">
      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>区域密度热力图</span>
          <span class="sp-dim">近 {{ heatmap?.windowMinutes ?? 30 }} 分钟 · {{ heatmap?.max ?? 0 }} 峰值</span>
        </div>
        <div class="chart-wrap">
          <div ref="heatmapRef" class="chart" />
          <div v-if="heatmapEmpty" class="chart-empty">
            <span class="chart-empty__title">暂无区域采样</span>
            <span class="chart-empty__hint">轨迹采样满 1 分钟后开始统计</span>
          </div>
        </div>
      </div>

      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>风险趋势</span>
          <span class="sp-dim">按分钟平均风险分</span>
        </div>
        <div class="chart-wrap">
          <div ref="trendRef" class="chart" />
          <div v-if="trendEmpty" class="chart-empty">
            <span class="chart-empty__title">暂无风险记录</span>
            <span class="chart-empty__hint">出现检测目标后按分钟聚合</span>
          </div>
        </div>
      </div>
    </div>

    <div class="charts charts--second">
      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>峰谷人流</span>
          <span class="sp-dim">每小时内峰值（近 {{ crowd?.windowHours ?? 6 }} 小时）</span>
        </div>
        <div class="chart-wrap">
          <div ref="crowdRef" class="chart chart--short" />
          <div v-if="crowdEmpty" class="chart-empty">
            <span class="chart-empty__title">暂无客流数据</span>
            <span class="chart-empty__hint">按分钟聚合后取小时峰值</span>
          </div>
        </div>
      </div>

      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>告警等级分布</span>
          <span class="sp-dim">强 {{ stats?.strong ?? 0 }} · 弱 {{ stats?.weak ?? 0 }}</span>
        </div>
        <div class="bars">
          <div class="bar">
            <span class="bar__label">强告警</span>
            <div class="bar__track"><div class="bar__fill bar__fill--strong" :style="{ width: strongWidth }" /></div>
            <span class="bar__value">{{ stats?.strong ?? 0 }}</span>
          </div>
          <div class="bar">
            <span class="bar__label">弱告警</span>
            <div class="bar__track"><div class="bar__fill bar__fill--weak" :style="{ width: weakWidth }" /></div>
            <span class="bar__value">{{ stats?.weak ?? 0 }}</span>
          </div>
          <div class="bar">
            <span class="bar__label">现场人数</span>
            <div class="bar__track">
              <div class="bar__fill bar__fill--people" :style="{ width: peopleWidth }" />
            </div>
            <span class="bar__value">{{ frames?.counts?.total ?? 0 }}</span>
          </div>
        </div>
        <div class="hint sp-dim">
          热力图与趋势来自每秒一次的轨迹采样；人流峰谷按分钟聚合取小时峰值。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchCrowd, fetchHeatmap, fetchSnapshot, fetchStats, fetchTrend } from '@/api'
import type { AlertStats, CrowdData, Frames, HeatmapData, TrendData } from '@/types/api'

const stats = ref<AlertStats | null>(null)
const frames = ref<Frames | null>(null)
const heatmap = ref<HeatmapData | null>(null)
const trend = ref<TrendData | null>(null)
const crowd = ref<CrowdData | null>(null)
const updatedAt = ref('')

const heatmapRef = ref<HTMLDivElement>()
const trendRef = ref<HTMLDivElement>()
const crowdRef = ref<HTMLDivElement>()

let charts: echarts.ECharts[] = []
let timer = 0

const maxLevelCount = computed(() => Math.max(1, stats.value?.strong ?? 0, stats.value?.weak ?? 0))
const strongWidth = computed(() => `${((stats.value?.strong ?? 0) / maxLevelCount.value) * 100}%`)
const weakWidth = computed(() => `${((stats.value?.weak ?? 0) / maxLevelCount.value) * 100}%`)
const peopleWidth = computed(() => `${Math.min(100, ((frames.value?.counts?.total ?? 0) / 20) * 100)}%`)

// 空态判定：接口未返回、或返回了全零数据，都算"暂无数据"。
// 直接用遮罩覆盖图表区，避免 ECharts 渲染出一片空白坐标轴。
const heatmapEmpty = computed(() => !heatmap.value || heatmap.value.max <= 0)
const trendEmpty = computed(() => !trend.value || trend.value.points.length === 0)
const crowdEmpty = computed(
  () => !crowd.value || !crowd.value.bars.length || crowd.value.bars.every((item) => !item.peak)
)

const AXIS_STYLE = {
  axisLine: { lineStyle: { color: '#2a3f52' } },
  axisLabel: { color: '#9db2c4', fontSize: 11 },
  splitLine: { lineStyle: { color: 'rgba(58, 82, 102, 0.6)' } }
}

function renderHeatmap() {
  const chart = charts[0]
  const data = heatmap.value
  if (!chart) {
    return
  }
  if (!data) {
    // 数据回退为 null 时清空，避免空态遮罩下面压着上一次的旧图
    chart.clear()
    return
  }
  const series: number[][] = []
  data.grid.forEach((row, y) => {
    row.forEach((value, x) => {
      series.push([x, y, value])
    })
  })
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 12, top: 12, bottom: 44, containLabel: true },
    tooltip: { position: 'top', formatter: (params: any) => `格 (${params.data[0]}, ${params.data[1]})：${params.data[2]} 次` },
    xAxis: { type: 'category', data: Array.from({ length: data.cols }, (_, i) => i), ...AXIS_STYLE },
    yAxis: { type: 'category', data: Array.from({ length: data.rows }, (_, i) => i), ...AXIS_STYLE },
    visualMap: {
      min: 0,
      max: Math.max(1, data.max),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: '#9db2c4', fontSize: 10 },
      inRange: { color: ['#12293a', '#4aa8e8', '#e0b45f', '#ff6b72'] }
    },
    series: [{
      type: 'heatmap',
      data: series,
      progressive: 0,
      itemStyle: { borderColor: '#16232f', borderWidth: 0.5 }
    }]
  })
}

function renderTrend() {
  const chart = charts[1]
  const data = trend.value
  if (!chart) {
    return
  }
  if (!data) {
    chart.clear()
    return
  }
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 12, top: 24, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均风险分', '高风险目标数'], textStyle: { color: '#9db2c4', fontSize: 11 }, top: 0 },
    xAxis: { type: 'category', data: data.points.map((item) => item.time), ...AXIS_STYLE },
    yAxis: [
      { type: 'value', min: 0, max: 1, ...AXIS_STYLE },
      { type: 'value', min: 0, ...AXIS_STYLE, splitLine: { show: false } }
    ],
    series: [
      {
        name: '平均风险分',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: data.points.map((item) => item.avgRisk),
        lineStyle: { color: '#43b9f5', width: 2 },
        areaStyle: { color: 'rgba(67, 185, 245, 0.16)' }
      },
      {
        name: '高风险目标数',
        type: 'bar',
        yAxisIndex: 1,
        data: data.points.map((item) => item.riskCount),
        itemStyle: { color: 'rgba(255, 107, 114, 0.55)' },
        barMaxWidth: 8
      }
    ]
  })
}

function renderCrowd() {
  const chart = charts[2]
  const data = crowd.value
  if (!chart) {
    return
  }
  if (!data) {
    chart.clear()
    return
  }
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 12, top: 20, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.bars.map((item) => item.hour), ...AXIS_STYLE },
    yAxis: { type: 'value', min: 0, ...AXIS_STYLE },
    series: [{
      type: 'bar',
      data: data.bars.map((item) => item.peak),
      barMaxWidth: 28,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#43b9f5' },
          { offset: 1, color: 'rgba(67, 185, 245, 0.22)' }
        ])
      }
    }]
  })
}

async function load() {
  try {
    stats.value = await fetchStats(24)
    updatedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    stats.value = null
  }
  try {
    frames.value = (await fetchSnapshot(1)).snapshot
  } catch {
    frames.value = null
  }
  try {
    heatmap.value = await fetchHeatmap(1, 30)
    trend.value = await fetchTrend(1, 30)
    crowd.value = await fetchCrowd(1, 6)
    renderHeatmap()
    renderTrend()
    renderCrowd()
  } catch {
    // 数据尚未积累时保持空图
  }
}

function onResize() {
  charts.forEach((chart) => chart.resize())
}

onMounted(async () => {
  await nextTick()
  if (heatmapRef.value) charts[0] = echarts.init(heatmapRef.value)
  if (trendRef.value) charts[1] = echarts.init(trendRef.value)
  if (crowdRef.value) charts[2] = echarts.init(crowdRef.value)
  await load()
  timer = window.setInterval(load, 15000)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
  window.removeEventListener('resize', onResize)
  charts.forEach((chart) => chart.dispose())
  charts = []
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.card {
  background: var(--sp-panel-2);
  border-radius: 10px;
  padding: 16px;
}

.card__value {
  font-size: 28px;
  font-weight: 600;
}

.card__value small {
  font-size: 11px;
  color: var(--sp-text-dim);
  margin-left: 2px;
}

.card__label {
  font-size: 12px;
  color: var(--sp-text-dim);
  margin-top: 4px;
}

.charts {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.charts--second {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.chart {
  width: 100%;
  height: 260px;
}

.chart--short {
  height: 200px;
}

.chart-wrap {
  position: relative;
}

/* 空态占位：图表已 clear()，无需遮罩底色，文字直接浮在卡片上更自然 */
.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  pointer-events: none;
}

.chart-empty__title {
  font-size: 13px;
  color: var(--ink-3);
}

.chart-empty__hint {
  font-size: 11.5px;
  color: var(--ink-placeholder);
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
}

.bar {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.bar__label {
  width: 70px;
  color: var(--sp-text-dim);
}

.bar__track {
  flex: 1;
  height: 10px;
  background: var(--line-soft);
  border-radius: 999px;
  overflow: hidden;
}

.bar__fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}

.bar__fill--strong { background: linear-gradient(90deg, #ff6b72, #e05a61); }
.bar__fill--weak { background: linear-gradient(90deg, #f5a25c, #c9a24c); }
.bar__fill--people { background: linear-gradient(90deg, #43b9f5, #67d9ff); }

.bar__value {
  width: 32px;
  text-align: right;
}

.hint {
  margin-top: 14px;
  line-height: 1.8;
}
</style>
