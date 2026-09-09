<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-card glass-surface-modal">
      <div class="modal-header">
        <h3 class="modal-title">新建音色</h3>
        <button class="modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>
      <div class="modal-body">
        <!-- Mode switch -->
        <div class="field-group">
          <SegmentedControl
            v-model="mode"
            :options="modeOptions"
            layout="fill"
          />
        </div>

        <!-- Name + Folder -->
        <div class="field-row">
          <div class="field-group field-group--name">
            <label class="glass-field-label">音色名称 <span class="required">*</span></label>
            <input
              v-model="name"
              class="glass-input-base field-input"
              placeholder="请输入音色名称"
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

        <!-- Design mode -->
        <template v-if="mode === 'design'">
          <!-- Voice style presets -->
          <div class="field-group">
            <label class="glass-field-label">选择声音风格</label>
            <div class="preset-chips">
              <button
                v-for="preset in VOICE_PRESETS"
                :key="preset.key"
                class="preset-chip"
                :class="{ 'preset-chip--active': selectedPresetKey === preset.key }"
                @click="handlePresetClick(preset)"
              >
                {{ preset.label }}
              </button>
            </div>
          </div>

          <!-- Voice prompt -->
          <div class="field-group">
            <label class="glass-field-label">自定义描述</label>
            <textarea
              v-model="voicePrompt"
              class="glass-textarea-base field-textarea"
              placeholder="描述你想要的音色特征，如：温柔的女声，略带沙哑"
              rows="3"
              @input="handlePromptInput"
            />
          </div>

          <!-- Preview text (collapsible) -->
          <details class="preview-details">
            <summary class="preview-summary">修改试听文本</summary>
            <textarea
              v-model="previewText"
              class="glass-textarea-base field-textarea preview-textarea"
              rows="2"
            />
          </details>

          <!-- Generate status -->
          <div v-if="isGenerating" class="generating-hint">
            <span class="generating-spinner" />
            <span>正在生成 {{ schemeCount }} 个声音方案，预计 15-30 秒...</span>
          </div>
          <div v-if="generateError" class="generate-error">{{ generateError }}</div>

          <!-- Generated voices grid -->
          <template v-if="generatedVoices.length > 0">
            <div class="scheme-grid">
              <div
                v-for="(voice, index) in generatedVoices"
                :key="index"
                class="scheme-card"
                :class="{ 'scheme-card--selected': selectedVoiceIndex === index }"
                @click="selectedVoiceIndex = index"
              >
                <div class="scheme-label">方案 {{ index + 1 }}</div>
                <button
                  class="scheme-play"
                  @click.stop="toggleSchemePlay(index)"
                >
                  <Pause v-if="playingIndex === index" :size="16" />
                  <Play v-else :size="16" />
                </button>
                <div v-if="selectedVoiceIndex === index" class="scheme-check">
                  <Check :size="14" />
                </div>
              </div>
            </div>
          </template>
        </template>

        <!-- Upload mode -->
        <template v-else>
          <!-- 选择文件后显示试听框 -->
          <div v-if="uploadFile" class="audio-preview">
            <div class="audio-preview-bar">
              <Mic :size="16" class="audio-preview-icon" />
              <span class="audio-preview-name">{{ uploadFile.name }}</span>
              <button class="audio-preview-play" @click="togglePreview">
                <Pause v-if="isPreviewing" :size="14" />
                <Play v-else :size="14" />
                <span>{{ isPreviewing ? '暂停' : '试听' }}</span>
              </button>
              <button class="audio-preview-remove" @click="clearFile">
                <X :size="16" />
              </button>
            </div>
          </div>
          <!-- 未选择文件时显示上传区域 -->
          <div
            v-else
            class="upload-area"
            @click="triggerFileInput"
            @dragover.prevent
            @drop.prevent="onFileDrop"
          >
            <Upload :size="32" color="var(--glass-text-tertiary)" />
            <p class="upload-hint">拖放文件或点击选择</p>
            <p class="upload-formats">支持 MP3、WAV、OGG、M4A、AAC 格式</p>
            <input
              ref="fileInputRef"
              type="file"
              accept=".mp3,.wav,.ogg,.m4a,.aac"
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
        <!-- AI 设计模式：状态切换按钮 -->
        <template v-if="mode === 'design'">
          <template v-if="generatedVoices.length > 0 && selectedVoiceIndex !== null">
            <button
              class="glass-btn-base glass-btn-secondary footer-btn"
              @click="resetGeneration"
            >
              重新生成
            </button>
            <button
              class="glass-btn-base glass-btn-primary footer-btn"
              :disabled="isSubmitting"
              @click="handleSubmit"
            >
              保存
            </button>
          </template>
          <template v-else>
            <div
              class="glass-btn-base glass-btn-primary generate-btn-footer"
              :class="{ 'is-disabled': !voicePrompt.trim() || !name.trim() || isGenerating }"
              @click="handleGenerate"
            >
              生成
              <span class="count-pill" @click.stop>
                <select
                  :value="schemeCount"
                  class="count-pill__select"
                  @change.stop="schemeCount = Number($event.target.value)"
                >
                  <option v-for="n in 5" :key="n" :value="n" class="count-option">{{ n }}</option>
                </select>
              </span>
              个音色
            </div>
          </template>
        </template>
        <!-- 上传模式：保存按钮 -->
        <template v-else>
          <button
            class="glass-btn-base glass-btn-primary footer-btn"
            :disabled="isSubmitDisabled"
            @click="handleSubmit"
          >
            保存
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { X, Upload, Sparkles, Mic, Play, Pause, Check } from '@lucide/vue'
import SegmentedControl from '../SegmentedControl.vue'
import { useAssetHubStore } from '@/store/assetHub'
import { uploadVoice, designVoice } from '@/api/asset/voice'

