<template>
  <div class="demo">
    <div class="sp-panel">
      <div class="sp-panel__title">
        <span>演示控制台</span>
        <span class="demo__meta">
          <span class="sp-dim">已演示 {{ elapsedText }}</span>
          <el-button size="small" type="warning" plain :loading="resetting" @click="reset">一键重置（含清空告警）</el-button>
        </span>
      </div>

      <div class="checks">
        <div class="check" :class="{ 'check--bad': !status?.aiOk }">
          <div class="check__label">推理服务</div>
          <div class="check__value">{{ status?.aiOk ? '正常' : '不可用' }}</div>
          <div class="sp-dim">{{ status?.provider }} · {{ status?.modelLoaded ? '已加载' : '占位' }}</div>
        </div>
        <div class="check" :class="{ 'check--warn': (status?.dataDelayMs ?? 0) > 3000 }">
          <div class="check__label">画面延迟</div>
          <div class="check__value">{{ delayText }}</div>
          <div class="sp-dim">已推 {{ status?.framesPushed ?? 0 }} 帧</div>
        </div>
        <div class="check" :class="{ 'check--warn': (status?.camerasOnline ?? 0) < (status?.camerasTotal ?? 0) }">
          <div class="check__label">摄像头</div>
          <div class="check__value">{{ status?.camerasOnline ?? 0 }}/{{ status?.camerasTotal ?? 0 }}</div>
          <div class="sp-dim">在线设备</div>
        </div>
        <div class="check" :class="{ 'check--bad': (status?.waterExceeded?.length ?? 0) > 0 }">
          <div class="check__label">水质</div>
          <div class="check__value">{{ (status?.waterExceeded?.length ?? 0) > 0 ? '超标' : '正常' }}</div>
          <div class="sp-dim">{{ (status?.waterExceeded || []).join(' / ') || '无异常' }}</div>
        </div>
        <div class="check" :class="{ 'check--warn': (status?.openAlerts ?? 0) > 0 }">
          <div class="check__label">待处置告警</div>
          <div class="check__value">{{ status?.openAlerts ?? 0 }}</div>
          <div class="sp-dim">需人工确认</div>
        </div>
        <div class="check">
          <div class="check__label">算力档位</div>
          <div class="check__value">{{ status?.mode === 'OFFPEAK' ? '低谷' : '高峰' }}</div>
          <div class="sp-dim">当前剧本 {{ scenarioLabel }}</div>
        </div>
      </div>

      <div class="faults" v-if="(status?.activeFaults?.length ?? 0) > 0">
        <span class="sp-dim">进行中的故障：</span>
        <el-tag v-for="fault in status?.activeFaults" :key="fault.type" type="warning" size="small">
          {{ faultLabel(fault.type) }}（剩 {{ fault.remainSec }}s）
        </el-tag>
      </div>
    </div>

    <div class="row">
      <div class="sp-panel">
        <div class="sp-panel__title">
          <span>演示主线（8 步）</span>
          <span class="sp-dim">{{ doneCount }}/{{ steps.length }} 完成</span>
        </div>
        <el-progress :percentage="Math.round((doneCount / steps.length) * 100)" :stroke-width="6" :show-text="false" style="margin-bottom: 14px" />
        <div v-for="(step, index) in steps" :key="step.key" class="step" :class="{ 'step--done': step.done }">
          <div class="step__index">{{ index + 1 }}</div>
          <div class="step__main">
            <div class="step__title">{{ step.title }}</div>
            <div class="sp-dim">{{ step.hint }}</div>
          </div>
          <div class="step__actions">
            <el-button v-if="step.action" size="small" link type="primary" :loading="busy === step.key" @click="runStep(step)">
              {{ step.actionLabel }}
            </el-button>
            <el-button v-if="!step.done && !step.auto" size="small" link @click="markDone(step.key)">标记完成</el-button>
            <el-tag v-if="step.done" size="small" type="success">完成</el-tag>
          </div>
        </div>
      </div>

      <div class="side">
        <div class="sp-panel">
          <div class="sp-panel__title">剧本注入</div>
          <div class="scenario-grid">
            <el-button
              v-for="item in scenarios"
              :key="item.key"
              size="small"
              :type="status?.scenario === item.key ? 'success' : 'default'"
              :plain="status?.scenario !== item.key"
              :loading="busy === item.key"
              @click="triggerScenario(item.key)"
            >
              {{ item.label }}
            </el-button>
          </div>
          <div class="sp-dim hint">「静止下沉」触发后等 30–45 秒出现强告警。</div>
        </div>

        <div class="sp-panel">
          <div class="sp-panel__title">
            <span>故障注入</span>
            <el-button size="small" link @click="clearAllFaults">全部恢复</el-button>
          </div>
          <div class="fault-grid">
            <el-button size="small" plain @click="fault('CAMERA_OFFLINE')">摄像头离线</el-button>
            <el-button size="small" plain @click="fault('INFER_DOWN')">推理中断</el-button>
            <el-button size="small" plain @click="fault('WS_FLOOD')">推送风暴</el-button>
          </div>
          <div class="sp-dim hint">
            注入持续 20 秒后自动恢复；推理中断会让画面冻结并触发降级横幅。
          </div>
        </div>

        <div class="sp-panel">
          <div class="sp-panel__title">演示时钟</div>
          <el-radio-group v-model="speed" @change="changeClock">
            <el-radio-button :value="1">1×</el-radio-button>
            <el-radio-button :value="2">2×</el-radio-button>
            <el-radio-button :value="5">5×</el-radio-button>
            <el-radio-button :value="10">10×</el-radio-button>
          </el-radio-group>
          <div class="sp-dim hint">倍速只影响模拟世界推进，不影响告警判定窗口。</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  clearFaults,
  fetchAlerts,
  fetchDemoStatus,
  fetchStats,
  injectFault,
  resetDemo,
  setClock,
  setModelMode,
  triggerScenario as triggerScenarioApi
} from '@/api'
import type { AlertStats, DemoStatus } from '@/types/api'

