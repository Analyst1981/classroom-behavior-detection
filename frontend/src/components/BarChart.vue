<template>
  <div ref="chartRef" :style="{ height: height + 'px', width: '100%' }"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  height: { type: Number, default: 260 },
  title: { type: String, default: '类别分布' }
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const keys = Object.keys(props.data || {})
  chart.setOption(
    {
      title: { text: props.title, textStyle: { fontSize: 13, color: '#1f4e79' } },
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: keys, axisLabel: { interval: 0, fontSize: 11 } },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        {
          type: 'bar',
          barWidth: '45%',
          itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', fontSize: 11 },
          data: keys.map((k) => props.data[k])
        }
      ]
    },
    true
  )
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})

function resize() {
  if (chart) chart.resize()
}

watch(() => props.data, render, { deep: true })
</script>