const VOICE_PRESETS = [
  { key: 'maleBroadcaster', label: '男播音', prompt: '沉稳的中年男性播音员，音色低沉浑厚，语速平稳，吐字清晰' },
  { key: 'gentleFemale', label: '温柔女', prompt: '温柔甜美的年轻女性，声音清脆悦耳，语调轻柔' },
  { key: 'matureMale', label: '成熟男', prompt: '成熟稳重的男性，声音富有磁性和感染力' },
  { key: 'livelyFemale', label: '活泼女', prompt: '活泼开朗的少女，声音甜美可爱，充满活力' },
  { key: 'intellectualFemale', label: '知性女', prompt: '知性优雅的女性，声音清晰悦耳，语调平和' },
  { key: 'narrator', label: '旁白', prompt: '富有感情的叙述者，声音温暖有故事感' },
]

const DEFAULT_PREVIEW_TEXT = '你好，很高兴认识你。这是AI为你专属设计的声音，无论是温柔的对话，还是激动的讲述，我都能完美呈现。'

const props = defineProps({
  folderId: { type: String, default: null }
})

const emit = defineEmits(['close', 'success'])

const store = useAssetHubStore()

const mode = ref('upload') // 暂时注释 AI 设计，默认使用上传模式
const name = ref('')
const selectedFolderId = ref(props.folderId || '')
const voicePrompt = ref('')
const previewText = ref(DEFAULT_PREVIEW_TEXT)
const selectedPresetKey = ref(null)
const schemeCount = ref(3)
const isGenerating = ref(false)
const generateError = ref(null)
const generatedVoices = ref([])
const selectedVoiceIndex = ref(null)
const playingIndex = ref(null)
const isSubmitting = ref(false)
const uploadFile = ref(null)
const fileInputRef = ref(null)
const isPreviewing = ref(false)
let uploadAudioUrl = null
let previewAudio = null

const modeOptions = [
  // { value: 'design', label: 'AI 设计音色', icon: Sparkles }, // 暂时注释
  { value: 'upload', label: '上传音频', icon: Upload }
]

const isSubmitDisabled = computed(() => {
  if (!name.value.trim() || isSubmitting.value) return true
  if (mode.value === 'upload' && !uploadFile.value) return true
  return false
})

