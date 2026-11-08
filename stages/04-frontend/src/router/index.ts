import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layout/AppLayout.vue'),
    children: [
      { path: '', redirect: '/monitor' },
      { path: 'monitor', name: 'monitor', component: () => import('@/views/MonitorView.vue'), meta: { title: '实时监控' } },
      { path: 'alerts', name: 'alerts', component: () => import('@/views/AlertsView.vue'), meta: { title: '告警中心' } },
      { path: 'wristbands', name: 'wristbands', component: () => import('@/views/WristbandsView.vue'), meta: { title: '智能手环' } },
      { path: 'replay', name: 'replay', component: () => import('@/views/ReplayView.vue'), meta: { title: '事件回溯' } },
      { path: 'playback', name: 'playback', component: () => import('@/views/PlaybackView.vue'), meta: { title: '结果回放' } },
      { path: 'zones', name: 'zones', component: () => import('@/views/ZonesView.vue'), meta: { title: '电子围栏' } },
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '数据看板' } },
      { path: 'devices', name: 'devices', component: () => import('@/views/DevicesView.vue'), meta: { title: '设备与水质' } },
      { path: 'model', name: 'model', component: () => import('@/views/ModelView.vue'), meta: { title: '模型与算力' } },
      { path: 'demo', name: 'demo', component: () => import('@/views/DemoView.vue'), meta: { title: '演示控制台' } }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/monitor' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to) => {
  const store = useUserStore()
  if (!to.meta.public && !store.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && store.isLoggedIn) {
    return { path: '/monitor' }
  }
  return true
})

export default router
