<template>
  <div class="monitor">
    <transition name="fade">
      <div v-if="banner" class="banner" :class="`banner--${banner.tone}`">
        <span class="banner__dot" />
        <span class="banner__text">{{ banner.text }}</span>
        <span class="banner__hint">{{ banner.hint }}</span>
      </div>
    </transition>

    <section class="sp-panel stage">
      <div class="sp-panel__title">
        <span>标准训练池 A · 全景（CAM-01）</span>
        <span class="stage__badges">
          <span v-if="wsConnected" class="sp-badge sp-badge--live">实时通道已连接</span>
          <span v-else class="sp-badge">通道重连中…</span>
          <span class="sp-badge sp-badge--mock">占位模型</span>
          <span class="stage__seg">
            <button
              type="button"
              :class="{ 'is-on': viewMode === 'sim' }"
              @click="viewMode = 'sim'"
            >合成画面</button>
            <button
              type="button"
              :class="{ 'is-on': viewMode === 'stream' }"
              @click="switchToStream"
            >摄像头</button>
          </span>
        </span>
      </div>

      <div
        ref="wrapRef"
        class="stage__canvas-wrap"
        @mousemove="onMouseMove"
        @mouseleave="hovered = null"
      >
        <canvas ref="canvasRef" v-show="viewMode === 'sim'" class="stage__canvas" />
        <img
          v-if="viewMode === 'stream'"
          :src="streamUrl"
          class="stage__stream"
          alt="实时摄像头画面"
          @error="onStreamError"
        />
        <div v-if="hovered" class="target-card" :style="cardStyle">
          <div class="target-card__head">
            <span class="target-card__id">#{{ hovered.trackNo }}</span>
            <span class="target-card__level" :class="`lv-${hovered.level.toLowerCase()}`">
              {{ levelLabel(hovered.level) }}
            </span>
          </div>
          <div class="target-card__row"><span>姿态</span><b>{{ postureLabel(hovered.posture) }}</b></div>
          <div class="target-card__row"><span>风险分</span><b>{{ hovered.riskScore.toFixed(2) }}</b></div>
          <div class="target-card__row"><span>头部未出水</span><b>{{ hovered.riskDetail?.underWaterSec ?? 0 }} s</b></div>
          <div class="target-card__row"><span>静止</span><b>{{ hovered.riskDetail?.stillSec ?? 0 }} s</b></div>
          <div class="target-card__row" v-if="hovered.wristband">
            <span>手环 {{ hovered.wristband }}</span>
            <b>{{ hovered.wristbandData?.heartRate ?? '-' }} bpm / {{ hovered.wristbandData?.spo2 ?? '-' }}%</b>
          </div>
          <div class="target-card__reason">{{ hovered.reason || '正常游泳' }}</div>
          <div class="target-card__foot sp-dim">置信度 {{ hovered.confidence?.toFixed(2) ?? '-' }} · 占位输出</div>
        </div>
        <div class="stage__watermark sp-dim">合成画面 · 占位模型输出 · 非真实泳池影像</div>
      </div>

      <div class="statusbar">
        <div class="statusbar__item"><span class="sp-dim">渲染</span><b>{{ fps }} FPS</b></div>
        <div class="statusbar__item"><span class="sp-dim">帧序号</span><b>{{ frames?.seq ?? 0 }}</b></div>
        <div class="statusbar__item"><span class="sp-dim">推理</span><b>{{ frames?.inferMs ?? '-' }} ms</b></div>
        <div class="statusbar__item"><span class="sp-dim">数据延迟</span><b>{{ (dataDelay / 1000).toFixed(1) }} s</b></div>
        <div class="statusbar__item"><span class="sp-dim">观察端</span><b>{{ online }} 在线</b></div>
        <div class="statusbar__item"><span class="sp-dim">档位</span><b>{{ frames?.mode ?? '-' }}</b></div>
        <div class="statusbar__item"><span class="sp-dim">剧本</span><b>{{ scenarioLabel }}</b></div>
      </div>
    </section>

    <aside class="side">
      <div class="side__inner">
        <div class="sp-panel">
          <div class="sp-panel__title">实时概况</div>
          <div class="metrics">
            <div class="metric">
              <div class="metric__value">{{ frames?.counts?.total ?? 0 }}</div>
              <div class="metric__label">在场人数</div>
            </div>
            <div class="metric">
              <div class="metric__value">{{ frames?.counts?.child ?? 0 }}</div>
              <div class="metric__label">儿童</div>
            </div>
            <div class="metric">
              <div class="metric__value" :style="{ color: heldCount ? '#f5a25c' : undefined }">{{ heldCount }}</div>
              <div class="metric__label">待确认风险</div>
            </div>
            <div class="metric">
              <div class="metric__value">{{ peakRisk }}<small>分</small></div>
              <div class="metric__label">最高风险</div>
            </div>
          </div>
        </div>

        <div class="sp-panel side__risk">
          <div class="sp-panel__title">
            <span>风险目标</span>
            <span class="sp-dim">{{ frames?.mode }} 档 · 阈值 {{ confidenceThreshold }}</span>
          </div>
          <div class="side__risk-bar">
            <span class="sp-dim">锁存至人工确认 · 待确认 {{ heldCount }}</span>
            <el-popconfirm
              title="确认全部告警已排查完毕？"
              confirm-button-text="确认"
              cancel-button-text="取消"
              width="230"
              @confirm="acknowledgeAll"
            >
              <template #reference>
                <el-button size="small" :disabled="heldCount === 0">全部确认</el-button>
              </template>
            </el-popconfirm>
          </div>
          <div class="side__risk-body">
            <div v-if="heldCount === 0" class="side__risk-empty sp-dim">
              <div>暂无待确认风险</div>
              <div class="side__risk-empty-hint">一旦超阈值就会一直保留，直到人工确认</div>
            </div>
            <div
              v-for="item in heldRisks"
              :key="item.trackNo"
              class="risk-item"
              :class="{ 'risk-item--active': hovered?.trackNo === item.trackNo, 'risk-item--held': !item.active }"
              @mouseenter="pinnedTrack = item.trackNo"
              @mouseleave="pinnedTrack = null"
            >
              <span class="risk-dot" :class="item.active ? `risk-dot--${item.level.toLowerCase()}` : 'risk-dot--held'" />
              <div class="risk-item__main">
                <div class="risk-item__head">
                  <b>#{{ item.trackNo }} · {{ postureLabel(item.posture) }}</b>
                  <span class="risk-item__score">{{ (item.riskScore * 100).toFixed(0) }}</span>
                </div>
                <div class="sp-dim risk-item__reason">{{ item.reason || '风险超阈值' }}</div>
                <div class="risk-item__meta">
                  <span class="risk-tag" :class="item.active ? 'risk-tag--live' : 'risk-tag--held'">
                    {{ item.active ? '报警中' : '已恢复 · 待确认' }}
                  </span>
                  <span class="sp-dim">{{ heldTime(item.triggeredAt) }}</span>
                  <button type="button" class="risk-ack" @click.stop="acknowledge(item.trackNo)">确认</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <div class="monitor__bottom">
      <section class="sp-panel">
        <div class="sp-panel__title">水质（模拟）</div>
        <div class="info-grid">
          <div class="water-row"><span>水温</span><b>{{ frames?.water?.temperature ?? '-' }} ℃</b></div>
          <div class="water-row"><span>pH</span><b>{{ frames?.water?.ph ?? '-' }}</b></div>
          <div class="water-row">
            <span>浑浊度</span>
            <b :style="{ color: turbidityColor }">{{ frames?.water?.turbidity ?? '-' }} NTU</b>
          </div>
          <div class="water-row"><span>余氯</span><b>{{ frames?.water?.chlorine ?? '-' }} mg/L</b></div>
        </div>
      </section>

      <section class="sp-panel">
        <div class="sp-panel__title">运行信息</div>
        <div class="info-grid">
          <div class="water-row"><span>检测提供者</span><b>{{ frames?.provider || '-' }}</b></div>
          <div class="water-row"><span>已推送帧</span><b class="num">{{ pushedFrames }}</b></div>
          <div class="water-row">
            <span>模型状态</span><b style="color: #9a8cff">{{ frames?.modelLoaded ? '已加载' : '占位（未加载权重）' }}</b>
          </div>
          <div class="water-row"><span>失败帧</span><b class="num" :style="{ color: failedFrames ? '#ff6b72' : undefined }">{{ failedFrames }}</b></div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ackAlert, fetchActiveAlerts, fetchSnapshot, fetchZones } from '@/api'
