<template>
  <div>
    <div class="panel">
      <div class="panel-title">
        <span>① 摄像头设置</span>
        <el-space>
          <el-button size="small" type="primary" :loading="starting" :disabled="opened" @click="start">
            打开摄像头
          </el-button>
          <el-button size="small" type="danger" :disabled="!opened" @click="stop">关闭</el-button>
          <el-button size="small" type="success" :disabled="!opened" @click="saveRecord">保存本次检测</el-button>
        </el-space>
      </div>

      <el-space wrap>
        <span class="muted">摄像头索引</span>
        <el-input-number v-model="index" :min="0" :max="9" size="small" :disabled="opened" />
        <el-checkbox v-model="record" :disabled="opened">同时录制保存为 MP4</el-checkbox>
      </el-space>

      <div v-if="task" style="margin-top: 12px">
        <el-tag :type="task.status === 'error' ? 'danger' : 'success'" size="small">
          状态：{{ task.status }} · 已处理 {{ task.processed || 0 }} 帧
        </el-tag>
        <span v-if="task.error" class="muted" style="margin-left: 8px">{{ task.error }}</span>
      </div>

      <el-alert
        v-if="hint"
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 12px"
        :title="hint"
      />
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-title">② 实时画面</div>
        <img v-if="streamUrl" :src="streamUrl" class="stream-frame" alt="摄像头实时检测" />
        <div v-else class="preview-box"><span class="muted">点击“打开摄像头”后显示实时标注画面</span></div>
      </div>

      <div class="panel">
        <div class="panel-title">③ 实时统计</div>
        <el-empty v-if="!task || !Object.keys(task.stats || {}).length" description="暂无数据" />
        <template v-else>
          <el-space wrap>
            <el-tag v-for="(v, k) in task.stats" :key="k" type="info" size="small">{{ k }}：{{ v }}</el-tag>
          </el-space>
          <BarChart :data="task.stats" title="累计检出（帧级）" :height="240" />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import BarChart from '@/components/BarChart.vue'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()

const index = ref(0)
const record = ref(false)
const opened = ref(false)
const starting = ref(false)
const task = ref(null)
const streamUrl = ref('')
const timer = ref(null)

const hint = computed(() => {
  if (!opened.value) {
    return '摄像头需浏览器具备设备权限；页面通过 HTTPS 或 localhost 访问时方可调用本机摄像头。'
  }
  return ''
})

async function start() {
  if (system.warnIfOffline()) return
  starting.value = true
  try {
    const res = await api.cameraStart({ index: index.value, record: record.value })
    task.value = { taskId: res.taskId, status: 'running', stats: {} }
    streamUrl.value = api.cameraStreamUrl(res.taskId)
    opened.value = true
    startWatch()
    ElMessage.success('摄像头已打开')
  } catch (e) {
    /* 已提示 */
  } finally {
    starting.value = false
  }
}

function startWatch() {
  stopWatchTimer()
  timer.value = setInterval(async () => {
    try {
      const t = await api.taskStatus(task.value.taskId)
      task.value = t
      if (t.status === 'error' || t.status === 'stopped') {
        stopWatchTimer()
        if (t.status === 'error') ElMessage.error(t.error || '摄像头异常')
      }
    } catch (e) {
      stopWatchTimer()
    }
  }, 1500)
}

async function stop() {
  if (!task.value) return
  try {
    await api.cameraStop(task.value.taskId)
    stopWatchTimer()
    opened.value = false
    streamUrl.value = ''
    ElMessage.info('摄像头已关闭')
  } catch (e) {
    /* 已提示 */
  }
}

async function saveRecord() {
  try {
    const res = await api.saveCameraRecord(task.value.taskId)
    ElMessage.success(`已保存记录 #${res.recordId}`)
  } catch (e) {
    /* 已提示 */
  }
}

function stopWatchTimer() {
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
}

onBeforeUnmount(() => {
  stopWatchTimer()
  if (opened.value && task.value) api.cameraStop(task.value.taskId).catch(() => {})
})
</script>
