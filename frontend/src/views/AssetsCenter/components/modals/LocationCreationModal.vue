<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-card glass-surface-modal">
      <div class="modal-header">
        <h3 class="modal-title">{{ isLocation ? '创建场景' : '创建道具' }}</h3>
        <button class="modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>
      <div class="modal-body">
        <!-- Name + Folder -->
        <div class="field-row">
          <div class="field-group field-group--name">
            <label class="glass-field-label">{{ isLocation ? '场景名称' : '道具名称' }} <span class="required">*</span></label>
            <input
              v-model="name"
              class="glass-input-base field-input"
              :placeholder="isLocation ? '请输入场景名称' : '请输入道具名称'"
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

        <!-- Art style (only for location) -->
        <div v-if="isLocation" class="field-group">
          <label class="glass-field-label">艺术风格</label>
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

        <!-- AI design section -->
        <div class="ai-design-card">
          <div class="ai-design-header">
            <Sparkles :size="16" class="sparkles-icon" />
            <span>AI 设计 (可选)</span>
          </div>
          <div class="ai-row">
            <input
              v-model="aiInstruction"
              class="glass-input-base field-input"
              :placeholder="isLocation ? '输入 AI 指令来自动生成场景描述' : '输入 AI 指令来自动生成道具描述'"
              @keydown.enter="handleAiDesign"
            />
            <button
              class="glass-btn-base glass-btn-tone-info ai-btn"
              :disabled="!aiInstruction.trim() || isAiDesigning"
              @click="handleAiDesign"
            >
              <Sparkles :size="14" /> {{ isAiDesigning ? '生成中...' : '生成' }}
            </button>
          </div>
          <p class="ai-hint">输入描述关键词，AI 将自动生成完整的{{ isLocation ? '场景' : '道具' }}描述</p>
        </div>

        <!-- Description -->
        <div class="field-group">
          <label class="glass-field-label">{{ isLocation ? '场景描述' : '道具描述' }} <span class="required">*</span></label>
          <textarea
            v-model="description"
            class="glass-textarea-base field-textarea"
            :placeholder="isLocation ? '请描述场景特征' : '请描述道具特征'"
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
          :disabled="!name.trim() || !description.trim() || isSubmitting"
          @click="handleAddOnly"
        >
          仅添加
        </button>
        <div
          class="glass-btn-base glass-btn-primary generate-btn-inline"
          :class="{ 'is-disabled': !name.trim() || !description.trim() || isSubmitting }"
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { X, Sparkles } from '@lucide/vue'
import { useAssetHubStore } from '@/store/assetHub'
import { ART_STYLES } from '@/constants/artStyles'
import { submitAsyncTask } from '@/utils/asyncTask'

const props = defineProps({
  folderId: { type: String, default: null },
  assetKind: { type: String, default: 'location' }
})

const emit = defineEmits(['close', 'success'])

const store = useAssetHubStore()

const name = ref('')
const description = ref('')
const selectedFolderId = ref(props.folderId || '')
const artStyle = ref('american-comic')
const aiInstruction = ref('')
const isSubmitting = ref(false)
const isAiDesigning = ref(false)

const COUNT_OPTIONS = [1, 2, 3, 4, 5, 6]
const STORAGE_KEY = 'image-count:location'
const imageCount = ref(3)

const isLocation = computed(() => props.assetKind === 'location')

async function handleAiDesign() {
  const instruction = aiInstruction.value.trim()
  if (!instruction || isAiDesigning.value) return
  isAiDesigning.value = true
  try {
    const result = await submitAsyncTask(
      '/asset-hub/ai-design-location',
      { user_instruction: instruction },
      { successMsg: 'AI 场景描述生成完成' }
    )
    if (result?.prompt) {
      description.value = result.prompt
      aiInstruction.value = ''
    }
  } catch {
    // submitAsyncTask already shows error message
  } finally {
    isAiDesigning.value = false
  }
}

async function handleAddOnly() {
  if (!name.value.trim() || !description.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    await store.createLocation({
      name: name.value.trim(),
      summary: description.value.trim(),
      art_style: artStyle.value,
      folder_id: selectedFolderId.value || null,
      asset_kind: props.assetKind
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
  if (!name.value.trim() || !description.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const created = await store.createLocation({
      name: name.value.trim(),
      summary: description.value.trim(),
      art_style: artStyle.value,
      folder_id: selectedFolderId.value || null,
      asset_kind: props.assetKind,
      count: imageCount.value,
    })
    const locationId = created?.id
    if (locationId) {
      // 乐观设置生成状态，确保关闭弹窗后卡片显示遮罩
      const newLoc = store.locations.find(l => l.id === locationId)
      if (newLoc?.images?.[0]) {
        newLoc.images[0].gen_status = 'generating'
      }
      try {
        await submitAsyncTask(
          '/asset-hub/generate-image',
          {
            type: props.assetKind,
            id: locationId,
            count: imageCount.value,
            art_style: artStyle.value,
          },
          { successMsg: '图片生成完成' }
        )
        await store.fetchLocations()
      } catch {
        // Image generation failed, but location was created
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

.field-input {
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
  margin-top: 6px;
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

.ai-design-card {
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  border: 1px solid var(--glass-stroke-base);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.ai-design-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-tone-info-fg);
}

.sparkles-icon {
  flex-shrink: 0;
}

.ai-row {
  display: flex;
  gap: 8px;
}

.ai-row .field-input {
  flex: 1;
  margin-top: 0;
}

.ai-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}

.ai-hint {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  margin: 0;
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
