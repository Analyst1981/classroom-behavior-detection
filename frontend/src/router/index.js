import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '系统概览' } },
  { path: '/image', name: 'image', component: () => import('@/views/ImageView.vue'), meta: { title: '单图检测' } },
  { path: '/batch', name: 'batch', component: () => import('@/views/BatchView.vue'), meta: { title: '批量检测' } },
  { path: '/video', name: 'video', component: () => import('@/views/VideoView.vue'), meta: { title: '视频检测' } },
  { path: '/camera', name: 'camera', component: () => import('@/views/CameraView.vue'), meta: { title: '实时摄像头' } },
  { path: '/records', name: 'records', component: () => import('@/views/RecordsView.vue'), meta: { title: '检测记录' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} - 课堂行为智能检测系统`
})

export default router
