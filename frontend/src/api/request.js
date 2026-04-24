import axios from 'axios'

const request = axios.create({
  baseURL: '',
  timeout: 120000
})

request.interceptors.response.use(
  response => response.data,
  error => {
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return Promise.reject(new Error('请求超时，请检查网络连接'))
    }
    if (!error.response) {
      return Promise.reject(new Error('无法连接到服务器，请确认后端已启动'))
    }
    const message =
      error.response.data?.detail ||
      error.response.data?.message ||
      error.message ||
      '请求失败，请稍后重试'
    return Promise.reject(new Error(message))
  }
)

export default request
