<template>
  <div
    class="voice-card glass-surface group"
    :class="{
      'voice-card--selectable': selectionMode,
      'voice-card--selected': isSelected,
      'voice-card--platform': isPlatformAsset,
    }"
    @click="onCardClick"
  >
    <!-- Selected checkmark -->
    <div v-if="isSelected" class="voice-card-check">
      <Check :size="14" />
    </div>

    <!-- Icon area -->
    <div class="voice-card-icon-area">
      <div class="voice-card-mic-circle">
        <Mic :size="32" color="var(--glass-tone-info-fg)" />
      </div>

      <!-- Gender badge -->
      <span class="voice-card-gender-badge glass-chip glass-chip-neutral">
        {{ voice.gender === 'female' ? 'F' : 'M' }}
      </span>

      <!-- Play button -->
      <button
        class="voice-card-play-btn glass-btn-base"
        :class="isPlaying ? 'glass-btn-tone-info voice-card-play-btn--playing' : 'glass-btn-secondary'"
        @click.stop="togglePlay"
      >
        <Pause v-if="isPlaying" :size="20" />
        <Play v-else :size="20" />
      </button>

      <!-- 未同步火山角标 -->
      <span
        v-if="props.voice.custom_voice_url && !isVolcSynced && !isSyncing && !props.selectionMode"
        class="volc-unsynced-badge"
        @click.stop="handleSyncToVolc"
      >未同步</span>
      <span
        v-if="props.voice.custom_voice_url && !isVolcSynced && isSyncing && !props.selectionMode"
        class="volc-unsynced-badge volc-unsynced-badge--syncing"
      >同步中</span>
      
    </div>

    <!-- Info area -->
    <div class="voice-card-info">
      <div class="voice-card-name-row">
        <span class="voice-card-name">{{ voice.name }}</span>
        <button
          v-if="!selectionMode"
          class="voice-card-delete-btn glass-btn-base glass-btn-soft"
          @click.stop="showDeleteConfirm = true"
        >
          <Trash2 :size="16" />
        </button>
      </div>

      <el-tooltip
        v-if="voice.description"
        :content="voice.description"
        placement="top"
        :show-after="300"
        :disabled="!isPlatformAsset"
      >
        <p class="voice-card-description">{{ voice.description }}</p>
      </el-tooltip>

      <el-tooltip
        v-else-if="voice.voice_prompt"
        :content="voice.voice_prompt"
        placement="top"
        :show-after="300"
        :disabled="!isPlatformAsset"
      >
        <p class="voice-card-description voice-card-description--prompt">{{ voice.voice_prompt }}</p>
      </el-tooltip>
    </div>

    <!-- Delete confirmation overlay -->
    <DeleteConfirmOverlay
      v-if="showDeleteConfirm"
      @confirm="onDeleteConfirm"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import {
  Check,
  Mic,
  Pause,
  Play,
  Trash2
} from '@lucide/vue'
import { useAssetHubStore } from '@/store/assetHub'
import { syncUserAssetToVolc } from '@/api/shortVideo'
import DeleteConfirmOverlay from './DeleteConfirmOverlay.vue'

const props = defineProps({
  voice: { type: Object, required: true },
  selectionMode: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false }
})

// 平台资产：禁用所有用户操作，仅展示
const isPlatformAsset = computed(() => !!props.voice?.is_management_asset)

const emit = defineEmits(['select', 'delete'])

const store = useAssetHubStore()
const showDeleteConfirm = ref(false)
const isPlaying = ref(false)
const localSyncing = ref(false)
let audio = null

// region 兼容：domestic 写 volc_private_asset_id，overseas 写 byteplus_asset_id
const isVolcSynced = computed(() =>
  Boolean(props.voice.volc_private_asset_id || props.voice.byteplus_asset_id)
)
// 同步中状态：本地单个同步 or 批量同步进行中
const isSyncing = computed(() =>
  localSyncing.value || store.isAssetBatchSyncing(props.voice.id)
)

function onCardClick() {
  if (props.selectionMode) {
    emit('select', props.voice)
  }
}

function togglePlay() {
  if (!props.voice.custom_voice_url) return

  if (isPlaying.value) {
    audio?.pause()
    isPlaying.value = false
  } else {
    audio = new Audio(props.voice.custom_voice_url)
    audio.onended = () => { isPlaying.value = false }
    audio.onerror = () => { isPlaying.value = false }
    audio.play()
    isPlaying.value = true
  }
}

function onDeleteConfirm() {
  showDeleteConfirm.value = false
  emit('delete', props.voice.id)
}

async function handleSyncToVolc() {
  if (!props.voice.custom_voice_url || isSyncing.value) return
  localSyncing.value = true
  try {
    await syncUserAssetToVolc(props.voice.id, 'voice')
    await store.fetchVoices()
  } catch {
    // error handled by interceptor
  } finally {
    localSyncing.value = false
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
.voice-card {
  overflow: hidden;
  position: relative;
  transition: all 0.2s;
}

.voice-card--selectable {
  cursor: pointer;
}

.voice-card--selectable:hover {
  box-shadow: 0 0 0 2px var(--glass-focus-ring-strong, rgba(64, 158, 255, 0.3));
}

.voice-card--selected {
  box-shadow: 0 0 0 2px var(--glass-stroke-focus, #409eff);
}

.voice-card-check {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-card-icon-area {
  position: relative;
  background: var(--glass-bg-muted);
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-card-mic-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-card-gender-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  font-size: 12px;
}

.voice-card-play-btn {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  border: none;
}

.voice-card-play-btn--playing {
  animation: voice-pulse 1.5s ease-in-out infinite;
}

@keyframes voice-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
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

/* 平台资产视图：隐藏所有用户操作 */
.voice-card--platform .voice-card-delete-btn,
.voice-card--platform .volc-unsynced-badge {
  display: none !important;
}

.voice-card--platform .voice-card-description {
  -webkit-line-clamp: 3;
}

.voice-card-info {
  padding: 12px;
}

.voice-card-name-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.voice-card-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--glass-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.voice-card-delete-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  color: var(--glass-tone-danger-fg, #f56c6c);
  opacity: 0;
  transition: opacity 0.2s;
}

.group:hover .voice-card-delete-btn {
  opacity: 1;
}

.voice-card-description {
  margin-top: 4px;
  font-size: 12px;
  color: var(--glass-text-secondary);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
}

.voice-card-description--prompt {
  font-style: italic;
  color: var(--glass-text-tertiary);
}
</style>
