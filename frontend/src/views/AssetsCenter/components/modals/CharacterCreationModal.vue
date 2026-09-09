<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-card glass-surface-modal">
      <div class="modal-header">
        <h3 class="modal-title">新建角色</h3>
        <button class="modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>
      <div class="modal-body">
        <!-- Mode switch -->
        <div class="field-group">
          <SegmentedControl
            v-model="createMode"
            :options="modeOptions"
            layout="fill"
          />
        </div>

        <!-- Name + Folder -->
        <div class="field-row">
          <div class="field-group field-group--name">
            <label class="glass-field-label">角色名称 <span class="required">*</span></label>
            <input
              v-model="name"
              class="glass-input-base field-input"
              placeholder="请输入角色名称"
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

        <!-- AI design section (description mode only) -->
        <template v-if="createMode === 'description'">
          <div class="ai-design-card">
            <div class="ai-design-header">
              <Sparkles :size="16" class="sparkles-icon" />
              <span>AI 设计</span>
            </div>
            <div class="ai-row">
              <input
                v-model="aiInstruction"
                class="glass-input-base field-input"
                placeholder="描述你想要的角色特征..."
                @keydown.enter="handleAiGenerate"
              />
              <button
                class="glass-btn-base glass-btn-tone-info ai-btn"
                :disabled="isAiDesigning"
                @click="handleAiGenerate"
              >
                <Sparkles :size="14" /> {{ isAiDesigning ? '生成中...' : '生成' }}
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="glass-field-label">角色描述 <span class="required">*</span></label>
            <textarea
              v-model="description"
              class="glass-textarea-base field-textarea"
              placeholder="请描述角色特征"
              rows="4"
            />
          </div>
        </template>

        <!-- Reference mode content -->
        <template v-else>
          <div class="reference-container">
            <!-- Sub-mode switcher -->
            <div class="sub-mode-bar">
              <span class="sub-mode-label">生成方式：</span>
              <SegmentedControl
                v-model="referenceSubMode"
                :options="subModeOptions"
                layout="compact"
              />
              <span class="paste-hint">支持 Ctrl+V 粘贴</span>
            </div>

            <!-- Extract prompt button (extract sub-mode only) -->
            <button
              v-if="referenceSubMode === 'extract'"
              class="glass-btn-base glass-btn-tone-info extract-btn"
              :disabled="isExtracting || referenceImages.length === 0"
              @click="handleExtractDescription"
            >
              <LoaderCircle v-if="isExtracting" :size="14" class="spin-icon" />
              {{ isExtracting ? '提取中...' : '反推提示词' }}
            </button>

            <!-- Upload zone (no images yet) -->
            <div
              v-if="referenceImages.length === 0"
              class="upload-area"
              @click="triggerFileInput"
              @dragover.prevent
              @drop.prevent="onFileDrop"
            >
              <ImagePlus :size="32" color="var(--glass-text-tertiary)" />
              <p class="upload-hint">点击上传或拖拽图片</p>
              <p class="upload-formats">最多 {{ MAX_IMAGES }} 张参考图</p>
            </div>

            <!-- Preview grid (images exist) -->
            <div v-else class="preview-section">
              <div class="preview-grid">
                <div v-for="img in referenceImages" :key="img.id" class="preview-item">
                  <img :src="img.url" class="preview-img" />
                  <button class="preview-remove" @click="removeImage(img.id)">
                    <X :size="12" />
                  </button>
                </div>
                <div
                  v-if="referenceImages.length < MAX_IMAGES"
                  class="preview-add"
                  @click="triggerFileInput"
                >
                  <ImagePlus :size="20" color="var(--glass-text-tertiary)" />
                </div>
              </div>
              <p class="preview-count">已选择 {{ referenceImages.length }}/{{ MAX_IMAGES }} 张参考图</p>
            </div>

            <input
              ref="fileInputRef"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              class="hidden-input"
              @change="onFileChange"
            />
          </div>
        </template>
      </div>
      <div class="modal-footer">
        <button class="glass-btn-base glass-btn-secondary footer-btn" @click="$emit('close')">
          取消
        </button>
        <template v-if="createMode === 'description'">
          <button
            class="glass-btn-base glass-btn-secondary footer-btn"
            :disabled="isSubmitting"
            @click="handleAddOnly"
          >
            仅添加到资产库
          </button>
          <div
            class="glass-btn-base glass-btn-primary generate-btn-inline"
            :class="{ 'is-disabled': !name.trim() || isSubmitting }"
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
        </template>
        <template v-else>
          <div
            class="glass-btn-base glass-btn-primary generate-btn-inline"
            :class="{ 'is-disabled': !name.trim() || isSubmitting || referenceImages.length === 0 || referenceSubMode === 'extract' }"
            @click="handleCreateWithReference"
          >
            使用参考图生成
            <span class="count-pill" @click.stop>
              <select
                :value="referenceImageCount"
                class="count-pill__select"
                @change.stop="referenceImageCount = Number($event.target.value)"
              >
                <option v-for="n in COUNT_OPTIONS" :key="n" :value="n" class="count-option">{{ n }}</option>
              </select>
            </span>
            张
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { X, Sparkles, ImagePlus, LoaderCircle } from '@lucide/vue'
import SegmentedControl from '../SegmentedControl.vue'
import { useAssetHubStore } from '@/store/assetHub'
import { ART_STYLES } from '@/constants/artStyles'
import { submitAsyncTask } from '@/utils/asyncTask'

