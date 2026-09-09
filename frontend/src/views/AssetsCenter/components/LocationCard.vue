<template>
  <div
    class="location-card glass-surface"
    :class="{
      'card-span-3': hasMultipleImages && !isUploading && !isUndoing,
      'location-card--multi': hasMultipleImages && !isUploading && !isUndoing,
      'location-card--platform': isPlatformAsset,
    }"
  >
    <!-- Multi-image selection mode -->
    <div v-if="hasMultipleImages && !isUploading && !isUndoing" class="location-card__multi-area">
      <div class="location-card__multi-header">
        <span class="location-card__name">{{ location.name }}</span>
        <div class="location-card__multi-actions">
          <button class="glass-btn-base glass-btn-secondary action-btn-sm" title="重新生成" :disabled="selectedImage?.gen_status === 'generating'" @click.stop="handleGenerate(location.images.filter(img => img.image_url).length)">
            <RefreshCw :size="12" />
          </button>
        </div>
      </div>
      <ImageCandidateGrid
        :items="locationCandidateItems"
        :model-value="locationSelectedIndex"
        min-height="88px"
        @select="handleSelectLocationImage"
        @confirm="handleConfirmLocationSelection"
        @preview="handleImageClick"
      />
      <!-- 生成中 overlay -->
      <div v-if="selectedImage?.gen_status === 'generating'" class="card-status-overlay">
        <div class="overlay-spinner" />
        <span>{{ generatingLabel }}</span>
      </div>
    </div>

    <!-- Single image mode -->
    <div v-else class="location-card__image-area" @click="handleImageClick()">
      <MediaImageWithLoading
        v-if="displayImageUrl"
        :src="displayImageUrl"
        :thumbnail-src="selectedImage?.thumbnail_url || ''"
        container-class="card-img-container"
        img-class="card-img"
        @click="handleImageClick()"
      />
      <!-- No image placeholder -->
      <div v-if="!displayImageUrl && selectedImage?.gen_status !== 'generating'" class="location-card__no-image">
        <ImageIcon :size="24" />
        <div
          class="glass-btn-base glass-btn-primary generate-btn-inline"
          @click.stop="handleGenerate(imageCount)"
        >
          <WandSparkles :size="14" />
          <span>生成</span>
          <span class="count-pill" @click.stop>
            <select
              :value="imageCount"
              class="count-pill__select"
              @change.stop="setImageCount(Number($event.target.value))"
            >
              <option v-for="n in COUNT_OPTIONS" :key="n" :value="n" class="count-option">{{ n }}</option>
            </select>
          </span>
          <span>张</span>
        </div>
        <button
          class="glass-btn-base glass-btn-secondary generate-btn-inline"
          @click.stop="handleUpload"
        >
          <Upload :size="14" />
          <span>上传图片</span>
        </button>
      </div>
      <!-- 生成中 overlay -->
      <div v-if="selectedImage?.gen_status === 'generating'" class="card-status-overlay">
        <div class="overlay-spinner" />
        <span>{{ generatingLabel }}</span>
      </div>
      <!-- 撤销中 overlay -->
      <div v-if="isUndoing" class="card-status-overlay">
        <div class="overlay-spinner" />
        <span>撤销中...</span>
      </div>
      <!-- 上传中 overlay -->
      <div v-if="isUploading" class="card-status-overlay">
        <div class="overlay-spinner" />
        <span>上传中...</span>
      </div>
      <!-- 失败标记 -->
      <div v-if="selectedImage?.gen_status === 'failed'" class="card-status-overlay card-overlay-failed">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-danger-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
        <span>生成失败</span>
      </div>
      <!-- Hover actions -->
      <div v-if="displayImageUrl && selectedImage?.gen_status !== 'generating' && !isUndoing && !isUploading" class="location-card__hover-actions">
        <button class="glass-btn-base glass-btn-secondary action-btn" title="上传图片" @click.stop="handleUpload">
          <Upload :size="14" />
        </button>
        <button class="glass-btn-base glass-btn-tone-info action-btn" title="AI 改图" @click.stop="handleImageEdit">
          <WandSparkles :size="14" />
        </button>
        <button class="glass-btn-base glass-btn-secondary action-btn" title="重新生成" @click.stop="handleGenerate(1)">
          <RefreshCw :size="14" />
        </button>
        <button
          v-if="selectedImage?.previous_image_url"
          class="glass-btn-base glass-btn-secondary action-btn"
          title="撤销"
          @click.stop="handleUndo"
        >
          <Undo2 :size="14" />
        </button>
      </div>
      <!-- 未同步火山角标 -->
      <span
        v-if="displayImageUrl && !isVolcSynced && !isSyncing"
        class="volc-unsynced-badge"
        @click.stop="handleSyncToVolc"
      >未同步</span>
      <span
        v-if="displayImageUrl && !isVolcSynced && isSyncing"
        class="volc-unsynced-badge volc-unsynced-badge--syncing"
      >同步中</span>
    </div>

    <!-- Info area -->
    <div class="location-card__info">
      <div class="location-card__name-row">
        <div class="location-card__text-block">
          <span class="location-card__name">{{ location.name }}</span>
          <p class="location-card__type-label">{{ label }}</p>
        </div>
        <button class="glass-btn-base glass-btn-soft icon-btn" title="编辑" @click="handleEdit">
          <Pencil :size="14" />
        </button>
        <button class="glass-btn-base glass-btn-soft icon-btn icon-btn--danger" title="删除" @click="showDeleteConfirm = true">
          <Trash2 :size="14" />
        </button>
      </div>
      <!-- Description -->
      <el-tooltip
        v-if="location.summary"
        :content="location.summary"
        placement="top"
        :show-after="300"
        :disabled="!isPlatformAsset"
      >
        <p class="location-card__desc">{{ location.summary }}</p>
      </el-tooltip>
    </div>

    <!-- Delete confirm overlay -->
    <DeleteConfirmOverlay
      v-if="showDeleteConfirm"
      :message="`确认删除该${label}？`"
      @confirm="handleDelete"
      @cancel="showDeleteConfirm = false"
    />

    <!-- Hidden file input for upload -->
    <input
      ref="fileInputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,image/gif,image/heic,image/heif"
      style="display: none"
      @change="onFileSelected"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Image as ImageIcon, WandSparkles, Upload, RefreshCw, Undo2, Pencil, Trash2
} from '@lucide/vue'
import { useAssetHubStore } from '@/store/assetHub'
import { submitAsyncTask } from '@/utils/asyncTask'
import { validateImageFile } from '@/utils/imageValidate'
import { selectImage } from '@/api/asset/characterAi'
import { syncUserAssetToVolc } from '@/api/shortVideo'
import MediaImageWithLoading from './MediaImageWithLoading.vue'
import DeleteConfirmOverlay from './DeleteConfirmOverlay.vue'
import ImageCandidateGrid from './ImageCandidateGrid.vue'

