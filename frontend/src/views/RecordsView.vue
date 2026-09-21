<template>
  <div class="panel">
    <div class="panel-title">
      <span>检测记录</span>
      <el-space>
        <el-select v-model="type" size="small" style="width: 130px" placeholder="全部类型" clearable @change="load">
          <el-option label="单图" value="IMAGE" />
          <el-option label="批量" value="BATCH" />
          <el-option label="视频" value="VIDEO" />
          <el-option label="摄像头" value="CAMERA" />
        </el-select>
        <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
        <el-button size="small" type="danger" plain @click="clearAll">清空</el-button>
      </el-space>
    </div>

    <el-table :data="rows" v-loading="loading" size="small" @row-click="openDetail">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="taskType" label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="typeTag(row.taskType)">{{ typeText(row.taskType) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sourceName" label="来源" min-width="160" show-overflow-tooltip />
      <el-table-column prop="count" label="目标数" width="90" />
      <el-table-column prop="elapsedMs" label="耗时(ms)" width="100" />
      <el-table-column prop="engine" label="引擎" width="110" />
      <el-table-column prop="createdAt" label="创建时间" width="170" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="openDetail(row)">详情</el-button>
          <el-button link type="success" size="small" @click.stop="genAdvice(row)">AI 建议</el-button>
          <el-button link type="warning" size="small" @click.stop="exportPdf(row)">PDF</el-button>
          <el-button link type="danger" size="small" @click.stop="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      style="margin-top: 12px; justify-content: flex-end"
      layout="total, sizes, prev, pager, next"
      :total="total"
      v-model:current-page="page"
      v-model:page-size="size"
      :page-sizes="[10, 20, 50]"
      @current-change="load"
      @size-change="load"
    />

    <el-drawer v-model="detailVisible" :title="`记录 #${current?.id || ''} 详情`" size="46%">
      <div v-if="current">
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item label="类型">{{ typeText(current.taskType) }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ current.sourceName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="目标数">{{ current.count }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ current.elapsedMs }} ms</el-descriptions-item>
          <el-descriptions-item label="引擎">{{ current.engine || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ current.createdAt }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 14px">
          <div class="muted" style="margin-bottom: 6px">结果图</div>
          <div class="preview-box">
            <img v-if="current.outUrl" :src="`http://127.0.0.1:5000${current.outUrl}`" alt="结果图" />
            <span v-else class="muted">该记录无结果图</span>
          </div>
        </div>

        <div style="margin-top: 14px">
          <div class="muted" style="margin-bottom: 6px">类别统计</div>
          <BarChart :data="parseJson(current.perClass)" title="检出数量" :height="220" />
        </div>

        <div style="margin-top: 14px">
          <div class="muted" style="margin-bottom: 6px">AI 建议</div>
          <el-input :model-value="current.advice || '（未生成）'" type="textarea" :rows="8" readonly />
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '@/api'
import BarChart from '@/components/BarChart.vue'

const rows = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const type = ref('')
const loading = ref(false)
const detailVisible = ref(false)
const current = ref(null)

const typeText = (t) => ({ IMAGE: '单图', BATCH: '批量', VIDEO: '视频', CAMERA: '摄像头' }[t] || t || '-')
const typeTag = (t) => ({ IMAGE: 'primary', BATCH: 'success', VIDEO: 'warning', CAMERA: 'danger' }[t] || 'info')

function parseJson(s) {
  if (!s) return {}
  try {
    return JSON.parse(s)
  } catch (e) {
    return {}
  }
}

async function load() {
  loading.value = true
  try {
    const res = await api.records({ page: page.value - 1, size: size.value, type: type.value })
    rows.value = res.content || []
    total.value = res.total || 0
  } catch (e) {
    /* 已提示 */
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  try {
    current.value = await api.record(row.id)
    detailVisible.value = true
  } catch (e) {
    /* 已提示 */
  }
}

async function genAdvice(row) {
  try {
    const res = await api.recordAdvice(row.id)
    ElMessage.success(`建议已生成（${res.provider || 'unknown'}${res.fallback ? '，本地兜底' : ''}）`)
    load()
  } catch (e) {
    /* 已提示 */
  }
}

function exportPdf(row) {
  window.open(api.reportUrl(row.id), '_blank')
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除记录 #${row.id}？`, '提示', { type: 'warning' })
  await api.deleteRecord(row.id)
  ElMessage.success('已删除')
  load()
}

async function clearAll() {
  await ElMessageBox.confirm('确认清空全部检测记录？该操作不可恢复。', '警告', { type: 'warning' })
  await api.clearRecords()
  ElMessage.success('已清空')
  load()
}

onMounted(load)
</script>
