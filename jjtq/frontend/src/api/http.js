import axios from 'axios'
import { apiConfig } from '@/config/api'
import { clearToken, getToken } from '@/utils/auth'

/**
 * 全局唯一的 axios 实例。
 * - 请求：自动带上 Authorization: Bearer <token>
 * - 响应：解包后端统一的 { code, message, data } 结构，非 200 直接 reject
 * - 网络错误：统一成 Error(message)，并标记 status / isAuthError
 */
const http = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => {
    const body = response.data

    // 后端统一响应格式：{ code: 200, message: 'ok', data: ... }
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 200) {
        return body.data
      }
      return Promise.reject(new Error(body.message || '请求失败'))
    }

    return body
  },
  (error) => {
    const status = error.response?.status
    const body = error.response?.data
    const validationMessage = status === 422 && Array.isArray(body?.data)
      ? body.data.find((item) => typeof item?.msg === 'string')?.msg
      : ''
    const message =
      validationMessage || body?.message ||
      body?.detail ||
      (typeof body === 'string' ? body : '') ||
      error.message ||
      '网络请求失败'

    const wrapped = new Error(message)
    wrapped.status = status

    if (status === 401) {
      clearToken()
      wrapped.isAuthError = true
    }

    return Promise.reject(wrapped)
  },
)

export default http