function handlePresetClick(preset) {
  if (selectedPresetKey.value === preset.key) {
    selectedPresetKey.value = null
    voicePrompt.value = ''
  } else {
    selectedPresetKey.value = preset.key
    voicePrompt.value = preset.prompt
  }
}

function handlePromptInput() {
  if (selectedPresetKey.value) {
    const preset = VOICE_PRESETS.find(p => p.key === selectedPresetKey.value)
    if (preset && voicePrompt.value !== preset.prompt) {
      selectedPresetKey.value = null
    }
  }
}

async function handleGenerate() {
  if (!voicePrompt.value.trim() || isGenerating.value) return

  isGenerating.value = true
  generateError.value = null
  generatedVoices.value = []
  selectedVoiceIndex.value = null

  try {
    const result = await designVoice({
      voice_prompt: voicePrompt.value.trim(),
      preview_text: previewText.value.trim(),
      count: schemeCount.value,
      language: 'zh',
    })
    generatedVoices.value = result.voices || []
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    isGenerating.value = false
  }
}

function resetGeneration() {
  stopSchemePlay()
  generatedVoices.value = []
  selectedVoiceIndex.value = null
  generateError.value = null
}

function toggleSchemePlay(index) {
  if (playingIndex.value === index) {
    stopSchemePlay()
    return
  }

  stopSchemePlay()

  const voice = generatedVoices.value[index]
  if (!voice) return

  const audioSrc = voice.audio_url || (voice.audio_base64 ? `data:audio/wav;base64,${voice.audio_base64}` : null)
  if (!audioSrc) return

  previewAudio = new Audio(audioSrc)
  previewAudio.onended = () => { playingIndex.value = null }
  previewAudio.onerror = () => { playingIndex.value = null }
  previewAudio.play()
  playingIndex.value = index
}

function stopSchemePlay() {
  if (previewAudio) {
    previewAudio.pause()
    previewAudio = null
  }
  playingIndex.value = null
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) selectFile(file)
}

function onFileDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file) selectFile(file)
}

async function selectFile(file) {
  uploadFile.value = file
  uploadAudioUrl = URL.createObjectURL(file)
  // 读取音频时长
  try {
    const audio = new Audio(uploadAudioUrl)
    await new Promise((resolve, reject) => {
      audio.onloadedmetadata = () => resolve()
      audio.onerror = () => reject(new Error('无法读取时长'))
    })
    uploadFile.value._duration = Math.round(audio.duration)
  } catch {
    uploadFile.value._duration = null
  }
}

