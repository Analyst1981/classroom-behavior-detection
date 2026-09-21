<template>
  <el-container class="app-shell">
    <el-aside width="216px" class="app-aside">
      <div class="brand">
        <el-icon :size="20"><View /></el-icon>
        <span>课堂行为检测</span>
      </div>
      <el-menu :default-active="route.path" router class="app-menu">
        <el-menu-item index="/"><el-icon><DataAnalysis /></el-icon><span>系统概览</span></el-menu-item>
        <el-menu-item index="/image"><el-icon><Picture /></el-icon><span>单图检测</span></el-menu-item>
        <el-menu-item index="/batch"><el-icon><Files /></el-icon><span>批量检测</span></el-menu-item>
        <el-menu-item index="/video"><el-icon><VideoCamera /></el-icon><span>视频检测</span></el-menu-item>
        <el-menu-item index="/camera"><el-icon><Camera /></el-icon><span>实时摄像头</span></el-menu-item>
        <el-menu-item index="/records"><el-icon><Tickets /></el-icon><span>检测记录</span></el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-title">{{ route.meta.title || '课堂行为智能检测系统' }}</div>
        <div class="header-status">
          <el-tag :type="system.online ? 'success' : 'danger'" effect="dark" size="small">
            AI 服务 {{ system.online ? '在线' : '离线' }}
          </el-tag>
          <el-tag :type="system.engine === 'ultralytics' ? 'success' : 'warning'" size="small">
            引擎 {{ system.engine || '未知' }}
          </el-tag>
          <el-tag v-if="system.demoMode" type="warning" size="small">演示模式</el-tag>
          <el-button size="small" text :icon="Refresh" @click="system.refresh()">刷新</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { useSystemStore } from '@/stores/system'

const route = useRoute()
const system = useSystemStore()

onMounted(() => system.refresh())
</script>

<style scoped>
.app-shell {
  height: 100vh;
}
.app-aside {
  background: #fff;
  border-right: 1px solid #ebeef5;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 60px;
  padding: 0 18px;
  font-size: 16px;
  font-weight: 600;
  color: #1f4e79;
  border-bottom: 1px solid #ebeef5;
}
.app-menu {
  border-right: none;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
}
.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
}
.app-main {
  background: #f5f7fa;
}
</style>
