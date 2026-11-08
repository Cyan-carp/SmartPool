<template>
  <div class="replay">
    <section class="sp-panel replay__toolbar">
      <div>
        <div class="sp-panel__title">事件回溯 <span class="sp-badge">告警前后 20 秒</span></div>
        <div class="sp-dim">选择一条告警，查看轨迹与风险曲线回放</div>
      </div>
      <el-select v-model="selectedId" placeholder="选择一条告警" style="width: 340px" @change="loadDetail">
        <el-option
          v-for="item in alerts"
          :key="item.id"
          :label="`#${item.id} ${levelLabel(item.level)} · ${item.zoneName || '未分区'} · ${shortTime(item.triggeredAt)}`"
          :value="item.id"
        />
      </el-select>
    </section>

    <div v-if="!detail" class="sp-panel sp-empty" style="min-height: 220px; height: auto">
      <div style="font-size: 15px">选择一条告警查看回溯</div>
      <div class="sp-dim">回溯数据来自每秒一次的轨迹采样</div>
    </div>

    <template v-else>
      <div class="replay__grid">
        <div class="replay__main">
          <div class="replay__main-inner">
            <section class="sp-panel replay__stage">
              <div class="sp-panel__title">
                <span>轨迹回放</span>
                <span class="sp-dim">采样每秒 1 点，播完自动停止</span>
              </div>
              <canvas ref="canvasRef" class="replay__canvas" />
              <div class="replay__controls">
                <el-button size="small" @click="togglePlay">{{ playing ? '暂停' : (isEnd ? '重新播放' : '播放') }}</el-button>
                <div class="speed" role="group" aria-label="播放倍速">
                  <button
                    v-for="item in SPEED_OPTIONS"
                    :key="item"
                    type="button"
                    class="speed__btn"
                    :class="{ 'is-on': speed === item }"
                    @click="setSpeed(item)"
                  >{{ item }}×</button>
                </div>
                <el-slider v-model="cursor" :max="Math.max(0, points.length - 1)" style="flex: 1" @input="pause()" />
                <span class="replay__time num">{{ timeText }}</span>
              </div>
            </section>

            <section class="sp-panel replay__samples">
              <div class="sp-panel__title">
                <span>复盘明细</span>
                <span class="sp-dim">点击色带或任意一帧可跳转回放</span>
              </div>
              <div class="replay__strip" role="group" aria-label="逐帧风险色带">
                <button
                  v-for="(point, index) in points"
                  :key="index"
                  type="button"
                  class="replay__strip-cell"
                  :class="[frameTone(point.riskScore), { 'is-current': index === cursor }]"
                  :title="`第 ${index} 秒 · 风险 ${point.riskScore.toFixed(2)}`"
                  @click="seek(index)"
                />
              </div>
              <div class="replay__samples-body">
                <div ref="sampleBodyRef" class="replay__samples-table">
                  <table class="replay__table">
                    <thead>
                      <tr><th>帧</th><th>时刻</th><th>姿态</th><th>画面坐标</th><th>风险分</th><th>判定</th></tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(point, index) in points"
                        :key="index"
                        :class="{ 'is-current': index === cursor, 'is-bad': point.riskScore >= 0.8 }"
                        @click="seek(index)"
                      >
                        <td class="num">{{ String(index).padStart(2, '0') }}</td>
                        <td class="num">{{ clockOf(point.ts) }}</td>
                        <td>{{ postureLabel(point.posture) }}</td>
                        <td class="num">({{ point.x.toFixed(2) }}, {{ point.y.toFixed(2) }})</td>
                        <td class="num">{{ point.riskScore.toFixed(2) }}</td>
                        <td><span class="replay__verdict" :class="frameTone(point.riskScore)">{{ verdict(point.riskScore) }}</span></td>
                      </tr>
                    </tbody>
                  </table>
                  <div v-if="points.length === 0" class="sp-dim replay__samples-empty">该事件暂无轨迹采样</div>
                </div>

                <div class="replay__samples-aside">
                  <div class="sp-dim replay__subtitle">处置时间线</div>
                  <div class="replay__timeline">
                    <div v-if="timeline.length === 0" class="sp-dim">暂无处置记录</div>
                    <div v-for="(item, index) in timeline" :key="index" class="replay__timeline-item">
                      <span class="replay__timeline-dot" />
                      <div>
                        <div class="replay__timeline-head"><b>{{ item.label }}</b><span class="sp-dim">{{ shortTime(item.at) }}</span></div>
                        <div v-if="item.note" class="sp-dim">{{ item.note }}</div>
                      </div>
                    </div>
                  </div>

                  <div class="sp-dim replay__subtitle">风险分布（按采样秒数）</div>
                  <div class="replay__segment-bar">
                    <span v-for="seg in riskSegments" :key="seg.key" :style="{ width: seg.pct + '%', background: seg.color }" />
                  </div>
                  <div class="replay__segment-legend">
                    <div v-for="seg in riskSegments" :key="seg.key">
                      <i :style="{ background: seg.color }" />
                      <span>{{ seg.label }}</span>
                      <b>{{ seg.count }} s</b>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>

        <aside class="replay__side">
          <section class="sp-panel">
            <div class="sp-panel__title">风险曲线</div>
            <svg viewBox="0 0 300 140" class="replay__chart">
              <line v-for="line in 4" :key="line" x1="0" :y1="line * 28" x2="300" :y2="line * 28" stroke="rgba(125, 195, 240, 0.3)" stroke-width="1" />
              <polyline :points="riskPolyline" fill="none" stroke="#f5a25c" stroke-width="1.6" />
              <line x1="0" :y1="riskThresholdY" x2="300" :y2="riskThresholdY" stroke="#ff6b72" stroke-dasharray="4 3" stroke-width="1" />
              <circle :cx="cursorX" :cy="cursorRiskY" r="3.5" fill="#ff6b72" />
            </svg>
            <div class="sp-dim replay__chart-hint">虚线为强告警阈值 0.80</div>
          </section>

          <section class="sp-panel">
            <div class="sp-panel__title">
              <span>当前帧</span>
              <span class="sp-dim">{{ timeText.split(' / ')[0] }}</span>
            </div>
            <div class="replay__current-value" :class="currentRiskTone">{{ currentPoint ? currentPoint.riskScore.toFixed(2) : '-' }}</div>
            <div class="sp-dim">{{ currentRiskHint }}</div>
            <div class="replay__kv">
              <span class="sp-dim">姿态</span><b>{{ postureLabel(currentPoint?.posture) }}</b>
              <span class="sp-dim">画面坐标</span><b>{{ coordText }}</b>
              <span class="sp-dim">采样时刻</span><b>{{ shortTime(currentPoint?.ts) }}</b>
            </div>
          </section>

          <section class="sp-panel">
            <div class="sp-panel__title">事件信息</div>
            <div class="replay__kv">
              <span class="sp-dim">目标</span><b>#{{ detail.alert.trackNo ?? '-' }}</b>
              <span class="sp-dim">区域</span><b>{{ detail.alert.zoneName || '未分区' }}</b>
              <span class="sp-dim">等级</span><b>{{ levelLabel(detail.alert.level) }}</b>
              <span class="sp-dim">状态</span><b>{{ statusLabel(detail.alert.status) }}</b>
              <span class="sp-dim">原因</span><b>{{ detail.alert.reason }}</b>
              <span class="sp-dim">触发时间</span><b>{{ shortTime(detail.alert.triggeredAt) }}</b>
            </div>
          </section>

          <section class="sp-panel">
            <div class="sp-panel__title">回放统计</div>
            <div class="replay__stats">
              <div class="replay__stat"><b>{{ points.length }}</b><span>采样点</span></div>
              <div class="replay__stat"><b>{{ maxRisk }}</b><span>最高风险</span></div>
              <div class="replay__stat"><b>{{ overThreshold }}</b><span>超阈值点</span></div>
            </div>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { fetchAlertDetail, fetchAlerts } from '@/api'
