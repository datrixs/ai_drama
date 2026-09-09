<template>
  <div class="modal-overlay glass-overlay" @click.self="onClose">
    <div class="modal-dialog glass-surface-modal">
      <div class="dialog-header">
        <div class="dialog-title-row">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <h3 class="dialog-title">批量上传本地图片</h3>
        </div>
        <button class="glass-btn-base glass-btn-soft close-btn" :disabled="uploading" @click="onClose">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>

      <!-- 类型 tab -->
      <div class="dialog-tabs">
        <button
          v-for="t in typeTabs"
          :key="t.value"
          :class="['tab-btn', { 'tab-btn-active': activeType === t.value }]"
          :disabled="uploading"
          @click="activeType = t.value"
        >
          {{ t.label }}
        </button>
        <span class="tab-hint">上传后将作为该类型资产</span>
      </div>

      <!-- 拖拽 / 点击 上传区 -->
      <div
        class="drop-zone"
        :class="{ 'drop-zone--active': isDragging }"
        @click="triggerPick"
        @dragover.prevent="isDragging = true"
        @dragenter.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,image/gif,image/heic,image/heif"
          multiple
          style="display: none"
          @change="onFilePicked"
        />
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <p class="drop-title">{{ isDragging ? '松开鼠标以上传' : uploading ? '批量上传中...' : '点击或拖拽图片到此处上传' }}</p>
        <p class="drop-hint">{{ uploading ? `已上传 ${uploadedCount}/${files.length} 项` : '支持多选 · 文件名将作为资产名称' }}</p>
      </div>

      <!-- 文件列表 -->
      <div v-if="files.length > 0" class="file-list">
        <div class="file-list-header">
          <span>待上传 {{ files.length }} 项</span>
          <button v-if="!uploading" class="clear-btn" @click="files = []">清空</button>
        </div>
        <div class="file-list-body">
          <div v-for="(item, idx) in fileItems" :key="idx" class="file-row">
            <div class="file-thumb">
              <img v-if="item.preview" :src="item.preview" :alt="item.name" />
              <span v-else class="file-thumb-fallback">{{ item.name.charAt(0) }}</span>
            </div>
            <div class="file-info">
              <span class="file-name">{{ item.name }}</span>
              <span class="file-meta">{{ formatSize(item.file.size) }}</span>
            </div>
            <span v-if="item.status === 'done'" class="file-status file-status--done">已上传</span>
            <span v-else-if="item.status === 'uploading'" class="file-status file-status--uploading">上传中...</span>
            <span v-else-if="item.status === 'failed'" class="file-status file-status--failed">失败</span>
            <button
              v-else
              class="file-remove"
              :disabled="uploading"
              @click.stop="removeFile(idx)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
        </div>
      </div>

      <div class="dialog-footer">
        <span class="footer-summary">
          <template v-if="uploadedCount > 0">已上传 {{ uploadedCount }}/{{ files.length }}</template>
        </span>
        <button class="glass-btn-base glass-btn-secondary footer-btn" :disabled="uploading" @click="onClose">取消</button>
        <button
          class="glass-btn-base glass-btn-primary footer-btn"
          :disabled="files.length === 0 || uploading"
          @click="onConfirm"
        >
          {{ uploading ? `上传中 ${uploadedCount}/${files.length}` : `上传 ${files.length} 项` }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectAssetStore } from '@/store/project_asset'
import { validateImageFile } from '@/utils/imageValidate'

const props = defineProps({
  visible: Boolean,
  projectId: { type: String, required: true },
})
const emit = defineEmits(['close', 'done'])

const typeTabs = [
  { value: 'character', label: '角色' },
  { value: 'location', label: '场景' },
  { value: 'prop', label: '道具' },
]

const activeType = ref('character')
const files = ref([]) // [{file, preview, status, error}]
const isDragging = ref(false)
const uploading = ref(false)
const fileInput = ref(null)
const store = useProjectAssetStore()

const fileItems = computed(() => files.value.map((f, i) => ({ ...f, idx: i })))
const uploadedCount = computed(() => files.value.filter(f => f.status === 'done').length)

function triggerPick() {
  if (uploading.value) return
  if (fileInput.value) {
    fileInput.value.value = ''
    fileInput.value.click()
  }
}

async function addFiles(fileList) {
  const arr = Array.from(fileList || []).filter(f => f.type.startsWith('image/'))
  for (const f of arr) {
    const { valid, error, file: validatedFile } = await validateImageFile(f)
    if (!valid) {
      ElMessage.error(error)
      continue
    }
    const name = validatedFile.name.replace(/\.[^.]+$/, '').slice(0, 60) || `资产${files.value.length + 1}`
    files.value.push({
      file: validatedFile,
      name,
      preview: URL.createObjectURL(validatedFile),
      status: 'pending',
    })
  }
}

function onFilePicked(e) {
  addFiles(e.target.files)
}

function onDrop(e) {
  isDragging.value = false
  if (uploading.value) return
  addFiles(e.dataTransfer.files)
}

