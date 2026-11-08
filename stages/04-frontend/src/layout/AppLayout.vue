<template>
  <div class="app-shell">
    <aside class="rail">
      <RouterLink to="/monitor" class="rail-brand" title="智慧泳池 · 溺水实时防护">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path v-for="(d, i) in BRAND_ICON" :key="i" :d="d" />
        </svg>
      </RouterLink>

      <nav class="rail-nav">
        <RouterLink
          v-for="item in visibleMenus"
          :key="item.key"
          :to="item.path"
          class="rail-btn"
          :class="{ 'is-on': activePath === item.path }"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path v-for="(d, i) in ICONS[item.key] || ICONS.default" :key="i" :d="d" />
          </svg>
          <span class="rail-tip">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="rail-foot">
        <span class="rail-foot__mark">SP</span>
      </div>
    </aside>

    <div class="shell">
      <header class="topbar">
        <span class="tb-tab">{{ pageTitle }}</span>
        <span class="tb-sub">智慧泳池 · 溺水实时防护</span>

        <nav class="tb-quick">
          <span class="tb-pill" :class="{ 'tb-pill--bad': !linkConnected }" :title="linkTitle">
            <i class="dot" :class="linkConnected ? 'dot--live' : 'dot--bad'" />实时链路<b>{{ linkConnected ? '在线' : '断开' }}</b>
          </span>
          <span class="tb-pill" :class="{ 'tb-pill--mock': !modelLoaded }" :title="modelTitle">
            <i class="dot" :class="modelLoaded ? 'dot--live' : 'dot--mock'" />检测模型<b>{{ modelLoaded ? '已加载' : '占位' }}</b>
          </span>
          <span class="tb-pill" title="演示版画面、手环与水质数据均由模拟器合成，未接入真实视频与传感器">
            <i class="dot" />数据源<b>合成</b>
          </span>
        </nav>

        <div class="tb-right">
          <span class="tb-clock num">{{ clockText }}</span>
          <el-dropdown @command="onCommand">
            <span class="tb-user">
              <span class="tb-avatar">{{ avatarText }}</span>
              <span class="tb-user-name">{{ store.user?.displayName || '未登录' }}</span>
              <span class="tb-user-role">{{ roleLabel }}</span>
              <svg class="tb-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="page">
        <div class="page-inner">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchModelInfo } from '@/api'
import { useUserStore } from '@/stores/user'
import { connectLive, disconnectLive, useLiveConnection } from '@/composables/useLiveSocket'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

// 实时链路由布局层统一持有：全应用一条连接，页面只订阅，避免同一用户多连接
// 注意必须解构为顶层 ref，模板才会自动解包；写成 link.connected 会恒为真
const { connected: linkConnected } = useLiveConnection()
const modelLoaded = ref(false)
const modelProvider = ref('')
let modelTimer = 0

const linkTitle = computed(() =>
  linkConnected.value ? '实时通道已连接' : '实时通道已断开，正在自动重连'
)
const modelTitle = computed(() =>
  modelLoaded.value
    ? `已加载真实权重${modelProvider.value ? `（${modelProvider.value}）` : ''}`
    : '检测为占位输出，未加载真实模型权重'
)

async function refreshModelState() {
  try {
    const info = await fetchModelInfo()
    modelLoaded.value = Boolean(info.modelLoaded)
    modelProvider.value = String(info.provider || '')
  } catch {
    // 接口暂不可用时保留上一次状态，避免顶栏反复闪烁
  }
}

const MENU_DEFS = [
  { key: 'monitor', label: '实时监控', path: '/monitor' },
  { key: 'alerts', label: '告警中心', path: '/alerts' },
  { key: 'wristbands', label: '智能手环', path: '/wristbands' },
  { key: 'replay', label: '事件回溯', path: '/replay' },
  { key: 'playback', label: '结果回放', path: '/playback' },
  { key: 'zones', label: '电子围栏', path: '/zones' },
  { key: 'dashboard', label: '数据看板', path: '/dashboard' },
  { key: 'devices', label: '设备与水质', path: '/devices' },
  { key: 'model', label: '模型与算力', path: '/model' },
  { key: 'demo', label: '演示控制台', path: '/demo' }
]