import type { AlertDetail, AlertItem, ClipPoint } from '@/types/api'

const LEVEL_LABEL: Record<string, string> = { NOTICE: '提示', WEAK: '弱告警', STRONG: '强告警' }
const STATUS_LABEL: Record<string, string> = {
  OPEN: '待确认',
  ACKED: '已确认',
  DISPATCHED: '已派单',
  RESOLVED: '已解除',
  FALSE_ALARM: '误报'
}
const POSTURE_LABEL: Record<string, string> = {
  SWIM: '正常游泳',
  SWIMMING: '正常游泳',
  FLOAT: '漂浮',
  STILL: '静止',
  SINK: '下沉',
  UNDERWATER: '没入水中',
  TREAD: '踩水'
}

// 采样为每秒 1 点，1× 即按真实时间回放
const SPEED_OPTIONS = [0.5, 1, 2, 4]

const alerts = ref<AlertItem[]>([])
const selectedId = ref<number | null>(null)
const detail = ref<AlertDetail | null>(null)
const cursor = ref(0)
const playing = ref(false)
const speed = ref(1)
const canvasRef = ref<HTMLCanvasElement>()

let playTimer = 0
let rafId = 0

const points = computed<ClipPoint[]>(() => detail.value?.clip.points ?? [])
const isEnd = computed(() => points.value.length > 0 && cursor.value >= points.value.length - 1)
const currentPoint = computed<ClipPoint | null>(() => points.value[cursor.value] ?? null)
const maxRisk = computed(() => (points.value.length ? Math.max(...points.value.map((item) => item.riskScore)) : 0).toFixed(2))
const overThreshold = computed(() => points.value.filter((item) => item.riskScore >= 0.8).length)
const currentRiskTone = computed(() => {
  const value = currentPoint.value?.riskScore
  if (value === undefined) return ''
  if (value >= 0.8) return 'is-bad'
  if (value >= 0.55) return 'is-warn'
  return ''
})
const currentRiskHint = computed(() => {
  const value = currentPoint.value?.riskScore
  if (value === undefined) return '暂无采样数据'
  if (value >= 0.8) return '风险分 · 超过强告警阈值'
  if (value >= 0.55) return '风险分 · 接近告警阈值'
  return '风险分 · 处于正常范围'
})
const coordText = computed(() => {
  const point = currentPoint.value
  return point ? `(${point.x.toFixed(2)}, ${point.y.toFixed(2)})` : '-'
})
const timeText = computed(() => {
  const clock = (sec: number) => `00:${String(sec).padStart(2, '0')}`
  return `${clock(cursor.value)} / ${clock(Math.max(0, points.value.length - 1))}`
})

