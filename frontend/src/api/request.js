import axios from 'axios'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 15000
})

request.interceptors.response.use(
  response => response.data,
  error => {
    const message =
      error?.response?.data?.detail ||
      error?.message ||
      '请求失败，请稍后重试'
    return Promise.reject(new Error(message))
  }
)

export default request
