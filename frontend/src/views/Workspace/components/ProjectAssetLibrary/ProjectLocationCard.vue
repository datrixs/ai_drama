<template>
  <div class="location-card glass-surface-elevated" :class="{ 'card-generating': location.gen_status === 'generating' }">
    <!-- 标题行：名称 + 编辑/删除 -->
    <div class="card-title-row">
      <span class="card-name">{{ location.name }}</span>
      <div class="card-title-actions">
        <button class="title-action-btn title-action-btn-import" title="从资产中心导入" @click.stop="$emit('import-from-global', { assetType: assetType, assetId: location.id })">
          <CircleArrowDown :size="14" />
        </button>
        <button class="title-action-btn title-action-btn-edit" title="编辑" @click.stop="$emit('edit', location)">
          <Pencil :size="14" />
        </button>
        <button class="title-action-btn title-action-btn-danger" title="删除" @click.stop="handleDelete">
          <Trash2 :size="14" />
        </button>
      </div>
    </div>

    <!-- 图片区域 3:2 -->
    <div class="card-image" @click="handlePreview">
      <img v-if="location.image_url" :src="location.thumbnail_url || location.image_url" :alt="location.name" class="card-img" @error="onImgError" />
      <div v-else-if="isUploading" class="card-placeholder card-placeholder--uploading">
        <div class="upload-spinner" />
        <span>上传中...</span>
      </div>
      <div v-else class="card-placeholder">
        <ImageIcon v-if="assetType === 'location'" :size="48" class="placeholder-icon" />
        <Diamond v-else :size="48" class="placeholder-icon" />
      </div>

      <!-- hover overlay 操作按钮 -->
      <div v-if="location.gen_status !== 'generating' && !isUploading" class="card-overlay-actions">
        <button class="glass-btn-base glass-btn-secondary action-btn" title="上传" @click.stop="triggerUpload">
          <Upload :size="14" />
        </button>
        <button v-if="location.image_url" class="glass-btn-base glass-btn-secondary action-btn" title="下载" @click.stop="$emit('download', location)">
          <Download :size="14" />
        </button>
        <button v-if="location.image_url" class="glass-btn-base glass-btn-tone-info action-btn" title="AI 改图" @click.stop="$emit('modify', { asset: location, assetType: assetType })">
          <WandSparkles :size="14" />
        </button>
        <button class="glass-btn-base glass-btn-secondary action-btn" title="重新生成" @click.stop="handleGenerate">
          <RefreshCw :size="14" />
        </button>
      </div>

      <!-- 火山同步（右对齐，已同步 hover 显示） -->
      <div v-if="location.gen_status !== 'generating' && location.image_url && location.volc_private_asset_id" class="card-overlay-actions card-overlay-actions--right">
        <button class="glass-btn-base action-btn volc-synced" title="已同步到火山" disabled>
          <CloudCheck :size="14" />
        </button>
      </div>

      <!-- 未同步火山角标（与资产中心一致） -->
      <span
        v-if="location.gen_status !== 'generating' && location.image_url && !location.volc_private_asset_id && !volcSyncing"
        class="volc-unsynced-badge"
        @click.stop="$emit('sync-volc', { assetType: assetType, assetId: location.id })"
      >未同步</span>
      <span
        v-if="location.gen_status !== 'generating' && location.image_url && !location.volc_private_asset_id && volcSyncing"
        class="volc-unsynced-badge volc-unsynced-badge--syncing"
      >同步中</span>

      <!-- 生成中 overlay -->
      <div v-if="location.gen_status === 'generating'" class="card-status-overlay">
        <div class="overlay-spinner" />
        <span>生成中...</span>
      </div>

      <!-- 失败标记 -->
      <div v-if="location.gen_status === 'failed'" class="card-status-overlay card-overlay-failed">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-danger-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
        <span>生成失败</span>
      </div>
    </div>

    <!-- 地点/时间标签 -->
    <div v-if="location.place || location.time" class="card-meta">
      <span v-if="location.place" class="meta-tag">{{ location.place }}</span>
      <span v-if="location.time" class="meta-tag">{{ location.time }}</span>
    </div>

    <!-- 底部描述 -->
    <div v-if="location.description" class="card-desc">{{ location.description }}</div>

    <!-- 无图时显示生成按钮 -->
    <div v-if="!location.image_url && location.gen_status !== 'generating'" class="card-generate">
      <button class="glass-btn-base glass-btn-primary generate-btn" @click="handleGenerate">
        <RefreshCw :size="14" />
        生成图片
      </button>
    </div>

    <!-- 隐藏文件输入 -->
    <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,image/gif,image/heic,image/heif" style="display:none" @change="handleFileChange" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, WandSparkles, RefreshCw, Download, CircleArrowDown, Pencil, Trash2, Image as ImageIcon, Diamond, CloudCheck } from '@lucide/vue'
import { useProjectAssetStore } from '@/store/project_asset'
import { validateImageFile } from '@/utils/imageValidate'