import { onLive, useLiveConnection } from '@/composables/useLiveSocket'
import type { ActiveAlert, Frames, Target, Zone } from '@/types/api'

const LEVEL_COLOR: Record<string, string> = {
  NORMAL: '#67d9ff',
  NOTICE: '#f7d488',
  WEAK: '#ffc078',
  STRONG: '#ff8a90'
}

const LEVEL_LABEL: Record<string, string> = {
  NORMAL: '正常',
  NOTICE: '提示',
  WEAK: '弱告警',
  STRONG: '强告警'
}

const POSTURE_LABEL: Record<string, string> = {
  swimming: '游泳',
  floating: '漂浮',
  standing: '站立',
  treading: '踩水',
  underwater_still: '水下静止',
  diving: '跳水',
  unknown: '未知'
}

const SCENARIO_LABEL: Record<string, string> = {
  normal: '正常游泳',
  drown_still: '静止下沉',
  zone_intrude: '越界闯入',
  night_intrude: '营业外闯入',
  water_poor: '水质超标'
}

interface RenderTarget {
  x: number
  y: number
  tx: number
  ty: number
  target: Target
  lastSeen: number
}

const wrapRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()
const frames = ref<Frames | null>(null)
const zones = ref<Zone[]>([])
const { connected: wsConnected } = useLiveConnection()

