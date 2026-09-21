import { defineStore } from 'pinia'
import { api } from '@/api'
import { ElMessage } from 'element-plus'

export const useSystemStore = defineStore('system', {
  state: () => ({
    online: false,
    backend: false,
    engine: '',
    demoMode: false,
    weights: '',
    classes: [],
    modelInfo: null,
    aiServiceUrl: '',
    loading: false
  }),
  actions: {
    async refresh() {
      this.loading = true
      try {
        const status = await api.systemStatus()
        this.backend = status?.backend === 'ok'
        this.online = !!status?.aiServiceOnline
        this.aiServiceUrl = status?.aiServiceUrl || ''
        const model = status?.model || {}
        this.engine = model.engine || ''
        this.demoMode = !!model.demo_mode
        this.weights = model.weights || ''
        this.modelInfo = model
        if (!this.classes.length) {
          const cls = await api.classes().catch(() => null)
          this.classes = cls?.classes || model.classes || []
        }
      } catch (e) {
        this.online = false
      } finally {
        this.loading = false
      }
    },
    warnIfOffline() {
      if (!this.online) {
        ElMessage.warning('AI 推理服务未连接，请先启动 ai-service')
        return true
      }
      return false
    }
  }
})