const props = defineProps({
  location: { type: Object, required: true },
  projectId: String,
  assetType: { type: String, default: 'location' },
})

const store = useProjectAssetStore()
const volcSyncing = computed(() => store.volcSyncingIds.has(props.location.id) || store.isAssetBatchSyncing(props.location.id))
const isUploading = computed(() => store.uploadingIds.includes(props.location.id))

const emit = defineEmits(['preview', 'edit', 'generate', 'upload', 'modify', 'delete', 'download', 'import-from-global', 'sync-volc'])
const fileInput = ref(null)

function handlePreview() {
  if (props.location.image_url) {
    emit('preview', { imageUrl: props.location.image_url })
  }
}

function onImgError(e) {
  const img = e.target
  if (img.dataset.fallback) return
  img.dataset.fallback = '1'
  img.src = props.location.image_url
}

function handleGenerate() {
  emit('generate', { assetType: props.assetType, assetId: props.location.id })
}

function handleDelete() {
  emit('delete', { assetType: props.assetType, assetId: props.location.id, name: props.location.name })
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const { valid, error, file: validatedFile } = await validateImageFile(file)
  if (!valid) {
    ElMessage.error(error)
    return
  }
  emit('upload', { assetType: props.assetType, assetId: props.location.id, file: validatedFile })
  e.target.value = ''
}
</script>

<style scoped>
.location-card {
  border-radius: var(--glass-radius-xl, 0.75rem);
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s ease;
}

.location-card:hover {
  box-shadow: var(--glass-shadow-md);
}

.card-generating { opacity: 0.85; }

/* === 标题行 === */
.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.card-name {
  font-weight: 600;
  font-size: 0.8125rem;
  color: var(--glass-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.card-title-actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.title-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.6875rem;
  padding: 0.125rem 0.375rem;
  border: none;
  background: transparent;
  border-radius: 0.375rem;
  color: var(--glass-text-secondary);
  transition: all 0.15s ease;
  cursor: pointer;
  white-space: nowrap;
}

.title-action-btn-import {
  color: var(--glass-tone-info-fg);
}

.title-action-btn-import:hover {
  background: var(--glass-tone-info-bg);
  color: var(--glass-tone-info-fg);
}

.title-action-btn-edit:hover {
  background: var(--glass-tone-info-bg);
  color: var(--glass-tone-info-fg);
}

.title-action-btn-danger {
  color: var(--glass-tone-danger-fg);
}

.title-action-btn-danger:hover {
  background: var(--glass-tone-danger-bg);
  color: var(--glass-tone-danger-fg);
}

/* === 图片区域 === */
.card-image {
  position: relative;
  aspect-ratio: 3 / 2;
  background: var(--glass-bg-muted);
  cursor: pointer;
  overflow: hidden;
  border-radius: var(--glass-radius-lg);
}

.card-img { width: 100%; height: 100%; object-fit: cover; }

.card-placeholder {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--glass-bg-muted), var(--glass-bg-surface));
}

.card-placeholder--uploading {
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: var(--glass-text-tertiary);
}

.upload-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.placeholder-icon {
  color: var(--glass-text-tertiary);
  opacity: 0.4;
}

/* === hover overlay 操作按钮 === */
.card-overlay-actions {
  position: absolute;
  top: 0.5rem; left: 0.5rem;
  display: flex; gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 2;
}
.card-overlay-actions--right {
  left: auto;
  right: 0.5rem;
}

.card-image:hover .card-overlay-actions { opacity: 1; }

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 9999px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* === 生成中/失败 overlay === */
.card-status-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem;
  background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
  color: white; font-size: 0.75rem;
}

.card-overlay-failed { background: rgba(0,0,0,0.6); }

.overlay-spinner {
  width: 24px; height: 24px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* === 地点/时间标签 === */
.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  padding-top: 0.375rem;
}

.meta-tag {
  font-size: 0.625rem;
  color: var(--glass-text-tertiary);
  background: var(--glass-bg-muted);
  padding: 0.0625rem 0.375rem;
  border-radius: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* === 底部描述 === */
.card-desc {
  padding-top: 0.5rem;
  font-size: 0.75rem; color: var(--glass-text-tertiary); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;
}

/* === 生成按钮 === */
.card-generate { padding-top: 0.375rem; }

.generate-btn {
  width: 100%; height: 2rem;
  display: flex; align-items: center; justify-content: center; gap: 0.375rem;
  font-size: 0.75rem; border-radius: var(--glass-radius-md);
}

/* === 火山同步状态 === */
.volc-synced {
  cursor: default;
  background: rgba(16, 185, 129, 0.9);
  border-color: transparent;
  color: #fff;
}

/* 未同步火山角标（与资产中心一致） */
.volc-unsynced-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  cursor: pointer;
  z-index: 5;
  transition: background 0.15s ease;
}
.volc-unsynced-badge:hover {
  background: rgba(245, 158, 11, 0.3);
}
.volc-unsynced-badge--syncing {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.3);
  cursor: default;
}
</style>