const riskPolyline = computed(() => {
  const list = points.value
  if (list.length < 2) {
    return ''
  }
  return list
    .map((point, index) => {
      const x = (index / (list.length - 1)) * 300
      const y = 140 - Math.min(1, point.riskScore) * 130
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const cursorX = computed(() => {
  const list = points.value
  if (list.length < 2) {
    return 0
  }
  return (cursor.value / (list.length - 1)) * 300
})

const cursorRiskY = computed(() => {
  const point = points.value[cursor.value]
  return point ? 140 - Math.min(1, point.riskScore) * 130 : 140
})

const riskThresholdY = 140 - 0.8 * 130

const ACTION_LABEL: Record<string, string> = {
  CREATE: '告警触发',
  OPEN: '告警触发',
  ACK: '确认告警',
  ACKED: '确认告警',
  DISPATCH: '派单处置',
  DISPATCHED: '派单处置',
  RESOLVE: '解除告警',
  RESOLVED: '解除告警',
  CLOSE: '事件关闭',
  CLOSED: '事件关闭',
  FALSE_ALARM: '标记误报',
  COMMENT: '添加备注',
  NOTE: '添加备注',
  ESCALATE: '告警升级',
  ESCALATED: '告警升级',
  ASSIGN: '指派处置',
  ASSIGNED: '指派处置',
  VERIFY: '现场核验'
}
const TRIGGER_ACTIONS = new Set(['CREATE', 'CREATED', 'OPEN', 'TRIGGER'])
const RISK_SEGMENTS = [
  { key: 'normal', label: '正常', color: '#43b9f5' },
  { key: 'warn', label: '接近阈值', color: '#f5a25c' },
  { key: 'bad', label: '超阈值', color: '#ff6b72' }
]

const sampleBodyRef = ref<HTMLElement>()

const timeline = computed(() => {
  const alert = detail.value?.alert
  if (!alert) return []
  const entries: Array<{ at: string; label: string; note: string }> = [
    { at: alert.triggeredAt, label: '告警触发', note: `${levelLabel(alert.level)} · ${alert.reason}` }
  ]
  const actions = detail.value?.actions ?? []
  if (actions.length) {
    for (const item of actions) {
      const key = item.action.toUpperCase()
      if (TRIGGER_ACTIONS.has(key)) continue
      entries.push({
        at: item.at,
        label: ACTION_LABEL[key] || item.action,
        note: item.note || (item.operatorId ? `操作人 #${item.operatorId}` : '')
      })
    }
  } else {
    if (alert.firstAckAt) entries.push({ at: alert.firstAckAt, label: '首次确认', note: '' })
    if (alert.closedAt) entries.push({ at: alert.closedAt, label: '事件关闭', note: '' })
  }
  return entries.sort((a, b) => a.at.localeCompare(b.at))
})

const riskSegments = computed(() => {
  const list = points.value
  const counts = {
    normal: list.filter((item) => item.riskScore < 0.55).length,
    warn: list.filter((item) => item.riskScore >= 0.55 && item.riskScore < 0.8).length,
    bad: list.filter((item) => item.riskScore >= 0.8).length
  }
  const total = Math.max(1, list.length)
  return RISK_SEGMENTS.map((seg) => ({
    ...seg,
    count: counts[seg.key as keyof typeof counts],
    pct: (counts[seg.key as keyof typeof counts] / total) * 100
  }))
})

function frameTone(score: number) {
  if (score >= 0.8) return 'is-bad'
  if (score >= 0.55) return 'is-warn'
  return 'is-normal'
}

function verdict(score: number) {
  if (score >= 0.8) return '超阈值'
  if (score >= 0.55) return '接近阈值'
  return '正常'
}

function clockOf(value: string) {
  return value ? value.replace('T', ' ').slice(11, 19) : '-'
}

function seek(index: number) {
  pause()
  cursor.value = index
}

// 播放时让当前帧始终留在采样表可视区域内
watch(cursor, () => {
  const body = sampleBodyRef.value
  if (!body) return
  const row = body.querySelector('tr.is-current') as HTMLElement | null
  if (!row) return
  const rowRect = row.getBoundingClientRect()
  const bodyRect = body.getBoundingClientRect()
  if (rowRect.top < bodyRect.top) {
    body.scrollTop -= bodyRect.top - rowRect.top
  } else if (rowRect.bottom > bodyRect.bottom) {
    body.scrollTop += rowRect.bottom - bodyRect.bottom
  }
}, { flush: 'post' })

function levelLabel(value: string) {
  return LEVEL_LABEL[value] || value
}

function statusLabel(value: string) {
  return STATUS_LABEL[value] || value
}

function postureLabel(value?: string) {
  if (!value) return '-'
  return POSTURE_LABEL[value.toUpperCase()] || value
}

function shortTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(5, 19) : '-'
}

function pause() {
  playing.value = false
  window.clearInterval(playTimer)
  playTimer = 0
}

// 按倍速重建计时器；到达最后一帧自动停止，不循环
function schedule() {
  window.clearInterval(playTimer)
  playTimer = window.setInterval(() => {
    if (cursor.value >= points.value.length - 1) {
      pause()
      return
    }
    cursor.value += 1
  }, Math.max(50, Math.round(1000 / speed.value)))
}

function togglePlay() {
  if (playing.value) {
    pause()
    return
  }
  if (points.value.length < 2) {
    return
  }
  if (isEnd.value) {
    cursor.value = 0
  }
  playing.value = true
  schedule()
}

function setSpeed(value: number) {
  if (speed.value === value) {
    return
  }
  speed.value = value
  if (playing.value) {
    schedule()
  }
}

async function loadAlerts() {
  const data = await fetchAlerts({ page: 1, size: 30 })
  alerts.value = data.list
  if (!selectedId.value && data.list.length) {
    selectedId.value = data.list[0].id
    await loadDetail()
  }
}

async function loadDetail() {
  if (!selectedId.value) {
    return
  }
  detail.value = await fetchAlertDetail(selectedId.value)
  pause()
  cursor.value = 0
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) {
    rafId = window.requestAnimationFrame(draw)
    return
  }
  const width = canvas.clientWidth || 320
  const height = Math.min(320, Math.round(width * 0.42))
  const dpr = window.devicePixelRatio || 1
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr)
    canvas.height = Math.round(height * dpr)
    canvas.style.height = `${height}px`
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  const gradient = ctx.createLinearGradient(0, 0, 0, height)
  gradient.addColorStop(0, '#14293c')
  gradient.addColorStop(1, '#0a1724')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, width, height)

  const list = points.value
  if (list.length > 1) {
    ctx.beginPath()
    list.forEach((point, index) => {
      const x = point.x * width
      const y = point.y * height
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.strokeStyle = 'rgba(92, 200, 255, 0.55)'
    ctx.lineWidth = 1.2
    ctx.stroke()

    const current = list[Math.min(cursor.value, list.length - 1)]
    for (let i = 0; i <= Math.min(cursor.value, list.length - 1); i += 1) {
      const point = list[i]
      ctx.beginPath()
      ctx.arc(point.x * width, point.y * height, 1.6, 0, Math.PI * 2)
      ctx.fillStyle = point.riskScore >= 0.8 ? '#ff9298' : point.riskScore >= 0.55 ? '#ffc078' : '#7ee0ff'
      ctx.fill()
    }
    ctx.beginPath()
    ctx.arc(current.x * width, current.y * height, 5, 0, Math.PI * 2)
    ctx.fillStyle = '#dff2ff'
    ctx.fill()
  }
  rafId = window.requestAnimationFrame(draw)
}

watch(points, () => {
  pause()
  cursor.value = 0
})

onMounted(async () => {
  await loadAlerts()
  rafId = window.requestAnimationFrame(draw)
})

onBeforeUnmount(() => {
  pause()
  window.cancelAnimationFrame(rafId)
})
</script>

<style scoped>
.replay {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.replay__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.replay__toolbar .sp-panel__title {
  justify-content: flex-start;
  gap: 10px;
  margin-bottom: 2px;
}

.replay__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  align-items: stretch;
  gap: 16px;
}

/* 左列内容脱离文档流，行高由右侧信息栏决定，明细卡自动填满左下方空白 */
.replay__main {
  position: relative;
  min-height: 460px;
}

.replay__main-inner {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.replay__stage {
  flex: none;
}

.replay__samples {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.replay__strip {
  display: flex;
  gap: 2px;
  height: 22px;
  margin-bottom: 12px;
}

.replay__strip-cell {
  flex: 1;
  min-width: 0;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 3px;
  background: rgba(67, 185, 245, .45);
  cursor: pointer;
  transition: transform .12s ease, box-shadow .12s ease;
}

.replay__strip-cell.is-warn { background: rgba(245, 162, 92, .72); }
.replay__strip-cell.is-bad { background: rgba(255, 107, 114, .85); }

.replay__strip-cell.is-current {
  border-color: #dff2ff;
  box-shadow: 0 0 0 2px rgba(223, 242, 255, .28);
  transform: scaleY(1.18);
}

.replay__strip-cell:hover { border-color: var(--brand-bright); }

.replay__samples-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr);
  gap: 16px;
}

.replay__samples-table,
.replay__samples-aside {
  min-height: 0;
  overflow-y: auto;
  border: 1px solid var(--line-soft);
  border-radius: var(--r-md);
  background: var(--inset);
}

.replay__samples-aside {
  padding: 12px 14px;
}

.replay__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.replay__table th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 8px 10px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  background: var(--card-soft);
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}

.replay__table td {
  padding: 6px 10px;
  color: var(--ink-2);
  border-bottom: 1px solid var(--line-soft);
  white-space: nowrap;
}

.replay__table tbody tr { cursor: pointer; }
.replay__table tbody tr:hover { background: rgba(67, 185, 245, .08); }
.replay__table tbody tr.is-current { background: rgba(67, 185, 245, .14); }
.replay__table tbody tr.is-current td { color: var(--ink); font-weight: 600; }
.replay__table tbody tr.is-bad td:nth-child(5) { color: var(--bad); }

.replay__verdict {
  display: inline-block;
  padding: 1px 7px;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 10.5px;
}

.replay__verdict.is-normal { color: var(--brand); }
.replay__verdict.is-warn { color: var(--warn); }
.replay__verdict.is-bad { color: var(--bad); }

.replay__samples-empty { padding: 16px; text-align: center; }

.replay__subtitle {
  margin-bottom: 10px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: .02em;
}

.replay__samples-aside .replay__subtitle:not(:first-child) { margin-top: 18px; }

.replay__timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.replay__timeline-item {
  display: flex;
  gap: 9px;
  font-size: 12px;
  line-height: 1.5;
}

.replay__timeline-dot {
  flex: none;
  width: 7px;
  height: 7px;
  margin-top: 5px;
  border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 0 3px rgba(67, 185, 245, .14);
}

.replay__timeline-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.replay__timeline-head b { font-weight: 600; color: var(--ink); }

.replay__segment-bar {
  display: flex;
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--card-soft);
}

