<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h1 class="section-title" style="margin-bottom: 0">设备总览</h1>
      <div class="auto-refresh-indicator" v-if="!error">
        <span class="refresh-dot" :class="{ active: refreshing }"></span>
        <span style="font-size: 12px; color: var(--text-secondary)">每30秒自动刷新</span>
      </div>
    </div>

    <div v-if="error" class="card error-banner">
      <div class="error-content">
        <span class="error-icon">&#9888;</span>
        <span>{{ error }}</span>
        <button class="btn btn-sm btn-primary" @click="loadAll" style="margin-left: auto">重试</button>
      </div>
    </div>

    <div v-if="loading && !devices.length" class="loading">正在加载设备数据...</div>

    <template v-if="!error">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ overview.total }}</div>
          <div class="stat-label">设备总数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: var(--success)">{{ overview.active }}</div>
          <div class="stat-label">运行正常</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: var(--warning)">{{ overview.warning }}</div>
          <div class="stat-label">预警设备</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" style="color: var(--danger)">{{ overview.critical }}</div>
          <div class="stat-label">严重告警</div>
        </div>
      </div>

      <div v-if="warningDevices.length > 0" class="card warning-list" style="margin-bottom: 24px;">
        <div class="card-title">&#9888; 预警设备 (置顶)</div>
        <div
          v-for="device in warningDevices"
          :key="device.id"
          class="warning-item"
          @click="$router.push(`/devices/${device.id}`)"
        >
          <div class="info">
            <div class="health" :style="{ color: getHealthColor(device.health_score) }">
              {{ device.health_score?.toFixed(0) ?? '--' }}
            </div>
            <div>
              <div style="font-weight: 500">{{ device.name }}</div>
              <div style="font-size: 12px; color: var(--text-secondary)">
                {{ device.location }} | {{ device.device_type }} |
                RUL: {{ device.rul_days ? device.rul_days.toFixed(0) + '天' : '--' }}
              </div>
            </div>
          </div>
          <span :class="'badge badge-' + device.status">{{ statusLabel(device.status) }}</span>
        </div>
      </div>

      <div class="card">
        <div class="card-title">设备健康度热力图 ({{ heatmapData.length }} 台设备)</div>
        <div v-if="heatmapData.length === 0 && !loading" style="text-align: center; padding: 20px; color: var(--text-secondary)">
          暂无设备数据
        </div>
        <div class="device-grid">
          <div
            v-for="device in heatmapData"
            :key="device.device_id"
            class="device-cell"
            :style="{ background: getHealthBg(device.health_score) }"
            @click="$router.push(`/devices/${device.device_id}`)"
          >
            <div class="name" :title="device.name">{{ device.name }}</div>
            <div class="score" :style="{ color: getHealthColor(device.health_score) }">
              {{ device.health_score.toFixed(0) }}
            </div>
            <div class="location">{{ device.location }}</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../api'

const overview = ref({ total: 0, active: 0, warning: 0, critical: 0, worst_devices: [] })
const heatmapData = ref([])
const devices = ref([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref(null)
let refreshTimer = null

const warningDevices = computed(() =>
  devices.value
    .filter(d => d.status === 'warning' || d.status === 'critical')
    .sort((a, b) => (a.health_score ?? 999) - (b.health_score ?? 999))
)

onMounted(() => {
  loadAll()
  refreshTimer = setInterval(() => {
    refreshing.value = true
    loadAll(true)
  }, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

async function loadAll(silent = false) {
  if (!silent) loading.value = true
  error.value = null
  try {
    const [overviewRes, heatmapRes, devicesRes] = await Promise.all([
      api.getDeviceOverview(),
      api.getHealthHeatmap(),
      api.getDevices(),
    ])
    overview.value = overviewRes.data
    heatmapData.value = heatmapRes.data
    devices.value = devicesRes.data
  } catch (e) {
    error.value = e.userMessage || '加载失败'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function getHealthColor(score) {
  if (score == null) return 'var(--text-secondary)'
  if (score >= 80) return '#10b981'
  if (score >= 60) return '#f59e0b'
  if (score >= 40) return '#f97316'
  return '#ef4444'
}

function getHealthBg(score) {
  if (score >= 80) return 'rgba(16, 185, 129, 0.1)'
  if (score >= 60) return 'rgba(245, 158, 11, 0.1)'
  if (score >= 40) return 'rgba(249, 115, 22, 0.1)'
  return 'rgba(239, 68, 68, 0.15)'
}

function statusLabel(status) {
  const map = { active: '正常', warning: '预警', critical: '严重', offline: '离线' }
  return map[status] || status
}
</script>