// 24x24 线性图标：与参考项目一致，不引图标库，颜色继承 currentColor
const BRAND_ICON = [
  'M12 2.6c3.3 4.3 5.7 7.3 5.7 10.1a5.7 5.7 0 0 1-11.4 0C6.3 9.9 8.7 6.9 12 2.6z',
  'M3 20.2c1.9 1.1 3.8 1.1 5.7 0 1.9-1.1 3.8-1.1 5.7 0 1.9 1.1 3.8 1.1 5.7 0'
]
const ICONS: Record<string, string[]> = {
  default: ['M4 4h16v16H4z'],
  monitor: ['M2.5 4.5h19v12h-19z', 'M8 20.5h8', 'M12 16.5v4'],
  alerts: ['M12 3a6.5 6.5 0 0 0-6.5 6.5c0 3.7-1.8 4.8-1.8 4.8h16.6s-1.8-1.1-1.8-4.8A6.5 6.5 0 0 0 12 3z', 'M10 17.5a2 2 0 0 0 4 0'],
  wristbands: ['M7.5 6.5h9v11h-9z', 'M9 6.5V3h6v3.5', 'M9 17.5V21h6v-3.5', 'M10.5 12h3'],
  replay: ['M3.2 12a8.8 8.8 0 1 0 2.7-6.3', 'M3 3.5v5h5', 'M12 7.5V12l3 2'],
  playback: ['M3 4.5h18v15H3z', 'M10 9.5l5 3-5 3z'],
  zones: ['M12 2.5 21 7v10l-9 4.5L3 17V7z', 'M3 7l9 4.5L21 7', 'M12 11.5V21.5'],
  dashboard: ['M3 20.5h18', 'M6 20.5v-7', 'M11 20.5V5', 'M16 20.5v-10'],
  devices: ['M12 2.8c3.2 4.2 5.6 7.2 5.6 10a5.6 5.6 0 0 1-11.2 0c0-2.8 2.4-5.8 5.6-10z', 'M4 20.5c1.7 1 3.4 1 5.1 0 1.7-1 3.4-1 5.1 0 1.7 1 3.4 1 5.1 0'],
  model: ['M5 5h14v14H5z', 'M9.5 9.5h5v5h-5z', 'M9 2v3', 'M15 2v3', 'M9 19v3', 'M15 19v3', 'M2 9h3', 'M2 15h3', 'M19 9h3', 'M19 15h3'],
  demo: ['M3 7h10', 'M17 7h4', 'M3 17h4', 'M11 17h10', 'M14 4v6', 'M8 14v6']
}

const visibleMenus = computed(() => {
  const menus = store.menus
  if (!menus.length) {
    return MENU_DEFS
  }
  // 智能手环与结果回放属新增页面，后端角色菜单尚未下发对应 key 时也保持可见
  const alwaysVisible = ['wristbands', 'playback']
  return MENU_DEFS.filter((item) => alwaysVisible.includes(item.key) || menus.includes(item.key))
})

const activePath = computed(() => route.path)
const pageTitle = computed(() => (route.meta.title as string) || '智慧泳池')
const roleLabel = computed(() => {
  const map: Record<string, string> = {
    RESCUER: '救生员',
    ADMIN: '管理员',
    SYS_ADMIN: '系统管理员',
    DEMO: '演示操作员'
  }
  return map[store.role] || store.role || '未知'
})
const avatarText = computed(() => (store.user?.displayName || '未').slice(0, 1))

const clockText = ref('')
let clockTimer = 0
function tick() {
  clockText.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}
onMounted(() => {
  tick()
  clockTimer = window.setInterval(tick, 1000)
  // 登录后在此建立全局实时连接；token 变化时 connectLive 内部会重建
  connectLive(store.token)
  refreshModelState()
  modelTimer = window.setInterval(refreshModelState, 60000)
})
onBeforeUnmount(() => {
  window.clearInterval(clockTimer)
  window.clearInterval(modelTimer)
  disconnectLive()
})

async function onCommand(command: string) {
  if (command === 'logout') {
    await store.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100%;
  background: transparent;
}

.rail {
  width: var(--rail-w);
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--card);
  border-right: 1px solid var(--line);
}

