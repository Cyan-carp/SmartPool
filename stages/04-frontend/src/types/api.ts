export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  traceId?: string
}

export interface UserView {
  id: number
  username: string
  displayName: string
  role: 'RESCUER' | 'ADMIN' | 'SYS_ADMIN' | 'DEMO'
  menus: string[]
}

export interface LoginResponse {
  token: string
  expiresIn: number
  user: UserView
}

export interface Pool {
  id: number
  name: string
  lengthM: number
  widthM: number
  openFrom: string
  openTo: string
  description?: string
}

export interface Camera {
  id: number
  poolId: number
  name: string
  position: string
  status: string
  cleanliness?: number
  sealScore?: number
  powerOk?: boolean
}

export interface Zone {
  id: number
  poolId: number
  name: string
  type: string
  polygonJson: string
  allowedGroups: string
  enabled: boolean
}

export interface Box {
  x: number
  y: number
  w: number
  h: number
}

export interface RiskDetail {
  underWaterSec?: number
  stillSec?: number
  speed?: number
  heartRate?: number | null
  spo2?: number | null
}

export interface Target {
  trackNo: number
  box: Box
  confidence?: number
  posture: string
  group: string
  wristband?: string | null
  wristbandData?: { heartRate: number; spo2: number; stillSec: number } | null
  riskScore: number
  level: 'NORMAL' | 'NOTICE' | 'WEAK' | 'STRONG'
  reason?: string
  riskDetail?: RiskDetail
  placeholder?: boolean
  synthetic?: boolean
}

export interface WaterQuality {
  temperature: number
  turbidity: number
  ph: number
  chlorine: number
}

export interface Frames {
  poolId: number
  ts: string
  seq: number
  provider: string
  modelLoaded: boolean
  placeholder: boolean
  inferMs: number
  mode: string
  scenario: string
  params?: { confidence: number; windowT: number; stride: string; computeRatio: number }
  targets: Target[]
  counts: { total: number; adult: number; child: number }
  water: WaterQuality
  synthetic?: boolean
}

export interface AlertItem {
  id: number
  poolId: number
  zoneId?: number | null
  zoneName?: string | null
  trackNo?: number | null
  level: 'NOTICE' | 'WEAK' | 'STRONG'
  status: 'OPEN' | 'ACKED' | 'DISPATCHED' | 'RESOLVED' | 'FALSE_ALARM'
  reason: string
  riskScore?: number | null
  triggeredAt: string
  firstAckAt?: string | null
  closedAt?: string | null
  ageSec?: number
}

/** 大屏锁存源：服务端未确认告警 */
export interface ActiveAlert {
  id: number
  trackNo: number
  level: 'NOTICE' | 'WEAK' | 'STRONG'
  status: string
  reason: string
  riskScore?: number | null
  triggeredAt: string
  active: boolean
  zoneName?: string | null
  posture?: string | null
}

export interface AlertActionItem {
  id: number
  alertId: number
  action: string
  operatorId?: number | null
  note?: string | null
  at: string
}

export interface ClipPoint {
  ts: string
  x: number
  y: number
  posture: string
  riskScore: number
}

export interface AlertDetail {
  alert: AlertItem
  actions: AlertActionItem[]
  riskEvent?: Record<string, unknown> | null
  clip: { windowFrom: string; windowTo: string; points: ClipPoint[] }
}

export interface WristbandItem {
  id: number
  code: string
  bindTrackNo?: number | null
  battery?: number | null
}

export interface HeatmapData {
  cols: number
  rows: number
  max: number
  windowMinutes: number
  grid: number[][]
}

export interface TrendData {
  windowMinutes: number
  points: Array<{ time: string; avgRisk: number; riskCount: number }>
}

export interface CrowdData {
  windowHours: number
  bars: Array<{ hour: string; peak: number }>
}

export interface DeviceItem {
  key: string
  id: number
  type: string
  name: string
  status: string
  metrics: Record<string, unknown>
  placeholder?: boolean
}

export interface MaintenanceItem {
  id: number
  deviceId: number
  type: string
  note?: string | null
  at: string
}

export interface WaterLatest {
  temperature?: number
  turbidity?: number
  ph?: number
  chlorine?: number
  exceeded: string[]
  source: string
  threshold: WaterThreshold
  placeholder?: boolean
}

export interface WaterThreshold {
  poolId: number
  turbidityMax: number
  phMin: number
  phMax: number
  temperatureMin: number
  temperatureMax: number
}

export interface WaterHistory {
  windowMinutes: number
  threshold: WaterThreshold
  points: Array<{ ts: string; temperature: number; turbidity: number; ph: number; chlorine: number }>
}

export interface ModelMetrics {
  mode: string
  windowMinutes: number
  placeholder?: boolean
  note?: string
  points: Array<{ ts: string; latencyMs: number; fps: number; computeRatio: number }>
}

export interface DemoStatus {
  aiOk: boolean
  provider: string
  modelLoaded: boolean
  framesPaused: boolean
  dataDelayMs: number
  framesPushed: number
  framesFailed: number
  mode: string
  scenario: string
  targets: number
  camerasOnline: number
  camerasTotal: number
  waterExceeded: string[]
  openAlerts: number
  activeFaults: Array<{ type: string; remainSec: number }>
  placeholder?: boolean
}

export interface AlertStats {
  hours: number
  total: number
  open: number
  acked: number
  dispatched: number
  resolved: number
  falseAlarm: number
  strong: number
  weak: number
  avgAckSeconds: number
  falseAlarmRate: number
}

export interface SnapshotResponse {
  poolId: number
  snapshot: Frames
  serverTime: string
  wsOnline: number
  dataDelayMs: number
  degraded?: boolean
  pushedFrames?: number
  failedFrames?: number
}
