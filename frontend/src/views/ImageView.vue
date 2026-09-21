<template>
  <div>
    <div class="grid-2">
      <div class="panel">
        <div class="panel-title">
          <span>① 上传图片</span>
          <el-button size="small" type="primary" :loading="loading" :disabled="!file" @click="runDetect">
            开始检测
          </el-button>
        </div>
        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="image/*"
          :on-change="onFileChange"
        >
          <el-icon :size="40"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽图片到此处，或<em>点击选择</em></div>
          <template #tip>
            <div class="muted" style="margin-top: 8px">支持 jpg / png / bmp / webp</div>
          </template>
        </el-upload>

        <div style="margin-top: 14px">
          <div class="muted" style="margin-bottom: 6px">原图预览</div>
          <div class="preview-box">
            <img v-if="originUrl" :src="originUrl" alt="原图" />
            <span v-else class="muted">尚未选择图片</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>② 检测结果</span>
          <el-tag v-if="result" size="small">耗时 {{ result.elapsedMs }} ms</el-tag>
        </div>
        <div class="preview-box">
          <img v-if="result?.outImage" :src="result.outImage" alt="检测结果" />
          <span v-else class="muted">检测结果将在此显示</span>
        </div>

        <div v-if="result" style="margin-top: 12px">
          <el-space wrap>
            <el-tag type="primary">检出 {{ result.count }} 个目标</el-tag>
            <el-tag v-for="(v, k) in result.stats?.per_class || {}" :key="k" type="info" size="small">
              {{ k }}：{{ v }}
            </el-tag>
          </el-space>

          <el-table :data="result.labels || []" size="small" max-height="220" style="margin-top: 10px">
            <el-table-column prop="label" label="行为类别" width="110" />
            <el-table-column prop="confidence" label="置信度" width="100">
              <template #default="{ row }">{{ row.confidence.toFixed(3) }}</template>
            </el-table-column>
            <el-table-column label="位置">
              <template #default="{ row }">{{ row.box.join(', ') }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-title">③ 类别统计</div>
        <BarChart :data="result?.stats?.per_class || {}" title="检出数量" />
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>④ AI 智能建议</span>
          <el-space>
            <el-select v-model="provider" size="small" style="width: 130px">
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="Qwen" value="qwen" />
            </el-select>
            <el-button size="small" type="success" :loading="adviceLoading" :disabled="!result" @click="getAdvice">
              生成建议
            </el-button>
            <el-button size="small" type="warning" :disabled="!result?.recordId" @click="exportPdf">
              导出 PDF
            </el-button>
          </el-space>
        </div>
        <el-input
          v-model="advice"
          type="textarea"
          :rows="9"
          readonly
          placeholder="点击“生成建议”后，由 DeepSeek / Qwen 输出课堂表现分析与教学建议"
        />
        <div v-if="adviceProvider" class="muted" style="margin-top: 6px">
          生成方：{{ adviceProvider }} <span v-if="adviceFallback">（本地规则引擎兜底，未配置 API Key）</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { api } from '@/api'
import BarChart from '@/components/BarChart.vue'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()

const file = ref(null)
const originUrl = ref('')
const result = ref(null)
const loading = ref(false)
const advice = ref('')
const adviceLoading = ref(false)
const adviceProvider = ref('')
const adviceFallback = ref(false)
const provider = ref('deepseek')

function onFileChange(uploadFile) {
  file.value = uploadFile.raw
  if (originUrl.value) URL.revokeObjectURL(originUrl.value)
  originUrl.value = URL.createObjectURL(uploadFile.raw)
  result.value = null
  advice.value = ''
}

async function runDetect() {
  if (system.warnIfOffline()) return
  loading.value = true
  try {
    result.value = await api.detectImage(file.value)
    ElMessage.success(`检测完成，检出 ${result.value.count} 个目标`)
  } catch (e) {
    /* 错误已由拦截器提示 */
  } finally {
    loading.value = false
  }
}

async function getAdvice() {
  adviceLoading.value = true
  try {
    const res = await api.advice({
      stats: {
        total: result.value.count,
        per_class: result.value.stats?.per_class || {}
      },
      provider: provider.value
    })
    advice.value = res.content || '（无返回内容）'
    adviceProvider.value = res.provider || ''
    adviceFallback.value = !!res.fallback
  } finally {
    adviceLoading.value = false
  }
}

function exportPdf() {
  window.open(api.reportUrl(result.value.recordId), '_blank')
}
</script>