function removeFile(idx) {
  if (uploading.value) return
  files.value.splice(idx, 1)
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function onConfirm() {
  if (files.value.length === 0 || uploading.value) return
  uploading.value = true
  const total = files.value.length
  let ok = 0
  let failed = 0
  const syncErrors = []  // 上传成功但资产库同步失败的明细
  try {
    for (const item of files.value) {
      if (item.status === 'done') continue
      item.status = 'uploading'
      item.error = null
      try {
        const created = await store.createAsset(props.projectId, activeType.value, { name: item.name }, { silent: true })
        const assetId = created?.id || created?.[activeType.value]?.id
        if (!assetId) throw new Error('创建失败')
        const res = await store.uploadImage(props.projectId, activeType.value, assetId, item.file, { silent: true })
        item.status = 'done'
        ok++
        if (res?.sync_error) {
          syncErrors.push(`${item.name}：${res.sync_error}`)
        }
      } catch (e) {
        item.status = 'failed'
        item.error = e?.message || '上传失败'
        failed++
      }
    }
    if (ok > 0 && failed === 0) {
      ElMessage.success(`已上传 ${ok}/${total} 项${syncErrors.length ? `，${syncErrors.length} 项资产库同步失败` : ''}`)
    } else if (ok > 0 && failed > 0) {
      ElMessage.warning(`已上传 ${ok}/${total} 项，${failed} 项失败`)
    } else if (failed > 0) {
      ElMessage.error(`全部 ${total} 项上传失败`)
    }
    // 同步失败原因明细：逐条 warning 展示
    syncErrors.slice(0, 5).forEach(msg => ElMessage.warning(`资产库同步失败 - ${msg}`))
    if (syncErrors.length > 5) {
      ElMessage.warning(`还有 ${syncErrors.length - 5} 项资产库同步失败未展示`)
    }
    if (ok > 0) {
      // 至少一项成功 → 通知父组件刷新
      emit('done')
    }
  } finally {
    uploading.value = false
  }
}

function onClose() {
  if (uploading.value) return
  emit('close')
}

watch(() => props.visible, (v) => {
  if (v) {
    activeType.value = 'character'
    files.value = []
    isDragging.value = false
    uploading.value = false
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-dialog {
  max-width: 640px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
}

.dialog-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--glass-text-tertiary);
}

.close-btn:hover:not(:disabled) {
  color: var(--glass-text-secondary);
}

.close-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dialog-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 0 20px;
  padding-top: 8px;
  flex-wrap: wrap;
}

.tab-btn {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-tertiary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.tab-btn:hover:not(:disabled) {
  color: var(--glass-text-primary);
}

.tab-btn-active {
  color: var(--glass-tone-info-fg);
  background: var(--glass-tone-info-bg);
}

.tab-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tab-hint {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  margin-left: 4px;
}

.drop-zone {
  margin: 12px 20px 0;
  padding: 2rem 1rem;
  border: 2px dashed var(--glass-stroke-base);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--glass-text-tertiary);
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
}

.drop-zone:hover {
  border-color: var(--glass-stroke-focus);
  color: var(--glass-tone-info-fg);
  background: var(--glass-tone-info-bg);
}

.drop-zone--active {
  border-color: var(--glass-stroke-focus);
  background: var(--glass-tone-info-bg);
  color: var(--glass-tone-info-fg);
}

.drop-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-primary);
  margin: 0;
}

.drop-hint {
  font-size: 12px;
  margin: 0;
}

.file-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 12px 20px 0;
  min-height: 0;
  overflow: hidden;
}

.file-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--glass-text-secondary);
  padding-bottom: 6px;
}

.clear-btn {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}

.clear-btn:hover {
  color: var(--glass-text-primary);
}

.file-list-body {
  flex: 1;
  overflow-y: auto;
  max-height: 220px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 8px;
  background: var(--glass-bg-muted);
}

.file-thumb {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  overflow: hidden;
  background: var(--glass-bg-surface);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-thumb-fallback {
  font-size: 14px;
  font-weight: 600;
  color: var(--glass-text-tertiary);
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.file-name {
  font-size: 13px;
  color: var(--glass-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 11px;
  color: var(--glass-text-tertiary);
}

.file-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

.file-status--done {
  color: var(--glass-tone-success-fg, #16a34a);
  background: var(--glass-tone-success-bg, rgba(22, 163, 74, 0.1));
}

.file-status--uploading {
  color: var(--glass-tone-info-fg);
  background: var(--glass-tone-info-bg);
}

.file-status--failed {
  color: var(--glass-tone-danger-fg, #dc2626);
  background: var(--glass-tone-danger-bg, rgba(220, 38, 38, 0.1));
}

.file-remove {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--glass-text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
}

.file-remove:hover:not(:disabled) {
  background: var(--glass-bg-surface);
  color: var(--glass-text-primary);
}

.file-remove:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  align-items: center;
  padding: 12px 20px;
  margin-top: 12px;
}

.footer-summary {
  flex: 1;
  font-size: 13px;
  color: var(--glass-text-secondary);
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}

.footer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
