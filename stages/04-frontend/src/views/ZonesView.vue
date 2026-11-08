<template>
  <div class="zones">
    <div class="sp-panel zones__canvas-panel">
      <div class="sp-panel__title">
        <span>电子围栏 · 画面坐标编辑</span>
        <span class="sp-badge">左键预览加点 · 双击确认 · 左键顶点删除</span>
      </div>
      <div ref="wrapRef" class="zones__wrap">
        <canvas
          ref="canvasRef"
          class="zones__canvas"
          @mousedown="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @mouseleave="onMouseLeave"
          @dblclick="onDoubleClick"
        />
        <div v-if="deleteTarget" class="vertex-confirm" :style="confirmStyle">
          <div class="vertex-confirm__text">删除顶点 #{{ deleteTarget.index + 1 }}？</div>
          <div class="vertex-confirm__actions">
            <el-button size="small" type="danger" @click="confirmDeleteVertex">确认删除</el-button>
            <el-button size="small" link @click="deleteTarget = null">取消</el-button>
          </div>
        </div>
      </div>
      <div v-if="previewing" class="zones__preview-hint">
        预览点位跟随鼠标移动，十字线对齐四边刻度 · <b>双击确认加入顶点</b> · 单击左键重选 · Esc 取消
      </div>
      <div class="zones__tip sp-dim">
        刻度为 0–1 归一化画面坐标（每小格 0.1），与检测框、告警同一坐标系；「全池」为兜底区域，不可删除。
      </div>
    </div>

    <aside class="zones__side">
      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>区域列表</span>
          <el-button size="small" @click="startCreate">新建</el-button>
        </div>
        <div
          v-for="zone in zones"
          :key="zone.id"
          class="zone-item"
          :class="{ 'zone-item--active': zone.id === selectedId }"
          @click="select(zone)"
        >
          <span class="zone-dot" :class="`zone-dot--${zone.type.toLowerCase()}`" />
          <div class="zone-item__main">
            <div>{{ zone.name }}</div>
            <div class="sp-dim">{{ typeLabel(zone.type) }} · {{ groupLabel(zone.allowedGroups) }}</div>
          </div>
          <el-tag v-if="!zone.enabled" size="small" type="info">停用</el-tag>
        </div>
      </div>

      <div class="sp-panel">
        <div class="sp-panel__title">{{ selectedId ? '编辑区域' : '新建区域' }}</div>
        <el-form label-position="top" size="small">
          <el-form-item label="名称">
            <el-input v-model="form.name" placeholder="如：深水区" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="form.type" style="width: 100%">
              <el-option v-for="item in TYPE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="适宜人群">
            <el-select v-model="form.allowedGroups" style="width: 100%">
              <el-option label="不限" value="ALL" />
              <el-option label="仅成人" value="ADULT" />
              <el-option label="仅儿童" value="CHILD" />
            </el-select>
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
        </el-form>

        <div class="zones__actions">
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button :disabled="!selectedId || form.type === 'POOL'" @click="remove">删除</el-button>
          <el-button link @click="reload">重新载入</el-button>
        </div>
        <div class="sp-dim zones__points">当前顶点：{{ points.length }} 个 · 拖拽顶点可微调位置</div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createZone, deleteZone, fetchZones, updateZone } from '@/api'
import type { Zone } from '@/types/api'

type Point = { x: number; y: number }
type Geo = { width: number; height: number; left: number; top: number; poolW: number; poolH: number }

const TYPE_OPTIONS = [
  { value: 'DEEP', label: '深水区' },
  { value: 'SHALLOW', label: '浅水区' },
  { value: 'KIDS', label: '儿童区' },
  { value: 'LANE', label: '泳道' },
  { value: 'RESTRICTED', label: '禁入区' },
  { value: 'POOL', label: '全池（兜底）' }
]

const TYPE_LABEL: Record<string, string> = Object.fromEntries(TYPE_OPTIONS.map((item) => [item.value, item.label]))
const GROUP_LABEL: Record<string, string> = { ALL: '不限', ADULT: '仅成人', CHILD: '仅儿童' }
const TYPE_COLOR: Record<string, string> = {
  DEEP: 'rgba(255, 107, 114, 0.20)',
  SHALLOW: 'rgba(67, 185, 245, 0.18)',
  KIDS: 'rgba(245, 162, 92, 0.20)',
  LANE: 'rgba(54, 209, 166, 0.16)',
  RESTRICTED: 'rgba(255, 107, 114, 0.32)',
  POOL: 'rgba(130, 160, 190, 0.10)'
}

const wrapRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()
const zones = ref<Zone[]>([])
const selectedId = ref<number | null>(null)
const points = ref<Point[]>([])
const form = reactive({ name: '', type: 'DEEP', allowedGroups: 'ADULT', enabled: true })
const dragging = ref(-1)
const saving = ref(false)

// 预览加点：左键确定起点后跟随鼠标，双击才真正写入顶点
const preview = ref<Point | null>(null)
const previewing = ref(false)
const deleteTarget = ref<{ index: number; px: number; py: number } | null>(null)
let dragState: { index: number; startX: number; startY: number; moved: boolean } | null = null
let rafId = 0

const confirmStyle = computed(() => {
  const target = deleteTarget.value
  const g = geo()
  if (!target || !g) {
    return {}
  }
  return {
    left: `${Math.max(6, Math.min(target.px + 14, g.width - 178))}px`,
    top: `${Math.max(6, Math.min(target.py - 12, g.height - 84))}px`
  }
})

function typeLabel(type: string) {
  return TYPE_LABEL[type] || type
}

function groupLabel(group: string) {
  return GROUP_LABEL[group] || group
}

function geo(): Geo | null {
  const wrap = wrapRef.value
  if (!wrap) {
    return null
  }
  const width = wrap.clientWidth
  const height = Math.round(width * 0.52)
  const left = 46
  const top = 18
  return { width, height, left, top, poolW: width - left - 18, poolH: height - top - 32 }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function round(value: number) {
  return Number(value.toFixed(4))
}

function drawGrid(ctx: CanvasRenderingContext2D, g: Geo) {
  ctx.save()
  for (let i = 1; i < 10; i += 1) {
    const t = i / 10
    const major = i === 5
    ctx.strokeStyle = major ? 'rgba(125, 195, 240, 0.34)' : 'rgba(125, 195, 240, 0.15)'
    ctx.lineWidth = major ? 1.2 : 1
    ctx.beginPath()
    ctx.moveTo(g.left + t * g.poolW, g.top)
    ctx.lineTo(g.left + t * g.poolW, g.top + g.poolH)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(g.left, g.top + t * g.poolH)
    ctx.lineTo(g.left + g.poolW, g.top + t * g.poolH)
    ctx.stroke()
  }
  ctx.restore()
}

function drawRulers(ctx: CanvasRenderingContext2D, g: Geo) {
  ctx.save()
  ctx.fillStyle = 'rgba(67, 185, 245, 0.07)'
  ctx.fillRect(g.left, g.top + g.poolH, g.poolW, 30)
  ctx.fillRect(0, g.top, g.left, g.poolH)

  ctx.font = '600 11px "Segoe UI", "Microsoft YaHei", sans-serif'
  ctx.lineWidth = 1
  ctx.strokeStyle = 'rgba(150, 214, 250, 0.9)'
  ctx.fillStyle = 'rgba(226, 242, 255, 0.96)'
  ctx.beginPath()
  ctx.moveTo(g.left, g.top + g.poolH + 0.5)
  ctx.lineTo(g.left + g.poolW, g.top + g.poolH + 0.5)
  ctx.moveTo(g.left + 0.5, g.top)
  ctx.lineTo(g.left + 0.5, g.top + g.poolH)
  ctx.stroke()
  for (let i = 0; i <= 10; i += 1) {
    const t = i / 10
    const x = g.left + t * g.poolW
    const y = g.top + t * g.poolH
    const major = i % 5 === 0
    const size = major ? 9 : 5
    ctx.lineWidth = major ? 1.4 : 1
    ctx.beginPath()
    ctx.moveTo(x, g.top + g.poolH)
    ctx.lineTo(x, g.top + g.poolH + size)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(g.left - size, y)
    ctx.lineTo(g.left, y)
    ctx.stroke()
    if (i % 2 === 0) {
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(t.toFixed(1), x, g.top + g.poolH + 11)
      ctx.textAlign = 'right'
      ctx.textBaseline = 'middle'
      ctx.fillText(t.toFixed(1), g.left - 11, y)
    }
  }
  ctx.restore()
}

function drawPreview(ctx: CanvasRenderingContext2D, g: Geo) {
  if (!previewing.value || !preview.value) {
    return
  }
  const px = g.left + preview.value.x * g.poolW
  const py = g.top + preview.value.y * g.poolH
  ctx.save()
  ctx.strokeStyle = 'rgba(92, 200, 255, 0.62)'
  ctx.lineWidth = 1
  ctx.setLineDash([5, 4])
  ctx.beginPath()
  ctx.moveTo(g.left, py)
  ctx.lineTo(g.left + g.poolW, py)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(px, g.top)
  ctx.lineTo(px, g.top + g.poolH)
  ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = '#5cc8ff'
  for (const [x, y] of [[g.left, py], [g.left + g.poolW, py], [px, g.top], [px, g.top + g.poolH]]) {
    ctx.fillRect(x - 2, y - 2, 4, 4)
  }

  ctx.font = '11px "Segoe UI", "Microsoft YaHei", sans-serif'
  ctx.fillStyle = 'rgba(224, 242, 255, 0.95)'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'bottom'
  ctx.fillText(`x ${preview.value.x.toFixed(2)}`, clamp(px, g.left + 32, g.left + g.poolW - 32), g.top - 3)
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(`y ${preview.value.y.toFixed(2)}`, g.left + 6, clamp(py - 12, g.top + 8, g.top + g.poolH - 8))

  ctx.beginPath()
  ctx.arc(px, py, 7, 0, Math.PI * 2)
  ctx.fillStyle = 'rgba(92, 200, 255, 0.22)'
  ctx.fill()
  ctx.strokeStyle = '#5cc8ff'
  ctx.lineWidth = 1.6
  ctx.stroke()
  ctx.restore()
}

function draw() {
  const canvas = canvasRef.value
  const g = geo()
  if (canvas && g) {
    const dpr = window.devicePixelRatio || 1
    if (canvas.width !== Math.round(g.width * dpr) || canvas.height !== Math.round(g.height * dpr)) {
      canvas.width = Math.round(g.width * dpr)
      canvas.height = Math.round(g.height * dpr)
      canvas.style.width = `${g.width}px`
      canvas.style.height = `${g.height}px`
    }
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, g.width, g.height)

      const gradient = ctx.createLinearGradient(0, g.top, 0, g.top + g.poolH)
      gradient.addColorStop(0, '#14293c')
      gradient.addColorStop(1, '#0a1724')
      ctx.fillStyle = gradient
      ctx.fillRect(g.left, g.top, g.poolW, g.poolH)

      drawGrid(ctx, g)

      for (const zone of zones.value) {
        const shape = parsePolygon(zone.polygonJson)
        if (shape.length < 3) {
          continue
        }
        const active = zone.id === selectedId.value
        ctx.beginPath()
        shape.forEach((point, index) => {
          const x = g.left + point.x * g.poolW
          const y = g.top + point.y * g.poolH
          if (index === 0) {
            ctx.moveTo(x, y)
          } else {
            ctx.lineTo(x, y)
          }
        })
        ctx.closePath()
        ctx.fillStyle = TYPE_COLOR[zone.type] || 'rgba(67,185,245,0.15)'
        ctx.fill()
        ctx.strokeStyle = active ? '#5cc8ff' : 'rgba(125, 195, 240, 0.62)'
        ctx.lineWidth = active ? 2 : 1
        ctx.stroke()
        const first = shape[0]
        ctx.fillStyle = 'rgba(215, 235, 252, 0.8)'
        ctx.font = '12px "Microsoft YaHei", sans-serif'
        ctx.fillText(zone.name, g.left + first.x * g.poolW + 6, g.top + first.y * g.poolH + 16)
      }

      if (selectedId.value !== null || points.value.length > 0) {
        const shape = points.value
        if (shape.length >= 3) {
          ctx.beginPath()
          shape.forEach((point, index) => {
            const x = g.left + point.x * g.poolW
            const y = g.top + point.y * g.poolH
            if (index === 0) {
              ctx.moveTo(x, y)
            } else {
              ctx.lineTo(x, y)
            }
          })
          ctx.closePath()
          ctx.strokeStyle = 'rgba(92, 200, 255, 0.9)'
          ctx.setLineDash([5, 4])
          ctx.stroke()
          ctx.setLineDash([])
        }
        shape.forEach((point, index) => {
          const x = g.left + point.x * g.poolW
          const y = g.top + point.y * g.poolH
          ctx.beginPath()
          ctx.arc(x, y, index === dragging.value ? 7 : 5, 0, Math.PI * 2)
          ctx.fillStyle = index === dragging.value ? '#ffc078' : '#5cc8ff'
          ctx.fill()
          ctx.strokeStyle = 'rgba(226, 242, 255, 0.92)'
          ctx.lineWidth = 1.5
          ctx.stroke()
        })
      }

      drawRulers(ctx, g)
      drawPreview(ctx, g)
    }
  }
  rafId = window.requestAnimationFrame(draw)
}

