<template>
  <v-chart :option="chartOption" autoresize class="chart-container" />
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps({
  curveData: {
    type: Object,
    default: () => ({ historical: [], predicted: [], confidence_upper: [], confidence_lower: [], failure_threshold: 30 }),
  },
})

const chartOption = computed(() => {
  const historical = props.curveData.historical || []
  const predicted = props.curveData.predicted || []
  const confUpper = props.curveData.confidence_upper || []
  const confLower = props.curveData.confidence_lower || []
  const threshold = props.curveData.failure_threshold || 30

  const allDays = [
    ...historical.map(p => p.day),
    ...predicted.map(p => p.day),
  ]

  const historicalData = historical.map(p => [p.day, p.score])
  const predictedData = predicted.map(p => [p.day, p.score])
  const upperData = confUpper.map(p => [p.day, p.score])
  const lowerData = confLower.map(p => [p.day, p.score])

  return {
    backgroundColor: 'transparent',
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e293b',
      borderColor: '#475569',
      textStyle: { color: '#f1f5f9', fontSize: 12 },
      formatter: (params) => {
        const day = params[0]?.value?.[0]?.toFixed(0)
        let text = `Day ${day}<br/>`
        for (const p of params) {
          text += `${p.seriesName}: ${p.value[1]?.toFixed(1)}<br/>`
        }
        return text
      },
    },
    xAxis: {
      type: 'value',
      name: '天数',
      nameLocation: 'end',
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#475569' } },
      splitLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: {
      type: 'value',
      name: '健康分',
      min: 0,
      max: 100,
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#334155' } },
    },
    series: [
      {
        name: '历史健康分',
        type: 'line',
        data: historicalData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#3b82f6', width: 2 },
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: '预测趋势',
        type: 'line',
        data: predictedData,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#f59e0b', width: 2, type: 'dashed' },
      },
      {
        name: '置信上界',
        type: 'line',
        data: upperData,
        smooth: true,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
      },
      {
        name: '置信下界',
        type: 'line',
        data: lowerData,
        smooth: true,
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(245, 158, 11, 0.12)', origin: 'start' },
      },
      {
        name: '失效阈值',
        type: 'line',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#ef4444', type: 'dashed', width: 1.5 },
          data: [{ yAxis: threshold, label: { formatter: `失效阈值 (${threshold})`, color: '#ef4444', fontSize: 11 } }],
        },
        data: [],
      },
    ],
  }
})
</script>
