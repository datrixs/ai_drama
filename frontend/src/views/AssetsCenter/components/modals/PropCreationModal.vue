<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-card glass-surface-modal">
      <div class="modal-header">
        <h3 class="modal-title">创建道具</h3>
        <button class="modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>
      <div class="modal-body">
        <!-- Name + Folder -->
        <div class="field-row">
          <div class="field-group field-group--name">
            <label class="glass-field-label">道具名称 <span class="required">*</span></label>
            <input
              v-model="name"
              class="glass-input-base field-input"
              placeholder="请输入道具名称"
            />
          </div>
          <div class="field-group field-group--folder">
            <label class="glass-field-label">资产组</label>
            <el-select
              v-model="selectedFolderId"
              placeholder="选择资产组"
              class="folder-select"
            >
              <el-option label="所有资产" value="" />
              <el-option v-for="f in store.folders" :key="f.id" :label="f.name" :value="f.id" />
            </el-select>
          </div>
        </div>

        <!-- Art style -->
        <div class="field-group">
          <label class="glass-field-label">画面风格</label>
          <div class="style-grid">
            <button
              v-for="style in ART_STYLES"
              :key="style.value"
              type="button"
              :class="[
                'glass-btn-base style-grid-btn',
                artStyle === style.value ? 'glass-btn-tone-info style-grid-btn--active' : 'glass-btn-soft'
              ]"
              @click="artStyle = style.value"
            >
              <span>{{ style.label }}</span>
            </button>
          </div>
        </div>

        <!-- Summary -->
        <div class="field-group">
          <label class="glass-field-label">道具摘要 <span class="required">*</span></label>
          <textarea
            v-model="summary"
            class="glass-textarea-base field-textarea"
            placeholder="请输入道具摘要"
            style="height: 144px; resize: none;"
          />
        </div>

        <!-- Description -->
        <div class="field-group">
          <label class="glass-field-label">道具描述 <span class="required">*</span></label>
          <textarea
            v-model="description"
            class="glass-textarea-base field-textarea"
            placeholder="请输入道具描述"
            style="height: 144px; resize: none;"
          />
        </div>
      </div>
      <div class="modal-footer">
        <button class="glass-btn-base glass-btn-secondary footer-btn" @click="$emit('close')">
          取消
        </button>
        <button
          class="glass-btn-base glass-btn-secondary footer-btn"
          :disabled="!name.trim() || !summary.trim() || !description.trim() || isSubmitting"
          @click="handleAddOnly"
        >
          仅添加
        </button>
        <div
          class="glass-btn-base glass-btn-primary generate-btn-inline"
          :class="{ 'is-disabled': !name.trim() || !summary.trim() || !description.trim() || isSubmitting }"
          @click="handleAddAndGenerate"
        >
          添加并生成
          <span class="count-pill" @click.stop>
            <select
              :value="imageCount"
              class="count-pill__select"
              @change.stop="imageCount = Number($event.target.value)"
            >
              <option v-for="n in COUNT_OPTIONS" :key="n" :value="n" class="count-option">{{ n }}</option>
            </select>
          </span>
          张
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { X } from '@lucide/vue'
import { useAssetHubStore } from '@/store/assetHub'
import { ART_STYLES } from '@/constants/artStyles'
import { submitAsyncTask } from '@/utils/asyncTask'

const props = defineProps({
  folderId: { type: String, default: null }
})

const emit = defineEmits(['close', 'success'])

const store = useAssetHubStore()

const name = ref('')
const summary = ref('')
const description = ref('')
const selectedFolderId = ref(props.folderId || '')
const artStyle = ref('american-comic')
const isSubmitting = ref(false)

const COUNT_OPTIONS = [1, 2, 3, 4, 5, 6]
const STORAGE_KEY = 'image-count:prop'
const imageCount = ref(3)

async function handleAddOnly() {
  if (!name.value.trim() || !summary.value.trim() || !description.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    await store.createLocation({
      name: name.value.trim(),
      summary: summary.value.trim(),
      description: description.value.trim(),
      art_style: artStyle.value,
      folder_id: selectedFolderId.value || null,
      asset_kind: 'prop'
    })
    emit('success')
    emit('close')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    isSubmitting.value = false
  }
}

async function handleAddAndGenerate() {
  if (!name.value.trim() || !summary.value.trim() || !description.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const created = await store.createLocation({
      name: name.value.trim(),
      summary: summary.value.trim(),
      description: description.value.trim(),
      art_style: artStyle.value,
      folder_id: selectedFolderId.value || null,
      asset_kind: 'prop',
      count: imageCount.value,
    })
    const propId = created?.id
    if (propId) {
      // 乐观设置生成状态，确保关闭弹窗后卡片显示遮罩
      const newProp = store.locations.find(l => l.id === propId)
      if (newProp?.images?.[0]) {
        newProp.images[0].gen_status = 'generating'
      }
      try {
        await submitAsyncTask(
          '/asset-hub/generate-image',
          {
            type: 'prop',
            id: propId,
            count: imageCount.value,
            art_style: artStyle.value,
          },
          { successMsg: '图片生成完成' }
        )
        await store.fetchLocations()
      } catch {
        // Image generation failed, but prop was created
      }
    }
    emit('success')
    emit('close')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    isSubmitting.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const num = Number(raw)
    if (Number.isFinite(num) && num >= 1 && num <= 6) {
      imageCount.value = Math.trunc(num)
    }
  } catch { /* ignore */ }
})
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
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

.modal-card {
  max-width: 576px;
  width: 100%;
  overflow: hidden;
}

.modal-header {
  border-bottom: none;
  padding: 16px 20px 0;
}

.modal-body {
  padding: 16px 20px 20px;
  max-height: 60vh;
  overflow-y: auto;
}

.field-group {
  margin-bottom: 16px;
}

.field-group:last-child {
  margin-bottom: 0;
}

.field-row {
  display: flex;
  gap: 12px;
}

.field-group--name {
  flex: 1;
}

.field-group--folder {
  width: 160px;
  flex-shrink: 0;
}

.folder-select {
  width: 100%;
  margin-top: 6px;
}

.folder-select :deep(.el-select__wrapper) {
  border-radius: var(--glass-radius-md);
}

.required {
  color: var(--glass-tone-danger-fg, #f56c6c);
}

.style-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 6px;
}

.style-grid-btn {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  text-align: left;
  border: 1px solid var(--glass-stroke-base);
  transition: all 0.15s ease;
}

.style-grid-btn--active {
  border-color: var(--glass-stroke-focus);
}

.field-input {
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
  margin-top: 6px;
}

.field-textarea {
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
  margin-top: 6px;
}

.modal-footer {
  border-top: none;
  background: none;
  padding: 16px 20px;
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}

.generate-btn-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 14px;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.generate-btn-inline.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

.count-pill {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 28px;
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
</style>
