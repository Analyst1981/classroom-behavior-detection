<template>
  <div>
    <div class="grid-3">
      <div class="panel">
        <div class="panel-title">服务状态</div>
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item label="后端服务">
            <el-tag :type="system.backend ? 'success' : 'danger'" size="small">
              {{ system.backend ? '运行中 (8080)' : '未连接' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="AI 推理服务">
            <el-tag :type="system.online ? 'success' : 'danger'" size="small">
              {{ system.online ? '运行中 (5000)' : '未连接' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="推理引擎">
            <el-tag :type="system.engine === 'ultralytics' ? 'success' : 'warning'" size="small">
              {{ system.engine || '-' }}
            </el-tag>
            <el-tag v-if="system.demoMode" type="warning" size="small" style="margin-left: 6px">演示模式</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="权重">{{ system.weights || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="panel">
        <div class="panel-title">检测能力</div>
        <div style="margin-bottom: 10px">
          <el-tag v-for="c in system.classes" :key="c" type="info" size="small" style="margin: 0 6px 6px 0">
            {{ c }}
          </el-tag>
          <span v-if="!system.classes.length" class="muted">未获取到类别</span>
        </div>
        <el-alert
          v-if="system.demoMode"
          type="warning"
          :closable="false"
          show-icon
          title="当前为演示引擎"
          description="未检测到课堂行为专用权重（models/best.pt）。可用 python train.py 训练并放入 models/ 目录后重启 AI 服务，即切换为真实检测。"
        />
        <el-alert
          v-else
          type="success"
          :closable="false"
          show-icon
          title="真实推理模式"
          description="已加载 YOLO 权重，检测结果来自模型推理。"
        />
      </div>

      <div class="panel">
        <div class="panel-title">检测统计</div>
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item label="记录总数">{{ stats.totalRecords || 0 }}</el-descriptions-item>
          <el-descriptions-item label="累计目标数">{{ stats.totalDetections || 0 }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 12px">
          <el-table :data="stats.byType || []" size="small" max-height="180">
            <el-table-column prop="taskType" label="类型" width="90" />
            <el-table-column prop="records" label="记录数" width="80" />
            <el-table-column prop="detections" label="目标数" />
          </el-table>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-title">使用流程</div>
      <el-steps :active="4" finish-status="success" align-center>
        <el-step title="上传素材" description="图片 / 文件夹 / 视频 / 摄像头" />
        <el-step title="YOLO 检测" description="6 类课堂行为识别" />
        <el-step title="AI 分析" description="DeepSeek / Qwen 生成建议" />
        <el-step title="导出报告" description="记录管理 + PDF 报告" />
      </el-steps>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '@/api'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()
const stats = ref({ byType: [], totalRecords: 0, totalDetections: 0 })

onMounted(async () => {
  try {
    stats.value = await api.recordStats()
  } catch (e) {
    /* 后端未就绪时保持默认值 */
  }
})
</script>
