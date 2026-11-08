/**
 * 实时通道封装：心跳、指数退避重连、消息分发。
 * 只负责推送接收；重连后由页面自行拉取 /live/snapshot 对齐。
 */
export type LiveHandler = (type: string, payload: any) => void

export interface LiveSocketOptions {
  /**
   * 多久收不到任何消息就判定链路失效（毫秒）。
   *
   * 后端以 100ms 固定节奏广播 frames，正常情况下始终有消息流入；
   * 一旦静默超过阈值，说明连接已死但 TCP 层尚未感知 —— 典型场景是客户端
   * 断网（浏览器不会主动关闭 WebSocket），此时 onclose 要等系统级超时，
   * 可能长达数分钟。主动关闭可立即触发重连与状态更新。
   *
   * 若后端将来改成"按需推送"，必须同步调大该阈值，否则会误判断线。
   */
  silenceTimeoutMs?: number
}

export class LiveSocket {
  private socket: WebSocket | null = null
  private handler: LiveHandler
  private token: string
  private retries = 0
  private closedByUser = false
  private heartbeatTimer: number | null = null
  private watchdogTimer: number | null = null
  private lastMessageAt = 0
  private readonly silenceTimeoutMs: number

  constructor(token: string, handler: LiveHandler, options: LiveSocketOptions = {}) {
    this.token = token
    this.handler = handler
    this.silenceTimeoutMs = options.silenceTimeoutMs ?? 6000
  }

  connect() {
    if (this.socket && this.socket.readyState <= WebSocket.OPEN) {
      return
    }
    this.closedByUser = false
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${scheme}://${location.host}/ws/live?token=${encodeURIComponent(this.token)}`
    const socket = new WebSocket(url)
    this.socket = socket

    socket.onopen = () => {
      this.retries = 0
      this.lastMessageAt = Date.now()
      this.startHeartbeat()
      this.startWatchdog()
      this.handler('ws.open', {})
    }

    socket.onmessage = (event) => {
      // 任何一条消息都算存活信号，不区分类型
      this.lastMessageAt = Date.now()
      try {
        const message = JSON.parse(event.data)
        this.handler(message.type, message.payload)
      } catch {
        // 忽略无法解析的消息
      }
    }

    socket.onclose = () => {
      this.stopHeartbeat()
      this.stopWatchdog()
      // 连接已被看门狗主动作废并重建时，这条迟到的 onclose 直接忽略，
      // 否则会重复上报断开并叠加重连定时器
      if (this.socket !== socket) {
        return
      }
      this.handler('ws.close', {})
      if (!this.closedByUser) {
        this.scheduleReconnect()
      }
    }

    socket.onerror = () => {
      socket.close()
    }
  }

  private scheduleReconnect() {
    const delay = [1000, 2000, 5000, 10000][Math.min(this.retries, 3)]
    this.retries += 1
    window.setTimeout(() => {
      if (!this.closedByUser) {
        this.connect()
      }
    }, delay)
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }))
      }
    }, 15000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer !== null) {
      window.clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 静默看门狗：每秒检查一次，连接仍为 OPEN 但长时间收不到任何消息时主动关闭。
   * 关闭会走正常的 onclose -> 状态更新 -> 指数退避重连，
   * 比等 TCP 自己超时（客户端断网时可能长达数分钟）快得多。
   */
  private startWatchdog() {
    this.stopWatchdog()
    this.watchdogTimer = window.setInterval(() => {
      if (this.socket?.readyState !== WebSocket.OPEN) {
        return
      }
      const silentFor = Date.now() - this.lastMessageAt
      if (silentFor <= this.silenceTimeoutMs) {
        return
      }
      // 先通知上层，再作废连接；顺序保证 UI 能拿到静默时长用于诊断
      this.handler('ws.stale', { silentMs: silentFor })

      // 关键：不能只调 close() 就指望 onclose 回调。
      // 对端假死（进程挂起 / 网络黑洞）时关闭握手无人应答，
      // onclose 可能延迟数十秒甚至永不触发，状态与重连都会卡住。
      // 因此这里主动解引用并立即调度重连，把主动权留在本地。
      const dying = this.socket
      this.socket = null
      try {
        dying?.close()
      } catch {
        // 已进入关闭流程，忽略
      }
      this.stopHeartbeat()
      this.stopWatchdog()
      if (!this.closedByUser) {
        this.scheduleReconnect()
      }
    }, 1000)
  }

  private stopWatchdog() {
    if (this.watchdogTimer !== null) {
      window.clearInterval(this.watchdogTimer)
      this.watchdogTimer = null
    }
  }

  close() {
    this.closedByUser = true
    this.stopHeartbeat()
    this.stopWatchdog()
    this.socket?.close()
    this.socket = null
  }
}
