<template>
  <AppLayout>
    <div class="canvas-list-page">
      <div class="canvas-header">
        <div class="header-info">
          <h1 class="header-title">无限画布</h1>
          <p class="header-subtitle">在无限画布上自由放置文本、图片、视频节点，串联你的创作灵感。</p>
        </div>
        <button class="glass-btn-base glass-btn-primary create-btn" :disabled="creating" @click="handleCreate">
          <svg v-if="creating" class="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14" /><path d="M5 12h14" /></svg>
          新建画布
        </button>
      </div>

      <div v-if="loading && documents.length === 0" class="canvas-empty">
        <LoaderCircle :size="22" class="spin" />
        <span>加载中...</span>
      </div>

      <div v-else-if="documents.length === 0" class="canvas-empty">
        <div class="empty-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect width="8" height="8" x="3" y="3" rx="2" /><path d="M7 11v4a2 2 0 0 0 2 2h4" /><rect width="8" height="8" x="13" y="13" rx="2" />
          </svg>
        </div>
        <p class="empty-title">暂无画布</p>
        <p class="empty-hint">点击右上角"新建画布"开始创作</p>
      </div>

      <div v-else class="canvas-grid">
        <div
          v-for="doc in documents"
          :key="doc.id"
          class="canvas-card glass-surface"
          @click="openCanvas(doc.id)"
        >
          <div class="card-thumb">
            <div class="thumb-placeholder">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
                <rect width="8" height="8" x="3" y="3" rx="2" /><path d="M7 11v4a2 2 0 0 0 2 2h4" /><rect width="8" height="8" x="13" y="13" rx="2" />
              </svg>
            </div>
            <button class="card-delete-btn" title="删除画布" @click.stop="handleDelete(doc)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
            </button>
          </div>
          <div class="card-body">
            <div class="card-title">{{ doc.title || '未命名画布' }}</div>
            <div class="card-meta">{{ formatTime(doc.update_time) || formatTime(doc.last_opened_at) || formatTime(doc.create_time) }}</div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        v-model="confirmVisible"
        title="删除画布"
        :message="`确定要删除画布「${pendingDelete?.title || ''}」吗？画布下的所有节点和连线都会一并删除，且不可恢复。`"
        confirm-text="删除"
        type="danger"
        @confirm="confirmDelete"
      />
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { LoaderCircle } from '@lucide/vue'
import AppLayout from '@/layout/AppLayout.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useCanvasStore } from '@/store/canvas'

const router = useRouter()
const { documents, loading, fetchDocuments, createDocument, removeDocument } = useCanvasStore()

const creating = ref(false)
const confirmVisible = ref(false)
const pendingDelete = ref(null)

onMounted(async () => {
  await fetchDocuments()
})

async function handleCreate() {
  if (creating.value) return
  creating.value = true
  try {
    const doc = await createDocument('')
    ElMessage.success('画布已创建')
    router.push(`/canvas/${doc.id}`)
  } finally {
    creating.value = false
  }
}

function openCanvas(id) {
  router.push(`/canvas/${id}`)
}

function handleDelete(doc) {
  pendingDelete.value = doc
  confirmVisible.value = true
}

async function confirmDelete() {
  if (!pendingDelete.value) return
  try {
    await removeDocument(pendingDelete.value.id)
    ElMessage.success('画布已删除')
    pendingDelete.value = null
  } catch (e) {
    // request 拦截器已弹错误提示
  }
}

function formatTime(s) {
  if (!s) return ''
  return s.replace('T', ' ').slice(0, 16)
}
</script>

<style scoped>
.canvas-list-page {
  max-width: 80rem;
  margin: 0 auto;
  padding: 2rem 1.5rem 4rem;
}

.canvas-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.75rem;
}

.header-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  margin: 0;
}

.header-subtitle {
  font-size: 0.875rem;
  color: var(--glass-text-secondary);
  margin: 0.25rem 0 0;
}

.create-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(47, 123, 255, 0.24);
}

.create-btn:hover:not(:disabled) {
  opacity: 0.92;
}

.create-btn:disabled {
  background: #c8d4e8;
  cursor: not-allowed;
  box-shadow: none;
}

.canvas-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5rem 1rem;
  color: var(--glass-text-tertiary);
  font-size: 0.875rem;
  gap: 0.5rem;
}

.empty-icon {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  background: rgba(47, 123, 255, 0.08);
  color: #2f7bff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.5rem;
}

.empty-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--glass-text-secondary);
  margin: 0;
}

.empty-hint {
  margin: 0;
}

.canvas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.canvas-card {
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  background: #fff;
  border: 1px solid rgba(111, 126, 153, 0.14);
}

.canvas-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.card-thumb {
  position: relative;
  aspect-ratio: 4 / 3;
  background: linear-gradient(135deg, #f0f5ff 0%, #e0eafc 100%);
}

.thumb-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2f7bff;
  opacity: 0.55;
}

.card-delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.15s ease;
}

.canvas-card:hover .card-delete-btn {
  opacity: 1;
}

.card-delete-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.card-body {
  padding: 12px 14px;
}

.card-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  font-size: 0.75rem;
  color: #9ca3af;
  margin-top: 4px;
}

.spin {
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
