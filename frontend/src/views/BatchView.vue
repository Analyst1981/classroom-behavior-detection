<template>
  <div>
    <div class="panel">
      <div class="panel-title">
        <span>① 选择图片文件夹 / 多张图片</span>
        <el-space>
          <el-button size="small" type="primary" :loading="loading" :disabled="!files.length" @click="runDetect">
            批量检测
          </el-button>
          <el-button size="small" :disabled="!files.length" @click="clearFiles">清空</el-button>
        </el-space>
      </div>

      <el-space wrap>
        <el-button size="small" :icon="FolderOpened" @click="pickFolder">选择图片文件夹（JSZip 打包上传）</el-button>
        <el-button size="small" :icon="Picture" @click="pickFiles">选择多张图片</el-button>
      </el-space>
      <input ref="folderInput" type="file" webkitdirectory multiple hidden @change="onFolderChange" />
      <input ref="fileInput" type="file" accept="image/*" multiple hidden @change="onFilesChange" />

      <div class="muted" style="margin-top: 10px">已选择 {{ files.length }} 个文件</div>

      <div style="margin-top: 10px">
        <el-progress v-if="loading" :percentage="100" :indeterminate="true" :duration="2" />
      </div>
    </div>

    <div v-if="result" class="panel">
      <div class="panel-title">
        <span>② 批量结果</span>
        <el-space>
          <el-tag type="primary">图片 {{ result.totalImages }} 张</el-tag>
          <el-tag type="success">目标 {{ result.totalDetections }} 个</el-tag>
          <el-tag type="info">耗时 {{ result.elapsedMs }} ms</el-tag>
          <el-button size="small" type="warning" @click="exportPdf">导出 PDF</el-button>
        </el-space>
      </div>

      <div class="grid-2">
        <BarChart :data="result.perClass || {}" title="合计类别分布" />
        <div>
          <el-table :data="result.results || []" size="small" max-height="260">
            <el-table-column prop="fileName" label="文件" min-width="140" show-overflow-tooltip />
            <el-table-column prop="count" label="目标数" width="90" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="preview(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div style="margin-top: 12px">
        <div class="muted" style="margin-bottom: 6px">结果预览</div>
        <div class="preview-box">
          <img v-if="current" :src="current" alt="结果预览" />
          <span v-else class="muted">点击“查看”预览单张结果</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened, Picture } from '@element-plus/icons-vue'
import { api } from '@/api'
import BarChart from '@/components/BarChart.vue'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()

const files = ref([])
const folderInput = ref(null)
const fileInput = ref(null)
const result = ref(null)
const loading = ref(false)
const current = ref('')

function pickFolder() {
  folderInput.value?.click()
}

function pickFiles() {
  fileInput.value?.click()
}

function onFolderChange(e) {
  const picked = Array.from(e.target.files || []).filter((f) => f.type.startsWith('image/'))
  if (!picked.length) {
    ElMessage.warning('所选文件夹中未找到图片')
    return
  }
  files.value = picked
  ElMessage.success(`已选择 ${picked.length} 张图片`)
}

function onFilesChange(e) {
  const picked = Array.from(e.target.files || [])
  files.value = picked
}

function clearFiles() {
  files.value = []
  result.value = null
  current.value = ''
}

async function runDetect() {
  if (system.warnIfOffline()) return
  loading.value = true
  try {
    // 文件夹选择（含 webkitRelativePath）走 JSZip 打包，保留目录结构
    const hasDir = files.value.some((f) => f.webkitRelativePath)
    result.value = hasDir ? await api.detectBatchZip(files.value) : await api.detectBatch(files.value)
    ElMessage.success(`批量检测完成：${result.value.totalImages} 张 / ${result.value.totalDetections} 个目标`)
  } finally {
    loading.value = false
  }
}

function preview(row) {
  current.value = row.outImage || row.outUrl
}

function exportPdf() {
  if (!result.value?.recordId) {
    ElMessage.warning('暂无可导出的记录')
    return
  }
  window.open(api.reportUrl(result.value.recordId), '_blank')
}
</script>