function parsePolygon(json: string): Point[] {
  try {
    const parsed = JSON.parse(json)
    return Array.isArray(parsed?.points) ? parsed.points as Point[] : []
  } catch {
    return []
  }
}

function toNormalized(event: MouseEvent) {
  const wrap = wrapRef.value
  const g = geo()
  if (!wrap || !g) {
    return null
  }
  const rect = wrap.getBoundingClientRect()
  return {
    x: clamp((event.clientX - rect.left - g.left) / g.poolW, 0, 1),
    y: clamp((event.clientY - rect.top - g.top) / g.poolH, 0, 1),
    px: event.clientX - rect.left,
    py: event.clientY - rect.top,
    g
  }
}

function nearestVertex(event: MouseEvent) {
  const pos = toNormalized(event)
  if (!pos) {
    return -1
  }
  let best = -1
  let bestDistance = 12
  points.value.forEach((point, index) => {
    const dx = pos.g.left + point.x * pos.g.poolW - pos.px
    const dy = pos.g.top + point.y * pos.g.poolH - pos.py
    const distance = Math.hypot(dx, dy)
    if (distance < bestDistance) {
      bestDistance = distance
      best = index
    }
  })
  return best
}

function resetInteraction() {
  previewing.value = false
  preview.value = null
  deleteTarget.value = null
  dragState = null
  dragging.value = -1
}

