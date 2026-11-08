<template>
  <div class="playback">
    <section class="sp-panel">
      <div class="sp-panel__title">
        <span>检测结果回放</span>
        <span class="sp-dim">离线预生成 · 按时间轴还原每帧检测框</span>
      </div>

      <div class="toolbar">
        <el-select
          v-model="selected"
          placeholder="选择回放文件"
          class="toolbar__select"
          :loading="loading"
          @change="onSelect"
        >
          <el-option
            v-for="item in items"
            :key="item.name"
            :label="`${item.name}（${item.frames} 帧 / ${item.targets} 目标）`"
            :value="item.name"
          />
        </el-select>
        <el-button :loading="loading" @click="loadList">刷新</el-button>
        <span v-if="payload" class="sp-dim toolbar__meta">
          {{ payload.provider }} · {{ payload.source.kind }} · conf {{ payload.params.conf }} ·
          imgsz {{ payload.params.imgsz }} · stride {{ payload.params.stride }}
        </span>
      </div>

      <div v-if="!items.length" class="empty">
        <p>暂无回放数据。</p>
        <p class="sp-dim">
          在推理服务目录执行 <code>python tools/pregenerate.py --source &lt;视频&gt; --out artifacts/xxx.json</code>
          生成后点击刷新。
        </p>
      </div>

      <template v-else>
        <div class="stage">
          <canvas ref="canvasRef" class="stage__canvas" />
          <div class="stage__note sp-dim">仅回放检测结果，原始画面未随结果保存</div>
        </div>

        <div class="controls">
          <el-button-group>
            <el-button @click="stepTo(-1)" :disabled="!frames.length">上一帧</el-button>
            <el-button type="primary" @click="togglePlay" :disabled="!frames.length">
              {{ playing ? '暂停' : '播放' }}
            </el-button>
            <el-button @click="stepTo(1)" :disabled="!frames.length">下一帧</el-button>
          </el-button-group>

          <el-slider
            v-model="cursor"
            :min="0"
            :max="Math.max(0, frames.length - 1)"
            :disabled="!frames.length"
            :show-tooltip="false"
            class="controls__slider"
          />

          <el-radio-group v-model="speed" size="small">
            <el-radio-button :value="0.5">0.5x</el-radio-button>
            <el-radio-button :value="1">1x</el-radio-button>
            <el-radio-button :value="2">2x</el-radio-button>
            <el-radio-button :value="4">4x</el-radio-button>
          </el-radio-group>
        </div>

        <div class="meta" v-if="current">
          <span>帧 <b>{{ current.index }}</b> / {{ frames.length }}</span>
          <span>时间戳 <b>{{ (current.ts / 1000).toFixed(2) }} s</b></span>
          <span>目标 <b>{{ current.targets.length }}</b></span>
          <span>推理 <b>{{ current.inferMs }} ms</b></span>
          <span class="sp-dim">按 {{ playFps.toFixed(1) }} FPS 还原</span>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

interface ReplayTarget {
  trackNo: number
  box: { x: number; y: number; w: number; h: number }
  confidence: number
  posture: string
  className: string
  placeholder: boolean
}

interface ReplayFrame {
  index: number
  sourceIndex: number
  ts: number
  inferMs: number
  count: number
  targets: ReplayTarget[]
}

interface ReplayPayload {
  version: number
  generatedAt: string
  provider: string
  modelLoaded: boolean
  params: { conf: number; imgsz: number; stride: number }
  source: { kind: string; uri: string; fps: number }
  summary: { frames: number; targets: number; avgInferMs: number }
  frames: ReplayFrame[]
}

interface ReplayItem {
  name: string
  frames: number
  targets: number
  generatedAt: string | null
  provider: string | null
  source: string | null
}

const items = ref<ReplayItem[]>([])
const selected = ref('')
const payload = ref<ReplayPayload | null>(null)
const frames = computed<ReplayFrame[]>(() => payload.value?.frames ?? [])
const loading = ref(false)

const cursor = ref(0)
const playing = ref(false)
const speed = ref(1)
const canvasRef = ref<HTMLCanvasElement>()

let timer = 0

const current = computed<ReplayFrame | null>(() => frames.value[cursor.value] ?? null)

// 回放帧率 = 源帧率 / 抽帧间隔，保证还原速度与真实时间轴一致
const playFps = computed(() => {
  const sourceFps = payload.value?.source.fps || 25
  const stride = Math.max(1, payload.value?.params.stride || 1)
  return sourceFps / stride
})

async function loadList() {
  loading.value = true
  try {
    const response = await fetch('/ai/replay/list')
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const data = await response.json()
    items.value = data.items ?? []
    if (!selected.value && items.value.length) {
      selected.value = items.value[0].name
      await onSelect(items.value[0].name)
    }
  } catch {
    items.value = []
    ElMessage.warning('回放列表获取失败，请确认推理服务已启动')
  } finally {
    loading.value = false
  }
}