const MAX_IMAGES = 5
const COUNT_OPTIONS = [1, 2, 3, 4, 5, 6]

const props = defineProps({
  folderId: { type: String, default: null }
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
const createMode = ref('description')
const referenceSubMode = ref('direct')
const isExtracting = ref(false)
const fileInputRef = ref(null)
const referenceImages = ref([])
const imageCount = ref(3)
const referenceImageCount = ref(3)

const modeOptions = [
  { value: 'description', label: '描述模式', icon: Sparkles },
  { value: 'reference', label: '参考图模式', icon: ImagePlus }
]

const subModeOptions = [
  { value: 'direct', label: '直接生成' },
  { value: 'extract', label: '反推提示词' }
]

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileChange(e) {
  addFiles(Array.from(e.target.files || []))
  e.target.value = ''
}

function onFileDrop(e) {
  addFiles(Array.from(e.dataTransfer?.files || []))
}

function addFiles(files) {
  const remaining = MAX_IMAGES - referenceImages.value.length
  const toAdd = files
    .filter(f => f.type.startsWith('image/'))
    .slice(0, remaining)
  for (const file of toAdd) {
    referenceImages.value.push({
      id: Date.now() + Math.random(),
      file,
      url: URL.createObjectURL(file)
    })
  }
  if (files.some(f => !f.type.startsWith('image/'))) {
    ElMessage.warning('仅支持图片文件')
  }
  if (files.filter(f => f.type.startsWith('image/')).length > remaining) {
    ElMessage.warning(`最多上传 ${MAX_IMAGES} 张参考图`)
  }
}

function removeImage(id) {
  const idx = referenceImages.value.findIndex(img => img.id === id)
  if (idx !== -1) {
    URL.revokeObjectURL(referenceImages.value[idx].url)
    referenceImages.value.splice(idx, 1)
  }
}

async function handleAiGenerate() {
  const instruction = aiInstruction.value.trim()
  if (!instruction || isAiDesigning.value) return
  isAiDesigning.value = true
  try {
    const result = await submitAsyncTask(
      '/asset-hub/ai-design-character',
      { user_instruction: instruction },
      { successMsg: 'AI 角色描述生成完成' }
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

async function handleExtractDescription() {
  if (referenceImages.value.length === 0 || isExtracting.value) return
  isExtracting.value = true
  try {
    const tempUrls = []
    for (const img of referenceImages.value) {
      const uploadResult = await store.uploadReferenceImage(img.file)
      if (uploadResult?.url) {
        tempUrls.push(uploadResult.url)
      }
    }
    if (tempUrls.length === 0) {
      ElMessage.error('参考图上传失败')
      return
    }
    const result = await submitAsyncTask(
      '/asset-hub/reference-to-character',
      { reference_image_urls: tempUrls, extract_only: true },
      { successMsg: '提示词提取完成' }
    )
    if (result?.description) {
      description.value = result.description
      // 清空参考图并跳转到描述模式
      referenceImages.value.forEach(img => URL.revokeObjectURL(img.url))
      referenceImages.value = []
      createMode.value = 'description'
    }
  } catch {
    // submitAsyncTask already shows error message
  } finally {
    isExtracting.value = false
  }
}

async function handleAddOnly() {
  if (!name.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    await store.createCharacter({
      name: name.value.trim(),
      description: description.value.trim(),
      art_style: artStyle.value,
      folder_id: selectedFolderId.value || null
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
  if (!name.value.trim() || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const created = await store.createCharacter({
      name: name.value.trim(),
      description: description.value.trim(),
      art_style: artStyle.value,
      folder_id: selectedFolderId.value || null
    })
    const characterId = created?.character?.id
    if (characterId) {
      // 乐观设置生成状态，确保关闭弹窗后卡片显示遮罩
      const newChar = store.characters.find(c => c.id === characterId)
      if (newChar?.appearances?.[0]) {
        newChar.appearances[0].gen_status = 'generating'
      }
      try {
        await submitAsyncTask(
          '/asset-hub/generate-image',
          {
            type: 'character',
            id: characterId,
            appearance_index: 0,
            count: imageCount.value,
            art_style: artStyle.value
          },
          { successMsg: '图片生成完成' }
        )
        await store.fetchCharacters()
      } catch {
        // Image generation failed, but character was created
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

async function handleCreateWithReference() {
  if (!name.value.trim() || isSubmitting.value) return
  if (referenceImages.value.length === 0) {
    ElMessage.warning('请至少上传一张参考图')
    return
  }
  isSubmitting.value = true
  try {
    // 1. 上传参考图
    const tempUrls = []
    for (const img of referenceImages.value) {
      const uploadResult = await store.uploadReferenceImage(img.file)
      if (uploadResult?.url) tempUrls.push(uploadResult.url)
    }
    if (tempUrls.length === 0) {
      ElMessage.error('参考图上传失败')
      return
    }

    // 2. extract 模式先提取描述
    let finalDescription = description.value.trim()
    let customDescription = undefined
    if (referenceSubMode.value === 'extract') {
      const extractResult = await submitAsyncTask(
        '/asset-hub/reference-to-character',
        { reference_image_urls: tempUrls, extract_only: true },
        { successMsg: '描述提取完成' }
      )
      finalDescription = extractResult?.description || finalDescription
      description.value = finalDescription
      customDescription = finalDescription
    }

    // 3. 创建角色（不带 generate_from_reference）
    const created = await store.createCharacter({
      name: name.value.trim(),
      description: finalDescription,
      art_style: artStyle.value,
      folder_id: selectedFolderId.value || null
    })
    const characterId = created?.character?.id
    const appearanceId = created?.appearance?.id
    if (!characterId || !appearanceId) {
      ElMessage.error('创建角色失败')
      return
    }

    // 乐观设置生成状态，确保关闭弹窗后卡片显示遮罩
    store.updateAppearanceStatus(appearanceId, 'generating')

    // 4. 提交参考图生成任务并通过 SSE 等待完成
    await submitAsyncTask(
      '/asset-hub/reference-to-character',
      {
        character_id: characterId,
        appearance_id: appearanceId,
        reference_image_urls: tempUrls,
        art_style: artStyle.value,
        custom_description: customDescription || '',
        count: referenceImageCount.value,
        is_background_job: true
      },
      { successMsg: '角色图片生成完成' }
    )

    // 5. 刷新列表
    await store.fetchCharacters()
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

function onGlobalPaste(e) {
  if (createMode.value !== 'reference') return

  const target = e.target
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return

  const items = e.clipboardData?.items
  if (!items) return

  for (let i = 0; i < items.length; i++) {
    if (!items[i].type.startsWith('image/')) continue
    const file = items[i].getAsFile()
    if (!file) continue
    e.preventDefault()
    addFiles([file])
    break
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('paste', onGlobalPaste)
})
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('paste', onGlobalPaste)
  referenceImages.value.forEach(img => URL.revokeObjectURL(img.url))
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

.field-textarea {
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
  margin-top: 6px;
  resize: none;
}

/* Reference image upload */
.upload-area {
  border: 2px dashed var(--glass-stroke-base);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  color: var(--glass-text-tertiary);
  transition: border-color 0.2s;
}

.upload-area:hover {
  border-color: var(--glass-text-secondary);
}

.upload-hint {
  margin-top: 8px;
  font-size: 14px;
  color: var(--glass-text-secondary);
}

.upload-formats {
  margin-top: 4px;
  font-size: 12px;
  color: var(--glass-text-tertiary);
}

.hidden-input {
  display: none;
}

.preview-section {
  margin-top: 8px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.preview-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--glass-stroke-base);
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
}

.preview-add {
  aspect-ratio: 1;
  border: 2px dashed var(--glass-stroke-base);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.2s;
}

.preview-add:hover {
  border-color: var(--glass-text-secondary);
}

.preview-count {
  margin-top: 8px;
  font-size: 12px;
  color: var(--glass-text-tertiary);
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

/* Reference mode container */
.reference-container {
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  border: 1px solid var(--glass-stroke-base);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sub-mode-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-mode-label {
  font-size: 12px;
  color: var(--glass-text-secondary);
  white-space: nowrap;
}

.paste-hint {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  margin-left: auto;
}

.extract-btn {
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
}

.extract-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
