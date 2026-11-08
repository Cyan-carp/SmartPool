<template>
  <div class="wristbands">
    <section class="sp-panel">
      <div class="sp-panel__title">
        <span>智能手环 · 实时生理概览</span>
        <span class="sp-dim">每 5 秒刷新 · 最近更新 {{ updatedAt || '加载中' }}</span>
      </div>
      <div class="wb-stats">
        <div class="wb-stat"><b>{{ bands.length }}</b><span>手环总数</span></div>
        <div class="wb-stat"><b>{{ bound }}</b><span>已绑定目标</span></div>
        <div class="wb-stat"><b>{{ onlineCount }}</b><span>实时在线</span></div>
        <div class="wb-stat" :class="{ 'wb-stat--bad': alertCount > 0 }">
          <b>{{ alertCount }}</b><span>异常指标</span>
        </div>
      </div>
    </section>

    <section class="sp-panel">
      <div class="sp-panel__title">
        <span>实时生理指标</span>
        <span class="sp-badge sp-badge--live">LIVE</span>
      </div>
      <div class="vitals">
        <div v-for="item in activeBands" :key="item.code" class="vital-card">
          <div class="vital-card__head">
            <span class="vital-card__code">{{ item.code }}</span>
            <span class="vital-card__live"><i />实时 · 目标 #{{ item.bindTrackNo }}</span>
          </div>
          <div class="vital-card__grid">
            <div class="vital">
              <div class="vital__label">心率</div>
              <div class="vital__value" :class="toneClass(heartTone(item.data.heartRate))">
                {{ item.data.heartRate }}<small>bpm</small>
              </div>
            </div>
            <div class="vital">
              <div class="vital__label">血氧</div>
              <div class="vital__value" :class="toneClass(spo2Tone(item.data.spo2))">
                {{ item.data.spo2 }}<small>%</small>
              </div>
            </div>
            <div class="vital">
              <div class="vital__label">静止时长</div>
              <div class="vital__value" :class="toneClass(stillTone(item.data.stillSec))">
                {{ item.data.stillSec }}<small>s</small>
              </div>
            </div>
          </div>
        </div>
        <div v-if="!activeBands.length" class="vitals__empty">暂无已绑定手环的实时生理数据</div>
      </div>
      <div class="sp-dim">
        异常阈值：心率 ≥130 或 &lt;50 bpm、血氧 &lt;90%、静止 ≥15 s；橙色为临界、红色为异常，需重点关注。
      </div>
    </section>

    <section class="sp-panel">
      <div class="sp-panel__title">
        <span>手环清单</span>
        <span class="sp-dim">共 {{ bands.length }} 只 · 其中 {{ demoCount }} 只为演示补充</span>
      </div>
      <el-table :data="bands" style="width: 100%" empty-text="暂无手环">
        <el-table-column prop="code" label="编号" width="110" />
        <el-table-column label="来源" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="isDemo(row.code) ? 'info' : 'success'">{{ isDemo(row.code) ? '演示' : '设备' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="绑定目标" width="100">
          <template #default="{ row }">
            <span v-if="row.bindTrackNo">#{{ row.bindTrackNo }}</span>
            <span v-else class="sp-dim">未绑定</span>
          </template>
        </el-table-column>
        <el-table-column label="心率" width="100">
          <template #default="{ row }">
            <div v-if="bandData(row)" class="vital-cell">
              <b :class="toneClass(heartTone(bandData(row)?.heartRate))">{{ bandData(row)?.heartRate ?? '-' }}</b>
              <small>bpm</small>
            </div>
            <span v-else class="sp-dim">无数据</span>
          </template>
        </el-table-column>
        <el-table-column label="血氧" width="100">
          <template #default="{ row }">
            <div v-if="bandData(row)" class="vital-cell">
              <b :class="toneClass(spo2Tone(bandData(row)?.spo2))">{{ bandData(row)?.spo2 ?? '-' }}</b>
              <small>%</small>
            </div>
            <span v-else class="sp-dim">无数据</span>
          </template>
        </el-table-column>
        <el-table-column label="静止时长" width="110">
          <template #default="{ row }">
            <div v-if="bandData(row)" class="vital-cell">
              <b :class="toneClass(stillTone(bandData(row)?.stillSec))">{{ bandData(row)?.stillSec ?? '-' }}</b>
              <small>s</small>
            </div>
            <span v-else class="sp-dim">无数据</span>
          </template>
        </el-table-column>
        <el-table-column prop="battery" label="电量" width="80">
          <template #default="{ row }">{{ row.battery ?? '-' }}%</template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="bind(row)">绑定</el-button>
            <el-button v-if="row.bindTrackNo" size="small" link @click="unbind(row)">解绑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { bindWristband, fetchSnapshot, fetchWristbands, unbindWristband } from '@/api'
import type { Frames, WristbandItem } from '@/types/api'

interface LiveBand {
  heartRate: number
  spo2: number
  stillSec: number
}

// 演示环境在设备表之外补充的手环；若后端已存在同编号则自动让位
const DEMO_BANDS: WristbandItem[] = [
  { id: 9001, code: 'WB-0005', bindTrackNo: 3, battery: 91 },
  { id: 9002, code: 'WB-0006', bindTrackNo: 4, battery: 84 },
  { id: 9003, code: 'WB-0007', bindTrackNo: 5, battery: 77 },
  { id: 9004, code: 'WB-0008', bindTrackNo: 6, battery: 96 },
  { id: 9005, code: 'WB-0009', bindTrackNo: 7, battery: 68 },
  { id: 9006, code: 'WB-0010', bindTrackNo: null, battery: 73 },
  { id: 9007, code: 'WB-0011', bindTrackNo: null, battery: 89 }
]
const DEMO_CODES = new Set(DEMO_BANDS.map((item) => item.code))

const remoteBands = ref<WristbandItem[]>([])
const demoOverrides = ref<Record<string, number | null>>({})
const liveBands = ref<Record<number, LiveBand>>({})
const updatedAt = ref('')
let seq = 0
let timer = 0

const bands = computed<WristbandItem[]>(() => {
  const list = remoteBands.value.map((item) => ({ ...item }))
  for (const demo of DEMO_BANDS) {
    if (list.some((item) => item.code === demo.code)) {
      continue
    }
    const override = demoOverrides.value[demo.code]
    list.push({ ...demo, bindTrackNo: override === undefined ? demo.bindTrackNo : override })
  }
  return list
})

const demoCount = computed(() => bands.value.filter((item) => DEMO_CODES.has(item.code)).length)
const bound = computed(() => bands.value.filter((item) => item.bindTrackNo).length)

const activeBands = computed(() => {
  const list: Array<{ code: string; bindTrackNo: number; data: LiveBand }> = []
  for (const item of bands.value) {
    const trackNo = item.bindTrackNo
    const data = trackNo ? liveBands.value[trackNo] : undefined
    if (trackNo && data) {
      list.push({ code: item.code, bindTrackNo: trackNo, data })
    }
  }
  return list
})

const onlineCount = computed(() => activeBands.value.length)
const alertCount = computed(() => {
  let count = 0
  for (const item of activeBands.value) {
    if (heartTone(item.data.heartRate) !== 'plain') count += 1
    if (spo2Tone(item.data.spo2) !== 'plain') count += 1
    if (stillTone(item.data.stillSec) !== 'plain') count += 1
  }
  return count
})

function isDemo(code: string) {
  return DEMO_CODES.has(code)
}

function bandData(row: WristbandItem): LiveBand | null {
  const trackNo = row.bindTrackNo
  return trackNo ? liveBands.value[trackNo] ?? null : null
}

type VitalTone = 'plain' | 'warn' | 'bad'

function heartTone(value?: number): VitalTone {
  if (value === undefined || !Number.isFinite(value)) return 'plain'
  if (value >= 130 || value < 50) return 'bad'
  if (value >= 110 || value < 60) return 'warn'
  return 'plain'
}

function spo2Tone(value?: number): VitalTone {
  if (value === undefined || !Number.isFinite(value)) return 'plain'
  if (value < 90) return 'bad'
  if (value < 95) return 'warn'
  return 'plain'
}

function stillTone(value?: number): VitalTone {
  if (value === undefined || !Number.isFinite(value)) return 'plain'
  if (value >= 15) return 'bad'
  if (value >= 8) return 'warn'
  return 'plain'
}

function toneClass(tone: VitalTone) {
  return tone === 'plain' ? '' : `is-${tone}`
}

// 演示手环的生理数据为本地合成，随帧序号轻微波动，与真实目标数据互不覆盖
function synthVitals(trackNo: number): LiveBand {
  const t = seq / 12
  return {
    heartRate: Math.round(96 + 22 * Math.sin(t + trackNo * 1.3) + (trackNo % 3) * 5),
    spo2: Number((97.4 + 1.4 * Math.sin(t * 0.6 + trackNo)).toFixed(1)),
    stillSec: Number(Math.max(0, 6 + 6 * Math.sin(t * 0.4 + trackNo * 0.8)).toFixed(1))
  }
}

function collectLiveBands(next: Frames) {
  seq = next.seq || seq + 1
  const map: Record<number, LiveBand> = {}
  for (const target of next.targets) {
    if (target.wristbandData) {
      map[target.trackNo] = {
        heartRate: target.wristbandData.heartRate,
        spo2: target.wristbandData.spo2,
        stillSec: target.wristbandData.stillSec
      }
    }
  }
  for (const item of bands.value) {
    if (item.bindTrackNo && !map[item.bindTrackNo] && isDemo(item.code)) {
      map[item.bindTrackNo] = synthVitals(item.bindTrackNo)
    }
  }
  liveBands.value = map
  updatedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

async function loadBands() {
  try {
    const data = await fetchWristbands()
    remoteBands.value = data.list
  } catch {
    remoteBands.value = []
  }
}

async function loadLive() {
  try {
    const data = await fetchSnapshot(1)
    collectLiveBands(data.snapshot)
  } catch {
    // 保持上次数据
  }
}

async function bind(row: WristbandItem) {
  const result = await ElMessageBox.prompt('输入要绑定的目标编号（如 3）', `绑定 ${row.code}`, {
    inputPattern: /^\d+$/,
    inputErrorMessage: '请输入数字'
  })
  const trackNo = Number(result.value)
  if (isDemo(row.code)) {
    demoOverrides.value = { ...demoOverrides.value, [row.code]: trackNo }
    ElMessage.success('演示手环已绑定（本地模拟）')
    await loadLive()
    return
  }
  await bindWristband(row.code, trackNo)
  ElMessage.success('已绑定')
  await Promise.all([loadBands(), loadLive()])
}

async function unbind(row: WristbandItem) {
  if (isDemo(row.code)) {
    demoOverrides.value = { ...demoOverrides.value, [row.code]: null }
    ElMessage.success('演示手环已解绑（本地模拟）')
    await loadLive()
    return
  }
  await unbindWristband(row.code)
  ElMessage.success('已解绑')
  await Promise.all([loadBands(), loadLive()])
}

onMounted(async () => {
  await Promise.all([loadBands(), loadLive()])
  timer = window.setInterval(loadLive, 5000)
})

onBeforeUnmount(() => {
  window.clearInterval(timer)
})
</script>

<style scoped>
.wristbands {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wb-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.wb-stat {
  padding: 14px 16px;
  border: 1px solid var(--line-soft);
  border-radius: var(--r-lg);
  background: var(--card-soft);
}

.wb-stat b {
  display: block;
  font-size: 28px;
  font-weight: 680;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.wb-stat span {
  font-size: 11.5px;
  color: var(--ink-4);
}

.wb-stat--bad {
  border-color: #6d3038;
  background: var(--bad-soft);
}

.wb-stat--bad b {
  color: var(--bad-deep);
}

.vitals {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.vitals__empty {
  padding: 18px;
  border: 1px dashed var(--line-strong);
  border-radius: var(--r-lg);
  background: var(--card-soft);
  color: var(--ink-4);
  font-size: 12.5px;
  text-align: center;
}

.vital-card {
  position: relative;
  padding: 14px 16px 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--card-soft);
  overflow: hidden;
}

.vital-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--brand);
}

.vital-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.vital-card__code {
  font-size: 13px;
  font-weight: 650;
  color: var(--ink);
}

.vital-card__live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ok);
}

.vital-card__live i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 0 4px rgba(54, 209, 166, .14);
  animation: vital-pulse 1.6s ease-in-out infinite;
}

@keyframes vital-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}

.vital-card__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.vital {
  padding: 10px 12px;
  border: 1px solid var(--line-soft);
  border-radius: var(--r-md);
  background: var(--card);
}

.vital__label {
  font-size: 11.5px;
  color: var(--ink-4);
}

.vital__value {
  margin-top: 2px;
  font-size: 26px;
  font-weight: 680;
  line-height: 1.25;
  letter-spacing: -0.02em;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.vital__value small {
  margin-left: 3px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0;
  color: var(--ink-4);
}

.vital__value.is-warn { color: var(--warn-deep); }
.vital__value.is-bad { color: var(--bad-deep); }

.vital-cell {
  display: inline-flex;
  align-items: baseline;
  gap: 3px;
}

.vital-cell b {
  font-size: 15px;
  font-weight: 650;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.vital-cell small {
  font-size: 10.5px;
  color: var(--ink-4);
}

.vital-cell b.is-warn { color: var(--warn-deep); }
.vital-cell b.is-bad { color: var(--bad-deep); }

@media (max-width: 900px) {
  .wb-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .vitals {
    grid-template-columns: 1fr;
  }
}
</style>
