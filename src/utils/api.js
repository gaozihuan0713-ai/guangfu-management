import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
    baseURL: '/api',
    timeout: 30000
})

api.interceptors.request.use(config => {
    const token = localStorage.getItem('solar_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

api.interceptors.response.use(
    response => response.data,
    error => {
        if (error.response?.status === 401) {
            localStorage.removeItem('solar_token')
            localStorage.removeItem('solar_user')
            window.location.href = '/login'
        }
        ElMessage.error(error.response?.data?.message || '请求失败')
        return Promise.reject(error)
    }
)

export const authAPI = {
    login: (username, password) => api.post('/auth/login', { username, password }),
    getUserInfo: () => api.get('/auth/info'),
    changePassword: (old_password, new_password) =>
        api.post('/auth/change-password', { old_password, new_password }),
    getUsers: () => api.get('/auth/users'),
    createUser: (data) => api.post('/auth/users', data),
    updateUser: (id, data) => api.put(`/auth/users/${id}`, data),
    deleteUser: (id) => api.delete(`/auth/users/${id}`)
}

export const dataAPI = {
    getRealtime: (hours = 24) => api.get(`/data/realtime?hours=${hours}`),
    getPredict: (hours = 6) => api.get(`/data/predict?hours=${hours}`),
    getComparison: (hours = 6) => api.get(`/data/comparison?hours=${hours}`),
    getDashboard: () => api.get('/data/dashboard'),
    getHistory: (params) => api.get('/data/history', { params }),
    exportData: (params) => api.get('/data/export', { params, responseType: 'blob' })
}

export const alarmAPI = {
    getAlarms: (params) => api.get('/alarm/list', { params }),
    getStats: () => api.get('/alarm/stats'),
    checkAlarms: () => api.post('/alarm/check'),
    ackAlarm: (id) => api.post(`/alarm/${id}/ack`),
    batchAck: (ids) => api.post('/alarm/batch-ack', { ids }),
    resolveAlarm: (id) => api.post(`/alarm/${id}/resolve`)
}

export default api