function onMouseDown(event: MouseEvent) {
  if (event.button !== 0) {
    return
  }
  const pos = toNormalized(event)
  if (!pos) {
    return
  }
  deleteTarget.value = null
  const hit = nearestVertex(event)
  if (hit >= 0) {
    previewing.value = false
    dragState = { index: hit, startX: pos.px, startY: pos.py, moved: false }
    return
  }
  dragState = null
  previewing.value = true
  preview.value = { x: round(pos.x), y: round(pos.y) }
}

function onMouseMove(event: MouseEvent) {
  const pos = toNormalized(event)
  if (!pos) {
    return
  }
  if (dragState) {
    if (Math.hypot(pos.px - dragState.startX, pos.py - dragState.startY) > 4) {
      dragState.moved = true
    }
    if (dragState.moved) {
      dragging.value = dragState.index
      const next = [...points.value]
      next[dragState.index] = { x: round(pos.x), y: round(pos.y) }
      points.value = next
    }
    return
  }
  if (previewing.value) {
    preview.value = { x: round(pos.x), y: round(pos.y) }
  }
}

function onMouseUp() {
  if (!dragState) {
    return
  }
  if (!dragState.moved) {
    const g = geo()
    const point = points.value[dragState.index]
    if (g && point) {
      deleteTarget.value = {
        index: dragState.index,
        px: g.left + point.x * g.poolW,
        py: g.top + point.y * g.poolH
      }
    }
  }
  dragState = null
  dragging.value = -1
}

function onMouseLeave() {
  // 删除确认浮层浮在画布之上，鼠标移过去会触发 mouseleave；
  // 此时必须保留浮层，否则用户还没点到按钮它就消失了
  if (deleteTarget.value) {
    dragState = null
    dragging.value = -1
    return
  }
  resetInteraction()
}

function onDoubleClick(event: MouseEvent) {
  const pos = toNormalized(event)
  if (!previewing.value || !pos) {
    return
  }
  points.value = [...points.value, { x: round(pos.x), y: round(pos.y) }]
  resetInteraction()
}

