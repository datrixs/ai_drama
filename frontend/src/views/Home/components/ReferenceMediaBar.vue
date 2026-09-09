<template>
  <div v-if="hasAnyReference || uploading" class="ref-bar">
    <div class="ref-scroll">
      <!-- 加载中状态 -->
      <div v-if="uploading" class="ref-card ref-loading-card">
        <div class="ref-loading-spinner" />
        <span class="ref-name">加载中</span>
      </div>
      <!-- 图片引用 -->
      <div v-for="(img, i) in images" :key="'img-' + i" class="ref-card" @click="preview('image', img.url)">
        <div class="ref-thumb-wrap">
          <img :src="img.thumbnail_url || img.url" :alt="img.refLabel" class="ref-thumb" @error="onImgError($event, img.url)" />
          <button class="ref-remove" @mousedown.prevent @click.stop="$emit('remove', 'image', i)">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
          </button>
          <span class="ref-type-badge ref-type-image">图</span>
        </div>
        <span class="ref-name">{{ img.refLabel || '图片' }}</span>
      </div>
      <!-- 视频引用 -->
      <div v-for="(vid, i) in videos" :key="'vid-' + i" class="ref-card" @click="preview('video', vid.url)">
        <div class="ref-thumb-wrap">
          <img v-if="vid.thumbnail_url" :src="vid.thumbnail_url" :alt="vid.refLabel" class="ref-thumb" />
          <div v-else class="ref-thumb ref-thumb-video">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          </div>
          <button class="ref-remove" @mousedown.prevent @click.stop="$emit('remove', 'video', i)">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
          </button>
          <span class="ref-type-badge ref-type-video">视</span>
        </div>
        <span class="ref-name">{{ vid.refLabel || '视频' }}</span>
      </div>
      <!-- 音频引用 -->
      <div v-for="(aud, i) in audios" :key="'aud-' + i" class="ref-card">
        <div class="ref-thumb-wrap">
          <div class="ref-thumb ref-thumb-audio" @click.stop="toggleAudio(aud)">
            <svg v-if="!aud.playing" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
          </div>
          <button class="ref-remove" @mousedown.prevent @click.stop="$emit('remove', 'audio', i)">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
          </button>
          <span class="ref-type-badge ref-type-audio">音</span>
        </div>
        <span class="ref-name">{{ aud.refLabel || '音频' }}</span>
        <audio :src="aud.url" preload="metadata" @ended="aud.playing = false" style="display:none" />
      </div>
    </div>
    <!-- 数量提示 -->
    <div class="ref-count">
      {{ totalCount }}/{{ maxTotal }}
    </div>

    <!-- 预览弹窗 -->
    <Teleport to="body">
      <div v-if="previewItem" class="ref-preview-mask" @click="previewItem = null">
        <div class="ref-preview-box" @click.stop>
          <img v-if="previewItem.type === 'image'" :src="previewItem.url" class="ref-preview-img" />
          <video v-if="previewItem.type === 'video'" :src="previewItem.url" controls class="ref-preview-video" autoplay />
          <button class="ref-preview-close" @click="previewItem = null">×</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  images: { type: Array, default: () => [] },
  videos: { type: Array, default: () => [] },
  audios: { type: Array, default: () => [] },
  uploading: { type: Boolean, default: false },
})

defineEmits(['remove'])

const hasAnyReference = computed(() =>
  props.images.length > 0 || props.videos.length > 0 || props.audios.length > 0
)

const totalCount = computed(() => props.images.length + props.videos.length + props.audios.length)
const maxTotal = 12

// 预览弹窗
const previewItem = ref(null)

function preview(type, url) {
  if (!url) return
  previewItem.value = { type, url }
}

function onImgError(e, originalUrl) {
  const img = e.target
  if (img.dataset.fallback || !originalUrl) return
  img.dataset.fallback = '1'
  img.src = originalUrl
}

// 音频播放
let currentAudioEl = null
let currentAudioRef = null

function toggleAudio(aud) {
  const cards = document.querySelectorAll('.ref-thumb-audio')
  for (const card of cards) {
    const audio = card.parentElement.querySelector('audio')
    if (audio && audio.src === aud.url) {
      if (aud.playing) {
        audio.pause()
        aud.playing = false
      } else {
        if (currentAudioEl && currentAudioEl !== audio) {
          currentAudioEl.pause()
          if (currentAudioRef) currentAudioRef.playing = false
        }
        audio.play()
        aud.playing = true
        currentAudioEl = audio
        currentAudioRef = aud
      }
      break
    }
  }
}
</script>

<style scoped>
.ref-bar {
  position: relative;
  padding: 4px 0;
}

.ref-scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  align-items: flex-start;
}

.ref-scroll::-webkit-scrollbar { display: none; }

.ref-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  cursor: pointer;
}

.ref-thumb-wrap {
  position: relative;
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}

.ref-thumb {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  object-fit: cover;
  display: block;
}

.ref-thumb-video,
.ref-thumb-audio {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-bg-muted, rgba(0,0,0,0.04));
  border: 1.5px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  border-radius: 10px;
  color: var(--glass-text-secondary, #666);
}

.ref-name {
  font-size: 11px;
  font-weight: 500;
  color: var(--glass-text-tertiary, #666);
  max-width: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.ref-type-badge {
  position: absolute;
  bottom: 3px;
  left: 3px;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  line-height: 1.4;
}

.ref-type-image { background: rgba(59, 130, 246, 0.85); }
.ref-type-video { background: rgba(139, 92, 246, 0.85); }
.ref-type-audio { background: rgba(245, 158, 11, 0.85); }

.ref-remove {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.95);
  color: var(--glass-text-tertiary, #999);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  transition: all 0.15s;
  padding: 0;
}

.ref-remove:hover {
  color: #ef4444;
  background: #fff;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.25);
}

.ref-count {
  position: absolute;
  top: 0;
  right: 2px;
  font-size: 11px;
  color: var(--glass-text-tertiary, #999);
}

/* 加载中卡片 */
.ref-loading-card {
  cursor: default;
}

.ref-loading-card .ref-loading-spinner {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  background: var(--glass-bg-muted, rgba(0,0,0,0.04));
  border: 1.5px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.ref-loading-card .ref-loading-spinner::after {
  content: '';
  width: 24px;
  height: 24px;
  border: 2.5px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  border-top-color: var(--glass-accent-from, #3b82f6);
  border-radius: 50%;
  animation: ref-spin 0.8s linear infinite;
  position: absolute;
}

@keyframes ref-spin {
  to { transform: rotate(360deg); }
}

/* 预览弹窗 */
.ref-preview-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.15s ease-out;
}

.ref-preview-box {
  position: relative;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ref-preview-img {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 0.5rem;
}

.ref-preview-video {
  max-width: 90vw;
  max-height: 85vh;
  border-radius: 0.5rem;
}

.ref-preview-close {
  position: absolute;
  top: -12px;
  right: -12px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.ref-preview-close:hover {
  background: rgba(239, 68, 68, 0.8);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
