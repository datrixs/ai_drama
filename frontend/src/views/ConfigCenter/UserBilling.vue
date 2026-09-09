<template>
  <div class="billing-page">
    <div class="section-header">
      <h2 class="section-title">积分使用记录</h2>
    </div>

    <div class="content-area">
      <div class="content-inner">
        <div class="summary-cards" v-loading="summaryLoading">
          <div class="summary-card">
            <p class="summary-label">总调用次数</p>
            <p class="summary-value">{{ summary.total_calls }}</p>
          </div>
          <div class="summary-card">
            <p class="summary-label">成功 / 失败</p>
            <p class="summary-value">
              <span class="text-green">{{ summary.success_calls }}</span>
              <span class="text-divider">/</span>
              <span class="text-red">{{ summary.failed_calls }}</span>
            </p>
          </div>
          <div class="summary-card">
            <p class="summary-label">总积分消耗</p>
            <p class="summary-value">{{ summary.total_point != null ? formatBalance(summary.total_point) : '-' }}</p>
          </div>
          <div class="summary-card">
            <p class="summary-label">平均耗时</p>
            <p class="summary-value">{{ summary.avg_latency_ms ? summary.avg_latency_ms + 'ms' : '-' }}</p>
          </div>
        </div>

        <div class="filter-bar">
          <div class="filter-left">
            <el-select
              v-model="filters.user_id"
              placeholder="用户"
              clearable
              size="default"
              class="filter-select"
            >
              <el-option
                v-for="u in userOptions"
                :key="u.id"
                :label="u.username"
                :value="u.id"
              />
            </el-select>
            <el-select
              v-model="filters.project_id"
              placeholder="项目"
              clearable
              size="default"
              class="filter-select"
              filterable
            >
              <el-option
                v-for="p in projectOptions"
                :key="p.id"
                :label="p.title"
                :value="p.id"
              />
            </el-select>
            <el-select
              v-model="filters.model_provider"
              placeholder="供应商"
              clearable
              size="default"
              class="filter-select"
              @change="handleProviderChange"
            >
              <el-option
                v-for="p in providerOptions"
                :key="p.value"
                :label="p.label"
                :value="p.value"
              />
            </el-select>
            <el-select
              v-model="filters.model_name"
              placeholder="模型"
              clearable
              size="default"
              class="filter-select"
              filterable
              :loading="modelLoading"
            >
              <el-option
                v-for="m in modelOptions"
                :key="m.model_name"
                :label="m.name"
                :value="m.model_name"
              />
            </el-select>
            <el-select
              v-model="filters.response_status"
              placeholder="状态"
              clearable
              size="default"
              class="filter-select-sm"
            >
              <el-option label="成功" :value="200" />
              <el-option label="失败" :value="0" />
            </el-select>
          </div>
          <button class="search-btn" @click="handleSearch">
            <el-icon :size="14"><Search /></el-icon>
            搜索
          </button>
        </div>

        <div v-loading="loading" class="table-wrapper">
          <el-table
            :data="records"
            height="100%"
            style="width: 100%"
            size="default"
            empty-text="暂无扣费记录"
            :header-cell-style="{ background: 'rgba(245,247,250,0.6)', fontWeight: 500 }"
          >
            <el-table-column prop="username" label="用户" width="100">
              <template #default="{ row }">
                {{ row.username || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="project_title" label="项目" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.project_title || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="call_time" label="调用时间" min-width="160">
              <template #default="{ row }">
                {{ formatDateTime(row.call_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="model_provider" label="供应商" width="120">
              <template #default="{ row }">
                <span class="provider-tag">{{ row.model_provider_name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="model_name" label="模型" min-width="300" show-overflow-tooltip />
            <el-table-column prop="response_status" label="状态" width="110" align="center">
              <template #default="{ row }">
                <span :class="row.response_status === 200 ? 'status-success' : 'status-fail'">
                  {{ row.response_status === 200 ? '成功' : '失败' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="point" label="消耗积分" width="110" align="left">
              <template #default="{ row }">
                {{ row.point != null ? formatBalance(row.point) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="remaining_point" label="剩余积分" width="110" align="left">
              <template #default="{ row }">
                {{ row.remaining_point != null ? formatBalance(row.remaining_point) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="latency_ms" label="耗时" width="90" align="right">
              <template #default="{ row }">
                {{ row.latency_ms ? row.latency_ms + 'ms' : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="primary" text size="small" @click="openDetail(row)">
                  详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="pagination.total_count > 0" class="pagination-bar">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.size"
            :total="pagination.total_count"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            background
            @current-change="loadRecords"
            @size-change="handleSizeChange"
          />
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="detailVisible" class="glass-overlay" @click.self="detailVisible = false">
        <div class="glass-surface-modal" style="max-width: 680px; width: 90%; display: flex; flex-direction: column;">
          <div class="modal-header">
            <h3 class="modal-title">调用详情</h3>
            <button class="modal-close-btn" @click="detailVisible = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div class="modal-body">
            <div v-if="detailData" class="detail-body">
        <div class="detail-section">
          <h4 class="detail-section-title">调用信息</h4>
          <div class="detail-desc-list">
            <div class="detail-row">
              <span class="detail-label">调用时间</span>
              <span class="detail-value">{{ formatDateTime(detailData.call_time) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">供应商</span>
              <span class="detail-value"><span class="provider-tag">{{ detailData.model_provider }}</span></span>
            </div>
            <div class="detail-row">
              <span class="detail-label">模型</span>
              <span class="detail-value detail-value-mono">{{ detailData.model_name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">状态</span>
              <span class="detail-value">
                <span
                  class="status-badge"
                  :class="detailData.response_status === 200 ? 'status-badge-success' : 'status-badge-fail'"
                >
                  {{ detailData.response_status === 200 ? '成功' : '失败' }}
                  {{ detailData.response_status }}
                </span>
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">耗时</span>
              <span class="detail-value">{{ detailData.latency_ms ? detailData.latency_ms + 'ms' : '-' }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4 class="detail-section-title">积分用量</h4>
          <div class="detail-desc-list">
            <div class="detail-row">
              <span class="detail-label">消耗积分</span>
              <span class="detail-value" style="font-size: 18px; font-weight: 600;">{{ detailData.point != null ? formatBalance(detailData.point) : '-' }}</span>
            </div>
          </div>
        </div>

        <div v-if="detailData.is_retry || detailData.error_message" class="detail-section">
          <h4 class="detail-section-title">异常信息</h4>
          <div class="detail-desc-list">
            <div v-if="detailData.is_retry" class="detail-row">
              <span class="detail-label">重试</span>
              <span class="detail-value">
                第 {{ detailData.retry_count }} 次 / 上限 {{ detailData.max_retries }} 次
              </span>
            </div>
            <div v-if="detailData.error_message" class="detail-row">
              <span class="detail-label">错误</span>
              <span class="detail-value text-red">{{ detailData.error_message }}</span>
            </div>
          </div>
        </div>

        <div v-if="detailData.request_body" class="detail-section">
          <div class="detail-section-header" @click="toggleSection('request')">
            <h4 class="detail-section-title">请求体</h4>
            <el-icon class="section-toggle-icon" :class="{ 'is-expanded': expandedSections.request }">
              <ArrowRight />
            </el-icon>
          </div>
          <el-collapse-transition>
            <div v-show="expandedSections.request">
              <pre class="detail-json">{{ JSON.stringify(detailData.request_body, null, 2) }}</pre>
            </div>
          </el-collapse-transition>
        </div>

        <div v-if="detailData.response_body" class="detail-section">
          <div class="detail-section-header" @click="toggleSection('response')">
            <h4 class="detail-section-title">响应体</h4>
            <el-icon class="section-toggle-icon" :class="{ 'is-expanded': expandedSections.response }">
              <ArrowRight />
            </el-icon>
          </div>
          <el-collapse-transition>
            <div v-show="expandedSections.response">
              <pre class="detail-json">{{ JSON.stringify(detailData.response_body, null, 2) }}</pre>
            </div>
          </el-collapse-transition>
        </div>
      </div>
          </div>
          <div class="modal-footer">
            <button class="glass-btn-secondary glass-btn-base" @click="detailVisible = false">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Search, ArrowRight } from '@element-plus/icons-vue'
import { getModelCallLogs, getModelCallLogSummary, getModelCallLogDetail } from '@/api/modelCallLog'
import { getUserInfo } from '@/api/user'
import { getSubUsers } from '@/api/subUser'
import { getAiProviderList } from '@/api/aiProvider'
import { getModelOptions } from '@/api/aiModel'
import request from '@/utils/request'
import { formatBalance } from '@/utils/format'

const loading = ref(false)
const summaryLoading = ref(false)
const records = ref([])
const userOptions = ref([])
const projectOptions = ref([])
const providerOptions = ref([])
const modelOptions = ref([])
const modelLoading = ref(false)

const summary = reactive({
  total_calls: 0,
  success_calls: 0,
  failed_calls: 0,
  total_tokens: 0,
  avg_latency_ms: null,
})

const pagination = reactive({
  page: 1,
  size: 20,
  total_count: 0,
})

const filters = reactive({
  user_id: '',
  project_id: '',
  model_provider: '',
  model_name: '',
  response_status: null,
})

const detailVisible = ref(false)
const detailData = ref(null)
const expandedSections = reactive({
  request: false,
  response: false,
})

const tokenInputPercent = computed(() => {
  if (!detailData.value || !detailData.value.total_tokens) return 50
  return Math.round((detailData.value.input_tokens / detailData.value.total_tokens) * 100)
})

function toggleSection(key) {
  expandedSections[key] = !expandedSections[key]
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatNumber(num) {
  if (!num && num !== 0) return '-'
  return num.toLocaleString()
}

function buildParams() {
  const params = {
    page: pagination.page,
    size: pagination.size,
    user_id: filters.user_id || undefined,
    project_id: filters.project_id || undefined,
    model_provider: filters.model_provider || undefined,
    model_name: filters.model_name || undefined,
  }
  if (filters.response_status !== null && filters.response_status !== undefined) {
    params.response_status = filters.response_status
  }
  return params
}

async function fetchSummary() {
  summaryLoading.value = true
  try {
    const data = await getModelCallLogSummary({
      user_id: filters.user_id || undefined,
      project_id: filters.project_id || undefined,
      model_provider: filters.model_provider || undefined,
      model_name: filters.model_name || undefined,
    })
    Object.assign(summary, data)
  } catch (e) {
    // handled by interceptor
  } finally {
    summaryLoading.value = false
  }
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await getModelCallLogs(buildParams())
    records.value = Array.isArray(res.data) ? res.data : []
    if (res.pagination) {
      pagination.total_count = res.pagination.total_count || 0
    }
  } catch (e) {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadRecords()
  fetchSummary()
}

function handleSizeChange() {
  pagination.page = 1
  loadRecords()
}

async function handleProviderChange() {
  filters.model_name = ''
  modelOptions.value = []
  
  if (!filters.model_provider) {
    return
  }
  
  modelLoading.value = true
  try {
    const data = await getModelOptions(null, filters.model_provider)
    modelOptions.value = Array.isArray(data) ? data : []
  } catch (e) {
    // handled by interceptor
  } finally {
    modelLoading.value = false
  }
}

async function openDetail(row) {
  try {
    const data = await getModelCallLogDetail(row.id)
    detailData.value = data
    detailVisible.value = true
  } catch (e) {
    // handled by interceptor
  }
}

onMounted(() => {
  loadFilterOptions()
  loadRecords()
  fetchSummary()
})

async function loadFilterOptions() {
  try {
    const userInfo = await getUserInfo()
    const isMain = userInfo.parent_user_id === null || userInfo.parent_user_id === undefined
    const users = [{ id: userInfo.id, username: userInfo.username }]
    let projectRes
    if (isMain) {
      const [subUsers, projData, providerData] = await Promise.all([
        getSubUsers(),
        request.get('/projects/all'),
        getAiProviderList(),
      ])
      if (Array.isArray(subUsers)) {
        users.push(...subUsers.map((u) => ({ id: u.id, username: u.username })))
      }
      projectRes = projData
      providerOptions.value = providerData || []
    } else {
      const [projData, providerData] = await Promise.all([
        request.get('/projects', { params: { page: 1, page_size: 50 } }),
        getAiProviderList(),
      ])
      projectRes = projData
      providerOptions.value = providerData || []
    }
    userOptions.value = users
    projectOptions.value = Array.isArray(projectRes)
      ? projectRes
      : (projectRes?.projects || [])
  } catch (e) {
    // handled by interceptor
  }
}
</script>

<style scoped>
.billing-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.section-header {
  padding: 16px 24px;
  border-bottom: 0.667px solid rgba(111, 126, 153, 0.12);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.98);
  z-index: 1;
  border-radius: 16px 16px 0 0;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #0a0a0a;
  margin: 0;
}

.content-area {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.content-inner {
  padding: 24px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-sizing: border-box;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid rgba(111, 126, 153, 0.12);
  background: rgba(255, 255, 255, 0.6);
}

.summary-label {
  font-size: 12px;
  color: #9ca3af;
  margin: 0 0 8px;
}

.summary-value {
  font-size: 22px;
  font-weight: 600;
  color: #0a0a0a;
  margin: 0;
}

.text-green {
  color: #22c55e;
}

.text-red {
  color: #ef4444;
}

.text-divider {
  color: #d1d5db;
  margin: 0 4px;
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 12px;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-select {
  width: 140px;
}

.filter-select-sm {
  width: 120px;
}

.filter-input {
  width: 200px;
}


.search-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: opacity 0.2s;
  height: 32px;
  box-shadow: rgba(47, 123, 255, 0.24) 0px 8px 20px 0px;
  flex-shrink: 0;
}

.search-btn:hover {
  opacity: 0.9;
}

.table-wrapper {
  min-height: 200px;
  flex: 1;
  overflow: hidden;
}

.provider-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(47, 123, 255, 0.1);
  color: #2f7bff;
}

.status-success {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.status-fail {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.empty-state {
  padding: 40px 0;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  flex-shrink: 0;
}

.detail-body {
  padding: 8px 0 16px;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}

.detail-section-header:hover .detail-section-title {
  color: #2f7bff;
}

.detail-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: color 0.15s;
}

.section-toggle-icon {
  font-size: 14px;
  color: #9ca3af;
  transition: transform 0.2s;
  margin-bottom: 8px;
}

.section-toggle-icon.is-expanded {
  transform: rotate(90deg);
}

.detail-desc-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-height: 28px;
}

.detail-label {
  font-size: 13px;
  color: #9ca3af;
  flex-shrink: 0;
  width: 64px;
  text-align: right;
}

.detail-value {
  font-size: 13px;
  color: #0a0a0a;
  word-break: break-all;
  flex: 1;
}

.detail-value-mono {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge-success {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.status-badge-fail {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.token-bar-wrapper {
  padding: 4px 0;
}

.token-bar {
  height: 8px;
  border-radius: 4px;
  background: rgba(245, 158, 11, 0.12);
  overflow: hidden;
}

.token-bar-input {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #2f7bff, #5ca8ff);
  transition: width 0.3s ease;
  min-width: 2px;
}

.token-bar-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.token-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.token-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.token-dot-input {
  background: #2f7bff;
}

.token-dot-output {
  background: rgba(245, 158, 11, 0.5);
}

.token-legend-total {
  margin-left: auto;
  font-weight: 600;
  color: #0a0a0a;
}

.detail-json {
  margin: 8px 0 0;
  padding: 12px;
  border-radius: 8px;
  background: rgba(245, 247, 250, 0.8);
  font-size: 12px;
  line-height: 1.5;
  color: #374151;
  max-height: 240px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  font-size: 14px;
  font-weight: 600;
  color: #0a0a0a;
  background: rgba(255, 255, 255, 0.94);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: background-color 0.15s;
  height: 33px;
  box-shadow: rgba(22, 35, 64, 0.05) 0px 2px 10px 0px;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.98);
}
</style>

<style>
/* 统一扣费记录页 el-select / el-input 样式 */
.billing-page .el-input__wrapper,
.billing-page .el-select__wrapper {
  border-radius: 10px !important;
  border: 0.667px solid rgba(111, 126, 153, 0.24) !important;
  background: rgba(255, 255, 255, 0.86) !important;
  box-shadow: none !important;
  padding: 4px 10px !important;
  min-height: 33px !important;
}

.billing-page .el-pagination .btn-prev,
.billing-page .el-pagination .btn-next,
.billing-page .el-pagination .el-pager li {
  border-radius: 50% !important;
}

.billing-page .el-input__wrapper.is-focus,
.billing-page .el-select__wrapper.is-focus {
  border-color: #2f7bff !important;
  box-shadow: 0 0 0 2px rgba(47, 123, 255, 0.15) !important;
}

.billing-page .el-input__inner {
  font-size: 13px;
  color: #0a0a0a;
}

.billing-page .el-input__inner::placeholder {
  color: #9ca3af;
}

.billing-page .el-select__placeholder {
  font-size: 13px !important;
  color: #9ca3af !important;
}

.billing-page .el-select__selected-item {
  font-size: 13px !important;
  color: #0a0a0a !important;
}
</style>