/* 真实摄像头画面（MJPEG）与合成画面互斥。
   AI 服务未配置 AI_VIDEO_SOURCE 时按钮会提示不可用，不影响原演示流程。 */
const viewMode = ref<'sim' | 'stream'>('sim')
const streamEnabled = ref(false)
const streamSession = ref(Date.now())
const streamUrl = computed(() => `/ai/stream.mjpg?session=${streamSession.value}`)

async function probeStream() {
  try {
    const response = await fetch('/ai/stream/status')
    if (!response.ok) {
      streamEnabled.value = false
      return
    }
    const data = await response.json()
    streamEnabled.value = Boolean(data.enabled)
  } catch {
    streamEnabled.value = false
  }
}

async function switchToStream() {
  if (viewMode.value === 'stream') {
    return
  }
  await probeStream()
  if (!streamEnabled.value) {
    ElMessage.warning('未配置真实视频源（AI_VIDEO_SOURCE），当前仅合成画面可用')
    return
  }
  // 换 session 参数强制重新发起连接，避免浏览器复用已断开的 MJPEG 响应
  streamSession.value = Date.now()
  viewMode.value = 'stream'
}

function onStreamError() {
  ElMessage.error('实时画面连接失败，已切回合成画面')
  viewMode.value = 'sim'
}

const dataDelay = ref(0)
const fps = ref(0)
const online = ref(0)
const hovered = ref<Target | null>(null)
const pinnedTrack = ref<number | null>(null)
const pushedFrames = ref(0)
const failedFrames = ref(0)
const cardPos = reactive({ x: 0, y: 0 })