function confirmDeleteVertex() {
  const target = deleteTarget.value
  if (!target) {
    return
  }
  if (points.value.length <= 3) {
    ElMessage.warning('至少需要保留 3 个顶点')
    deleteTarget.value = null
    return
  }
  points.value = points.value.filter((_, index) => index !== target.index)
  resetInteraction()
  ElMessage.success('顶点已删除')
}

function onKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    resetInteraction()
  }
}

function select(zone: Zone) {
  resetInteraction()
  selectedId.value = zone.id
  points.value = parsePolygon(zone.polygonJson)
  form.name = zone.name
  form.type = zone.type
  form.allowedGroups = zone.allowedGroups
  form.enabled = zone.enabled
}

function startCreate() {
  resetInteraction()
  selectedId.value = null
  points.value = [
    { x: 0.2, y: 0.2 },
    { x: 0.5, y: 0.2 },
    { x: 0.5, y: 0.5 },
    { x: 0.2, y: 0.5 }
  ]
  form.name = '新区域'
  form.type = 'DEEP'
  form.allowedGroups = 'ADULT'
  form.enabled = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写区域名称')
    return
  }
  if (points.value.length < 3) {
    ElMessage.warning('至少需要 3 个顶点')
    return
  }
  saving.value = true
  const payload = {
    poolId: 1,
    name: form.name.trim(),
    type: form.type,
    allowedGroups: form.allowedGroups,
    enabled: form.enabled,
    polygonJson: JSON.stringify({
      points: points.value.map((point) => ({ x: Number(point.x.toFixed(4)), y: Number(point.y.toFixed(4)) })),
      version: 1
    })
  }
  try {
    const saved = selectedId.value
      ? await updateZone(selectedId.value, payload)
      : await createZone(payload)
    ElMessage.success('已保存')
    await reload()
    const fresh = zones.value.find((zone) => zone.id === saved.id)
    if (fresh) {
      select(fresh)
    }
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!selectedId.value) {
    return
  }
  await ElMessageBox.confirm('删除后该区域不再参与越界判定，确认删除？', '删除区域', { type: 'warning' })
  await deleteZone(selectedId.value)
  ElMessage.success('已删除')
  resetInteraction()
  selectedId.value = null
  points.value = []
  await reload()
}

async function reload() {
  zones.value = await fetchZones(1)
}

onMounted(async () => {
  await reload()
  if (zones.value.length) {
    select(zones.value[0])
  }
  window.addEventListener('keydown', onKeyDown)
  rafId = window.requestAnimationFrame(draw)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.cancelAnimationFrame(rafId)
})
</script>

<style scoped>
.zones {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  align-items: start;
}

.zones__wrap {
  position: relative;
  width: 100%;
}

.zones__canvas {
  display: block;
  width: 100%;
  border-radius: 8px;
  cursor: crosshair;
}

.zones__preview-hint {
  margin-top: 10px;
  padding: 8px 12px;
  border: 1px solid var(--brand-line);
  border-radius: var(--r-md);
  background: var(--brand-soft);
  color: var(--brand-deep);
  font-size: 12px;
}

.zones__preview-hint b {
  font-weight: 650;
}

.zones__tip {
  margin-top: 10px;
}

.vertex-confirm {
  position: absolute;
  z-index: 5;
  width: 168px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--card);
  box-shadow: var(--shadow-2);
}

.vertex-confirm__text {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
}

.vertex-confirm__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}

.zones__side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.zone-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 6px;
  border-radius: 6px;
  cursor: pointer;
  border-bottom: 1px dashed var(--sp-border);
}

.zone-item--active {
  background: rgba(67, 185, 245, 0.12);
}

.zone-item__main {
  flex: 1;
  font-size: 13px;
  line-height: 1.5;
}

.zone-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex: none;
}

.zone-dot--deep { background: #ff6b72; }
.zone-dot--shallow { background: #43b9f5; }
.zone-dot--kids { background: #e9c46a; }
.zone-dot--lane { background: #36d1a6; }
.zone-dot--restricted { background: #e05a61; }
.zone-dot--pool { background: #6c8397; }

.zones__actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.zones__points {
  margin-top: 10px;
}

@media (max-width: 1000px) {
  .zones {
    grid-template-columns: 1fr;
  }
}
</style>