.rail-brand {
  width: var(--rail-w);
  height: var(--top-h);
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--brand);
  border-bottom: 1px solid var(--line-soft);
}

.rail-brand svg {
  width: 24px;
  height: 24px;
}

.rail-nav {
  width: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 0;
  overflow: visible;
}

@media (max-height: 640px) {
  .rail-nav {
    gap: 2px;
    padding: 6px 0;
  }
  .rail-btn {
    width: 34px;
    height: 34px;
  }
}

.rail-btn {
  position: relative;
  width: 40px;
  height: 40px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-lg);
  color: var(--ink-3);
  transition: background .16s ease, color .16s ease, box-shadow .16s ease;
}

.rail-btn svg {
  width: 21px;
  height: 21px;
}

.rail-btn:hover {
  background: var(--card-soft);
  color: var(--brand);
}

.rail-btn.is-on {
  background: var(--brand);
  color: #f0f7ff;
  box-shadow: 0 4px 12px var(--brand-glow);
}

.rail-btn.is-on:hover {
  background: var(--brand);
  color: #f0f7ff;
}

.rail-tip {
  position: absolute;
  left: 50px;
  top: 50%;
  transform: translateY(-50%) translateX(-4px);
  z-index: 20;
  padding: 5px 9px;
  border-radius: var(--r-md);
  background: var(--ink);
  color: #f0f7ff;
  font-size: 11.5px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity .14s ease, transform .14s ease;
}

.rail-btn:hover .rail-tip {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

.rail-foot {
  width: 100%;
  padding: 12px 0 14px;
  border-top: 1px solid var(--line-soft);
  display: flex;
  justify-content: center;
}

.rail-foot__mark {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  color: var(--ink-placeholder);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .04em;
}

.shell {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: var(--top-h);
  flex: none;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 20px;
  background: var(--card);
  border-bottom: 1px solid var(--line);
}

.tb-tab {
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: var(--brand);
  white-space: nowrap;
}

.tb-sub {
  padding-left: 18px;
  border-left: 1px solid var(--line);
  font-size: 12px;
  color: var(--ink-4);
  white-space: nowrap;
}

.tb-quick {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 6px;
}

.tb-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--card);
  font-size: 11.5px;
  font-weight: 500;
  color: var(--ink-4);
  white-space: nowrap;
}

.tb-pill b {
  font-weight: 650;
  color: var(--ink-2);
}

.dot {
  width: 6px;
  height: 6px;
  flex: none;
  border-radius: 50%;
  background: var(--line-strong);
  box-shadow: 0 0 0 3px rgba(130, 152, 170, .10);
}

.dot--live {
  background: var(--ok);
  box-shadow: 0 0 0 3px rgba(54, 209, 166, .14);
}

.dot--mock {
  background: var(--violet);
  box-shadow: 0 0 0 3px rgba(154, 140, 255, .12);
}

.dot--bad {
  background: var(--bad);
  box-shadow: 0 0 0 3px rgba(255, 107, 114, .16);
}

.tb-pill--bad {
  border-color: var(--bad-deep);
}

.tb-pill--bad b {
  color: var(--bad);
}

.tb-pill--mock b {
  color: var(--violet);
}

.tb-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}

.tb-clock {
  font-size: 12.5px;
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.tb-user {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}

.tb-avatar {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-md);
  background: var(--brand-soft);
  color: var(--brand-deep);
  font-size: 12.5px;
  font-weight: 650;
}

.tb-user-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
}

.tb-user-role {
  font-size: 11.5px;
  color: var(--ink-4);
}

.tb-chevron {
  width: 14px;
  height: 14px;
  color: var(--ink-placeholder);
}

.page {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 22px 30px;
}

.page-inner {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (max-width: 1180px) {
  .tb-quick .tb-pill:last-child {
    display: none;
  }
}

@media (max-width: 1000px) {
  .rail {
    width: 56px;
  }
  .rail-brand {
    width: 56px;
  }
  .tb-quick,
  .tb-sub {
    display: none;
  }
}

@media (max-width: 680px) {
  .page {
    padding: 12px 12px 24px;
  }
  .tb-clock,
  .tb-user-role {
    display: none;
  }
}
</style>