const renderMap = new Map<number, RenderTarget>()
let offLive: (() => void) | null = null
let rafId = 0
let bgCanvas: HTMLCanvasElement | null = null
let bgDirty = true
let lastDrawAt = 0
let fpsAccum = 0
let fpsFrames = 0
let lastFrameAt = 0
let delayTimer = 0
const noticeDegraded = ref(false)

/* 风险锁存：以服务端未确认告警（status=OPEN）为唯一事实源。
   目标超阈值后由后端建单，即使恢复正常也不自动消失，只有人工确认才关闭；
   刷新、换浏览器、换值守人看到的是同一份列表，并留下处置时间线与审计。 */
type HeldRisk = ActiveAlert & { riskScore: number }

const heldRisks = ref<HeldRisk[]>([])
let alertTimer = 0

async function refreshActiveAlerts() {
  try {
    const data = await fetchActiveAlerts(1)
    heldRisks.value = data.list.map((item) => ({
      ...item,
      riskScore: Number(item.riskScore ?? 0)
    }))
  } catch {
    // 接口暂时不可用时保留上一份列表，避免面板闪空
  }
}

async function acknowledge(trackNo: number) {
  const item = heldRisks.value.find((entry) => entry.trackNo === trackNo)
  if (!item) {
    return
  }
  try {
    await ackAlert(item.id, '大屏值班确认')
    heldRisks.value = heldRisks.value.filter((entry) => entry.id !== item.id)
    if (pinnedTrack.value === trackNo) {
      pinnedTrack.value = null
    }
    await refreshActiveAlerts()
  } catch {
    /* 拦截器已提示 */
  }
}

async function acknowledgeAll() {
  for (const item of [...heldRisks.value]) {
    try {
      await ackAlert(item.id, '大屏批量确认')
    } catch {
      // 单条失败不影响其它条目
    }
  }
  pinnedTrack.value = null
  await refreshActiveAlerts()
}

function heldTime(ts: string) {
  const date = new Date(ts)
  return Number.isNaN(date.getTime()) ? ts : date.toLocaleTimeString('zh-CN', { hour12: false })
}

const heldCount = computed(() => heldRisks.value.length)
const peakRisk = computed(() =>
  heldRisks.value.reduce((max, item) => Math.max(max, item.riskScore), 0).toFixed(2)
)
const confidenceThreshold = computed(
  () => frames.value?.params?.confidence ?? (frames.value?.mode === 'OFFPEAK' ? 0.85 : 0.7)
)
const turbidityColor = computed(() => ((frames.value?.water?.turbidity ?? 0) > 5 ? '#f5a25c' : 'inherit'))
const scenarioLabel = computed(() => SCENARIO_LABEL[frames.value?.scenario || 'normal'] || frames.value?.scenario)

const banner = computed(() => {
  if (noticeDegraded.value) {
    return { tone: 'danger', text: '推理服务不可用，画面已冻结', hint: '恢复后自动继续，无需刷新' }
  }
  if (!wsConnected.value) {
    return { tone: 'warn', text: '实时通道已断开，正在重连', hint: '重连成功后自动对齐最新帧' }
  }
  if (dataDelay.value > 5000) {
    return { tone: 'warn', text: `数据延迟 ${(dataDelay.value / 1000).toFixed(1)} s`, hint: '请检查推理服务与网络' }
  }
  return null
})

const cardStyle = computed(() => ({
  left: `${cardPos.x}px`,
  top: `${cardPos.y}px`
}))

function levelLabel(level: string) {
  return LEVEL_LABEL[level] || level
}

function postureLabel(posture?: string | null) {
  if (!posture) {
    return '-'
  }
  return POSTURE_LABEL[posture] || posture
}

