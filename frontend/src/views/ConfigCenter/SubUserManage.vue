<template>
  <div class="sub-user-manage">
    <div class="section-header">
      <h2 class="section-title">子账号管理</h2>
    </div>

    <div class="content-area">
      <div class="content-inner">
        <div class="stats-bar">
          <div class="stats-info">
            <el-icon :size="16"><User /></el-icon>
            <span>已使用 {{ subUsers.length }} / {{ maxSubUsers }} 个子账号</span>
          </div>
          <button class="add-btn" @click="openAddDialog">
            <el-icon :size="16"><Plus /></el-icon>
            添加子账号
          </button>
        </div>

        <div v-loading="loading" class="user-grid">
          <div
            v-for="user in subUsers"
            :key="user.id"
            class="user-card"
          >
            <div class="user-avatar">
              {{ getAvatarLetter(user.username) }}
            </div>
            <div class="user-info">
              <div class="user-name-row">
                <span
                  class="status-dot"
                  :class="user.status === 'enable' ? 'active' : 'inactive'"
                ></span>
                <p class="user-name">{{ user.username }}</p>
              </div>
            </div>
            <el-button text size="small" class="edit-btn" @click="openDetailDialog(user)">
              <el-icon :size="16"><Edit /></el-icon>
            </el-button>
          </div>

          <div v-if="!loading && subUsers.length === 0" class="empty-state">
            <el-empty description="暂无子账号" :image-size="80" />
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="addDialogVisible" class="glass-overlay" @click.self="addDialogVisible = false">
        <div class="glass-surface-modal" style="max-width: 448px; width: 90%; display: flex; flex-direction: column;">
          <div class="modal-header">
            <h3 class="modal-title">添加子账号</h3>
            <button class="modal-close-btn" @click="addDialogVisible = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="custom-form">
              <div class="form-field">
                <label class="form-label">用户名 <span class="required">*</span></label>
                <input
                  v-model="addForm.username"
                  type="text"
                  class="form-input"
                  placeholder="请输入用户名（至少2个字符）"
                  maxlength="32"
                />
              </div>
              <div class="form-field">
                <label class="form-label">密码 <span class="required">*</span></label>
                <input
                  v-model="addForm.password"
                  type="password"
                  class="form-input"
                  placeholder="请输入密码（至少6位）"
                  maxlength="64"
                />
              </div>
              <div class="form-field">
                <label class="form-label">邮箱</label>
                <input
                  v-model="addForm.email"
                  type="email"
                  class="form-input"
                  placeholder="请输入邮箱地址"
                />
              </div>
              <div class="form-field">
                <label class="form-label">备注</label>
                <input
                  v-model="addForm.remark"
                  type="text"
                  class="form-input"
                  placeholder="请输入备注信息"
                  maxlength="20"
                />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="glass-btn-secondary glass-btn-base" @click="addDialogVisible = false">取消</button>
            <button
              class="glass-btn-primary glass-btn-base"
              :disabled="!isAddFormValid || addLoading"
              @click="handleAddSubUser"
            >
              {{ addLoading ? '添加中...' : '添加子账号' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="detailDialogVisible" class="glass-overlay" @click.self="detailDialogVisible = false">
        <div class="glass-surface-modal" style="max-width: 672px; width: 90%; max-height: 80vh; display: flex; flex-direction: column;">
          <div class="modal-header">
            <h3 class="modal-title">子账号详情</h3>
            <button class="modal-close-btn" @click="detailDialogVisible = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div class="modal-body" style="max-height: 60vh;">
            <div class="detail-body">
        <div class="detail-header-row">
          <div class="detail-user-info">
            <div class="detail-avatar">
              {{ getAvatarLetter(currentUser?.username || '') }}
            </div>
            <p class="detail-username">{{ currentUser?.username }}</p>
          </div>
          <div class="detail-meta">
            <div class="meta-item">
              <span class="meta-label">状态</span>
              <div class="meta-value status-value">
                <span :class="editForm.status === 'enable' ? 'text-green' : 'text-gray'">
                  {{ editForm.status === 'enable' ? '已启用' : '已禁用' }}
                </span>
                <el-switch
                  v-model="editForm.status"
                  active-value="enable"
                  inactive-value="disable"
                  size="small"
                />
              </div>
            </div>
            <div class="meta-item">
              <span class="meta-label">类型</span>
              <span class="meta-value">专业版</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">创建时间</span>
              <span class="meta-value">{{ formatDate(currentUser?.create_time) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-field-row">
          <label class="field-label">备注</label>
          <input
            v-model="editForm.remark"
            type="text"
            class="glass-input"
            placeholder="请输入备注信息"
            maxlength="20"
          />
        </div>

        <div class="detail-divider"></div>

        <div class="section-block">
          <h4 class="section-subtitle">积分管理</h4>
          <div class="balance-section">
            <div class="balance-info-row">
              <div class="balance-info-item">
                <span class="balance-info-label">子账号积分</span>
                <span class="balance-info-value">{{ formatBalance(currentUser?.balance) }}</span>
              </div>
              <div class="balance-info-item">
                <span class="balance-info-label">主账号积分</span>
                <span class="balance-info-value">{{ formatBalance(mainAccountBalance) }}</span>
              </div>
            </div>
            <div class="balance-actions">
                <input
                  v-model.number="transferAmount"
                  type="number"
                  class="glass-input transfer-input"
                  placeholder="请输入划拨积分数量"
                  min="0"
                  step="0.01"
                />
                <button
                  class="btn-primary balance-action-btn"
                  :disabled="!transferAmount || transferAmount <= 0 || transferLoading"
                  @click="handleTransferBalance"
                >
                  {{ transferLoading ? '划拨中...' : '划分积分' }}
                </button>
                <button
                  class="btn-secondary reclaim-btn"
                  :disabled="parseFloat(currentUser?.balance || '0') <= 0 || reclaimLoading"
                  @click="handleReclaimBalance"
                >
                  {{ reclaimLoading ? '回收中...' : '回收积分' }}
                </button>
            </div>
          </div>
        </div>

        <div class="detail-divider"></div>

        <div class="section-block">
          <h4 class="section-subtitle">API Key</h4>
          <div class="api-key-row">
            <el-input
              v-model="editForm.api_key"
              :type="apiKeyVisible ? 'text' : 'password'"
              placeholder="输入 API Key（可选）"
              size="small"
              class="api-key-input"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
            <el-icon class="api-key-toggle" @click="apiKeyVisible = !apiKeyVisible">
              <View v-if="apiKeyVisible" /><Hide v-else />
            </el-icon>
          </div>
        </div>

        <div class="detail-divider"></div>

        <div class="section-block">
          <h4 class="section-subtitle">权限配置</h4>
          <div class="permissions-grid">
            <div v-for="group in permissionGroups" :key="group.label" class="permission-group">
              <p class="permission-group-label">{{ group.label }}</p>
              <div class="permission-items">
                <label
                  v-for="perm in group.items"
                  :key="perm.key"
                  class="permission-item"
                >
                  <span class="su-check" :class="{ 'su-check-on': editForm.permissions[perm.key] }" @click.prevent="editForm.permissions[perm.key] = !editForm.permissions[perm.key]">
                    <svg v-if="editForm.permissions[perm.key]" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </span>
                  <span class="permission-text">{{ perm.label }}</span>
                </label>
              </div>
            </div>
          </div>

          <div v-if="editForm.permissions['main_user_asset:read']" class="folder-share-section">
            <div class="folder-share-header">
              <span class="folder-share-title">选择共享资产组</span>
              <span class="folder-share-desc">勾选需要共享给该子账号的资产组</span>
            </div>
            <div v-loading="foldersLoading" class="folder-checkbox-list">
              <div v-if="!foldersLoading && mainUserFolders.length === 0" class="folder-empty">
                暂无资产组，请先在资产中心创建资产组
              </div>
              <label
                v-for="folder in mainUserFolders"
                :key="folder.id"
                class="folder-checkbox-item"
              >
                <span class="su-check" :class="{ 'su-check-on': editForm.shared_folder_ids.includes(folder.id) }" @click.prevent="toggleFolder(folder.id, !editForm.shared_folder_ids.includes(folder.id))">
                  <svg v-if="editForm.shared_folder_ids.includes(folder.id)" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                </span>
                <span class="folder-checkbox-text">{{ folder.name }}</span>
              </label>
            </div>
            <div v-if="mainUserFolders.length > 0" class="folder-share-actions">
              <el-button size="small" text type="primary" @click="selectAllFolders">全选</el-button>
              <el-button size="small" text @click="clearAllFolders">清空</el-button>
            </div>
          </div>
        </div>
      </div>

          </div>
          <div class="modal-footer">
            <button class="glass-btn-danger glass-btn-base" @click="handleDeleteSubUser">删除子账号</button>
            <div style="flex:1"></div>
            <button class="glass-btn-secondary glass-btn-base" @click="detailDialogVisible = false">取消</button>
            <button
              class="glass-btn-primary glass-btn-base"
              :disabled="!isEditFormChanged"
              @click="handleSaveSubUser"
            >
              {{ saveLoading ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <ConfirmDialog
      v-model="deleteSubConfirmVisible"
      title="删除确认"
      :message="deleteSubMessage"
      confirm-text="删除"
      type="danger"
      @confirm="doDeleteSubUser"
    />

    <ConfirmDialog
      v-model="reclaimConfirmVisible"
      title="回收积分确认"
      :message="reclaimMessage"
      confirm-text="确认回收"
      @confirm="doReclaimBalance"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { User, Plus, Edit, Lock } from '@element-plus/icons-vue'
import { getSubUsers, getMainUserFolders, createSubUser, updateSubUser, deleteSubUser, transferBalance, reclaimBalance } from '@/api/subUser'
import { getUserInfo } from '@/api/user'
import { formatBalance } from '@/utils/format'

const emit = defineEmits(['balance-changed'])

const maxSubUsers = ref(10)
const loading = ref(false)
const subUsers = ref([])

const addDialogVisible = ref(false)
const addLoading = ref(false)

const addForm = reactive({
  username: '',
  password: '',
  email: '',
  remark: ''
})

const isAddFormValid = computed(() => {
  return addForm.username.length >= 2 && addForm.password.length >= 6
})

const detailDialogVisible = ref(false)
const saveLoading = ref(false)
const apiKeyVisible = ref(false)
const currentUser = ref(null)
const deleteSubConfirmVisible = ref(false)
const reclaimConfirmVisible = ref(false)
const deleteSubMessage = computed(() => `确定要删除子账号「${currentUser.value?.username || ''}」吗？此操作不可恢复。`)
const reclaimMessage = computed(() => `确定要回收子账号「${currentUser.value?.username || ''}」的全部积分（${formatBalance(currentUser.value?.balance)}）吗？`)
const originalForm = ref(null)
const mainUserFolders = ref([])
const foldersLoading = ref(false)
const transferAmount = ref(null)
const transferLoading = ref(false)
const reclaimLoading = ref(false)
const mainAccountBalance = ref('0.00')

const editForm = reactive({
  status: 'enable',
  remark: '',
  api_key: '',
  permissions: {
    'project:create': true,
    'project:delete': true,
    'project:read': true,
    'project:update': true,
    'asset:create': true,
    'asset:delete': true,
    'asset:read': true,
    'asset:update': true,
    'main_user_asset:read': false
  },
  shared_folder_ids: []
})

const permissionGroups = [
  {
    label: '项目',
    items: [
      { key: 'project:create', label: '创建项目' },
      { key: 'project:delete', label: '删除项目' },
      { key: 'project:read', label: '查看项目' },
      { key: 'project:update', label: '编辑项目' }
    ]
  },
  {
    label: '资产',
    items: [
      { key: 'asset:create', label: '创建资产' },
      { key: 'asset:delete', label: '删除资产' },
      { key: 'asset:read', label: '查看资产' },
      { key: 'asset:update', label: '编辑资产' }
    ]
  },
  {
    label: '主账号资产',
    items: [
      { key: 'main_user_asset:read', label: '查看主账号资产' }
    ]
  }
]

const isEditFormChanged = computed(() => {
  if (!originalForm.value) return false
  return JSON.stringify({
    status: editForm.status,
    remark: editForm.remark,
    api_key: editForm.api_key,
    permissions: editForm.permissions,
    shared_folder_ids: editForm.shared_folder_ids
  }) !== JSON.stringify(originalForm.value)
})

function getAvatarLetter(username) {
  return username ? username.charAt(0).toUpperCase() : ''
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
}

async function fetchSubUsers() {
  loading.value = true
  try {
    const [subData, userData] = await Promise.all([getSubUsers(), getUserInfo()])
    subUsers.value = Array.isArray(subData) ? subData : []
    if (userData?.sub_user_limit) {
      maxSubUsers.value = userData.sub_user_limit
    }
  } catch (e) {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  addForm.username = ''
  addForm.password = ''
  addForm.email = ''
  addForm.remark = ''
  addDialogVisible.value = true
}

async function handleAddSubUser() {
  if (!isAddFormValid.value) return
  addLoading.value = true
  try {
    await createSubUser({
      username: addForm.username,
      password: addForm.password,
      email: addForm.email || undefined,
      remark: addForm.remark || undefined
    })
    ElMessage.success('添加子账号成功')
    addDialogVisible.value = false
    await fetchSubUsers()
  } catch (e) {
    // error handled by interceptor
  } finally {
    addLoading.value = false
  }
}

function openDetailDialog(user) {
  currentUser.value = user
  apiKeyVisible.value = false
  transferAmount.value = null
  transferLoading.value = false
  reclaimLoading.value = false
  editForm.status = user.status ?? 'enable'
  editForm.remark = user.remark || ''
  editForm.api_key = user.api_key || ''
  editForm.permissions = {
    'project:create': user.permissions?.['project:create'] ?? false,
    'project:delete': user.permissions?.['project:delete'] ?? false,
    'project:read': user.permissions?.['project:read'] ?? false,
    'project:update': user.permissions?.['project:update'] ?? false,
    'asset:create': user.permissions?.['asset:create'] ?? false,
    'asset:delete': user.permissions?.['asset:delete'] ?? false,
    'asset:read': user.permissions?.['asset:read'] ?? false,
    'asset:update': user.permissions?.['asset:update'] ?? false,
    'main_user_asset:read': user.permissions?.['main_user_asset:read'] ?? false
  }
  editForm.shared_folder_ids = user.shared_folder_ids
    ? [...user.shared_folder_ids]
    : []
  originalForm.value = JSON.parse(JSON.stringify({
    status: editForm.status,
    remark: editForm.remark,
    api_key: editForm.api_key,
    permissions: editForm.permissions,
    shared_folder_ids: editForm.shared_folder_ids
  }))
  detailDialogVisible.value = true
  fetchMainUserFolders()
  fetchMainAccountBalance()
}

async function handleSaveSubUser() {
  if (!currentUser.value) return
  saveLoading.value = true
  try {
    await updateSubUser(currentUser.value.id, {
      status: editForm.status,
      remark: editForm.remark,
      api_key: editForm.api_key,
      permissions: editForm.permissions,
      shared_folder_ids: editForm.shared_folder_ids
    })
    ElMessage.success('保存成功')
    detailDialogVisible.value = false
    await fetchSubUsers()
  } catch (e) {
    // error handled by interceptor
  } finally {
    saveLoading.value = false
  }
}



async function handleDeleteSubUser() {
  if (!currentUser.value) return
  deleteSubConfirmVisible.value = true
}

async function doDeleteSubUser() {
  try {
    await deleteSubUser(currentUser.value.id)
    ElMessage.success('删除成功')
    detailDialogVisible.value = false
    await fetchSubUsers()
  } catch (e) {
    if (e !== 'cancel') {
      // error handled by interceptor
    }
  }
}

async function fetchMainUserFolders() {
  foldersLoading.value = true
  try {
    const data = await getMainUserFolders()
    mainUserFolders.value = Array.isArray(data) ? data : []
  } catch (e) {
    mainUserFolders.value = []
  } finally {
    foldersLoading.value = false
  }
}

function toggleFolder(folderId, checked) {
  if (checked) {
    if (!editForm.shared_folder_ids.includes(folderId)) {
      editForm.shared_folder_ids.push(folderId)
    }
  } else {
    editForm.shared_folder_ids = editForm.shared_folder_ids.filter(id => id !== folderId)
  }
}

function selectAllFolders() {
  editForm.shared_folder_ids = mainUserFolders.value.map(f => f.id)
}

function clearAllFolders() {
  editForm.shared_folder_ids = []
}

async function fetchMainAccountBalance() {
  try {
    const userData = await getUserInfo()
    mainAccountBalance.value = userData.balance || '0.00'
  } catch {
    mainAccountBalance.value = '0.00'
  }
}

async function handleTransferBalance() {
  if (!currentUser.value || !transferAmount.value || transferAmount.value <= 0) return
  const mainBalance = parseFloat(mainAccountBalance.value)
  if (transferAmount.value > mainBalance) {
    ElMessage.warning('划拨积分不能超过主账号可用积分')
    return
  }
  transferLoading.value = true
  try {
    const data = await transferBalance(currentUser.value.id, transferAmount.value)
    ElMessage.success(`成功划拨 ${transferAmount.value} 积分`)
    if (data) {
      currentUser.value = { ...currentUser.value, balance: data.balance }
    }
    transferAmount.value = null
    await fetchMainAccountBalance()
    await fetchSubUsers()
    emit('balance-changed')
  } catch {
    // error handled by interceptor
  } finally {
    transferLoading.value = false
  }
}

async function handleReclaimBalance() {
  if (!currentUser.value) return
  const subBalance = parseFloat(currentUser.value.balance || '0')

  if (subBalance <= 0) {
    ElMessage.warning('子账号无可用积分')
    return
  }
  reclaimConfirmVisible.value = true
}

async function doReclaimBalance() {
  const subBalance = parseFloat(currentUser.value.balance || '0')
  reclaimLoading.value = true
  try {
    const data = await reclaimBalance(currentUser.value.id)
    ElMessage.success(`成功回收 ${subBalance} 积分`)
    if (data) {
      currentUser.value = { ...currentUser.value, balance: data.balance }
    }
    await fetchMainAccountBalance()
    await fetchSubUsers()
    emit('balance-changed')
  } catch {
    // error handled by interceptor
  } finally {
    reclaimLoading.value = false
  }
}

onMounted(() => {
  fetchSubUsers()
})
</script>

<style scoped>
.sub-user-manage {
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

.stats-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.stats-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--el-text-color-secondary, #6b7280);
}

.add-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: opacity 0.2s;
  box-shadow: rgba(47, 123, 255, 0.24) 0px 8px 20px 0px;
}

.add-btn:hover {
  opacity: 0.9;
}

.user-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  min-height: 100px;
}

@media (min-width: 1024px) {
  .user-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter, rgba(111, 126, 153, 0.12));
  background: rgba(255, 255, 255, 0.6);
  transition: all 0.2s ease;
  height: 80px;
}

.user-card:hover {
  border-color: var(--el-border-color, rgba(111, 126, 153, 0.25));
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--el-fill-color-light, #f5f7fa);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary, #0a0a0a);
}

.user-info {
  min-width: 0;
  flex: 1;
}

.user-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.active {
  background: #22c55e;
}

.status-dot.inactive {
  background: #9ca3af;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary, #0a0a0a);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edit-btn {
  flex-shrink: 0;
  color: var(--el-text-color-secondary, #6b7280);
}

.empty-state {
  grid-column: 1 / -1;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 0;
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
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

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 16px 0;
}

.detail-header-row {
  display: flex;
  align-items: flex-start;
  gap: 24px;
}

.detail-user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.detail-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--el-fill-color-light, #f5f7fa);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary, #0a0a0a);
}

.detail-username {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary, #0a0a0a);
  margin: 0;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-left: auto;
  flex-shrink: 0;
}

.meta-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: #9ca3af;
}

.meta-value {
  font-size: 14px;
  color: #0a0a0a;
}

.status-value {
  display: flex;
  align-items: center;
  gap: 6px;
}

.text-green {
  color: #22c55e;
}

.text-gray {
  color: #9ca3af;
}

.detail-field-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.field-label {
  font-size: 14px;
  color: #9ca3af;
  white-space: nowrap;
  flex-shrink: 0;
}

.detail-field-row .el-input {
  flex: 1;
}

.glass-input {
  flex: 1;
  height: 33px;
  border-radius: 10px;
  border: 0.667px solid #0a0a0a;
  background: rgba(255, 255, 255, 0.86);
  padding: 6px 12px;
  font-size: 14px;
  color: #0a0a0a;
  outline: none;
  transition: border-color 0.2s;
  line-height: 20px;
  box-sizing: border-box;
  box-shadow: none;
}

.glass-input:focus {
  border-color: #2f7bff;
}

.glass-input::placeholder {
  color: #9ca3af;
}

.detail-divider {
  height: 1px;
  border-top: 0.667px solid rgba(111, 126, 153, 0.2);
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 500;
  color: #0a0a0a;
  margin: 0;
}

.api-key-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.api-key-input {
  flex: 1;
}

.api-key-toggle {
  cursor: pointer;
  color: #9ca3af;
  font-size: 16px;
  flex-shrink: 0;
  transition: color 0.2s;
}

.api-key-toggle:hover {
  color: #0a0a0a;
}

.permissions-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.permission-group-label {
  font-size: 12px;
  font-weight: 500;
  color: #9ca3af;
  margin: 0 0 8px;
}

.permission-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.permission-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.permission-item:hover {
  background: var(--el-fill-color-light, #f5f7fa);
}

.permission-text {
  font-size: 14px;
  color: #0a0a0a;
}

.detail-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.detail-footer-right {
  display: flex;
  gap: 8px;
}

.folder-share-section {
  margin-top: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  border: 0.667px solid rgba(111, 126, 153, 0.18);
  background: rgba(255, 255, 255, 0.6);
}

.folder-share-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.folder-share-title {
  font-size: 13px;
  font-weight: 500;
  color: #0a0a0a;
}

.folder-share-desc {
  font-size: 12px;
  color: #9ca3af;
}

/* 自定义勾选框 */
.su-check {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px;
  border: 1.5px solid rgba(111,126,153,0.36);
  border-radius: 4px;
  background: #fff;
  transition: all 0.15s;
  flex-shrink: 0;
  cursor: pointer;
}
.su-check-on {
  background: #2f7bff;
  border-color: #2f7bff;
  color: #fff;
}
.su-check svg { display: block; }

.folder-checkbox-list {
  max-height: 200px;
  overflow-y: auto;
  min-height: 40px;
}

.folder-checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.folder-checkbox-item:hover {
  background: var(--el-fill-color-light, #f5f7fa);
}

.folder-checkbox-text {
  font-size: 14px;
  color: #0a0a0a;
}

.folder-empty {
  padding: 12px 0;
  text-align: center;
  font-size: 13px;
  color: #9ca3af;
}

.folder-share-actions {
  display: flex;
  gap: 4px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 0.667px solid rgba(111, 126, 153, 0.12);
}

.balance-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.balance-info-row {
  display: flex;
  gap: 24px;
}

.balance-info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  padding: 12px 16px;
  border-radius: 10px;
  background: #f9fafb;
  border: 0.667px solid rgba(111, 126, 153, 0.12);
}

.balance-info-label {
  font-size: 12px;
  font-weight: 500;
  color: #9ca3af;
}

.balance-info-value {
  font-size: 20px;
  font-weight: 600;
  color: #0a0a0a;
}

.balance-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.transfer-input {
  width: 180px;
  flex-shrink: 0;
}

.balance-action-btn {
  flex-shrink: 0;
  white-space: nowrap;
}

.reclaim-btn {
  flex-shrink: 0;
  white-space: nowrap;
  color: #dc2626;
  background: rgba(239, 68, 68, 0.08);
  box-shadow: none;
}

.reclaim-btn:hover {
  background: rgba(239, 68, 68, 0.15);
}

.reclaim-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

<style>
.detail-dialog .api-key-input .el-input__wrapper {
  border-radius: 10px !important;
  border: 0.667px solid #0a0a0a !important;
  background: rgba(255, 255, 255, 0.86) !important;
  box-shadow: none !important;
  padding: 8px 12px !important;
  min-height: 37px !important;
}

.detail-dialog .api-key-input .el-input__wrapper:hover {
  border-color: #0a0a0a !important;
}

.detail-dialog .api-key-input .el-input__wrapper.is-focus {
  border-color: #2f7bff !important;
  box-shadow: none !important;
}

.detail-dialog .api-key-input .el-input__inner {
  font-size: 14px !important;
  color: #0a0a0a !important;
}

.detail-dialog .api-key-input .el-input__prefix .el-icon {
  color: #9ca3af !important;
}
</style>
