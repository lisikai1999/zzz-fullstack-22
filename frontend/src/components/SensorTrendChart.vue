<template>
  <div v-if="props.readings.length === 0" style="text-align: center; padding: 40px; color: var(--text-secondary)">
    暂无传感器数据
  </div>
  <v-chart v-else :option="chartOption" autoresize class="chart-container" />
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, ScatterChart, GridComponent, TooltipComponent, DataZoomComponent, MarkLineComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  readings: { type: Array, default: () => [] },
  anomalies: { type: Array, default: () => [] },
  sensorType: { type: String, default: '' },
})

const chartOption = computed(() => {
  const timestamps = props.readings.map(r => r.timestamp)
  const values = props.readings.map(r => r.value)
  const timestampSet = new Set(timestamps)

  // Match anomalies by exact timestamp and build colored scatter points
  const anomalyPoints = []
  const anomalyItemColors = []
  const severityColors = { low: '#f59e0b', medium: '#f97316', high: '#ef4444' }

  for (const a of props.anomalies) {
    if (timestampSet.has(a.detected_at)) {
      const idx = timestamps.indexOf(a.detected_at)
      if (idx >= 0) {
        anomalyPoints.push([idx, a.value])
        anomalyItemColors.push(severityColors[a.severity] || '#ef4444')
      }
    }
  }

  return {
    backgroundColor: 'transparent',
    grid: { left: 55, right: 20, top: 30, bottom: 60 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e293b',
      borderColor: '#475569',
      textStyle: { color: '#f1f5f9', fontSize: 12 },
      formatter: (params) => {
        if (!params.length) return ''
        const ts = params[0].axisValue
        const d = new Date(ts)
        const dateStr = `${d.getFullYear()}/${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:00`
        let text = `<div style="font-size:11px;color:#94a3b8;margin-bottom:4px">${dateStr}</div>`
        for (const p of params) {
          if (p.seriesType === 'scatter') {
            text += `<div style="color:${p.color}">&#9679; 异常: ${p.value[1]?.toFixed(2)}</div>`
          } else {
            text += `<div style="color:${p.color}">&#9679; 数值: ${p.value?.toFixed?.(2) ?? p.value}</div>`
          }
        }
        return text
      },
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (val) => {
          const d = new Date(val)
          return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:00`
        },
      },
      axisLine: { lineStyle: { color: '#475569' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#334155' } },
    },
    dataZoom: [
      { type: 'inside', start: 60, end: 100 },
      { type: 'slider', start: 60, end: 100, height: 20, bottom: 8, borderColor: '#475569', fillerColor: 'rgba(59,130,246,0.2)', textStyle: { color: '#94a3b8' } },
    ],
    series: [
      {
        name: '传感器值',
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#3b82f6', width: 1.5 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(59,130,246,0.12)' },
          { offset: 1, color: 'rgba(59,130,246,0)' },
        ]}},
      },
      {
        name: '异常点',
        type: 'scatter',
        data: anomalyPoints,
        symbolSize: 12,
        itemStyle: {
          color: (params) => anomalyItemColors[params.dataIndex] || '#ef4444',
          borderColor: '#fff',
          borderWidth: 1.5,
          shadowColor: 'rgba(239, 68, 68, 0.4)',
          shadowBlur: 6,
        },
        z: 10,
      },
    ],
  }
})
</script>