function applyFrames(next: Frames) {
  frames.value = next
  const now = performance.now()
  for (const target of next.targets) {
    const cx = target.box.x + target.box.w / 2
    const cy = target.box.y + target.box.h / 2
    const existing = renderMap.get(target.trackNo)
    if (existing) {
      existing.tx = cx
      existing.ty = cy
      existing.target = target
      existing.lastSeen = now
    } else {
      renderMap.set(target.trackNo, { x: cx, y: cy, tx: cx, ty: cy, target, lastSeen: now })
    }
  }
  if (pinnedTrack.value !== null) {
    hovered.value = next.targets.find((t) => t.trackNo === pinnedTrack.value) || hovered.value
  }
}

function geometry() {
  const wrap = wrapRef.value
  if (!wrap) {
    return null
  }
  const width = wrap.clientWidth
  const height = Math.round(width * 0.52)
  return { width, height, pad: 18 }
}

function buildBackground(width: number, height: number, pad: number) {
  const canvas = document.createElement('canvas')
  const dpr = window.devicePixelRatio || 1
  canvas.width = Math.round(width * dpr)
  canvas.height = Math.round(height * dpr)
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return canvas
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  const poolW = width - pad * 2
  const poolH = height - pad * 2
  const gradient = ctx.createLinearGradient(0, pad, 0, pad + poolH)
  gradient.addColorStop(0, '#14293c')
  gradient.addColorStop(0.55, '#0f2032')
  gradient.addColorStop(1, '#0a1724')
  ctx.fillStyle = gradient
  ctx.fillRect(pad, pad, poolW, poolH)

  ctx.strokeStyle = 'rgba(125, 195, 240, 0.22)'
  ctx.lineWidth = 1
  for (let i = 1; i < 6; i += 1) {
    const y = pad + (poolH / 6) * i
    ctx.beginPath()
    ctx.moveTo(pad, y)
    ctx.lineTo(pad + poolW, y)
    ctx.stroke()
  }
  for (let i = 1; i < 5; i += 1) {
    const x = pad + (poolW / 5) * i
    ctx.strokeStyle = 'rgba(125, 195, 240, 0.11)'
    ctx.beginPath()
    ctx.moveTo(x, pad)
    ctx.lineTo(x, pad + poolH)
    ctx.stroke()
  }

  for (const zone of zones.value) {
    const points = parsePolygon(zone.polygonJson)
    if (points.length < 3) {
      continue
    }
    ctx.beginPath()
    points.forEach((point, index) => {
      const x = pad + point.x * poolW
      const y = pad + point.y * poolH
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.closePath()
    const fill = zone.type === 'DEEP' ? 'rgba(255, 107, 114, 0.07)'
      : zone.type === 'KIDS' ? 'rgba(233, 196, 106, 0.07)'
        : 'rgba(67, 185, 245, 0.07)'
    ctx.fillStyle = fill
    ctx.fill()
    ctx.strokeStyle = 'rgba(125, 195, 240, 0.4)'
    ctx.setLineDash([6, 4])
    ctx.stroke()
    ctx.setLineDash([])
    const first = points[0]
    ctx.fillStyle = 'rgba(190, 220, 240, 0.7)'
    ctx.font = '12px "Microsoft YaHei", sans-serif'
    ctx.fillText(zone.name, pad + first.x * poolW + 8, pad + first.y * poolH + 18)
  }

  return canvas
}

function drawTarget(ctx: CanvasRenderingContext2D, state: RenderTarget, pad: number, poolW: number, poolH: number) {
  const { target } = state
  const color = LEVEL_COLOR[target.level] || '#67d9ff'
  const cx = pad + state.x * poolW
  const cy = pad + state.y * poolH
  const radius = Math.max(5, Math.min(poolW, poolH) * 0.022)

  // 水波
  const ripple = 0.5 + 0.5 * Math.sin(performance.now() / 600 + target.trackNo)
  ctx.beginPath()
  ctx.ellipse(cx, cy + radius * 0.55, radius * (1.4 + ripple * 0.35), radius * (0.6 + ripple * 0.15), 0, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(125, 195, 240, ${0.18 + ripple * 0.12})`
  ctx.lineWidth = 1
  ctx.stroke()

  // 泳者
  const body = ctx.createRadialGradient(cx - radius * 0.3, cy - radius * 0.3, radius * 0.2, cx, cy, radius)
  body.addColorStop(0, '#dff2ff')
  body.addColorStop(1, color)
  ctx.beginPath()
  ctx.arc(cx, cy, radius, 0, Math.PI * 2)
  ctx.fillStyle = body
  ctx.fill()

  // 风险环
  if (target.riskScore > 0.1) {
    ctx.beginPath()
    ctx.arc(cx, cy, radius + 4, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1, target.riskScore))
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.stroke()
  }

  // 检测框
  const bw = target.box.w * poolW
  const bh = target.box.h * poolH
  const bx = cx - bw / 2
  const by = cy - bh / 2
  ctx.strokeStyle = color
  ctx.lineWidth = target.level === 'STRONG' ? 2 : 1.2
  if (target.level === 'STRONG') {
    ctx.setLineDash([])
    const pulse = 0.35 + 0.35 * Math.sin(performance.now() / 220)
    ctx.strokeStyle = `rgba(255, 138, 144, ${0.55 + pulse * 0.45})`
  }
  ctx.strokeRect(bx, by, bw, bh)
  ctx.setLineDash([])

  // 标签
  const label = `#${target.trackNo} ${(target.riskScore * 100).toFixed(0)}`
  ctx.font = '11px "Microsoft YaHei", sans-serif'
  const textWidth = ctx.measureText(label).width + 10
  ctx.fillStyle = color
  ctx.fillRect(bx, by - 17, textWidth, 16)
  ctx.fillStyle = '#0b1a28'
  ctx.fillText(label, bx + 5, by - 5)
}

function draw() {
  const canvas = canvasRef.value
  const geo = geometry()
  if (!canvas || !geo) {
    return
  }
  const { width, height, pad } = geo
  const dpr = window.devicePixelRatio || 1
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr)
    canvas.height = Math.round(height * dpr)
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    bgDirty = true
  }
  if (!bgCanvas || bgDirty) {
    bgCanvas = buildBackground(width, height, pad)
    bgDirty = false
  }

  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)
  ctx.drawImage(bgCanvas, 0, 0, width, height)

  const poolW = width - pad * 2
  const poolH = height - pad * 2
  const now = performance.now()
  for (const [trackNo, state] of renderMap) {
    if (now - state.lastSeen > 3000) {
      renderMap.delete(trackNo)
      continue
    }
    drawTarget(ctx, state, pad, poolW, poolH)
  }
}