const props = defineProps({
  location: {
    type: Object,
    required: true
  },
  assetType: {
    type: String,
    default: 'location',
    validator: (v) => ['location', 'prop'].includes(v)
  }
})

// 平台资产：禁用所有用户操作，仅展示
const isPlatformAsset = computed(() => !!props.location?.is_management_asset)

const emit = defineEmits(['imageClick', 'imageEdit', 'edit'])

const store = useAssetHubStore()

const showDeleteConfirm = ref(false)
const fileInputRef = ref(null)
const isUndoing = ref(false)
const isUploading = ref(false)
const localSyncing = ref(false)

const COUNT_OPTIONS = [1, 2, 3, 4, 5, 6]
const STORAGE_KEY = `image-count:${props.assetType}`
const imageCount = ref(3)

function setImageCount(value) {
  const clamped = Math.min(6, Math.max(1, Math.trunc(value)))
  imageCount.value = clamped
  try { localStorage.setItem(STORAGE_KEY, String(clamped)) } catch { /* ignore */ }
}

onMounted(() => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const num = Number(raw)
    if (Number.isFinite(num) && num >= 1 && num <= 6) {
      imageCount.value = Math.trunc(num)
    }
  } catch { /* ignore */ }
})

const label = computed(() =>
  props.assetType === 'prop' ? '道具' : '场景'
)

