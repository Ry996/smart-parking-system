import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const http = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

http.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.msg || '请求失败，请稍后重试。'

    if (status === 401) {
      sessionStorage.clear()
      router.push('/login')
      ElMessage.warning('登录状态已失效，请重新登录。')
    } else {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)

export const login = (data) => http.post('/auth/login', data)
export const getUserInfo = () => http.get('/auth/info')

export const recognizePlate = (formData) => http.post('/lpr/recognize', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
})
export const getLprMode = () => http.get('/lpr/mode')

export const vehicleEnter = (data) => http.post('/parking/enter', data)
export const getParkedList = (params) => http.get('/parking/parked', { params })
export const getSpaces = () => http.get('/parking/spaces')
export const updateSpaces = (data) => http.put('/parking/spaces', data)
export const previewExit = (data) => http.post('/parking/exit-preview', data)
export const vehicleExit = (data) => http.post('/parking/exit', data)
export const payRecord = (id) => http.post(`/parking/${id}/pay`)

export const getRecords = (params) => http.get('/records/', { params })
export const getRecord = (id) => http.get(`/records/${id}`)
export const updateRemark = (id, data) => http.put(`/records/${id}/remark`, data)

export const getOverview = () => http.get('/stats/overview')
export const getFlowStats = (params) => http.get('/stats/flow', { params })
export const getIncomeStats = (params) => http.get('/stats/income', { params })
export const getAiAdvice = (params) => http.get('/stats/ai-advice', { params })

export const getFeeRules = () => http.get('/fee-rules/')
export const createFeeRule = (data) => http.post('/fee-rules/', data)
export const updateFeeRule = (id, data) => http.put(`/fee-rules/${id}`, data)
export const deleteFeeRule = (id) => http.delete(`/fee-rules/${id}`)

export const getUsers = () => http.get('/users/')
export const createUser = (data) => http.post('/users/', data)
export const updateUser = (id, data) => http.put(`/users/${id}`, data)
export const deleteUser = (id) => http.delete(`/users/${id}`)

// V2 新增：月租车辆
export const getMonthlyList = (params) => http.get('/monthly/', { params })
export const createMonthly = (data) => http.post('/monthly/', data)
export const renewMonthly = (id, data) => http.post(`/monthly/${id}/renew`, data)
export const updateMonthly = (id, data) => http.put(`/monthly/${id}`, data)
export const deleteMonthly = (id) => http.delete(`/monthly/${id}`)
export const checkMonthly = (plate) => http.get('/monthly/check', { params: { plate } })

// V2 新增：车位预约
export const getReservations = (params) => http.get('/reservations/', { params })
export const createReservation = (data) => http.post('/reservations/', data)
export const updateReservationStatus = (id, data) => http.put(`/reservations/${id}/status`, data)
export const deleteReservation = (id) => http.delete(`/reservations/${id}`)

// V2 新增：黑名单
export const getBlacklist = (params) => http.get('/blacklist/', { params })
export const createBlacklist = (data) => http.post('/blacklist/', data)
export const updateBlacklist = (id, data) => http.put(`/blacklist/${id}`, data)
export const deleteBlacklist = (id) => http.delete(`/blacklist/${id}`)

// V2 新增：操作日志
export const getLogs = (params) => http.get('/logs/', { params })

// V2 新增：数据导出
export const exportRecords = (params) => http.get('/export/records', { params, responseType: 'blob' })
export const exportMonthly = () => http.get('/export/monthly', { responseType: 'blob' })

// V2.2 新增：RBAC 角色权限（实验四）
export const getMyPermissions = () => http.get('/roles/me')
export const getRoles = () => http.get('/roles/')
export const getPermissionCatalog = () => http.get('/roles/permissions')
export const updateRolePermissions = (id, permissions) => http.put(`/roles/${id}/permissions`, { permissions })
export const createRole = (data) => http.post('/roles/', data)
export const deleteRole = (id) => http.delete(`/roles/${id}`)

// V2.2 新增：RAG 知识库问答与 AI 复核（实验五）
export const getAiStatus = () => http.get('/ai/status')
export const askAi = (data) => http.post('/ai/ask', data)
export const submitAiFeedback = (data) => http.post('/ai/feedback', data)
export const getAiFeedback = (params) => http.get('/ai/feedback', { params })
export const getAiCalls = () => http.get('/ai/calls')
export const reindexKnowledge = () => http.post('/ai/reindex')

export default http
