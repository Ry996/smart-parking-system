import { defineStore } from 'pinia'

// 令牌与会话信息存放在 sessionStorage：关闭标签页即失效，
// 相比 localStorage 长期驻留更不容易被 XSS 直接读取（实验四「前端不裸存明文令牌」）。
const readPermission = () => {
  try {
    return JSON.parse(sessionStorage.getItem('permissions') || '[]')
  } catch (error) {
    return []
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: sessionStorage.getItem('token') || '',
    user_id: sessionStorage.getItem('user_id') || '',
    username: sessionStorage.getItem('username') || '',
    real_name: sessionStorage.getItem('real_name') || '',
    role: sessionStorage.getItem('role') || '',
    permissions: readPermission(),
    permissionsLoaded: false,
  }),
  getters: {
    isAdmin: (state) => state.role === 'admin',
    isLogin: (state) => Boolean(state.token),
    hasPermission: (state) => (code) => state.permissions.includes(code),
  },
  actions: {
    setUser(user) {
      this.token = user.token
      this.user_id = String(user.user_id)
      this.username = user.username
      this.real_name = user.real_name
      this.role = user.role
      this.permissions = []
      this.permissionsLoaded = false
      sessionStorage.setItem('token', user.token)
      sessionStorage.setItem('user_id', String(user.user_id))
      sessionStorage.setItem('username', user.username)
      sessionStorage.setItem('real_name', user.real_name)
      sessionStorage.setItem('role', user.role)
      sessionStorage.removeItem('permissions')
    },
    setPermissions(codes) {
      this.permissions = Array.isArray(codes) ? codes : []
      this.permissionsLoaded = true
      sessionStorage.setItem('permissions', JSON.stringify(this.permissions))
    },
    logout() {
      this.token = ''
      this.user_id = ''
      this.username = ''
      this.real_name = ''
      this.role = ''
      this.permissions = []
      this.permissionsLoaded = false
      sessionStorage.clear()
    },
  },
})
