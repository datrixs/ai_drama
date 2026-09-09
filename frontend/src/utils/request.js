import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const WHITE_LIST = ['/', '/auth/signin', '/auth/signup']
let isRedirecting = false

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 120000     // 120秒超时
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 0) {
      if (res.pagination !== undefined) {
        return { data: res.data, pagination: res.pagination }
      }
      return res.data
    }
    ElMessage.error(res.msg || res.message || '请求失败')
    return Promise.reject(new Error(res.msg || res.message || '请求失败'))
  },
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    const message = detail || error.response?.data?.msg || '请求失败'

    if (status === 401 && !isRedirecting) {
      const currentPath = router.currentRoute.value.path
      if (!WHITE_LIST.includes(currentPath)) {
        isRedirecting = true
        localStorage.removeItem('token')
        ElMessage.error('登录已过期，请重新登录')
        router.replace({ path: '/auth/signin', query: { redirect: router.currentRoute.value.fullPath } }).finally(() => {
          isRedirecting = false
        })
        return Promise.reject(error)
      }
    }

    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request
