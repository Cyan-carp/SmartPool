import { defineStore } from 'pinia'
import { login as loginApi, logout as logoutApi } from '@/api'
import type { UserView } from '@/types/api'

interface State {
  token: string
  user: UserView | null
}

const TOKEN_KEY = 'smartpool.token'
const USER_KEY = 'smartpool.user'

export const useUserStore = defineStore('user', {
  state: (): State => ({
    token: sessionStorage.getItem(TOKEN_KEY) || '',
    user: JSON.parse(sessionStorage.getItem(USER_KEY) || 'null')
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    role: (state) => state.user?.role || '',
    menus: (state) => state.user?.menus || []
  },
  actions: {
    async login(username: string, password: string) {
      const data = await loginApi(username, password)
      this.token = data.token
      this.user = data.user
      sessionStorage.setItem(TOKEN_KEY, data.token)
      sessionStorage.setItem(USER_KEY, JSON.stringify(data.user))
      return data.user
    },
    async logout() {
      try {
        await logoutApi()
      } catch {
        // 无状态 JWT：服务端无状态可清，忽略失败
      }
      this.token = ''
      this.user = null
      sessionStorage.removeItem(TOKEN_KEY)
      sessionStorage.removeItem(USER_KEY)
    }
  }
})
