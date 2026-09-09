<template>
  <div class="pay-order-page">
    <div class="section-header">
      <h2 class="section-title">积分获取记录</h2>
    </div>

    <div class="content-area">
      <div class="content-inner">
        <div class="filter-bar">
          <div class="filter-left">
            <el-select
              v-model="filters.type"
              placeholder="类型"
              clearable
              size="default"
              class="filter-select"
            >
              <el-option label="会员购买" value="membership" />
              <el-option label="积分购买" value="point_purchase" />
              <el-option label="每月赠送" value="monthly_grant" />
              <el-option label="每日赠送" value="daily_grant" />
              <el-option label="过期清零" value="expire_clear" />
              <el-option label="其他" value="others" />
            </el-select>
            <el-select
              v-model="filters.status"
              placeholder="状态"
              clearable
              size="default"
              class="filter-select-sm"
            >
              <el-option label="待支付" :value="1" />
              <el-option label="支付中" :value="2" />
              <el-option label="成功" :value="3" />
              <el-option label="失败" :value="4" />
            </el-select>
          </div>
          <button class="search-btn" @click="handleSearch">
            <el-icon :size="14"><Search /></el-icon>
            搜索
          </button>
        </div>

        <div v-loading="loading" class="table-wrapper">
          <el-table
            :data="orders"
            height="100%"
            style="width: 100%"
            size="default"
            empty-text="暂无积分获取记录"
            :header-cell-style="{ background: 'rgba(245,247,250,0.6)', fontWeight: 500 }"
          >
            <el-table-column label="订单号" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.order_no || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <span class="type-tag" :class="typeClass(row.type)">
                  {{ typeLabel(row.type) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="金额" width="100">
              <template #default="{ row }">
                <span v-if="row.amount != null">¥{{ row.amount }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="积分" min-width="110">
              <template #default="{ row }">
                <span v-if="row.points != null" class="text-muted">{{ formatPoints(row.points) }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="订阅类型" width="90" align="center">
              <template #default="{ row }">
                {{ row.subscribe_type === 'monthly' ? '月付' : row.subscribe_type === 'yearly' ? '年付' : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <span v-if="row.status != null" class="status-tag" :class="statusClass(row.status)">
                  {{ statusLabel(row.status) }}
                </span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="开始时间" min-width="160">
              <template #default="{ row }">
                {{ formatDateTime(row.create_time) }}
              </template>
            </el-table-column>
            <el-table-column label="结束时间" min-width="160">
              <template #default="{ row }">
                {{ formatDateTime(row.finished_time) }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="total > 0" class="pagination-bar">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="size"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            background
            @current-change="loadOrders"
            @size-change="handleSizeChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getCombinedRecords } from '@/api/payOrder'
import { formatBalance } from '@/utils/format'

const orders = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const loading = ref(false)

const filters = reactive({
  type: null,
  status: null,
})

// 统一类型映射（合并订单 + 积分流水）
const TYPE_MAP = {
  membership:     { label: '会员购买', cls: 'type-tag--membership' },
  point_purchase: { label: '积分购买', cls: 'type-tag--points' },
  monthly_grant:  { label: '每月赠送', cls: 'type-tag--grant' },
  daily_grant:    { label: '每日赠送', cls: 'type-tag--grant' },
  expire_clear:   { label: '过期清零', cls: 'type-tag--expire' },
  others:         { label: '其他',     cls: 'type-tag--others' },
}

const STATUS_MAP = { 1: '待支付', 2: '支付中', 3: '成功', 4: '失败' }

function typeLabel(type) {
  return TYPE_MAP[type]?.label || '-'
}

function typeClass(type) {
  return TYPE_MAP[type]?.cls || ''
}

function statusLabel(status) {
  return STATUS_MAP[status] || '-'
}

function statusClass(status) {
  if (status === 3) return 'status-success'
  if (status === 4) return 'status-fail'
  if (status === 1) return 'status-pending'
  if (status === 2) return 'status-info'
  return 'status-info'
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 积分显示：负数（扣减）保留负号，正数（获得）加 + 前缀
function formatPoints(val) {
  if (val == null) return '-'
  const s = formatBalance(val)
  return s.startsWith('-') ? s : `+${s}`
}

function buildParams() {
  const params = {
    page: page.value,
    size: size.value,
  }
  if (filters.type !== null) params.type = filters.type
  if (filters.status !== null) params.status = filters.status
  return params
}

async function loadOrders() {
  loading.value = true
  try {
    const res = await getCombinedRecords(buildParams())
    orders.value = res.data || []
    total.value = res.pagination?.total_count || 0
  } catch {
    orders.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadOrders()
}

function handleSizeChange() {
  page.value = 1
  loadOrders()
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.pay-order-page {
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

.text-muted {
  color: #9ca3af;
}

.type-tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 6px;
  border: 1px solid currentColor;
  background: #fff;
  font-size: 12px;
  font-weight: 500;
  line-height: 18px;
}

.type-tag--membership {
  color: #a855f7;
}

.type-tag--points {
  color: #2f7bff;
}

.type-tag--grant {
  color: #22c55e;
}

.type-tag--expire {
  color: #ef4444;
}

.type-tag--others {
  color: #6b7280;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.status-success {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.status-fail {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.status-pending {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.status-info {
  background: rgba(47, 123, 255, 0.1);
  color: #2f7bff;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  flex-shrink: 0;
}
</style>

<style>
/* 统一积分获取记录页 el-select / el-input 样式，与积分使用记录一致 */
.pay-order-page .el-input__wrapper,
.pay-order-page .el-select__wrapper {
  border-radius: 10px !important;
  border: 0.667px solid rgba(111, 126, 153, 0.24) !important;
  background: rgba(255, 255, 255, 0.86) !important;
  box-shadow: none !important;
  padding: 4px 10px !important;
  min-height: 33px !important;
}

.pay-order-page .el-pagination .btn-prev,
.pay-order-page .el-pagination .btn-next,
.pay-order-page .el-pagination .el-pager li {
  border-radius: 50% !important;
}

.pay-order-page .el-input__wrapper.is-focus,
.pay-order-page .el-select__wrapper.is-focus {
  border-color: #2f7bff !important;
  box-shadow: 0 0 0 2px rgba(47, 123, 255, 0.15) !important;
}

.pay-order-page .el-input__inner {
  font-size: 13px;
  color: #0a0a0a;
}

.pay-order-page .el-input__inner::placeholder {
  color: #9ca3af;
}

.pay-order-page .el-select__placeholder {
  font-size: 13px !important;
  color: #9ca3af !important;
}

.pay-order-page .el-select__selected-item {
  font-size: 13px !important;
  color: #0a0a0a !important;
}
</style>