async function onSelect(name: string) {
  if (!name) {
    return
  }
  loading.value = true
  pause()
  try {
    const response = await fetch(`/ai/replay/${encodeURIComponent(name)}`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    payload.value = await response.json()
    cursor.value = 0
    draw()
  } catch {
    payload.value = null
    ElMessage.error('回放文件读取失败')
  } finally {
    loading.value = false
  }
}

function togglePlay() {
  if (playing.value) {
    pause()
    return
  }
  if (!frames.value.length) {
    return
  }
  if (cursor.value >= frames.value.length - 1) {
    cursor.value = 0
  }
  playing.value = true
  timer = window.setInterval(step, Math.max(30, 1000 / playFps.value / speed.value))
}

function pause() {
  playing.value = false
  window.clearInterval(timer)
  timer = 0
}

function step() {
  if (!playing.value) {
    return
  }
  if (cursor.value < frames.value.length - 1) {
    cursor.value += 1
  } else {
    pause()
  }
}

function stepTo(delta: number) {
  pause()
  const next = cursor.value + delta
  cursor.value = Math.max(0, Math.min(frames.value.length - 1, next))
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) {
    return
  }
  // 每次绘制都对一次尺寸：onMounted 时 CSS 可能还没布局完（量到默认 300px），
  // 靠这里自校正，避免位图被拉伸导致框线发虚
  const rect = canvas.getBoundingClientRect()
  const expectWidth = Math.round(rect.width)
  if (expectWidth > 100) {
    const expectHeight = Math.round((expectWidth * 9) / 16)
    if (canvas.width !== expectWidth || canvas.height !== expectHeight) {
      canvas.width = expectWidth
      canvas.height = expectHeight
    }
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  const width = canvas.width
  const height = canvas.height

  ctx.fillStyle = '#0b1520'
  ctx.fillRect(0, 0, width, height)

  // 网格背景，用来示意画面区域（原始画面未保存）
  ctx.strokeStyle = 'rgba(58, 82, 102, .35)'
  ctx.lineWidth = 1
  for (let x = 0; x <= width; x += 80) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
  }
  for (let y = 0; y <= height; y += 60) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  const frame = current.value
  if (!frame) {
    ctx.fillStyle = '#8fa8bc'
    ctx.font = '14px Inter, "Microsoft YaHei", sans-serif'
    ctx.fillText('未选择回放数据', 20, 34)
    return
  }

  for (const target of frame.targets) {
    const x = target.box.x * width
    const y = target.box.y * height
    const boxW = target.box.w * width
    const boxH = target.box.h * height
    const color =
      target.posture === 'underwater_still'
        ? '#ff6b72'
        : target.posture === 'swimming'
          ? '#43b9f5'
          : '#8fa8bc'

    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.strokeRect(x, y, boxW, boxH)

    const label =
      `#${target.trackNo}` +
      (target.className ? ` ${target.className}` : '') +
      ` ${target.confidence.toFixed(2)}`
    ctx.font = '12px Inter, "Microsoft YaHei", sans-serif'
    const labelWidth = ctx.measureText(label).width + 10
    const labelY = Math.max(18, y)
    // 靠右的目标标签会超出画布，向左收拢到边界内
    const labelX = Math.min(x, width - labelWidth - 2)
    ctx.fillStyle = color
    ctx.fillRect(labelX, labelY - 18, labelWidth, 18)
    ctx.fillStyle = '#0b1520'
    ctx.fillText(label, labelX + 5, labelY - 4)
  }

  // 左上角 HUD
  const hud =
    `帧 ${frame.index} · ${(frame.ts / 1000).toFixed(2)}s · ` +
    `${frame.targets.length} 目标 · 推理 ${frame.inferMs}ms`
  ctx.font = '12px Inter, "Microsoft YaHei", sans-serif'
  const hudWidth = ctx.measureText(hud).width + 16
  ctx.fillStyle = 'rgba(11, 21, 32, .78)'
  ctx.fillRect(10, 10, hudWidth, 26)
  ctx.fillStyle = '#dfe9f3'
  ctx.fillText(hud, 18, 28)
}

watch(cursor, () => draw())
watch(speed, () => {
  if (playing.value) {
    pause()
    togglePlay()
  }
})

function onResize() {
  draw()
}

onMounted(async () => {
  // 等布局完成先画一帧空态，后续每次 draw 都会自校正画布尺寸
  await nextTick()
  draw()
  loadList()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  pause()
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.playback {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.toolbar__select {
  width: 420px;
}

.toolbar__meta {
  font-size: 12px;
}

/* 16:9 画布在宽屏下会过高，把控制条挤出视口，限制最大宽度并居中 */
.stage {
  position: relative;
  max-width: 1120px;
  margin: 0 auto;
}

.stage__canvas {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  background: #0b1520;
}

.stage__note {
  position: absolute;
  right: 12px;
  bottom: 10px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(6, 18, 28, .66);
  font-size: 11.5px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-top: 14px;
}

.controls__slider {
  flex: 1;
  margin: 0 6px;
}

.meta {
  display: flex;
  gap: 22px;
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--ink-3);
}

.meta b {
  color: var(--ink);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.empty {
  padding: 40px 8px;
  text-align: center;
  line-height: 2;
}

.empty code {
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--inset);
  color: var(--brand);
  font-size: 12px;
}
</style>
