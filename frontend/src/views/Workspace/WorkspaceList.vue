<template>
  <AppLayout>
    <div class="workspace-list-page">
      <!-- 标题与搜索栏 -->
      <div class="workspace-header">
        <div class="header-info">
          <h1 class="header-title">我的项目</h1>
          <p class="header-subtitle">管理您的AI短剧制作项目</p>
        </div>
        <div class="header-search">
          <input
            v-model="searchInput"
            class="glass-input-base search-input"
            placeholder="搜索项目名称..."
            @keyup.enter="handleSearch"
          />
          <button class="glass-btn-base glass-btn-primary search-btn" @click="handleSearch">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
            搜索
          </button>
          <button v-if="searchQuery" class="glass-btn-base glass-btn-secondary clear-btn" @click="clearSearch">
            清除
          </button>
        </div>
      </div>

      <!-- 新建项目入口卡片 -->
      <div class="grid-create">
        <div class="create-card glass-surface" @click="openCreateModeDialog">
          <div class="create-icon-wrap">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14" /><path d="M12 5v14" /></svg>
          </div>
          <span class="create-text">新建项目</span>
        </div>
      </div>

      <!-- 模式选择弹框 -->
      <ProjectCreateModeDialog
        v-model="modeDialogVisible"
        @select="handleModeSelect"
      />
      <!-- 导演模式配置弹框 -->
      <DirectorProjectDialog v-model="directorDialogVisible" />

      <!-- 加载骨架屏 -->
      <template v-if="loading">
        <div class="project-grid">
          <div v-for="i in 3" :key="i" class="glass-surface skeleton-card">
            <div class="skeleton-line title-line" />
            <div class="skeleton-line" />
            <div class="skeleton-line short" />
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <template v-else-if="projects.length === 0">
        <div class="empty-state">
          <div class="empty-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" /></svg>
          </div>
          <h3 class="empty-title">{{ searchQuery ? '没有找到匹配的项目' : '还没有项目' }}</h3>
          <p class="empty-desc">{{ searchQuery ? '尝试使用不同的搜索词' : '创建您的第一个AI短剧制作项目' }}</p>
        </div>
      </template>

      <!-- 项目卡片网格 -->
      <template v-else>
        <div class="project-grid">
          <div
            v-for="project in projects"
            :key="project.id"
            class="project-card glass-surface"
            @click="router.push(`/workspace/${project.id}`)"
          >
            <!-- 悬停覆盖层 -->
            <div class="card-hover-overlay" />

            <!-- 操作按钮 -->
            <div class="card-actions">
              <button class="glass-btn-base glass-btn-secondary action-btn" title="编辑" @click.stop="openEditModal(project)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" /></svg>
              </button>
              <button class="glass-btn-base glass-btn-secondary action-btn" title="删除" @click.stop="confirmDelete(project)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-danger-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /></svg>
              </button>
            </div>

            <!-- 卡片内容 -->
            <div class="card-content">
              <!-- 标题：带模式图标 -->
              <div class="card-title-row">
                <!-- 创作模式：书本图标 -->
                <svg v-if="project.mode !== 'director'" class="card-mode-icon card-mode-icon-novel" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3Z"/></svg>
                <!-- 导演模式：场记板图标 -->
                <svg v-else class="card-mode-icon card-mode-icon-director" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.3.3 2.6 1.4L20.2 6Z"/><path d="M6.2 5.3 9 9"/><path d="M12.4 3.4 15 7"/><path d="M18.7 1.6 21 5"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/></svg>
                <h3 class="card-title">{{ project.title || '未命名项目' }}</h3>
              </div>

              <!-- 描述区：全局模式显示小说预览，导演模式显示项目描述（无则占位），并预留高度让底部信息对齐 -->
              <p v-if="project.mode === 'director'" class="card-novel-preview director-desc">
                <span :class="{ 'preview-placeholder': !project.description }">{{ project.description || '暂无项目描述' }}</span>
              </p>
              <p v-else-if="project.novel_preview" class="card-novel-preview">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="1.5" style="flex-shrink:0;margin-top:2px"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6" /><path d="M16 13H8" /><path d="M16 17H8" /><path d="M10 9H8" /></svg>
                {{ project.novel_preview }}
              </p>

              <!-- 资产统计：剧集、图片、视频 -->
              <div class="card-stats">
                <div class="stats-items">
                  <span class="stat-item">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-accent-from)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    {{ project.stats?.episodes || 0 }}
                  </span>
                  <span class="stat-item">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-accent-from)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                    {{ project.stats?.images || 0 }}
                  </span>
                  <span class="stat-item">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-accent-from)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                    {{ project.stats?.videos || 0 }}
                  </span>
                </div>
              </div>

              <!-- 底部信息 -->
              <div class="card-footer">
                <span class="footer-time">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                  {{ formatTime(project.update_time || project.create_time) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="pagination.total_pages > 1" class="pagination-wrap">
          <button
            class="glass-btn-base glass-btn-secondary page-btn"
            :disabled="pagination.page <= 1"
            @click="changePage(pagination.page - 1)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <template v-for="p in displayPages" :key="p">
            <span v-if="p === '...'" class="page-ellipsis">...</span>
            <button
              v-else
              class="glass-btn-base page-btn"
              :class="p === pagination.page ? 'glass-btn-primary' : 'glass-btn-secondary'"
              @click="changePage(p)"
            >
              {{ p }}
            </button>
          </template>
          <button
            class="glass-btn-base glass-btn-secondary page-btn"
            :disabled="pagination.page >= pagination.total_pages"
            @click="changePage(pagination.page + 1)"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6" /></svg>
          </button>
          <span class="page-total">共 {{ pagination.total }} 个项目</span>
        </div>
      </template>

      <!-- 编辑弹窗 -->
      <div v-if="editModalVisible" class="glass-overlay" @click.self="editModalVisible = false">
        <div class="glass-surface-modal edit-modal">
          <h2 class="modal-title">编辑项目</h2>
          <div class="modal-field">
            <label class="field-label">项目名称 <span class="required">*</span></label>
            <input
              v-model="editForm.title"
              class="glass-input-base modal-input"
              maxlength="100"
              placeholder="请输入项目名称"
            />
          </div>
          <div class="modal-field">
            <label class="field-label">项目描述</label>
            <textarea
              v-model="editForm.description"
              class="glass-textarea-base modal-textarea"
              maxlength="500"
              rows="3"
              placeholder="请输入项目描述（可选）"
            />
          </div>
          <div v-if="editError" class="modal-error">{{ editError }}</div>
          <div class="modal-actions">
            <button class="glass-btn-base glass-btn-secondary" @click="editModalVisible = false">取消</button>
            <button
              class="glass-btn-base glass-btn-primary"
              :disabled="editLoading || !editForm.title.trim()"
              @click="handleEdit"
            >
              {{ editLoading ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <ConfirmDialog
      v-model="deleteConfirmVisible"
      title="删除项目"
      :message="deleteMessage"
      confirm-text="删除"
      type="danger"
      @confirm="doDelete"
    />
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import AppLayout from '@/layout/AppLayout.vue'
import ProjectCreateModeDialog from './components/ProjectCreateModeDialog.vue'
import DirectorProjectDialog from './components/DirectorProjectDialog.vue'
import { getProjectList, updateProject, deleteProject } from '@/api/project'

const router = useRouter()

// 新建项目模式选择
const modeDialogVisible = ref(false)
const directorDialogVisible = ref(false)

function openCreateModeDialog() {
  modeDialogVisible.value = true
}

function handleModeSelect(mode) {
  if (mode === 'novel') {
    router.push('/home')
  } else if (mode === 'director') {
    directorDialogVisible.value = true
  }
}

const loading = ref(false)
const projects = ref([])
const pagination = ref({ page: 1, page_size: 8, total: 0, total_pages: 0 })
const searchInput = ref('')
const searchQuery = ref('')

// 编辑弹窗
const editModalVisible = ref(false)
const editLoading = ref(false)
const editError = ref('')
const editForm = ref({ id: '', title: '', description: '' })

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  const day = d.getDate()
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  return `${year}年${month}月${day}日 ${hour}时${minute}分`
}

// 分页展示逻辑
const displayPages = computed(() => {
  const { page, total_pages } = pagination.value
  if (total_pages <= 7) return Array.from({ length: total_pages }, (_, i) => i + 1)
  const pages = []
  pages.push(1)
  const start = Math.max(2, page - 2)
  const end = Math.min(total_pages - 1, page + 2)
  if (start > 2) pages.push('...')
  for (let i = start; i <= end; i++) pages.push(i)
  if (end < total_pages - 1) pages.push('...')
  pages.push(total_pages)
  return pages
})

async function fetchProjects(page = 1) {
  loading.value = true
  try {
    const res = await getProjectList({ page, page_size: 8, search: searchQuery.value })
    projects.value = res.projects || []
    pagination.value = res.pagination || { page, page_size: 8, total: 0, total_pages: 0 }
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  searchQuery.value = searchInput.value.trim()
  fetchProjects(1)
}

function clearSearch() {
  searchInput.value = ''
  searchQuery.value = ''
  fetchProjects(1)
}

function changePage(page) {
  fetchProjects(page)
}

function openEditModal(project) {
  editForm.value = { id: project.id, title: project.title || '', description: project.description || '' }
  editError.value = ''
  editModalVisible.value = true
}

async function handleEdit() {
  if (!editForm.value.title.trim()) {
    editError.value = '项目名称不能为空'
    return
  }
  editLoading.value = true
  editError.value = ''
  try {
    const updated = await updateProject(editForm.value.id, {
      title: editForm.value.title.trim(),
      description: editForm.value.description?.trim() || null,
    })
    const idx = projects.value.findIndex(p => p.id === editForm.value.id)
    if (idx !== -1) projects.value[idx] = updated
    editModalVisible.value = false
    ElMessage.success('项目已更新')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    editLoading.value = false
  }
}

const deleteConfirmVisible = ref(false)
const deleteTarget = ref(null)
const deleteMessage = computed(() => `确定要删除项目"${deleteTarget.value?.title || '未命名项目'}"吗？此操作无法撤销。`)

async function confirmDelete(project) {
  deleteTarget.value = project
  deleteConfirmVisible.value = true
}

async function doDelete() {
  try {
    await deleteProject(deleteTarget.value.id)
    ElMessage.success('项目已删除')
    fetchProjects(pagination.value.page)
  } catch {
    // 用户取消
  }
}

onMounted(() => fetchProjects())
</script>

<style scoped>
.workspace-list-page {
  max-width: 1600px;
  margin: 0 auto;
  padding: 2rem 2.5rem;
  animation: fadeIn 0.3s ease-out;
}

/* Header */
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.header-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--glass-text-primary);
}

.header-subtitle {
  font-size: 0.875rem;
  color: var(--glass-text-tertiary);
  margin-top: 0.25rem;
}

.header-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.search-input {
  width: 16rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.search-btn,
.clear-btn {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

/* Create card */
.grid-create {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

@media (min-width: 768px) {
  .grid-create { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .grid-create { grid-template-columns: repeat(3, 1fr); }
}
@media (min-width: 1280px) {
  .grid-create { grid-template-columns: repeat(4, 1fr); }
}

.create-card {
  padding: 1.5rem;
  min-height: 8rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  background: linear-gradient(135deg, rgba(47,123,255,0.05), rgba(92,168,255,0.05), rgba(47,123,255,0.06));
  transition: all 0.3s;
}

.create-card:hover {
  background: linear-gradient(135deg, rgba(47,123,255,0.1), rgba(92,168,255,0.1), rgba(47,123,255,0.12));
}

.create-icon-wrap {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, var(--glass-accent-from), var(--glass-accent-to));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px var(--glass-accent-shadow-soft);
  transition: all 0.3s;
}

.create-card:hover .create-icon-wrap {
  transform: scale(1.1);
  box-shadow: 0 6px 16px var(--glass-accent-shadow-strong);
}

.create-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--glass-text-secondary);
  transition: color 0.3s;
}

.create-card:hover .create-text {
  color: var(--glass-text-primary);
}

/* Project grid */
.project-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 768px) {
  .project-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .project-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (min-width: 1280px) {
  .project-grid { grid-template-columns: repeat(4, 1fr); }
}

/* Project card */
.project-card {
  position: relative;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s;
}

.project-card:hover {
  border-color: rgba(47, 123, 255, 0.3);
}

.card-hover-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(47,123,255,0.05), rgba(168,85,247,0.05));
  opacity: 0;
  transition: opacity 0.5s;
  pointer-events: none;
  border-radius: inherit;
}

.project-card:hover .card-hover-overlay {
  opacity: 1;
}

.card-content {
  padding: 1.25rem;
  position: relative;
  z-index: 1;
}

.card-actions {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: flex;
  gap: 0.375rem;
  z-index: 10;
  opacity: 0;
  transition: opacity 0.2s;
}

.project-card:hover .card-actions {
  opacity: 1;
}

.action-btn {
  padding: 0.375rem;
  border-radius: 0.5rem;
}

/* Novel preview */
.card-novel-preview {
  display: flex;
  align-items: flex-start;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--glass-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

/* 导演模式描述：预留 2 行高度，margin-bottom 与 .card-novel-preview 保持一致，让底部图标/时间与创作模式卡片对齐 */
.director-desc {
  min-height: calc(2 * 0.8125rem * 1.5);
}
.preview-placeholder {
  color: var(--glass-text-tertiary);
  opacity: 0.7;
}

/* Card title */
.card-title-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.375rem;
  padding-right: 4.5rem; /* 给右上角操作按钮留位置 */
}
.card-mode-icon {
  flex-shrink: 0;
}
.card-mode-icon-novel { color: var(--glass-accent-from); }
.card-mode-icon-director { color: #7c3aed; }

.card-title {
  flex: 1;
  min-width: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color 0.2s;
}

.project-card:hover .card-title {
  color: var(--glass-tone-info-fg);
}

/* Card stats */
.card-stats {
  margin-bottom: 0.625rem;
}

.stats-items {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-accent-from);
}

/* Card footer */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-time {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.6875rem;
  color: var(--glass-text-tertiary);
}

/* Skeleton */
.skeleton-card {
  padding: 1.5rem;
  animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-line {
  height: 0.75rem;
  background: var(--glass-bg-muted);
  border-radius: 0.375rem;
  margin-bottom: 0.5rem;
}

.skeleton-line.title-line {
  height: 1rem;
  width: 70%;
  margin-bottom: 0.75rem;
}

.skeleton-line.short {
  width: 40%;
  margin-bottom: 0;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 3rem 0;
}

.empty-icon {
  width: 4rem;
  height: 4rem;
  background: var(--glass-bg-muted);
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
}

.empty-title {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--glass-text-primary);
  margin-bottom: 0.5rem;
}

.empty-desc {
  font-size: 0.875rem;
  color: var(--glass-text-secondary);
}

/* Pagination */
.pagination-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 4rem;
}

.page-btn {
  padding: 0.5rem 0.875rem;
  font-size: 0.875rem;
  min-width: 2.25rem;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-ellipsis {
  color: var(--glass-text-tertiary);
  padding: 0 0.25rem;
  font-size: 0.875rem;
}

.page-total {
  margin-left: 1rem;
  font-size: 0.875rem;
  color: var(--glass-text-tertiary);
}

/* Edit modal */
.edit-modal {
  padding: 1.5rem;
  width: 100%;
  max-width: 28rem;
  margin: 0 1rem;
  animation: fadeIn 0.15s ease-out;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  margin-bottom: 1rem;
}

.modal-field {
  margin-bottom: 1rem;
}

.field-label {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-text-secondary);
  margin-bottom: 0.375rem;
}

.required {
  color: var(--glass-tone-danger-fg);
}

.modal-input {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.modal-textarea {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  resize: vertical;
}

.modal-error {
  border-radius: 0.75rem;
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.1);
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #dc2626;
  margin-bottom: 0.75rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.modal-actions .glass-btn-base {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}
</style>
