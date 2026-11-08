import http from './http'
import type {
  ActiveAlert,
  AlertDetail,
  AlertItem,
  AlertStats,
  Camera,
  CrowdData,
  DemoStatus,
  DeviceItem,
  HeatmapData,
  LoginResponse,
  MaintenanceItem,
  ModelMetrics,
  Pool,
  SnapshotResponse,
  TrendData,
  UserView,
  WaterHistory,
  WaterLatest,
  WaterThreshold,
  WristbandItem,
  Zone
} from '@/types/api'

export function login(username: string, password: string) {
  return http.post<never, LoginResponse>('/auth/login', { username, password })
}

export function fetchMe() {
  return http.get<never, UserView>('/auth/me')
}

export function logout() {
  return http.post<never, { closed: boolean }>('/auth/logout')
}

export function fetchPools() {
  return http.get<never, Pool[]>('/pools')
}

export function fetchCameras(poolId = 1) {
  return http.get<never, Camera[]>('/cameras', { params: { poolId } })
}

export function fetchZones(poolId = 1) {
  return http.get<never, Zone[]>('/zones', { params: { poolId } })
}

export function fetchSnapshot(poolId = 1) {
  return http.get<never, SnapshotResponse>('/live/snapshot', { params: { poolId } })
}

export function fetchAlerts(params: Record<string, unknown> = {}) {
  return http.get<never, { list: AlertItem[]; total: number; page: number; size: number }>('/alerts', { params })
}

export function fetchActiveAlerts(poolId = 1) {
  return http.get<never, { list: ActiveAlert[]; total: number }>('/alerts/active', { params: { poolId } })
}

export function fetchAlertDetail(id: number) {
  return http.get<never, AlertDetail>(`/alerts/${id}`)
}

export function ackAlert(id: number, note = '') {
  return http.post<never, AlertItem>(`/alerts/${id}/ack`, { note })
}

export function dispatchAlert(id: number, assignee: string, note = '') {
  return http.post<never, AlertItem>(`/alerts/${id}/dispatch`, { assignee, note })
}

export function resolveAlert(id: number, result: string, note = '') {
  return http.post<never, AlertItem>(`/alerts/${id}/resolve`, { result, note })
}

export function markFalseAlarm(id: number, note = '') {
  return http.post<never, AlertItem>(`/alerts/${id}/false-alarm`, { note })
}

export function fetchStats(hours = 24) {
  return http.get<never, AlertStats>('/stats/overview', { params: { hours } })
}

export function fetchHeatmap(poolId = 1, minutes = 30) {
  return http.get<never, HeatmapData>('/stats/heatmap', { params: { poolId, minutes } })
}

export function fetchTrend(poolId = 1, minutes = 30) {
  return http.get<never, TrendData>('/stats/trend', { params: { poolId, minutes } })
}

export function fetchCrowd(poolId = 1, hours = 6) {
  return http.get<never, CrowdData>('/stats/crowd', { params: { poolId, hours } })
}

export function createZone(payload: Partial<Zone>) {
  return http.post<never, Zone>('/zones', payload)
}

export function updateZone(id: number, payload: Partial<Zone>) {
  return http.put<never, Zone>(`/zones/${id}`, payload)
}

export function deleteZone(id: number) {
  return http.delete<never, { deleted: boolean }>(`/zones/${id}`)
}

export function fetchWristbands() {
  return http.get<never, { list: WristbandItem[]; total: number; bound: number }>('/wristbands')
}

export function bindWristband(code: string, trackNo: number) {
  return http.post<never, WristbandItem>(`/wristbands/${code}/bind`, { trackNo })
}

export function unbindWristband(code: string) {
  return http.post<never, WristbandItem>(`/wristbands/${code}/unbind`)
}

export function fetchModelInfo() {
  return http.get<never, Record<string, unknown>>('/model/info')
}

export function fetchModelParams() {
  return http.get<never, Record<string, unknown>>('/model/params')
}

export function setModelMode(mode: string, auto = true) {
  return http.post<never, Record<string, unknown>>('/model/mode', { mode, auto })
}

export function fetchModelMetrics(minutes = 30) {
  return http.get<never, ModelMetrics>('/model/metrics', { params: { minutes } })
}

export function fetchDevices(poolId = 1) {
  return http.get<never, { items: DeviceItem[]; total: number; online: number }>('/devices', { params: { poolId } })
}

export function postMaintenance(key: string, type: string, note: string) {
  return http.post<never, MaintenanceItem>(`/devices/${key}/maintenance`, { type, note })
}

export function fetchMaintenance(key: string) {
  return http.get<never, MaintenanceItem[]>(`/devices/${key}/maintenance`)
}

export function fetchWaterLatest(poolId = 1) {
  return http.get<never, WaterLatest>('/water-quality/latest', { params: { poolId } })
}

export function fetchWaterHistory(poolId = 1, minutes = 60) {
  return http.get<never, WaterHistory>('/water-quality/history', { params: { poolId, minutes } })
}

export function updateWaterThreshold(payload: Partial<WaterThreshold> & { poolId?: number }) {
  return http.put<never, WaterThreshold>('/water-quality/thresholds', payload)
}

export function fetchDemoStatus() {
  return http.get<never, DemoStatus>('/demo/status')
}

export function injectFault(type: string, seconds = 20, cameraId?: number) {
  return http.post<never, { type: string; seconds: number; until: number }>('/demo/faults', { type, seconds, cameraId })
}

export function clearFaults() {
  return http.post<never, { cleared: boolean }>('/demo/faults/clear')
}

export function triggerScenario(key: string) {
  return http.post<never, Record<string, unknown>>(`/demo/scenarios/${key}`)
}

export function setClock(speed: number) {
  return http.post<never, Record<string, unknown>>('/demo/clock', { speed })
}

export function resetDemo(seed = 2026, swimmerCount = 8, clearAlerts = false) {
  return http.post<never, Record<string, unknown>>('/demo/reset', null, {
    params: { seed, swimmerCount, clearAlerts }
  })
}
