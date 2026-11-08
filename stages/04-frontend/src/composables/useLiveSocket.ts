/**
 * 全局实时通道单例。
 *
 * 背景：原先 MonitorView 与 AlertsView 各自 new LiveSocket，导致同一用户存在
 * 两条 WS 连接，切换页面即断连重连，且各自维护的 wsConnected 互不相通，
 * 顶栏无法反映真实链路状态（曾出现"横幅提示已断开、顶栏显示在线"的矛盾）。
 *
 * 现在：连接由 AppLayout 在登录后建立、登出时关闭，全应用共享一条连接；
 * 页面通过 onLive() 订阅消息，卸载时取消订阅，不会干扰连接生命周期。
 */
import { readonly, ref } from 'vue'
import { LiveSocket, type LiveSocketOptions } from '@/ws/live'

export type LiveHandler = (type: string, payload: any) => void

const connected = ref(false)
const lastOpenAt = ref(0)
const lastMessageAt = ref(0)

let socket: LiveSocket | null = null
let currentToken = ''
const listeners = new Set<LiveHandler>()

function emit(type: string, payload: any) {
  if (type === 'ws.open') {
    connected.value = true
    lastOpenAt.value = Date.now()
  } else if (type === 'ws.close' || type === 'ws.stale') {
    // stale = 连接还在但已收不到数据（对端假死/网络黑洞），
    // 直接按断开处理，不依赖可能永不触发的 onclose
    connected.value = false
  } else {
    lastMessageAt.value = Date.now()
  }

  // 复制一份再遍历：订阅方在回调里取消订阅时不破坏本轮分发
  for (const handler of [...listeners]) {
    try {
      handler(type, payload)
    } catch (error) {
      console.error('[live] handler error', error)
    }
  }
}

/** 建立全局连接；token 变化时重建，重复调用无副作用。 */
export function connectLive(token: string, options?: LiveSocketOptions) {
  if (!token) {
    return
  }
  if (socket && currentToken === token) {
    return
  }
  socket?.close()
  currentToken = token
  socket = new LiveSocket(token, emit, options)
  socket.connect()
}

/** 关闭全局连接（登出或应用卸载时调用）。 */
export function disconnectLive() {
  socket?.close()
  socket = null
  currentToken = ''
  connected.value = false
}

/**
 * 订阅实时消息，返回取消订阅函数。
 * 若订阅时连接已就绪，立即补发一次 ws.open，
 * 保证后挂载的页面也能完成首次数据对齐。
 */
export function onLive(handler: LiveHandler) {
  listeners.add(handler)
  if (connected.value) {
    queueMicrotask(() => {
      if (listeners.has(handler)) {
        try {
          handler('ws.open', {})
        } catch (error) {
          console.error('[live] handler error', error)
        }
      }
    })
  }
  return () => {
    listeners.delete(handler)
  }
}

/** 供组件读取的只读连接状态。 */
export function useLiveConnection() {
  return {
    connected: readonly(connected),
    lastOpenAt: readonly(lastOpenAt),
    lastMessageAt: readonly(lastMessageAt)
  }
}