.replay__segment-bar span { height: 100%; }

.replay__segment-legend {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: 10px;
  font-size: 11px;
}

.replay__segment-legend div {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--ink-3);
}

.replay__segment-legend i {
  width: 7px;
  height: 7px;
  border-radius: 2px;
  flex: none;
}

.replay__segment-legend b {
  margin-left: auto;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.replay__side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.replay__canvas {
  width: 100%;
  border-radius: 8px;
  display: block;
  border: 1px solid var(--line-soft);
}

.replay__controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.speed {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--card-soft);
}

.speed__btn {
  height: 22px;
  min-width: 40px;
  padding: 0 8px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--ink-4);
  font-family: var(--font);
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background .16s ease, color .16s ease, box-shadow .16s ease;
}

.speed__btn:hover {
  color: var(--brand);
}

.speed__btn.is-on {
  background: var(--card);
  color: var(--brand-deep);
  box-shadow: var(--shadow-1);
}

.replay__time {
  font-size: 12px;
  color: var(--ink-3);
  white-space: nowrap;
}

.replay__chart {
  width: 100%;
  height: 150px;
  background: #14293c;
  border: 1px solid var(--line-soft);
  border-radius: 8px;
}

.replay__chart-hint {
  margin-top: 8px;
}

.replay__current-value {
  font-size: 30px;
  font-weight: 680;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.replay__current-value.is-warn { color: var(--warn-deep); }
.replay__current-value.is-bad { color: var(--bad-deep); }

.replay__kv {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  gap: 9px 12px;
  margin-top: 14px;
  font-size: 12.5px;
}

.replay__kv b {
  font-weight: 600;
  color: var(--ink);
  overflow-wrap: anywhere;
}

.replay__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.replay__stat {
  padding: 10px 6px;
  border: 1px solid var(--line-soft);
  border-radius: var(--r-md);
  background: var(--card-soft);
  text-align: center;
}

.replay__stat b {
  display: block;
  font-size: 20px;
  font-weight: 650;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.replay__stat span {
  font-size: 11px;
  color: var(--ink-4);
}

@media (max-width: 1100px) {
  .replay__grid {
    grid-template-columns: 1fr;
  }
  .replay__main {
    position: static;
    min-height: 0;
  }
  .replay__main-inner {
    position: static;
  }
  .replay__samples {
    flex: none;
    height: 420px;
  }
  .replay__side {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .replay__side {
    grid-template-columns: 1fr;
  }
  .replay__samples {
    height: 560px;
  }
  .replay__samples-body {
    grid-template-columns: 1fr;
  }
}
</style>