const selectedImage = computed(() => {
  const images = props.location.images
  if (!images || images.length === 0) return null
  return images.find((img) => img.is_selected) || images[0]
})

// region 兼容：domestic 写 volc_private_asset_id，overseas 写 byteplus_asset_id
const isVolcSynced = computed(() =>
  Boolean(selectedImage.value?.volc_private_asset_id || selectedImage.value?.byteplus_asset_id)
)

// 同步中状态：本地单个同步 or 批量同步进行中
const isSyncing = computed(() =>
  localSyncing.value || (selectedImage.value ? store.isAssetBatchSyncing(selectedImage.value.id) : false)
)

const generatingLabel = computed(() => {
  const labels = { generate: '生成中...', modify: '改图中...', upload: '上传中...', undo: '撤销中...', reference: '生成中...' }
  return labels[selectedImage.value?.action_type] || '生成中...'
})

const displayImageUrl = computed(() =>
  selectedImage.value?.image_url || ''
)

const hasMultipleImages = computed(() => {
  const images = props.location.images
  if (!images) return false
  return images.filter(img => !!img.image_url).length > 1
})

const locationSelectedIndex = computed(() => {
  const images = props.location.images
  if (!images) return null
  const idx = images.findIndex(img => img.is_selected)
  return idx >= 0 ? idx : 0
})

const locationCandidateItems = computed(() => {
  const images = props.location.images
  if (!images) return []
  return images.filter(img => !!img.image_url).map(img => ({
    url: img.image_url,
    thumbnailUrl: img.thumbnail_url || '',
  }))
})

const currentImageIndex = computed(() => {
  if (!selectedImage.value) return 0
  return selectedImage.value.image_index ?? 0
})

function handleImageClick(url) {
  if (url) {
    emit('imageClick', url)
  } else if (displayImageUrl.value) {
    emit('imageClick', displayImageUrl.value)
  }
}

async function handleSelectLocationImage(index) {
  const images = props.location.images
  if (!images) return
  const target = images[index]
  if (!target) return
  target.is_selected = true
  for (let i = 0; i < images.length; i++) {
    if (i !== index) images[i].is_selected = false
  }
  try {
    await selectImage({
      type: props.assetType,
      id: props.location.id,
      image_index: target.image_index,
    })
  } catch {
    await store.fetchLocations()
  }
}

async function handleConfirmLocationSelection(index) {
  const images = props.location.images
  const target = images[index]
  if (!target) return
  try {
    await selectImage({
      type: props.assetType,
      id: props.location.id,
      image_index: target.image_index,
      confirm: true,
    })
    ElMessage.success('已确认选择')
    await store.fetchLocations()
  } catch {
    await store.fetchLocations()
  }
}

async function handleGenerate(count = imageCount.value) {
  if (selectedImage.value?.gen_status === 'generating') return
  if (selectedImage.value) selectedImage.value.gen_status = 'generating'
  try {
    await submitAsyncTask(
      '/asset-hub/generate-image',
      {
        type: props.assetType,
        id: props.location.id,
        image_index: currentImageIndex.value,
        count,
        art_style: props.location.art_style || '',
      },
      { successMsg: '图片生成完成' }
    )
    await store.fetchLocations()
  } catch {
    // submitAsyncTask already shows error message
  }
}

function handleUpload() {
  fileInputRef.value?.click()
}