function loop(now: number) {
  const dt = now - lastDrawAt
  lastDrawAt = now
  const k = Math.min(1, dt / 140)
  for (const state of renderMap.values()) {
    state.x += (state.tx - state.x) * k
    state.y += (state.ty - state.y) * k
  }
  draw()

  fpsAccum += dt
  fpsFrames += 1
  if (fpsAccum >= 500) {
    fps.value = Math.round((fpsFrames * 1000) / fpsAccum)
    fpsAccum = 0
    fpsFrames = 0
  }
  rafId = window.requestAnimationFrame(loop)
}

function onMouseMove(event: MouseEvent) {
  const wrap = wrapRef.value
  const geo = geometry()
  if (!wrap || !geo) {
    return
  }
  const rect = wrap.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const { pad } = geo
  const poolW = geo.width - pad * 2
  const poolH = geo.height - pad * 2
  const nx = (x - pad) / poolW
  const ny = (y - pad) / poolH

  let hit: Target | null = null
  for (const state of renderMap.values()) {
    const box = state.target.box
    if (nx >= box.x - 0.01 && nx <= box.x + box.w + 0.01 && ny >= box.y - 0.015 && ny <= box.y + box.h + 0.015) {
      hit = state.target
      break
    }
  }
  hovered.value = hit
  if (hit) {
    cardPos.x = Math.min(Math.max(12, x + 16), Math.max(12, geo.width - 240))
    cardPos.y = Math.min(Math.max(12, y + 16), Math.max(12, geo.height - 210))
  }
}