const SCENARIOS = [
  { key: 'normal', label: '正常游泳' },
  { key: 'drown_still', label: '静止下沉' },
  { key: 'zone_intrude', label: '儿童进深水区' },
  { key: 'water_poor', label: '水质超标' },
  { key: 'night_intrude', label: '营业外闯入' }
]

const SCENARIO_LABEL: Record<string, string> = {
  normal: '正常游泳',
  drown_still: '静止下沉',
  zone_intrude: '儿童进深水区',
  night_intrude: '营业外闯入',
  water_poor: '水质超标'
}

const FAULT_LABEL: Record<string, string> = {
  CAMERA_OFFLINE: '摄像头离线',
  INFER_DOWN: '推理中断',
  WS_FLOOD: '推送风暴'
}

const router = useRouter()
const scenarios = SCENARIOS
const status = ref<DemoStatus | null>(null)
const stats = ref<AlertStats | null>(null)
const alertTotal = ref(0)
const busy = ref('')
const resetting = ref(false)
const speed = ref(1)
const startedAt = ref(Date.now())
const now = ref(Date.now())
const manualDone = ref<Record<string, boolean>>({})

let timer = 0

const scenarioLabel = computed(() => SCENARIO_LABEL[status.value?.scenario || 'normal'] || status.value?.scenario)
const delayText = computed(() => {
  const delay = status.value?.dataDelayMs ?? -1
  return delay < 0 ? '-' : `${(delay / 1000).toFixed(1)}s`
})
const elapsedText = computed(() => {
  const seconds = Math.max(0, Math.floor((now.value - startedAt.value) / 1000))
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  return `${mm}:${ss}`
})

const steps = computed(() => {
  const current = status.value
  return [
    {
      key: 'normal',
      title: '确认正常态',
      hint: '8 名游客正常游动，无风险目标',
      done: current?.scenario === 'normal' && (current?.targets ?? 0) > 0,
      auto: true,
      action: 'normal',
      actionLabel: '切回正常'
    },
    {
      key: 'drown',
      title: '触发静止下沉',
      hint: '指定目标头部未出水，风险分持续上升',
      done: current?.scenario === 'drown_still',
      auto: true,
      action: 'drown_still',
      actionLabel: '触发剧本'
    },
    {
      key: 'alert',
      title: '强告警出现',
      hint: '大屏描红并弹出强告警，告警中心可见',
      done: alertTotal.value > 0,
      auto: true
    },
    {
      key: 'resolve',
      title: '完成处置闭环',
      hint: '确认 → 派单 → 解除，时间线留痕',
      done: (stats.value?.resolved ?? 0) > 0,
      auto: true
    },
    {
      key: 'replay',
      title: '查看事件回溯',
      hint: '风险曲线 + 轨迹回放 + 20 秒窗口',
      done: Boolean(manualDone.value.replay),
      auto: false,
      action: 'goto-replay',
      actionLabel: '去回溯'
    },
    {
      key: 'mode',
      title: '切换算力档位',
      hint: '切到低谷档，参数与指标曲线变化',
      done: current?.mode === 'OFFPEAK',
      auto: true,
      action: 'offpeak',
      actionLabel: '切低谷档'
    },
    {
      key: 'dashboard',
      title: '核对数据看板',
      hint: '热力图 / 趋势 / 峰谷三图有数据',
      done: Boolean(manualDone.value.dashboard),
      auto: false,
      action: 'goto-dashboard',
      actionLabel: '去看板'
    },
    {
      key: 'reset',
      title: '重置并复演',
      hint: '一键重置后重复演示，结果可复现',
      done: Boolean(manualDone.value.reset),
      auto: false,
      action: 'reset',
      actionLabel: '重置'
    }
  ]
})

