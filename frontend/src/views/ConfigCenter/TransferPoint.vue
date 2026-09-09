<template>
  <div class="transfer-point">
    <div class="section-header">
      <h2 class="section-title">积分转账</h2>
    </div>

    <div class="content-area">
      <div class="content-inner">
        <!-- 转账表单 -->
        <div class="custom-form">
          <div class="form-field">
            <label class="form-label">对方用户名 <span class="required">*</span></label>
            <input
              v-model="form.targetUsername"
              type="text"
              class="form-input"
              placeholder="请输入对方的用户名"
              maxlength="32"
            />
          </div>
          <div class="form-field">
            <label class="form-label">转账积分数量 <span class="required">*</span></label>
            <input
              v-model.number="form.amount"
              type="number"
              class="form-input"
              placeholder="请输入转账积分数量"
              min="0"
              step="0.01"
            />
          </div>
          <div class="form-actions">
            <button
              class="btn-primary"
              :disabled="!isFormValid || submitting"
              @click="handleSubmit"
            >
              {{ submitting ? '转账中...' : '发起转账' }}
            </button>
          </div>
        </div>

        <div class="section-divider"></div>

        <!-- 转账记录列表 -->
        <div v-loading="recordsLoading" class="table-wrapper">
          <el-table
            :data="records"
            style="width: 100%"
            size="default"
            empty-text="暂无转账记录"
            :header-cell-style="{ background: 'rgba(245,247,250,0.6)', fontWeight: 500 }"
          >
            <el-table-column prop="target_username" label="对方用户名" min-width="120">
              <template #default="{ row }">
                {{ row.target_username || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="point" label="转账积分" width="140" align="left">
              <template #default="{ row }">
                <span :class="row.direction === 'in' ? 'amount-in' : 'amount-out'">
                  {{ row.direction === 'in' ? '+' : '-' }}{{ formatBalance(row.point) }}
                </span>
              </template>
            </el-table-column>
            <!-- <el-table-column prop="direction" label="方向" width="100" align="center">
              <template #default="{ row }">
                {{ row.direction === 'in' ? '收入' : '支出' }}
              </template>
            </el-table-column> -->
            <el-table-column prop="transfer_type" label="转账类型" width="120" align="center">
              <template #default="{ row }">
                {{ row.transfer_type === 0 ? '内部转账' : '子账号划分' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <span :class="row.status === 1 ? 'status-success' : 'status-fail'">
                  {{ row.status === 1 ? '成功' : '失败' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="时间" width="180">
              <template #default="{ row }">
                {{ row.create_time || '-' }}
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

    <!-- 密码确认弹窗 -->
    <Teleport to="body">
      <div v-if="passwordDialogVisible" class="glass-overlay" @click.self="passwordDialogVisible = false">
        <div class="glass-surface-modal" style="max-width: 448px; width: 90%; display: flex; flex-direction: column;">
          <div class="modal-header">
            <h3 class="modal-title">确认转账</h3>
            <button class="modal-close-btn" @click="passwordDialogVisible = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="confirm-info">
              <p>即将向 <strong>{{ form.targetUsername }}</strong> 转账 <strong class="text-primary">{{ form.amount }}</strong> 积分</p>
            </div>
            <div class="custom-form" style="padding-top: 12px;">
              <div class="form-field">
                <label class="form-label">请输入密码确认 <span class="required">*</span></label>
                <input
                  ref="passwordInputRef"
                  v-model="passwordForm.password"
                  type="password"
                  class="form-input"
                  placeholder="请输入当前账号密码"
                  @keyup.enter="confirmTransfer"
                />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="glass-btn-secondary glass-btn-base" @click="passwordDialogVisible = false">取消</button>
            <button
              class="glass-btn-primary glass-btn-base"
              :disabled="!passwordForm.password || submitting"
              @click="confirmTransfer"
            >
              {{ submitting ? '转账中...' : '确定' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { createTransfer, getTransferRecords } from '@/api/transfer'
import { formatBalance } from '@/utils/format'

const emit = defineEmits(['balance-changed'])

const form = reactive({
  targetUsername: '',
  amount: null
})

const submitting = ref(false)

const isFormValid = computed(() => {
  return form.targetUsername.trim().length > 0 && form.amount > 0
})

// 密码确认弹窗
const passwordDialogVisible = ref(false)
const passwordInputRef = ref(null)
const passwordForm = reactive({ password: '' })

const handleSubmit = () => {
  if (!isFormValid.value) return
  passwordForm.password = ''
  passwordDialogVisible.value = true
  nextTick(() => {
    passwordInputRef.value?.focus()
  })
}

const confirmTransfer = async () => {
  if (!passwordForm.password || submitting.value) return
  submitting.value = true
  try {
    await createTransfer({
      target_username: form.targetUsername,
      amount: form.amount,
      password: passwordForm.password
    })
    ElMessage.success('转账成功')
    passwordDialogVisible.value = false
    form.targetUsername = ''
    form.amount = null
    emit('balance-changed')
    loadRecords()
  } catch {
    // error handled by interceptor
  } finally {
    submitting.value = false
  }
}

// 转账记录
const recordsLoading = ref(false)
const records = ref([])
const pagination = reactive({
  page: 1,
  size: 10,
  total_count: 0
})

async function loadRecords() {
  recordsLoading.value = true
  try {
    const res = await getTransferRecords({ page: pagination.page, size: pagination.size })
    records.value = res.data || []
    pagination.total_count = res.pagination?.total_count || 0
  } catch {
    // error handled by interceptor
  } finally {
    recordsLoading.value = false
  }
}

function handleSizeChange() {
  pagination.page = 1
  loadRecords()
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.transfer-point {
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
  overflow-y: auto;
}

.content-inner {
  padding: 24px;
}

.section-divider {
  height: 1px;
  border-top: 0.667px solid rgba(111, 126, 153, 0.2);
  margin: 24px 0;
}

.record-subtitle {
  font-size: 16px;
  font-weight: 600;
  color: #0a0a0a;
  margin: 0 0 16px;
}

.table-wrapper {
  min-height: 200px;
}

.amount-out {
  color: #ef4444;
  font-weight: 500;
}

.status-success {
  color: #22c55e;
  font-weight: 500;
}

.status-fail {
  color: #ef4444;
  font-weight: 500;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  flex-shrink: 0;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 480px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 14px;
  color: #111827;
}

.form-label .required {
  color: #f87171;
}

.form-input {
  width: 100%;
  border-radius: 10px;
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  background: rgba(255, 255, 255, 0.86);
  padding: 8px 12px;
  font-size: 14px;
  color: #0a0a0a;
  outline: none;
  transition: border-color 0.2s;
  line-height: 20px;
  box-sizing: border-box;
  box-shadow: none;
}

.form-input:focus {
  border-color: #2f7bff;
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: opacity 0.2s;
  height: 33px;
  box-shadow: rgba(47, 123, 255, 0.24) 0px 8px 20px 0px;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.confirm-info {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
}

.confirm-info strong {
  color: #0a0a0a;
}

.text-primary {
  color: #2f7bff;
}

.amount-in {
  color: #22c55e;
  font-weight: 500;
}
</style>
