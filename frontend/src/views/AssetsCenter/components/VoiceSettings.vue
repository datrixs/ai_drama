<template>
  <div
    class="voice-settings glass-surface-soft"
    :class="{ 'voice-settings--compact': compact }"
  >
    <!-- Header row -->
    <div class="voice-settings-header">
      <div
        class="voice-settings-icon-circle glass-chip"
        :class="hasVoice ? 'glass-chip-neutral' : 'glass-chip-warning'"
      >
        <Mic :size="compact ? 12 : 14" />
      </div>
      <span class="voice-settings-label">
        语音设置
        <span v-if="!hasVoice" class="voice-settings-unset">(未设置)</span>
      </span>
    </div>

    <!-- Button row -->
    <div class="voice-settings-buttons">
      <!-- Upload button -->
      <button
        class="glass-btn-base glass-btn-secondary voice-settings-btn"
        :disabled="isUploading"
        @click="triggerUpload"
      >
        <Upload :size="14" />
        <span>{{ isUploading ? '上传中...' : hasVoice ? '已上传' : '上传语音' }}</span>
        <span v-if="hasVoice" class="voice-settings-dot"></span>
        <input
          ref="fileInputRef"
          type="file"
          accept="audio/*"
          class="voice-settings-file-input"
          @change="onFileSelect"
        />
      </button>

      <!-- AI Design button (暂时注释) -->
      <!-- <button
        class="glass-btn-base glass-btn-tone-info voice-settings-btn"
        @click="$emit('voiceDesign')"
      >
        <WandSparkles :size="14" />
        <span>AI 设计</span>
      </button> -->

      <!-- Voice Library button -->
      <button
        class="glass-btn-base glass-btn-secondary voice-settings-btn voice-settings-btn--library"
        @click="$emit('voiceSelect')"
      >
        <FolderOpen :size="14" />
        <span>音色库</span>
      </button>
    </div>

    <!-- Preview button -->
    <button
      v-if="customVoiceUrl"
      class="voice-settings-preview glass-btn-base"
      :class="isPreviewingVoice ? 'glass-btn-tone-info' : 'glass-btn-secondary'"
      @click="togglePreview"
    >
      <Pause v-if="isPreviewingVoice" :size="16" />
      <Play v-else :size="16" />
      <span>{{ isPreviewingVoice ? '暂停试听' : '试听语音' }}</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Mic,
  Upload,
  WandSparkles,
  FolderOpen,
  Pause,
  Play
} from '@lucide/vue'
import request from '@/utils/request'

const props = defineProps({
  characterId: { type: String, required: true },
  characterName: { type: String, required: true },
  customVoiceUrl: { type: String, default: null },
  compact: { type: Boolean, default: false },
  uploadHandler: { type: Function, default: null }
})

const emit = defineEmits(['voiceDesign', 'voiceSelect', 'voiceChanged'])

const hasVoice = computed(() => !!props.customVoiceUrl)

const fileInputRef = ref(null)
const isPreviewingVoice = ref(false)
const isUploading = ref(false)
let audio = null

function triggerUpload() {
  fileInputRef.value?.click()
}

async function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return

  const allowedExts = ['mp3', 'wav', 'ogg', 'm4a', 'aac']
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !allowedExts.includes(ext)) {
    ElMessage.warning('不支持的音频格式，请上传 MP3、WAV、OGG、M4A 或 AAC 文件')
    return
  }

  isUploading.value = true
  try {
    if (props.uploadHandler) {
      await props.uploadHandler(props.characterId, file)
    } else {
      const formData = new FormData()
      formData.append('character_id', props.characterId)
      formData.append('file', file)
      await request.post('/asset-hub/character-voice', formData)
    }
    ElMessage.success('语音上传成功')
    emit('voiceChanged')
  } catch {
    // request interceptor handles error display
  } finally {
    isUploading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

function togglePreview() {
  if (!props.customVoiceUrl) return

  if (isPreviewingVoice.value) {
    audio?.pause()
    isPreviewingVoice.value = false
  } else {
    audio = new Audio(props.customVoiceUrl)
    audio.onended = () => { isPreviewingVoice.value = false }
    audio.onerror = () => { isPreviewingVoice.value = false }
    audio.play()
    isPreviewingVoice.value = true
  }
}

onUnmounted(() => {
  if (audio) {
    audio.pause()
    audio = null
  }
})
</script>

<style scoped>
.voice-settings {
  border: 1px solid var(--glass-stroke-base);
  border-radius: 12px;
  padding: 16px;
}

.voice-settings--compact {
  padding: 12px;
}

/* Header */
.voice-settings-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--glass-stroke-base);
}

.voice-settings--compact .voice-settings-header {
  margin-bottom: 8px;
}

.voice-settings-header {
  border-bottom-color: var(--glass-stroke-base);
}

.voice-settings-icon-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.voice-settings--compact .voice-settings-icon-circle {
  width: 20px;
  height: 20px;
}

.voice-settings-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-secondary);
}

.voice-settings--compact .voice-settings-label {
  font-size: 12px;
}

.voice-settings-unset {
  color: var(--glass-text-tertiary);
}

/* Buttons row */
.voice-settings-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.voice-settings-btn {
  flex: 1;
  min-width: 70px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  position: relative;
}

.voice-settings--compact .voice-settings-btn {
  padding: 6px 8px;
}

.voice-settings-btn--library {
  color: var(--glass-tone-info-fg);
}

.voice-settings-file-input {
  display: none;
}

.voice-settings-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67c23a;
  position: absolute;
  top: 4px;
  right: 4px;
}

/* Preview button */
.voice-settings-preview {
  width: 100%;
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  border: 1px solid var(--glass-stroke-base);
}

.voice-settings-preview.glass-btn-tone-info {
  border-color: var(--glass-stroke-focus, #409eff);
}

.voice-settings-preview.glass-btn-secondary {
  color: var(--glass-tone-info-fg);
  border-color: var(--glass-stroke-base);
}
</style>