const doneCount = computed(() => steps.value.filter((step) => step.done).length)

function faultLabel(type: string) {
  return FAULT_LABEL[type] || type
}

function markDone(key: string) {
  manualDone.value = { ...manualDone.value, [key]: true }
}

async function load() {
  try {
    status.value = await fetchDemoStatus()
  } catch {
    status.value = null
  }
  try {
    const data = await fetchAlerts({ page: 1, size: 1 })
    alertTotal.value = data.total
  } catch {
    alertTotal.value = 0
  }
  try {
    stats.value = await fetchStats(24)
  } catch {
    stats.value = null
  }
}

async function triggerScenario(key: string) {
  busy.value = key
  try {
    await triggerScenarioApi(key)
    ElMessage.success(`已触发：${SCENARIO_LABEL[key] || key}`)
    await load()
  } catch {
    /* 拦截器已提示 */
  } finally {
    busy.value = ''
  }
}

async function runStep(step: { key: string; action?: string }) {
  if (!step.action) {
    return
  }
  busy.value = step.key
  try {
    if (step.action === 'goto-replay') {
      markDone(step.key)
      router.push('/replay')
    } else if (step.action === 'goto-dashboard') {
      markDone(step.key)
      router.push('/dashboard')
    } else if (step.action === 'offpeak') {
      await setModelMode('OFFPEAK', false)
      ElMessage.success('已切到低谷档')
    } else if (step.action === 'reset') {
      await doReset()
    } else {
      await triggerScenarioApi(step.action)
      ElMessage.success('剧本已触发')
    }
    await load()
  } catch {
    /* 拦截器已提示 */
  } finally {
    busy.value = ''
  }
}

async function fault(type: string) {
  busy.value = type
  try {
    await injectFault(type, 20, type === 'CAMERA_OFFLINE' ? 3 : undefined)
    ElMessage.warning(`已注入：${faultLabel(type)}（20 秒后自动恢复）`)
    await load()
  } catch {
    /* 拦截器已提示 */
  } finally {
    busy.value = ''
  }
}

async function clearAllFaults() {
  await clearFaults()
  ElMessage.success('故障已全部恢复')
  await load()
}

async function changeClock(value: number | string | boolean) {
  await setClock(Number(value))
  ElMessage.success(`时钟 ${Number(value)}×`)
}

async function doReset() {
  resetting.value = true
  try {
    await resetDemo(2026, 8, true)
    speed.value = 1
    startedAt.value = Date.now()
    manualDone.value = {}
    ElMessage.success('已重置并重新播种')
    await load()
  } catch {
    /* 拦截器已提示 */
  } finally {
    resetting.value = false
  }
}

function reset() {
  doReset()
}

onMounted(async () => {
  await load()
  timer = window.setInterval(() => {
    now.value = Date.now()
    load()
  }, 5000)
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
})
</script>

<style scoped>
.demo {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.demo__meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.checks {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.check {
  background: var(--sp-panel-2);
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 12px 14px;
}

.check--warn {
  border-color: rgba(233, 196, 106, 0.5);
  background: rgba(233, 196, 106, 0.08);
}

.check--bad {
  border-color: rgba(255, 107, 114, 0.5);
  background: rgba(255, 107, 114, 0.08);
}

.check__label {
  font-size: 12px;
  color: var(--sp-text-dim);
}

.check__value {
  font-size: 24px;
  font-weight: 600;
  margin: 2px 0;
}

.faults {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.row {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-bottom: 1px dashed var(--sp-border);
}

.step:last-child {
  border-bottom: none;
}

.step__index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--sp-panel-2);
  color: var(--sp-text-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex: none;
}

.step--done .step__index {
  background: rgba(54, 209, 166, 0.2);
  color: #36d1a6;
}

.step__main {
  flex: 1;
  font-size: 13px;
  line-height: 1.6;
}

.step__title {
  font-weight: 600;
}

.step--done .step__title {
  color: #36d1a6;
}

.step__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.scenario-grid,
.fault-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.fault-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.hint {
  margin-top: 10px;
  line-height: 1.7;
}
</style>