function parsePolygon(json: string): Array<{ x: number; y: number }> {
  try {
    const parsed = JSON.parse(json)
    return Array.isArray(parsed?.points) ? parsed.points : []
  } catch {
    return []
  }
}

async function pullSnapshot() {
  try {
    const response = await fetchSnapshot(1)
    applyFrames(response.snapshot)
    dataDelay.value = response.dataDelayMs
    online.value = response.wsOnline
    pushedFrames.value = response.pushedFrames ?? 0
    failedFrames.value = response.failedFrames ?? 0
    noticeDegraded.value = Boolean(response.degraded)
  } catch {
    // 首帧未就绪时由 WS 补上
  }
}

async function bootstrap() {
  // 先订阅再拉数据：连接若已就绪会立即补发 ws.open，避免漏掉首帧对齐。
  // 连接本身由 AppLayout 统一持有，本页卸载不会影响其它页面。
  offLive = onLive((type, payload) => {
    if (type === 'frames') {
      applyFrames(payload as Frames)
      lastFrameAt = performance.now()
      dataDelay.value = 0
      noticeDegraded.value = false
    } else if (type === 'system.notice') {
      const level = (payload as { level?: string })?.level
      noticeDegraded.value = level === 'degraded'
    } else if (type === 'alert.created' || type === 'alert.updated') {
      refreshActiveAlerts()
    } else if (type === 'ws.open') {
      pullSnapshot()
      refreshActiveAlerts()
    }
  })

  try {
    zones.value = await fetchZones(1)
    bgDirty = true
  } catch {
    zones.value = []
  }
  await pullSnapshot()
  await refreshActiveAlerts()

  delayTimer = window.setInterval(() => {
    if (lastFrameAt > 0) {
      dataDelay.value = performance.now() - lastFrameAt
    }
  }, 1000)

  // 兜底轮询：WS 通知丢失时也能在 3 秒内对齐服务端锁存列表
  alertTimer = window.setInterval(refreshActiveAlerts, 3000)
}

function onResize() {
  bgDirty = true
}