async function onFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  isUploading.value = true
  try {
    const { valid, error, file: validatedFile } = await validateImageFile(file)
    if (!valid) {
      ElMessage.error(error)
      return
    }
    await store.uploadLocationImage({
      file: validatedFile,
      locationId: props.location.id,
      imageIndex: currentImageIndex.value,
      labelText: props.location.name || '',
    })
  } catch {
    // request interceptor handles error display
  } finally {
    isUploading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

function handleImageEdit() {
  emit('imageEdit', {
    type: props.assetType,
    id: props.location.id,
    name: props.location.name,
    imageUrl: displayImageUrl.value,
    imageIndex: currentImageIndex.value,
  })
}

async function handleUndo() {
  isUndoing.value = true
  try {
    await store.undoLocationImage({
      locationId: props.location.id,
      imageIndex: currentImageIndex.value,
    })
  } catch {
    // request interceptor handles error display
  } finally {
    isUndoing.value = false
  }
}

function handleEdit() {
  emit('edit', props.location, currentImageIndex.value)
}

async function handleSyncToVolc() {
  if (!selectedImage.value || isSyncing.value) return
  localSyncing.value = true
  try {
    await syncUserAssetToVolc(selectedImage.value.id, 'location_image')
    await store.fetchLocations()
  } catch {
    // error handled by interceptor
  } finally {
    localSyncing.value = false
  }
}

async function handleDelete() {
  showDeleteConfirm.value = false
  await store.deleteLocation(props.location.id)
}
</script>

<style scoped>
.location-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-span-3 {
  grid-column: span 3;
}

.location-card--multi {
  overflow: visible;
}

/* Image area */
.location-card__image-area {
  position: relative;
  background: var(--glass-bg-muted);
  overflow: hidden;
  cursor: pointer;
}

.location-card__image-area--location {
  aspect-ratio: 1 / 1;
}

.location-card__image-area--prop {
  aspect-ratio: 3 / 2;
}

.location-card__image-area {
  aspect-ratio: v-bind(assetType === 'prop' ? '3/2' : '1/1');
}

.location-card__image-area :deep(.card-img-container) {
  height: 100%;
  width: 100%;
}

.location-card__image-area :deep(.card-img) {
  height: 100%;
  width: 100%;
  object-fit: contain;
  cursor: zoom-in;
}

/* No image placeholder */
.location-card__no-image {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8px;
  color: var(--glass-text-tertiary);
}

.generate-btn-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 14px;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
}

.generate-btn-inline.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}

.count-pill {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  transition: background 0.15s;
}

.count-pill:hover {
  background: rgba(255, 255, 255, 0.25);
}

.count-pill__select {
  appearance: none;
  -webkit-appearance: none;
  background: transparent;
  border: none;
  color: inherit;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  outline: none;
  padding: 0 4px;
}

.count-option {
  color: #000;
}

/* Hover actions */
.location-card__hover-actions {
  position: absolute;
  top: 4px;
  left: 4px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.location-card:hover .location-card__hover-actions {
  opacity: 1;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Info area */
.location-card__info {
  padding: 12px;
}

.location-card__name-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.location-card__text-block {
  flex: 1;
  min-width: 0;
}

.location-card__type-label {
  font-size: 10px;
  color: var(--glass-text-tertiary);
  margin: 0;
}

.location-card__name {
  font-weight: 500;
  font-size: 14px;
  color: var(--glass-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.icon-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.location-card:hover .icon-btn {
  opacity: 1;
}

.icon-btn--danger {
  color: var(--glass-tone-danger-fg);
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

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 未同步火山角标 */
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
  transition: all 0.15s;
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

/* 平台资产视图：隐藏所有用户操作，只保留图片、名称、描述 */
.location-card--platform .location-card__hover-actions,
.location-card--platform .location-card__no-image,
.location-card--platform .volc-unsynced-badge,
.location-card--platform .location-card__multi-actions,
.location-card--platform .icon-btn {
  display: none !important;
}

.location-card--platform .location-card__desc {
  -webkit-line-clamp: 3;
}

/* Description */
.location-card__desc {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--glass-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Multi-image selection mode */
.location-card__multi-area {
  padding: 12px;
  position: relative;
}

.location-card__multi-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.location-card__multi-actions {
  display: flex;
  gap: 4px;
}

.action-btn-sm {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
