import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiEnvelope } from '@/types/api'

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000
})

export function getToken(): string {
  return sessionStorage.getItem('smartpool.token') || ''
}

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  config.headers['Idempotency-Key'] = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
  return config
})

http.interceptors.response.use(
  (response) => {
    const body = response.data as ApiEnvelope<unknown>
    if (body && typeof body.code === 'number' && body.code !== 0) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body.data as never
  },
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      sessionStorage.removeItem('smartpool.token')
      sessionStorage.removeItem('smartpool.user')
      if (!location.hash.includes('/login')) {
        location.hash = '#/login'
      }
    } else if (status === 403) {
      ElMessage.error('当前角色无权访问')
    } else if (status === 503) {
      ElMessage.error('依赖服务不可用，请查看运行状态')
    } else {
      ElMessage.error(error?.response?.data?.message || '网络异常')
    }
    return Promise.reject(error)
  }
)

export default http
