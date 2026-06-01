<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <h1 class="section-title" style="margin-bottom: 0">维护工单</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">+ 新建工单</button>
    </div>

    <div v-if="error" class="card error-banner" style="margin-bottom: 16px">
      <div class="error-content">
        <span class="error-icon">&#9888;</span>
        <span>{{ error }}</span>
        <button class="btn btn-sm btn-primary" @click="loadOrders" style="margin-left: auto">重试</button>
      </div>
    </div>

    <div class="filters">
      <select v-model="filterStatus" @change="resetAndLoad">
        <option value="">全部状态</option>
        <option value="open">待处理</option>
        <option value="assigned">已指派</option>
        <option value="in_progress">处理中</option>
        <option value="completed">已完成</option>
      </select>
      <select v-model="filterPriority" @change="resetAndLoad">
        <option value="">全部优先级</option>
        <option value="critical">紧急</option>
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
      <span v-if="totalCount > 0" style="font-size: 13px; color: var(--text-secondary); align-self: center">
        共 {{ totalCount }} 条
      </span>
    </div>

    <div class="card">
      <div v-if="loading" class="loading">加载中...</div>
      <template v-else>
        <table v-if="workorders.length > 0">
          <thead>
            <tr>
              <th>ID</th>
              <th>标题</th>
              <th>设备</th>
              <th>优先级</th>
              <th>状态</th>
              <th>触发方式</th>
              <th>指派</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="wo in workorders" :key="wo.id">
              <td>#{{ wo.id }}</td>
              <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap" :title="wo.title">
                {{ wo.title }}
              </td>
              <td>
                <router-link :to="`/devices/${wo.device_id}`" style="color: var(--accent)">
                  设备{{ wo.device_id }}
                </router-link>
              </td>
              <td><span :class="'badge badge-' + wo.priority">{{ priorityLabel(wo.priority) }}</span></td>
              <td><span :class="'badge badge-' + wo.status">{{ statusLabel(wo.status) }}</span></td>
              <td>{{ triggerLabel(wo.trigger_type) }}</td>
              <td>{{ wo.assigned_to || '--' }}</td>
              <td>{{ formatDate(wo.created_at) }}</td>
              <td>
                <button
                  v-if="wo.status !== 'completed' && wo.status !== 'cancelled'"
                  class="btn btn-sm btn-success"
                  @click="completeOrder(wo.id)"
                >完成</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else style="text-align: center; padding: 40px; color: var(--text-secondary)">暂无工单</div>
      </template>

      <div v-if="totalPages > 1" class="pagination">
        <button class="btn btn-sm" :disabled="page <= 1" @click="page--; loadOrders()">上一页</button>
        <span style="font-size: 13px; color: var(--text-secondary)">第 {{ page }} / {{ totalPages }} 页</span>
        <button class="btn btn-sm" :disabled="page >= totalPages" @click="page++; loadOrders()">下一页</button>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>新建维护工单</h3>
        <div v-if="formError" class="form-error">{{ formError }}</div>
        <div class="form-group">
          <label>设备ID <span class="required">*</span></label>
          <input v-model.number="newOrder.device_id" type="number" min="1" placeholder="设备ID">
        </div>
        <div class="form-group">
          <label>标题 <span class="required">*</span></label>
          <input v-model="newOrder.title" placeholder="工单标题" maxlength="200">
          <div class="char-count" v-if="newOrder.title.length > 150">{{ newOrder.title.length }}/200</div>
        </div>
        <div class="form-group">
          <label>描述</label>
          <textarea v-model="newOrder.description" placeholder="详细描述（可选）"></textarea>
        </div>
        <div class="form-group">
          <label>优先级</label>
          <select v-model="newOrder.priority">
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="critical">紧急</option>
          </select>
        </div>
        <div class="form-actions">
          <button class="btn" @click="closeModal">取消</button>
          <button class="btn btn-primary" @click="createOrder" :disabled="creating">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import apiClient from '../api'

const workorders = ref([])
const filterStatus = ref('')
const filterPriority = ref('')
const showCreateModal = ref(false)
const newOrder = ref({ device_id: null, title: '', description: '', priority: 'medium' })
const formError = ref(null)
const creating = ref(false)
const loading = ref(true)
const error = ref(null)
const page = ref(1)
const pageSize = 20
const totalCount = ref(0)

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize)))

onMounted(() => {
  loadOrders()
  loadCount()
})

function resetAndLoad() {
  page.value = 1
  loadOrders()
  loadCount()
}

async function loadOrders() {
  loading.value = true
  error.value = null
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterPriority.value) params.priority = filterPriority.value
    const res = await apiClient.getWorkOrders(params)
    workorders.value = res.data
  } catch (e) {
    error.value = e.userMessage || '加载工单失败'
  } finally {
    loading.value = false
  }
}

async function loadCount() {
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (filterPriority.value) params.priority = filterPriority.value
    const res = await apiClient.getWorkOrderCount(params)
    totalCount.value = res.data.count
  } catch { /* ignore count error */ }
}

function validateForm() {
  if (!newOrder.value.device_id || newOrder.value.device_id < 1) {
    formError.value = '请输入有效的设备ID'
    return false
  }
  if (!newOrder.value.title || !newOrder.value.title.trim()) {
    formError.value = '标题不能为空'
    return false
  }
  if (newOrder.value.title.trim().length > 200) {
    formError.value = '标题不能超过200字'
    return false
  }
  formError.value = null
  return true
}

async function createOrder() {
  if (!validateForm()) return
  creating.value = true
  try {
    await apiClient.createWorkOrder({
      ...newOrder.value,
      title: newOrder.value.title.trim(),
    })
    closeModal()
    resetAndLoad()
  } catch (e) {
    formError.value = e.userMessage || '创建失败'
  } finally {
    creating.value = false
  }
}

function closeModal() {
  showCreateModal.value = false
  formError.value = null
  newOrder.value = { device_id: null, title: '', description: '', priority: 'medium' }
}

async function completeOrder(id) {
  try {
    await apiClient.completeWorkOrder(id)
    loadOrders()
    loadCount()
  } catch (e) {
    error.value = e.userMessage || '操作失败'
  }
}

function priorityLabel(p) {
  const map = { critical: '紧急', high: '高', medium: '中', low: '低' }
  return map[p] || p
}

function statusLabel(s) {
  const map = { open: '待处理', assigned: '已指派', in_progress: '处理中', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}

function triggerLabel(t) {
  const map = { health_threshold: '健康阈值', rul_critical: 'RUL预警', anomaly_burst: '异常突增', manual: '人工' }
  return map[t] || t || '--'
}

function formatDate(d) {
  if (!d) return '--'
  return new Date(d).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>
