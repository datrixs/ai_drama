<template>
  <div class="vhp-wrap" @mouseenter="startPlay" @mouseleave="stopPlay" @click="openFull">
    <video
      ref="videoEl"
      :src="src"
      class="vhp-video"
      :class="{ 'vhp-video-playing': isPlaying }"
      muted
      loop
      playsinline
      preload="none"
    />
    <div v-if="!isPlaying" class="vhp-play-hint">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21 5 3"/></svg>
    </div>
  </div>

  <!-- 大播放弹窗 -->
  <Teleport to="body">
    <div v-if="showFull" class="vfp-mask" @click.self="closeFull">
      <div class="vfp-box">
        <video
          ref="fullVideoEl"
          :src="src"
          class="vfp-video"
          controls
          autoplay
          playsinline
        />
        <button class="vfp-close" @click="closeFull">&times;</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  poster: { type: String, default: '' },
})

const videoEl = ref(null)
const fullVideoEl = ref(null)
const isPlaying = ref(false)
const showFull = ref(false)

function startPlay() {
  if (!videoEl.value) return
  videoEl.value.play().catch(() => {})
  isPlaying.value = true
}

function stopPlay() {
  if (!videoEl.value) return
  videoEl.value.pause()
  videoEl.value.currentTime = 0
  isPlaying.value = false
}

function openFull(e) {
  e.stopPropagation()
  showFull.value = true
}

function closeFull() {
  showFull.value = false
  if (fullVideoEl.value) {
    fullVideoEl.value.pause()
  }
}

function onKeyEsc(e) {
  if (e.key === 'Escape' && showFull.value) closeFull()
}

onMounted(() => document.addEventListener('keydown', onKeyEsc))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyEsc)
  if (videoEl.value) videoEl.value.pause()
})
</script>

<style scoped>
.vhp-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 0.5rem;
  overflow: hidden;
  background: #000;
  cursor: pointer;
}

.vhp-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.vhp-play-hint {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

/* 大播放弹窗 */
.vfp-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: vfp-in 0.15s ease-out;
}

.vfp-box {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.vfp-video {
  max-width: 90vw;
  max-height: 85vh;
  border-radius: 0.5rem;
  background: #000;
}

.vfp-close {
  position: absolute;
  top: -10px;
  right: -10px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.vfp-close:hover {
  background: rgba(239, 68, 68, 0.8);
}

@keyframes vfp-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