function clearFile() {
  stopPreview()
  if (uploadAudioUrl) {
    URL.revokeObjectURL(uploadAudioUrl)
    uploadAudioUrl = null
  }
  uploadFile.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function togglePreview() {
  if (!uploadAudioUrl) return
  if (isPreviewing.value) {
    stopPreview()
  } else {
    previewAudio = new Audio(uploadAudioUrl)
    previewAudio.onended = () => { isPreviewing.value = false }
    previewAudio.onerror = () => { isPreviewing.value = false }
    previewAudio.play()
    isPreviewing.value = true
  }
}

function stopPreview() {
  if (previewAudio) {
    previewAudio.pause()
    previewAudio = null
  }
  isPreviewing.value = false
}

async function handleSubmit() {
  if (!name.value.trim() || isSubmitting.value) return

  if (mode.value === 'upload') {
    if (!uploadFile.value) return
    isSubmitting.value = true
    try {
      const formData = new FormData()
      formData.append('name', name.value.trim())
      formData.append('file', uploadFile.value)
      if (selectedFolderId.value) formData.append('folder_id', selectedFolderId.value)
      if (uploadFile.value._duration != null) formData.append('duration', String(uploadFile.value._duration))
      await uploadVoice(formData)
      await store.fetchVoices()
      emit('success')
      emit('close')
    } catch {
      // 错误提示由 request 拦截器统一处理
    } finally {
      isSubmitting.value = false
    }
    return
  }

  // Design mode
  isSubmitting.value = true
  try {
    const payload = {
      name: name.value.trim(),
      folder_id: selectedFolderId.value || null,
      voice_type: 'ai_designed',
      voice_prompt: voicePrompt.value.trim(),
    }
    if (selectedVoiceIndex.value !== null && generatedVoices.value[selectedVoiceIndex.value]) {
      const selected = generatedVoices.value[selectedVoiceIndex.value]
      payload.voice_id = selected.voice_id
      payload.custom_voice_url = selected.audio_url
    }
    await store.createVoice(payload)
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

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  stopPreview()
  stopSchemePlay()
  if (uploadAudioUrl) {
    URL.revokeObjectURL(uploadAudioUrl)
    uploadAudioUrl = null
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
  max-height: 70vh;
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

.field-textarea {
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
  margin-top: 6px;
  resize: none;
}

/* Preset chips */
.preset-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.preset-chip {
  padding: 5px 14px;
  border-radius: 16px;
  border: 1px solid var(--glass-stroke-base);
  background: none;
  color: var(--glass-text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.preset-chip:hover {
  border-color: var(--glass-tone-info-fg);
  color: var(--glass-tone-info-fg);
}

.preset-chip--active {
  background: var(--glass-tone-info-fg);
  border-color: var(--glass-tone-info-fg);
  color: #fff;
}

.preset-chip--active:hover {
  background: var(--glass-tone-info-fg);
  color: #fff;
}

/* Preview text collapsible */
.preview-details {
  margin-bottom: 16px;
}

.preview-summary {
  font-size: 13px;
  color: var(--glass-text-tertiary);
  cursor: pointer;
  padding: 6px 0;
  user-select: none;
}

.preview-summary:hover {
  color: var(--glass-text-secondary);
}

.preview-textarea {
  margin-top: 8px;
}

/* Generate section */
.generate-btn-footer {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 14px;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
}

.generate-btn-footer.is-disabled {
  opacity: 0.5;
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

.generating-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  font-size: 14px;
  color: var(--glass-text-secondary);
}

.generating-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-tone-info-fg);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.generate-error {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--glass-tone-danger-bg, rgba(245, 108, 108, 0.1));
  color: var(--glass-tone-danger-fg, #f56c6c);
  font-size: 13px;
}

/* Scheme grid */
.scheme-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.scheme-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  border-radius: 10px;
  border: 1.5px solid var(--glass-stroke-base);
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  cursor: pointer;
  transition: all 0.2s;
}

.scheme-card:hover {
  border-color: var(--glass-tone-info-fg);
}

.scheme-card--selected {
  border-color: var(--glass-tone-info-fg);
  background: var(--glass-tone-info-bg, rgba(64, 158, 255, 0.08));
}

.scheme-label {
  font-size: 13px;
  color: var(--glass-text-secondary);
}

.scheme-play {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1.5px solid var(--glass-stroke-base);
  background: none;
  color: var(--glass-tone-info-fg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s;
}

.scheme-play:hover {
  border-color: var(--glass-tone-info-fg);
}

.scheme-check {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--glass-tone-info-fg);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Upload area */
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

.audio-preview {
  margin-top: 0;
  padding: 12px;
  border-radius: 10px;
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  border: 1px solid var(--glass-stroke-base);
}

.audio-preview-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.audio-preview-icon {
  flex-shrink: 0;
  color: var(--glass-tone-info-fg);
}

.audio-preview-name {
  flex: 1;
  font-size: 14px;
  color: var(--glass-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audio-preview-play {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--glass-stroke-base);
  background: none;
  color: var(--glass-tone-info-fg);
  cursor: pointer;
  font-size: 12px;
  flex-shrink: 0;
  transition: border-color 0.2s;
}

.audio-preview-play:hover {
  border-color: var(--glass-tone-info-fg);
}

.audio-preview-remove {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: none;
  color: var(--glass-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.audio-preview-remove:hover {
  color: var(--glass-tone-danger-fg, #f56c6c);
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
</style>
