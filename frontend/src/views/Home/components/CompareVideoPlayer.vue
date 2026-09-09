<template>
  <div class="cvp-wrap">
    <!-- 处理中占位 -->
    <div v-if="!afterSrc" class="cvp-empty">
      <span class="cvp-empty-text">{{ emptyText }}</span>
    </div>

    <template v-else>
      <!-- 模式切换工具栏：仅当两个视频都有时显示 -->
      <div v-if="beforeSrc" class="cvp-toolbar">
        <button
          type="button"
          class="cvp-mode-btn"
          :class="{ 'cvp-mode-active': mode === 'single' }"
          @click="setMode('single')"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="2"/></svg>
          仅结果
        </button>
        <button
          type="button"
          class="cvp-mode-btn"
          :class="{ 'cvp-mode-active': mode === 'split' }"
          @click="setMode('split')"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="8" rx="1"/><rect x="3" y="13" width="18" height="8" rx="1"/></svg>
          对比
        </button>
      </div>

      <!-- 单视频模式（默认） -->
      <div
        v-show="mode === 'single' || !beforeSrc"
        class="cvp-stage cvp-stage-single"
        @mouseenter="onSingleEnter"
        @mouseleave="onSingleLeave"
        @click="openFull(afterSrc)"
      >
        <span class="cvp-stage-label cvp-stage-label-after">超分后</span>
        <video
          ref="afterSingleEl"
          :src="afterSrc"
          :poster="afterPoster"
          class="cvp-video"
          muted
          loop
          playsinline
          preload="metadata"
        />
        <div v-if="!singlePlaying" class="cvp-play-hint">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        </div>
      </div>

      <!-- 上下分屏对比模式 -->
      <div
        v-show="mode === 'split' && beforeSrc"
        class="cvp-stage cvp-stage-split"
        @mouseenter="onSplitEnter"
        @mouseleave="onSplitLeave"
      >
        <div class="cvp-split-row" @click="openFull(beforeSrc)">
          <span class="cvp-split-label cvp-split-label-before">原视频</span>
          <video
            ref="beforeSplitEl"
            :src="beforeSrc"
            :poster="beforePoster"
            class="cvp-video"
            muted
            loop
            playsinline
            preload="metadata"
          />
        </div>
        <div class="cvp-split-divider" />
        <div class="cvp-split-row" @click="openFull(afterSrc)">
          <span class="cvp-split-label cvp-split-label-after">超分后</span>
          <video
            ref="afterSplitEl"
            :src="afterSrc"
            :poster="afterPoster"
            class="cvp-video"
            muted
            loop
            playsinline
            preload="metadata"
          />
        </div>
      </div>
    </template>

    <!-- 大图弹窗 -->
    <Teleport to="body">
      <div v-if="showFull" class="cvp-mask" @click.self="closeFull">
        <div class="cvp-modal">
          <video
            ref="fullEl"
            :src="fullSrc"
            class="cvp-full-video"
            controls
            autoplay
            playsinline
          />
          <button class="cvp-close" @click="closeFull">&times;</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  beforeSrc: { type: String, default: '' },
  afterSrc: { type: String, default: '' },
  beforePoster: { type: String, default: '' },
  afterPoster: { type: String, default: '' },
  emptyText: { type: String, default: '处理中…' },
})

// 'single'（默认仅结果） | 'split'（上下分屏对比）
const mode = ref('single')
const showFull = ref(false)
const fullSrc = ref('')
const singlePlaying = ref(false)

const afterSingleEl = ref(null)
const beforeSplitEl = ref(null)
const afterSplitEl = ref(null)
const fullEl = ref(null)

function pauseAll() {
  if (afterSingleEl.value) afterSingleEl.value.pause()
  if (beforeSplitEl.value) beforeSplitEl.value.pause()
  if (afterSplitEl.value) afterSplitEl.value.pause()
  singlePlaying.value = false
}

function setMode(m) {
  if (mode.value === m) return
  pauseAll()
  mode.value = m
}

