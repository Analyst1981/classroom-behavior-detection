<template>
  <div>
    <div class="panel">
      <div class="panel-title">
        <span>① 上传视频并开始处理</span>
        <el-space>
          <el-button size="small" type="primary" :disabled="!file || running" @click="start">开始处理</el-button>
          <el-button size="small" type="danger" :disabled="!running" @click="stopWatch">停止跟随</el-button>
          <el-button size="small" type="success" :disabled="!task || task.status !== 'finished'" @click="saveRecord">
            保存记录
          </el-button>
        </el-space>
      </div>

      <el-upload drag :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="onFileChange">
        <el-icon :size="40"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽视频到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="muted" style="margin-top: 8px">支持 mp4 / avi / mov / mkv / flv / webm</div>
        </template>
      </el-upload>

      <div v-if="task" style="margin-top: 14px">
        <el-progress :percentage="Math.round(task.progress || 0)" :status="progressStatus" />
        <div class="muted" style="margin-top: 6px">
          状态：{{ statusText }} · 已处理 {{ task.processed || 0 }} / {{ task.totalFrames || 0 }} 帧 ·
          处理速率 {{ task.fps || 0 }} FPS
        </div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-title">② 实时检测流（MJPEG）</div>
        <img v-if="streamUrl" :src="streamUrl" class="stream-frame" alt="实时检测流" />
        <div v-else class="preview-box"><span class="muted">上传并开始处理后显示实时标注画面</span></div>
      </div>

      <div class="panel">
        <div class="panel-title">③ 处理结果与统计</div>
        <div v-if="task">
          <el-space wrap>
            <el-tag v-for="(v, k) in task.stats || {}" :key="k" type="info" size="small">{{ k }}：{{ v }}</el-tag>
            <span v-if="!Object.keys(task.stats || {}).length" class="muted">暂无统计</span>
          </el-space>
          <BarChart :data="task.stats || {}" title="累计检出（帧级）" :height="220" />
        </div>
        <div v-if="outputVideoUrl" style="margin-top: 12px">
          <div class="muted" style="margin-bottom: 6px">处理后视频（H.264 MP4）</div>
          <video :src="outputVideoUrl" controls class="stream-frame" style="background:#000"></video>
          <div class="muted" style="margin-top: 6px">文件：{{ task?.outputFile }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { api } from '@/api'
import BarChart from '@/components/BarChart.vue'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()

const file = ref(null)
const task = ref(null)
const running = ref(false)
const streamUrl = ref('')
const timer = ref(null)

const statusText = computed(
  () => ({ running: '处理中', finished: '已完成', error: '出错', stopped: '已停止' }[task.value?.status] || '未知')
)
const progressStatus = computed(() => {
  const s = task.value?.status
  if (s === 'finished') return 'success'
  if (s === 'error') return 'exception'
  return undefined
})
const outputVideoUrl = computed(() => {
  const url = task.value?.outputUrl
  return url ? `http://127.0.0.1:5000${url}` : ''
})

function onFileChange(uploadFile) {
  file.value = uploadFile.raw
  task.value = null
  streamUrl.value = ''
}

async function start() {
  if (system.warnIfOffline()) return
  try {
    const res = await api.detectVideo(file.value)
    task.value = { taskId: res.taskId, status: 'running', progress: 0 }
    streamUrl.value = api.videoStreamUrl(res.taskId)
    running.value = true
    startWatch()
    ElMessage.success('已提交视频处理任务')
  } catch (e) {
    /* 已提示 */
  }
}

function startWatch() {
  stopWatchTimer()
  timer.value = setInterval(async () => {
    try {
      const t = await api.taskStatus(task.value.taskId)
      task.value = t
      if (t.status === 'finished' || t.status === 'error' || t.status === 'stopped') {
        running.value = false
        stopWatchTimer()
        if (t.status === 'finished') ElMessage.success('视频处理完成')
      }
    } catch (e) {
      stopWatchTimer()
      running.value = false
    }
  }, 1000)
}

function stopWatch() {
  stopWatchTimer()
  running.value = false
}

function stopWatchTimer() {
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
}

async function saveRecord() {
  try {
    const res = await api.saveVideoRecord(task.value.taskId)
    ElMessage.success(`已保存记录 #${res.recordId}`)
  } catch (e) {
    /* 已提示 */
  }
}

onBeforeUnmount(() => {
  stopWatchTimer()
  if (task.value) api.cameraStop(task.value.taskId).catch(() => {})
})
</script>
