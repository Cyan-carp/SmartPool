<template>
  <div class="alerts">
    <div class="sp-panel">
      <div class="sp-panel__title">
        <span>告警中心</span>
        <span class="sp-badge sp-badge--live" v-if="wsConnected">实时刷新中</span>
        <span class="sp-badge" v-else>通道重连中…</span>
      </div>

      <div class="filters">
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px" @change="reload">
          <el-option v-for="item in STATUS_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.level" placeholder="全部等级" clearable style="width: 150px" @change="reload">
          <el-option v-for="item in LEVEL_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button :loading="loading" @click="reload">刷新</el-button>
        <div class="filters__spacer" />
        <el-button type="primary" link @click="exportCsv">导出 CSV（24h）</el-button>
      </div>

      <el-table :data="rows" style="width: 100%" empty-text="暂无告警" @row-click="openDetail">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ shortTime(row.triggeredAt) }}</template>
        </el-table-column>
        <el-table-column label="等级" width="100">
          <template #default="{ row }">
            <span class="pill" :class="`pill--${row.level.toLowerCase()}`">{{ levelLabel(row.level) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="trackNo" label="目标" width="80">
          <template #default="{ row }">#{{ row.trackNo }}</template>
        </el-table-column>
        <el-table-column label="区域" width="100">
          <template #default="{ row }">{{ row.zoneName || '未分区' }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="触发原因" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status" :class="`status--${row.status.toLowerCase()}`">{{ statusLabel(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="持续" width="90">
          <template #default="{ row }">{{ row.ageSec ?? 0 }}s</template>
        </el-table-column>
        <el-table-column label="操作" width="190">
          <template #default="{ row }">
            <el-button v-if="row.status === 'OPEN'" size="small" type="primary" link @click.stop="quickAck(row)">
              确认
            </el-button>
            <el-button v-if="canResolve(row)" size="small" type="success" link @click.stop="openDetail(row)">
              处置
            </el-button>
            <el-button size="small" link @click.stop="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="size"
          :total="total"
          layout="prev, pager, next, total"
          @current-change="load"
        />
      </div>
    </div>

    <el-drawer v-model="drawer" title="告警详情" size="520px" @closed="detail = null">
      <div v-if="detail" class="detail">
        <div class="detail__head">
          <span class="pill" :class="`pill--${detail.alert.level.toLowerCase()}`">
            {{ levelLabel(detail.alert.level) }}
          </span>
          <span class="status" :class="`status--${detail.alert.status.toLowerCase()}`">
            {{ statusLabel(detail.alert.status) }}
          </span>
          <span class="sp-dim">#{{ detail.alert.id }} · {{ shortTime(detail.alert.triggeredAt) }}</span>
        </div>

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="目标">#{{ detail.alert.trackNo }}</el-descriptions-item>
          <el-descriptions-item label="区域">{{ detail.alert.zoneName || '未分区' }}</el-descriptions-item>
          <el-descriptions-item label="风险分">{{ detail.alert.riskScore ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="持续">{{ detail.alert.ageSec ?? 0 }} s</el-descriptions-item>
          <el-descriptions-item label="触发原因" :span="2">{{ detail.alert.reason }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail__section">处置时间线</div>
        <el-timeline>
          <el-timeline-item
            v-for="item in detail.actions"
            :key="item.id"
            :timestamp="shortTime(item.at)"
            placement="top"
          >
            <b>{{ actionLabel(item.action) }}</b>
            <span v-if="item.note" class="sp-dim"> · {{ item.note }}</span>
          </el-timeline-item>
        </el-timeline>

        <div class="detail__section">处置操作</div>
        <div class="detail__form" v-if="detail.alert.closedAt === null">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="处置说明（可选）" />
          <div class="detail__row">
            <el-button v-if="detail.alert.status === 'OPEN'" type="primary" @click="doAck">确认告警</el-button>
            <template v-else>
              <el-input v-model="form.assignee" placeholder="指派对象" style="width: 160px" />
              <el-button v-if="detail.alert.status === 'ACKED'" @click="doDispatch">派单</el-button>
              <el-select v-model="form.result" style="width: 130px">
                <el-option label="已施救" value="RESCUED" />
                <el-option label="自行恢复" value="SELF_RECOVERED" />
              </el-select>
              <el-button type="success" @click="doResolve">解除</el-button>
            </template>
            <el-button type="danger" plain @click="doFalseAlarm">标记误报</el-button>
          </div>
        </div>
        <div v-else class="sp-dim">该告警已关闭，不可再处置。</div>

        <div class="detail__section">事件片段</div>
        <div class="sp-dim" v-if="detail.clip.points.length === 0">暂无轨迹采样</div>
        <div v-else class="clip">
          <svg :viewBox="`0 0 240 120`" class="clip__svg">
            <rect x="0" y="0" width="240" height="120" fill="#14293c" rx="4" />
            <polyline :points="clipPolyline" fill="none" stroke="#43b9f5" stroke-width="1.2" />
            <circle :cx="clipHook.x" :cy="clipHook.y" r="3" fill="#ff6b72" />
          </svg>
          <div class="sp-dim">窗口 {{ shortTime(detail.clip.windowFrom) }} ~ {{ shortTime(detail.clip.windowTo) }} · {{ detail.clip.points.length }} 个采样</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import {
  ackAlert,
  dispatchAlert,
  fetchAlertDetail,
  fetchAlerts,
  markFalseAlarm,
  resolveAlert
} from '@/api'
import { onLive, useLiveConnection } from '@/composables/useLiveSocket'
import type { AlertDetail, AlertItem } from '@/types/api'

const STATUS_OPTIONS = [
  { value: 'OPEN', label: '待确认' },
  { value: 'ACKED', label: '已确认' },
  { value: 'DISPATCHED', label: '已派单' },
  { value: 'RESOLVED', label: '已解除' },
  { value: 'FALSE_ALARM', label: '误报' }
]

const LEVEL_OPTIONS = [
  { value: 'STRONG', label: '强告警' },
  { value: 'WEAK', label: '弱告警' }
]

const STATUS_LABEL: Record<string, string> = {
  OPEN: '待确认',
  ACKED: '已确认',
  DISPATCHED: '已派单',
  RESOLVED: '已解除',
  FALSE_ALARM: '误报'
}

const LEVEL_LABEL: Record<string, string> = { NOTICE: '提示', WEAK: '弱告警', STRONG: '强告警' }

const ACTION_LABEL: Record<string, string> = {
  CREATE: '系统触发',
  ACK: '确认告警',
  DISPATCH: '派单',
  RESOLVE: '解除',
  FALSE_ALARM: '误报',
  ESCALATE: '升级'
}

const rows = ref<AlertItem[]>([])
const total = ref(0)
const page = ref(1)
const size = 20
const loading = ref(false)
const { connected: wsConnected } = useLiveConnection()
const drawer = ref(false)
const detail = ref<AlertDetail | null>(null)
const filters = reactive({ status: '', level: '' })
const form = reactive({ note: '', assignee: '现场救生员', result: 'RESCUED' })

let offLive: (() => void) | null = null

const clipPolyline = computed(() => {
  const points = detail.value?.clip.points ?? []
  return points
    .map((point) => `${(point.x * 240).toFixed(1)},${(120 - point.y * 120).toFixed(1)}`)
    .join(' ')
})

const clipHook = computed(() => {
  const points = detail.value?.clip.points ?? []
  if (!points.length) {
    return { x: 0, y: 0 }
  }
  const max = points.reduce((acc, item) => (item.riskScore > acc.riskScore ? item : acc), points[0])
  return { x: max.x * 240, y: 120 - max.y * 120 }
})

function statusLabel(value: string) {
  return STATUS_LABEL[value] || value
}

function levelLabel(value: string) {
  return LEVEL_LABEL[value] || value
}

function actionLabel(value: string) {
  return ACTION_LABEL[value] || value
}

function shortTime(value?: string | null) {
  if (!value) {
    return '-'
  }
  return value.replace('T', ' ').slice(5, 19)
}

function canResolve(row: AlertItem) {
  return row.status === 'ACKED' || row.status === 'DISPATCHED'
}

async function load() {
  loading.value = true
  try {
    const data = await fetchAlerts({
      status: filters.status || undefined,
      level: filters.level || undefined,
      page: page.value,
      size
    })
    rows.value = data.list
    total.value = data.total
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}

async function openDetail(row: AlertItem) {
  try {
    detail.value = await fetchAlertDetail(row.id)
    drawer.value = true
  } catch {
    detail.value = null
  }
}

async function quickAck(row: AlertItem) {
  try {
    await ackAlert(row.id, '值班台快速确认')
    ElMessage.success('已确认')
    await load()
  } catch {
    /* 拦截器已提示 */
  }
}

async function doAck() {
  if (!detail.value) {
    return
  }
  await ackAlert(detail.value.alert.id, form.note)
  ElMessage.success('已确认')
  await refreshDetail()
}

async function doDispatch() {
  if (!detail.value) {
    return
  }
  await dispatchAlert(detail.value.alert.id, form.assignee, form.note)
  ElMessage.success('已派单')
  await refreshDetail()
}

async function doResolve() {
  if (!detail.value) {
    return
  }
  await resolveAlert(detail.value.alert.id, form.result, form.note)
  ElMessage.success('已解除')
  await refreshDetail()
}

async function doFalseAlarm() {
  if (!detail.value) {
    return
  }
  await ElMessageBox.confirm('确认该告警为误报？误报会计入统计口径。', '标记误报', { type: 'warning' })
  await markFalseAlarm(detail.value.alert.id, form.note || '人工判定为误报')
  ElMessage.success('已标记误报')
  await refreshDetail()
}

async function refreshDetail() {
  if (detail.value) {
    detail.value = await fetchAlertDetail(detail.value.alert.id)
  }
  await load()
}

async function exportCsv() {
  const token = sessionStorage.getItem('smartpool.token') || ''
  const response = await fetch('/api/v1/alerts/export.csv?hours=24', {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!response.ok) {
    ElMessage.error('导出失败')
    return
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `alerts-${Date.now()}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await load()
  // 连接由 AppLayout 统一持有，本页只订阅；卸载时只取消订阅，不断开连接
  offLive = onLive((type, payload) => {
    if (type === 'alert.created') {
      const item = payload as AlertItem
      ElNotification({ title: `${levelLabel(item.level)} · 目标 #${item.trackNo}`, message: item.reason, type: 'warning', duration: 4000 })
      load()
    } else if (type === 'alert.updated') {
      const item = payload as AlertItem
      const index = rows.value.findIndex((row) => row.id === item.id)
      if (index >= 0) {
        rows.value[index] = item
      }
      if (detail.value?.alert.id === item.id) {
        refreshDetail()
      }
    } else if (type === 'ws.open') {
      load()
    }
  })
})

onBeforeUnmount(() => {
  offLive?.()
})
</script>

<style scoped>
.alerts {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.filters__spacer {
  flex: 1;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.pill {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid currentColor;
}

.pill--weak { color: #f5a25c; }
.pill--strong { color: #ff6b72; }
.pill--notice { color: #e9c46a; }

.status {
  font-size: 12px;
}

.status--open { color: #ff6b72; }
.status--acked { color: #e9c46a; }
.status--dispatched { color: #43b9f5; }
.status--resolved { color: #36d1a6; }
.status--false_alarm { color: #6c8397; }

.detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail__head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail__section {
  margin-top: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--sp-text);
}

.detail__form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail__row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.clip__svg {
  width: 100%;
  height: 120px;
  border-radius: 6px;
  background: #14293c; border: 1px solid var(--line-soft);
}
</style>
