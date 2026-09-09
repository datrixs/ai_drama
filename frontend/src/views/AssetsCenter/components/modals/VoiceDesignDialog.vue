<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-card glass-surface-modal">
      <!-- Header -->
      <div class="modal-header">
        <h3 class="modal-title">
          为「{{ speaker }}」设计AI声音
          <span v-if="hasExistingVoice" class="glass-chip glass-chip-neutral existing-chip">已有音色</span>
        </h3>
        <button class="glass-btn-base glass-btn-soft modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="modal-body">
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
        <div class="form-field">
          <label class="glass-field-label">音色描述</label>
          <textarea
            v-model="voicePrompt"
            class="glass-textarea-base field-textarea"
            rows="3"
            placeholder="请先选择声音风格..."
            readonly
          ></textarea>
        </div>

        <!-- Preview text (collapsible) -->
        <details class="preview-details">
          <summary class="preview-summary">修改试听文本</summary>
          <textarea
            v-model="previewText"
            class="glass-textarea-base field-textarea preview-textarea"
            rows="2"
          ></textarea>
        </details>

        <!-- Scheme count + Generate button -->
        <template v-if="isGenerating">
          <div class="generating-hint">
            <span class="generating-spinner" />
            <span>正在生成 {{ schemeCount }} 个声音方案...</span>
          </div>
        </template>
        <div v-if="generateError" class="generate-error">{{ generateError }}</div>

        <!-- Generated voice schemes -->
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
              <button class="scheme-play" @click.stop="toggleSchemePlay(index)">
                <Pause v-if="playingIndex === index" :size="16" />
                <Play v-else :size="16" />
              </button>
              <div v-if="selectedVoiceIndex === index" class="scheme-check">
                <Check :size="14" />
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button class="glass-btn-base glass-btn-secondary" @click="$emit('close')">
          取消
        </button>
        <template v-if="generatedVoices.length > 0 && selectedVoiceIndex !== null">
          <button
            v-if="generatedVoices.length > 0"
            class="glass-btn-base glass-btn-secondary"
            @click="resetGeneration"
          >
            重新生成
          </button>
          <button
            class="glass-btn-base glass-btn-primary"
            :disabled="isSubmitting"
            @click="handleSave"
          >
            保存
          </button>
        </template>
        <template v-else>
          <div
            class="glass-btn-base glass-btn-primary generate-btn-footer"
            :class="{ 'is-disabled': !voicePrompt.trim() || isGenerating }"
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { X, Play, Pause, Check } from '@lucide/vue'
import { designVoice } from '@/api/asset/voice'
import { useAssetHubStore } from '@/store/assetHub'

const VOICE_PRESETS = [
  { key: 'maleBroadcaster', label: '男播音', prompt: '沉稳的中年男性播音员，音色低沉浑厚，语速平稳，吐字清晰' },
  { key: 'gentleFemale', label: '温柔女', prompt: '温柔甜美的年轻女性，声音清脆悦耳，语调轻柔' },
  { key: 'matureMale', label: '成熟男', prompt: '成熟稳重的男性，声音富有磁性和感染力' },
  { key: 'livelyFemale', label: '活泼女', prompt: '活泼开朗的少女，声音甜美可爱，充满活力' },
  { key: 'intellectualFemale', label: '知性女', prompt: '知性优雅的女性，声音清晰悦耳，语调平和' },
  { key: 'narrator', label: '旁白', prompt: '富有感情的叙述者，声音温暖有故事感' },
]

const DEFAULT_PREVIEW_TEXT = '你好，很高兴认识你。这是AI为你专属设计的声音。'

const props = defineProps({
  speaker: { type: String, required: true },
  hasExistingVoice: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save'])

const store = useAssetHubStore()

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
let previewAudio = null

function handlePresetClick(preset) {
  if (selectedPresetKey.value === preset.key) {
    selectedPresetKey.value = null
    voicePrompt.value = ''
  } else {
    selectedPresetKey.value = preset.key
    voicePrompt.value = preset.prompt
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

async function handleSave() {
  if (selectedVoiceIndex.value === null || isSubmitting.value) return

  const selected = generatedVoices.value[selectedVoiceIndex.value]
  if (!selected) return

  isSubmitting.value = true
  try {
    emit('save', {
      voice_id: selected.voice_id,
      voice_type: 'ai_designed',
      custom_voice_url: selected.audio_url,
      voice_prompt: voicePrompt.value.trim(),
    })
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
  stopSchemePlay()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  border-bottom: none;
  padding: 16px 20px;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  border-top: none;
  background: none;
  padding: 12px 20px;
}

/* Speaker info */
.existing-chip {
  font-size: 11px;
  vertical-align: middle;
  margin-left: 8px;
}

/* Field groups */
.field-group {
  margin-bottom: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.field-textarea {
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
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
</style>
