import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const http = axios.create({
  baseURL: API_BASE,
  timeout: 120000
})

http.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const msg = error?.response?.data?.message || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

/** 统一后端响应：{code, message, data} */
function unwrap(res) {
  if (res && typeof res === 'object' && 'code' in res) {
    if (res.code !== 0) {
      ElMessage.error(res.message || '操作失败')
      throw new Error(res.message || '操作失败')
    }
    return res.data
  }
  return res
}

export const api = {
  // ---------- 系统 ----------
  systemStatus: () => http.get('/system/status').then(unwrap),
  classes: () => http.get('/system/classes').then(unwrap),

  // ---------- 检测 ----------
  detectImage(file) {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/detect/image', fd).then(unwrap)
  },
  detectBatch(files) {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    return http.post('/detect/batch', fd).then(unwrap)
  },
  async detectBatchZip(fileList) {
    const JSZip = (await import('jszip')).default
    const zip = new JSZip()
    for (const item of fileList) {
      const name = item.webkitRelativePath || item.name
      zip.file(name, item)
    }
    const blob = await zip.generateAsync({ type: 'blob' })
    const fd = new FormData()
    fd.append('zip', new File([blob], 'batch.zip', { type: 'application/zip' }))
    return http.post('/detect/batch', fd).then(unwrap)
  },
  detectVideo(file) {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/detect/video', fd).then(unwrap)
  },
  taskStatus: (taskId) => http.get(`/detect/task/${taskId}`).then(unwrap),
  saveVideoRecord: (taskId) => http.post(`/detect/video/${taskId}/save`).then(unwrap),
  videoStreamUrl: (taskId) => `${API_BASE}/detect/stream/video/${taskId}`,

  // ---------- 摄像头 ----------
  cameraStart: (payload) => http.post('/camera/start', payload).then(unwrap),
  cameraStop: (taskId) => http.post(`/camera/stop/${taskId}`).then(unwrap),
  saveCameraRecord: (taskId) => http.post(`/camera/${taskId}/save`).then(unwrap),
  cameraStreamUrl: (taskId) => `${API_BASE}/detect/stream/camera/${taskId}`,

  // ---------- AI ----------
  advice: (payload) => http.post('/ai/advice', payload).then(unwrap),

  // ---------- 记录 ----------
  records: (params) => http.get('/records', { params }).then(unwrap),
  record: (id) => http.get(`/records/${id}`).then(unwrap),
  deleteRecord: (id) => http.delete(`/records/${id}`).then(unwrap),
  clearRecords: () => http.delete('/records').then(unwrap),
  recordAdvice: (id, payload) => http.post(`/records/${id}/advice`, payload || {}).then(unwrap),
  recordStats: () => http.get('/records/stats').then(unwrap),
  reportUrl: (id) => `${API_BASE}/records/${id}/report`
}

export default http