onMounted(() => {
  bootstrap()
  rafId = window.requestAnimationFrame(loop)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  offLive?.()
  window.cancelAnimationFrame(rafId)
  window.clearInterval(delayTimer)
  window.clearInterval(alertTimer)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.monitor {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 16px;
  align-items: stretch;
}

.banner {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  border: 1px solid transparent;
}

.banner--warn {
  background: rgba(233, 196, 106, 0.12);
  border-color: rgba(233, 196, 106, 0.45);
  color: #c9a24c;
}

.banner--danger {
  background: rgba(255, 107, 114, 0.12);
  border-color: rgba(255, 107, 114, 0.45);
  color: #e05a61;
}

.banner__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 1.4s infinite;
}

.banner__hint {
  margin-left: auto;
  color: var(--sp-text-dim);
  font-size: 12px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.stage {
  display: flex;
  flex-direction: column;
}

.stage__badges {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 合成画面 / 摄像头 切换 */
.stage__seg {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  overflow: hidden;
}

.stage__seg button {
  padding: 3px 10px;
  border: 0;
  background: transparent;
  color: var(--ink-4);
  font-size: 11.5px;
  cursor: pointer;
  transition: background .16s ease, color .16s ease;
}

.stage__seg button:hover {
  color: var(--brand);
}

.stage__seg button.is-on {
  background: var(--brand-soft);
  color: var(--brand);
}

.stage__canvas-wrap {
  position: relative;
  width: 100%;
}

.stage__canvas {
  display: block;
  width: 100%;
  border-radius: 8px;
  cursor: crosshair;
}

/* MJPEG 画面：与 canvas 同区域覆盖 */
.stage__stream {
  display: block;
  width: 100%;
  border-radius: 8px;
  background: #09111a;
}

.stage__watermark {
  position: absolute;
  right: 12px;
  bottom: 10px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(6, 18, 28, 0.6); color: rgba(206, 228, 246, .9);
}

.target-card {
  position: absolute;
  z-index: 5;
  width: 226px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(22, 35, 47, .96);
  border: 1px solid var(--sp-border);
  box-shadow: 0 10px 24px rgba(2, 8, 14, .16);
  font-size: 12px;
  pointer-events: none;
}

.target-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.target-card__id {
  font-size: 14px;
  font-weight: 600;
}

.target-card__level {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  border: 1px solid currentColor;
}

.lv-normal { color: #36d1a6; }
.lv-notice { color: #e9c46a; }
.lv-weak { color: #f5a25c; }
.lv-strong { color: #ff6b72; }

.target-card__row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
  color: var(--sp-text-dim);
}

.target-card__row b {
  color: var(--sp-text);
  font-weight: 500;
}

.target-card__reason {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--sp-border);
  color: #c9a24c;
  line-height: 1.5;
}

.target-card__foot {
  margin-top: 4px;
}

.statusbar {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--sp-border);
  font-size: 12px;
}

.statusbar__item {
  display: flex;
  gap: 6px;
  align-items: baseline;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
}

.statusbar__item b {
  font-weight: 600;
  color: var(--sp-text);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 900px) {
  .statusbar {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .statusbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.side {
  position: relative;
  min-height: 0;
}

.side__inner {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
}

.side__risk {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.side__risk-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.side__risk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.side__risk-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-align: center;
  height: 100%;
  min-height: 64px;
}

.side__risk-empty-hint {
  font-size: 11px;
  color: var(--ink-placeholder);
}

.monitor__bottom {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 24px;
}

.metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.metric {
  background: var(--sp-panel-2);
  border-radius: 8px;
  padding: 10px 12px;
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
  margin-top: 2px;
}

.risk-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 6px;
  border-bottom: 1px dashed var(--sp-border);
  border-radius: 6px;
  cursor: default;
}

.risk-item:last-child {
  border-bottom: none;
}

.risk-item--active {
  background: rgba(67, 185, 245, 0.12);
}

.risk-item--held {
  opacity: .88;
}

.risk-item__main {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 1.5;
}

.risk-item__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.risk-item__head b {
  font-weight: 600;
}

.risk-item__score {
  color: var(--warn);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.risk-item__reason {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.risk-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.risk-tag {
  flex: none;
  padding: 1px 6px;
  font-size: 10.5px;
  line-height: 1.5;
  border: 1px solid currentColor;
  border-radius: 999px;
}

.risk-tag--live { color: var(--warn); }
.risk-tag--held { color: var(--ink-4); }

.risk-ack {
  margin-left: auto;
  padding: 2px 9px;
  font: inherit;
  font-size: 11px;
  color: var(--brand);
  background: var(--brand-soft);
  border: 1px solid var(--brand-line);
  border-radius: var(--r-sm);
  cursor: pointer;
}

.risk-ack:hover {
  background: rgba(67, 185, 245, .18);
}

.risk-dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  flex: none;
}

.risk-dot--normal { background: #36d1a6; }
.risk-dot--notice { background: #e9c46a; }
.risk-dot--weak { background: #f5a25c; }
.risk-dot--strong { background: #ff6b72; }
.risk-dot--held { background: #6c8397; }

.water-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  font-size: 12.5px;
  padding: 7px 0;
  color: var(--sp-text-dim);
}

.water-row b {
  color: var(--sp-text);
  font-weight: 500;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1100px) {
  .monitor {
    grid-template-columns: minmax(0, 1fr);
  }
  .side {
    position: static;
  }
  .side__inner {
    position: static;
    grid-template-rows: auto 240px;
  }
  .monitor__bottom {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
