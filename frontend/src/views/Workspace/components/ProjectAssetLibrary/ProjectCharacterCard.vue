<template>
  <div class="character-card glass-surface-elevated">
    <!-- 标题行：名称 + 操作按钮 -->
    <div class="card-title-row">
      <span class="card-name">{{ character.name }}</span>
      <div class="card-title-actions">
        <button class="title-action-btn title-action-btn-import" title="从资产中心导入" @click.stop="$emit('import-from-global', { assetType: 'character', assetId: character.id })">
          <CircleArrowDown :size="14" />
        </button>
        <button class="title-action-btn title-action-btn-edit" title="编辑" @click.stop="$emit('edit', character)">
          <Pencil :size="14" />
        </button>
        <button class="title-action-btn title-action-btn-danger" title="删除" @click.stop="handleDelete">
          <Trash2 :size="14" />
        </button>
      </div>
    </div>

    <!-- 图片区域 3:2 -->
    <div class="card-image" @click="handlePreview">
      <img v-if="character.image_url" :src="character.thumbnail_url || character.image_url" :alt="character.name" class="card-img" @error="onImgError" />
      <div v-else-if="isUploading" class="card-placeholder card-placeholder--uploading">
        <div class="upload-spinner" />
        <span>上传中...</span>
      </div>
      <div v-else class="card-placeholder">
        <svg class="placeholder-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      </div>

      <!-- hover overlay 操作按钮 -->
      <div v-if="character.gen_status !== 'generating' && !isUploading" class="card-overlay-actions">
        <button class="glass-btn-base glass-btn-secondary action-btn" title="上传" @click.stop="triggerUpload">
          <Upload :size="14" />
        </button>
        <button v-if="character.image_url" class="glass-btn-base glass-btn-secondary action-btn" title="下载" @click.stop="$emit('download', character)">
          <Download :size="14" />
        </button>
        <button v-if="character.image_url" class="glass-btn-base glass-btn-tone-info action-btn" title="AI 改图" @click.stop="$emit('modify', { asset: character, assetType: 'character' })">
          <WandSparkles :size="14" />
        </button>
        <button class="glass-btn-base glass-btn-secondary action-btn" title="重新生成" @click.stop="handleGenerate">
          <RefreshCw :size="14" />
        </button>
      </div>

      <!-- 火山同步（右对齐，已同步 hover 显示） -->
      <div v-if="character.gen_status !== 'generating' && character.image_url && character.volc_private_asset_id" class="card-overlay-actions card-overlay-actions--right">
        <button class="glass-btn-base action-btn volc-synced" title="已同步到火山" disabled>
          <CloudCheck :size="14" />
        </button>
      </div>

      <!-- 未同步火山角标（与资产中心一致） -->
      <span
        v-if="character.gen_status !== 'generating' && character.image_url && !character.volc_private_asset_id && !volcSyncing"
        class="volc-unsynced-badge"
        @click.stop="$emit('sync-volc', { assetType: 'character', assetId: character.id })"
      >未同步</span>
      <span
        v-if="character.gen_status !== 'generating' && character.image_url && !character.volc_private_asset_id && volcSyncing"
        class="volc-unsynced-badge volc-unsynced-badge--syncing"
      >同步中</span>

      <!-- 生成中 overlay -->
      <div v-if="character.gen_status === 'generating'" class="card-status-overlay">
        <div class="overlay-spinner" />
        <span>生成中...</span>
      </div>

      <!-- 失败标记 -->
      <div v-if="character.gen_status === 'failed'" class="card-status-overlay card-overlay-failed">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-danger-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
        <span>生成失败</span>
      </div>
    </div>

    <!-- 底部描述 -->
    <div v-if="character.description" class="card-desc">{{ character.description }}</div>

    <!-- 音色设置 -->
    <div class="card-voice">
      <VoiceSettings
        :character-id="character.id"
        :character-name="character.name"
        :custom-voice-url="character.custom_voice_url"
        :compact="true"
        :upload-handler="voiceUploadHandler"
        @voice-design="$emit('voiceDesign', character)"
        @voice-select="$emit('voiceSelect', character)"
        @voice-changed="$emit('voiceChanged', character)"
      />
    </div>

    <!-- 无图时显示生成按钮 -->
    <div v-if="!character.image_url && character.gen_status !== 'generating'" class="card-generate">
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
import { Upload, WandSparkles, RefreshCw, Download, CircleArrowDown, Pencil, Trash2, CloudCheck } from '@lucide/vue'
import { useProjectAssetStore } from '@/store/project_asset'
import { validateImageFile } from '@/utils/imageValidate'
import VoiceSettings from '@/views/AssetsCenter/components/VoiceSettings.vue'

const props = defineProps({
  character: { type: Object, required: true },
  projectId: String,
  voiceUploadHandler: { type: Function, default: null },
})

const store = useProjectAssetStore()
const volcSyncing = computed(() => store.volcSyncingIds.has(props.character.id) || store.isAssetBatchSyncing(props.character.id))
const isUploading = computed(() => store.uploadingIds.includes(props.character.id))

const emit = defineEmits(['preview', 'generate', 'upload', 'modify', 'download', 'edit', 'delete', 'import-from-global', 'sync-volc', 'voiceDesign', 'voiceSelect', 'voiceChanged'])
const fileInput = ref(null)

function handlePreview() {
  if (props.character.image_url) {
    emit('preview', { imageUrl: props.character.image_url })
  }
}

function onImgError(e) {
  const img = e.target
  if (img.dataset.fallback) return
  img.dataset.fallback = '1'
  img.src = props.character.image_url
}

function handleGenerate() {
  emit('generate', { assetType: 'character', assetId: props.character.id })
}

function handleDelete() {
  emit('delete', { assetType: 'character', assetId: props.character.id, name: props.character.name })
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
  emit('upload', { assetType: 'character', assetId: props.character.id, file: validatedFile })
  e.target.value = ''
}
</script>

<style scoped>
.character-card {
  border-radius: var(--glass-radius-xl, 0.75rem);
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s ease;
}

.character-card:hover {
  box-shadow: var(--glass-shadow-md);
}

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

.card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
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
  top: 0.5rem;
  left: 0.5rem;
  display: flex;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 2;
}
.card-overlay-actions--right {
  left: auto;
  right: 0.5rem;
}

.card-image:hover .card-overlay-actions {
  opacity: 1;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 9999px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* === 生成中/失败 overlay === */
.card-status-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  color: white;
  font-size: 0.75rem;
}

.card-overlay-failed {
  background: rgba(0, 0, 0, 0.6);
}

.overlay-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* === 底部描述 === */
.card-desc {
  padding-top: 0.5rem;
  font-size: 0.75rem;
  color: var(--glass-text-tertiary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* === 生成按钮 === */
.card-generate {
  padding-top: 0.375rem;
}

/* === 音色设置 === */
.card-voice {
  padding-top: 0.5rem;
}

.generate-btn {
  width: 100%;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  border-radius: var(--glass-radius-md);
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
