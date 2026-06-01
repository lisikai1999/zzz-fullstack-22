import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 10000 })

api.interceptors.response.use(
  res => res,
  error => {
    if (!error.response) {
      error.userMessage = '无法连接服务器，请检查后端服务是否启动'
    } else if (error.response.status === 404) {
      error.userMessage = '请求的资源不存在'
    } else if (error.response.status === 422) {
      const detail = error.response.data?.detail
      error.userMessage = typeof detail === 'string' ? detail : '请求参数无效'
    } else {
      error.userMessage = `服务器错误 (${error.response.status})`
    }
    return Promise.reject(error)
  }
)

export default {
  getDevices: () => api.get('/devices'),
  getDeviceOverview: () => api.get('/devices/overview'),
  getDevice: (id) => api.get(`/devices/${id}`),
  getHealthHeatmap: () => api.get('/health/heatmap'),
  getHealthHistory: (deviceId, limit = 100) => api.get(`/health/${deviceId}`, { params: { limit } }),
  calculateHealth: (deviceId) => api.post(`/health/calculate/${deviceId}`),
  getSensorReadings: (deviceId, sensorType, limit = 2000) =>
    api.get(`/sensors/readings/${deviceId}`, { params: { sensor_type: sensorType, limit } }),
  getAnomalies: (deviceId, limit = 200) => api.get(`/anomalies/${deviceId}`, { params: { limit } }),
  getRul: (deviceId) => api.get(`/rul/${deviceId}`),
  getRulCurve: (deviceId) => api.get(`/rul/${deviceId}/curve`),
  estimateRul: (deviceId) => api.post(`/rul/estimate/${deviceId}`),
  getWorkOrders: (params = {}) => api.get('/workorders', { params }),
  getWorkOrderCount: (params = {}) => api.get('/workorders/count', { params }),
  createWorkOrder: (data) => api.post('/workorders', data),
  updateWorkOrder: (id, data) => api.patch(`/workorders/${id}`, data),
  completeWorkOrder: (id) => api.post(`/workorders/${id}/complete`),
}
