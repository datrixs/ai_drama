<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-dialog glass-surface-modal">
      <div class="dialog-header">
        <div class="dialog-title-row">
          <Mic :size="18" color="var(--glass-tone-info-fg)" />
          <h3 class="dialog-title">从音色库选择</h3>
        </div>
        <button class="glass-btn-base glass-btn-soft close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>

      <div class="dialog-content">
        <div v-if="voiceList.length === 0" class="empty-state">
          <p class="empty-text">暂无音色，请先创建</p>
        </div>
        <div v-else class="voice-grid">
          <div
            v-for="voice in voiceList"
            :key="voice.id"
            :class="[
              'voice-item',
              { 'voice-item--selected': selectedVoiceId === voice.id }
            ]"
            @click="selectedVoiceId = voice.id"
          >
            <div class="voice-item-left">
              <Mic :size="14" class="voice-item-icon" />
              <span class="voice-item-name">{{ voice.name }}</span>
            </div>
            <button
              class="play-btn"
              :class="playingId === voice.id ? 'play-btn--active' : ''"
              @click.stop="togglePlay(voice)"
            >
              <Pause v-if="playingId === voice.id" :size="14" />
              <Play v-else :size="14" />
              <span class="play-btn-text">{{ playingId === voice.id ? '暂停' : '试听' }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="dialog-footer">
        <button class="glass-btn-base glass-btn-secondary footer-btn" @click="$emit('close')">
          取消
        </button>
        <button
          class="glass-btn-base glass-btn-primary footer-btn"
          :disabled="!selectedVoiceId"
          @click="onConfirm"
        >
          确认选择
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { X, Mic, Pause, Play } from '@lucide/vue'
import { useAssetHubStore } from '@/store/assetHub'

const props = defineProps({
  voices: { type: Array, default: null }
})

const emit = defineEmits(['close', 'select'])

const store = useAssetHubStore()

const voiceList = computed(() => props.voices ?? store.voices)

const selectedVoiceId = ref(null)
const playingId = ref(null)
let audio = null

function togglePlay(voice) {
  if (playingId.value === voice.id) {
    audio?.pause()
    playingId.value = null
    return
  }

  if (!voice.custom_voice_url) return

  if (audio) {
    audio.pause()
  }

  audio = new Audio(voice.custom_voice_url)
  audio.onended = () => { playingId.value = null }
  audio.onerror = () => { playingId.value = null }
  audio.play()
  playingId.value = voice.id
}

function onConfirm() {
  const voice = voiceList.value.find(v => v.id === selectedVoiceId.value)
  if (voice) emit('select', voice)
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  if (audio) {
    audio.pause()
    audio = null
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

.close-btn:hover {
  color: var(--glass-text-secondary);
}

.dialog-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
}

.empty-text {
  font-size: 14px;
  color: var(--glass-text-tertiary);
}

.voice-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.voice-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid var(--glass-stroke-base);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  transition: border-color 0.2s, background 0.2s;
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.02));
}

.voice-item:hover {
  border-color: var(--glass-text-secondary);
}

.voice-item--selected {
  border-color: var(--glass-stroke-focus);
}

.voice-item-left {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.voice-item-icon {
  flex-shrink: 0;
  color: var(--glass-tone-info-fg);
}

.voice-item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.play-btn {
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
  transition: border-color 0.2s, background 0.2s;
}

.play-btn:hover {
  border-color: var(--glass-tone-info-fg);
}

.play-btn--active {
  border-color: var(--glass-stroke-focus);
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.04));
}

.play-btn-text {
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 12px 20px;
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}
</style>