// 单视频模式：hover 启动播放
function onSingleEnter() {
  if (mode.value !== 'single') return
  const el = afterSingleEl.value
  if (!el) return
  el.play().catch(() => {})
  singlePlaying.value = true
}

function onSingleLeave() {
  if (afterSingleEl.value) afterSingleEl.value.pause()
  singlePlaying.value = false
}

// 分屏模式：hover 同步播放两个视频
function onSplitEnter() {
  if (mode.value !== 'split') return
  syncSplitPlay()
}

function onSplitLeave() {
  if (beforeSplitEl.value) beforeSplitEl.value.pause()
  if (afterSplitEl.value) afterSplitEl.value.pause()
}

function syncSplitPlay() {
  const a = afterSplitEl.value
  const b = beforeSplitEl.value
  if (!a || !b) return
  // 以结果视频为基准对齐原视频
  if (Math.abs(a.currentTime - b.currentTime) > 0.15) {
    try { b.currentTime = a.currentTime } catch { /* noop */ }
  }
  a.play().catch(() => {})
  b.play().catch(() => {})
}

function openFull(src) {
  if (!src) return
  fullSrc.value = src
  showFull.value = true
  pauseAll()
}

function closeFull() {
  showFull.value = false
  fullSrc.value = ''
  if (fullEl.value) fullEl.value.pause()
}

function onKeyEsc(e) {
  if (e.key === 'Escape' && showFull.value) closeFull()
}

document.addEventListener('keydown', onKeyEsc)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyEsc)
  pauseAll()
})

// 任务结果到来时（WS 推送 result_video_url），重置为 single 模式
watch(() => props.afterSrc, (v) => {
  if (v) mode.value = 'single'
})
</script>

<style scoped>
.cvp-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 0.5rem;
  overflow: hidden;
  user-select: none;
}

/* 工具栏 */
.cvp-toolbar {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
  display: flex;
  gap: 4px;
  padding: 3px;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 8px;
  backdrop-filter: blur(6px);
}

.cvp-mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.75);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.cvp-mode-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.cvp-mode-active {
  background: rgba(59, 130, 246, 0.9);
  color: #fff;
}

.cvp-mode-active:hover {
  background: rgba(59, 130, 246, 0.9);
}

/* 视频舞台（单/分屏共用容器尺寸） */
.cvp-stage {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.cvp-stage-single {
  cursor: pointer;
}

.cvp-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  pointer-events: none;
}

/* 角标 */
.cvp-stage-label,
.cvp-split-label {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 5;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: rgba(0, 0, 0, 0.55);
  pointer-events: none;
  letter-spacing: 0.02em;
}

.cvp-stage-label-after,
.cvp-split-label-after {
  background: rgba(59, 130, 246, 0.85);
}

/* 单视频模式 */
.cvp-play-hint {
  position: absolute;
  bottom: 8px;
  right: 8px;
  z-index: 6;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

/* 分屏模式：上下两个 video，同步播放 */
.cvp-stage-split {
  display: flex;
  flex-direction: column;
}

.cvp-split-row {
  position: relative;
  flex: 1;
  min-height: 0;
  background: #000;
  cursor: pointer;
  overflow: hidden;
}

.cvp-split-row .cvp-video {
  object-fit: contain;
}

.cvp-split-divider {
  height: 2px;
  background: rgba(255, 255, 255, 0.85);
  flex-shrink: 0;
  box-shadow: 0 0 4px rgba(0, 0, 0, 0.4);
}

/* 处理中占位 */
.cvp-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(31, 41, 55, 0.6), rgba(17, 24, 39, 0.6));
}

.cvp-empty-text {
  color: #fff;
  font-size: 13px;
  font-weight: 500;
}

/* 大图弹窗 */
.cvp-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: cvp-in 0.15s ease-out;
}

.cvp-modal {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}

.cvp-full-video {
  max-width: 90vw;
  max-height: 85vh;
  border-radius: 0.5rem;
  background: #000;
}

.cvp-close {
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
}

.cvp-close:hover { background: rgba(239, 68, 68, 0.85); }

@keyframes cvp-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
