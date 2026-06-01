<template>
  <div>
    <router-link to="/dashboard" class="back-link">&larr; 返回总览</router-link>

    <div v-if="error" class="card error-banner">
      <div class="error-content">
        <span class="error-icon">&#9888;</span>
        <span>{{ error }}</span>
        <button class="btn btn-sm btn-primary" @click="loadDevice" style="margin-left: auto">重试</button>
      </div>
    </div>

    <div v-if="notFound" class="card" style="text-align: center; padding: 40px">
      <div style="font-size: 48px; margin-bottom: 16px">&#128683;</div>
      <div style="font-size: 18px; margin-bottom: 8px">设备不存在</div>
      <div style="color: var(--text-secondary)">设备 ID {{ deviceId }} 未找到，可能已被删除</div>
      <router-link to="/dashboard" class="btn btn-primary" style="margin-top: 16px; display: inline-block; text-decoration: none">
        返回总览
      </router-link>
    </div>

    <div v-if="loading && !notFound" class="loading">正在加载设备数据...</div>

    <template v-if="device.id && !notFound">
      <div class="detail-header">
        <div>
          <h1>{{ device.name }}</h1>
          <div class="detail-meta">
            <span>类型: {{ device.device_type }}</span>
            <span>位置: {{ device.location }}</span>
            <span>安装日期: {{ device.install_date }}</span>
            <span :class="'badge badge-' + device.status">{{ statusLabel(device.status) }}</span>
          </div>
        </div>
        <div style="text-align: right">
          <div style="font-size: 14px; color: var(--text-secondary)">健康评分</div>
          <div style="font-size: 36px; font-weight: 700" :style="{ color: getHealthColor(device.health_score) }">
            {{ device.health_score?.toFixed(1) ?? '--' }}
          </div>
          <div v-if="rulData" style="font-size: 13px; color: var(--text-secondary); margin-top: 4px">
            预计剩余寿命: <strong>{{ rulData.estimated_rul_days?.toFixed(0) ?? '--' }}</strong> 天
          </div>
        </div>
      </div>

      <div class="charts-grid">
        <div class="card" v-for="st in sensorTypes" :key="st">
          <div class="card-title">
            {{ sensorLabel(st) }} 趋势
            <span v-if="anomalyStats[st]" style="font-size: 12px; font-weight: 400; color: var(--text-secondary); margin-left: 8px">
              ({{ anomalyStats[st].shown }}/{{ anomalyStats[st].total }} 个异常可见)
            </span>
          </div>
          <div v-if="sensorLoading[st]" class="loading" style="height: 200px; display: flex; align-items: center; justify-content: center">
            加载中...
          </div>
          <div v-else-if="!sensorData[st] || sensorData[st].length === 0" class="empty-sensor">
            <div style="color: var(--text-secondary); text-align: center; padding: 40px">
              该传感器暂无数据
            </div>
          </div>
          <SensorTrendChart v-else :readings="sensorData[st]" :anomalies="filteredAnomalies[st] || []" :sensor-type="st" />
        </div>

        <div class="card">
          <div class="card-title">RUL 预测曲线</div>
          <div v-if="!rulCurve.historical.length" class="empty-sensor">
            <div style="color: var(--text-secondary); text-align: center; padding: 40px">
              健康历史不足，暂无法生成预测
            </div>
          </div>
          <RulChart v-else :curve-data="rulCurve" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import SensorTrendChart from '../components/SensorTrendChart.vue'
import RulChart from '../components/RulChart.vue'

const route = useRoute()
const deviceId = route.params.id

const device = ref({})
const sensorTypes = ['temperature', 'vibration', 'current']
const sensorData = ref({})
const sensorLoading = ref({ temperature: true, vibration: true, current: true })
const allAnomalies = ref({})
const rulData = ref(null)
const rulCurve = ref({ historical: [], predicted: [], confidence_upper: [], confidence_lower: [], failure_threshold: 30 })
const loading = ref(true)
const error = ref(null)
const notFound = ref(false)
let refreshTimer = null

// Only show anomalies whose timestamps fall within the loaded readings window
const filteredAnomalies = computed(() => {
  const result = {}
  for (const st of sensorTypes) {
    const readings = sensorData.value[st] || []
    const anomalies = allAnomalies.value[st] || []
    if (!readings.length || !anomalies.length) {
      result[st] = []
      continue
    }
    const readingTimestamps = new Set(readings.map(r => r.timestamp))
    result[st] = anomalies.filter(a => readingTimestamps.has(a.detected_at))
  }
  return result
})

const anomalyStats = computed(() => {
  const stats = {}
  for (const st of sensorTypes) {
    const total = (allAnomalies.value[st] || []).length
    const shown = (filteredAnomalies.value[st] || []).length
    if (total > 0) {
      stats[st] = { total, shown }
    }
  }
  return stats
})

onMounted(() => {
  loadDevice()
  refreshTimer = setInterval(() => loadDevice(true), 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

async function loadDevice(silent = false) {
  if (!silent) loading.value = true
  error.value = null
  notFound.value = false

  try {
    const [deviceRes, anomalyRes, rulRes, rulCurveRes] = await Promise.all([
      api.getDevice(deviceId),
      api.getAnomalies(deviceId),
      api.getRul(deviceId),
      api.getRulCurve(deviceId),
    ])

    device.value = deviceRes.data
    rulData.value = rulRes.data
    rulCurve.value = rulCurveRes.data || rulCurve.value

    const anomalies = anomalyRes.data || []
    const anomalyMap = {}
    for (const a of anomalies) {
      if (!anomalyMap[a.sensor_type]) anomalyMap[a.sensor_type] = []
      anomalyMap[a.sensor_type].push(a)
    }
    allAnomalies.value = anomalyMap

    // Load sensor data in parallel
    await Promise.all(sensorTypes.map(async (st) => {
      sensorLoading.value[st] = true
      try {
        const res = await api.getSensorReadings(deviceId, st, 2000)
        sensorData.value[st] = (res.data || []).reverse()
      } catch {
        sensorData.value[st] = []
      } finally {
        sensorLoading.value[st] = false
      }
    }))
  } catch (e) {
    if (e.response?.status === 404) {
      notFound.value = true
    } else {
      error.value = e.userMessage || '加载设备数据失败'
    }
  } finally {
    loading.value = false
  }
}

function getHealthColor(score) {
  if (score == null) return 'var(--text-secondary)'
  if (score >= 80) return '#10b981'
  if (score >= 60) return '#f59e0b'
  if (score >= 40) return '#f97316'
  return '#ef4444'
}

function statusLabel(status) {
  const map = { active: '正常', warning: '预警', critical: '严重', offline: '离线' }
  return map[status] || status
}

function sensorLabel(type) {
  const map = { temperature: '温度 (°C)', vibration: '振动 (mm/s)', current: '电流 (A)' }
  return map[type] || type
}
</script>
