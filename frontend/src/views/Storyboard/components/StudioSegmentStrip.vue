<template>
  <div :class="['sss-wrap', { 'sss-embed': embedInCard }]" @click.stop @keydown.stop>
    <div class="sss-label">片段</div>
    <div class="sss-row">
      <div v-for="(seg, idx) in segments" :key="seg.id"
        class="sss-card" :class="{ 'sss-active': idx === activeIndex }"
        role="button" tabindex="0"
        @click="$emit('select', idx)"
        @keydown.enter.prevent="$emit('select', idx)"
        :title="seg.segment_intent ? `片段 ${idx + 1} · ${seg.segment_intent}` : `片段 ${idx + 1}`">

        <!-- 左侧 + 号：在当前片段前插入 -->
        <button type="button" class="sss-insert sss-insert-left"
          @click.stop="$emit('insert-before', idx)"
          title="在前面插入片段" aria-label="在前面插入片段">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>

        <!-- 右侧 + 号：在当前片段后插入 -->
        <button type="button" class="sss-insert sss-insert-right"
          @click.stop="$emit('insert-after', idx)"
          title="在后面插入片段" aria-label="在后面插入片段">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>

        <!-- 右上角删除按钮：hover 时显示；生成中的片段不显示；导演模式下唯一片段不显示（避免删空） -->
        <button v-if="!isGenerating(seg) && (!isDirectorMode || segments.length > 1)" type="button" class="sss-delete"
          @click.stop="$emit('delete', idx)"
          title="删除片段" aria-label="删除片段">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>

        <div class="sss-thumb">
          <img v-if="seg.thumbnail_url || seg.cover_url || seg.image_url" :src="seg.thumbnail_url || seg.cover_url || seg.image_url" class="sss-img" @error="onImgError($event, seg)" />
          <video v-else-if="seg.video_url" :src="seg.video_url" class="sss-img" preload="metadata" muted playsinline @loadeddata="onVideoThumb" />
          <div v-else class="sss-empty-ph">{{ idx + 1 }}</div>

          <!-- 视频标记 -->
          <template v-if="seg.video_url">
            <div class="sss-play-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21"/></svg>
            </div>
            <div class="sss-dot" />
          </template>

          <!-- 生成中遮罩 -->
          <div v-if="isGenerating(seg)" class="sss-gen-mask">
            <div class="sss-spinner" />
          </div>

          <!-- 底部信息 -->
          <div class="sss-overlay">
            <span class="sss-overlay-title">片段 {{ idx + 1 }}</span>
            <span v-if="segDuration(seg)" class="sss-overlay-dur">{{ segDuration(seg) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  segments: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: 0 },
  embedInCard: { type: Boolean, default: false },
  isDirectorMode: { type: Boolean, default: false },
})
defineEmits(['select', 'insert-before', 'insert-after', 'delete'])

function isGenerating(seg) {
  return seg?.status === 'image_generating' || seg?.status === 'video_generating'
}

function onVideoThumb(e) {
  const v = e.target
  if (v.duration && isFinite(v.duration)) {
    v.currentTime = Math.min(0.5, v.duration * 0.1)
  }
}

function onImgError(e, seg) {
  const img = e.target
  if (img.dataset.fallback) return
  const fallback = seg.cover_url || seg.image_url
  if (!fallback) { img.remove(); return }
  img.dataset.fallback = '1'
  img.src = fallback
}

function segDuration(seg) {
  const shots = seg.shots || []
  if (!shots.length) return null
  const total = shots.reduce((sum, s) => sum + (s.durationHintSec || 3), 0)
  return formatDuration(total)
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`
}
</script>

<style scoped>
.sss-wrap {
  width: 100%;
  padding: 0.5rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(111,126,153,0.24);
  background: rgba(255,255,255,0.688);
}
.sss-embed {
  border: none;
  background: none;
  padding: 0;
}
.sss-label {
  font-size: 10px; font-weight: 500; color: #4b5563;
  margin-bottom: 0.375rem;
}
.sss-row {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  /* overflow-x:auto 会强制 overflow-y 也变 auto，按钮悬出 padding 会被裁切，需留足余量：
     - 按钮宽 18px，hover 时 scale(1.15) 视觉宽 ≈20.7px
     - + 号按钮 translate(-50%) 悬出 ≈10.35px（hover 态）
     - 删除按钮 translate(40%, -40%) 悬出 ≈8.3px（hover 态）
     - 垂直 padding 0.75rem(12px) 单独容纳；水平方向 .sss-wrap 自带 0.5rem padding 叠加即可 */
  padding: 0.75rem 0.25rem;
  scrollbar-width: thin;
  -ms-overflow-style: none;
}
.sss-row::-webkit-scrollbar { height: 6px; }
@media (min-width: 640px) {
  .sss-row { gap: 0.625rem; }
}
.sss-card {
  flex-shrink: 0; display: flex; flex-direction: column;
  overflow: visible; text-align: left;
  border-radius: 0.75rem; border: 1px solid rgba(111,126,153,0.24);
  background: none; cursor: pointer; padding: 0; transition: all 0.15s;
  outline: none; position: relative;
}
.sss-card:focus-visible {
  outline: 2px solid #1d63e8;
  outline-offset: -2px;
}
.sss-card:hover { border-color: rgba(47,123,255,0.64); }
.sss-active {
  border-color: #0a0a0a;
  box-shadow: 0 0 0 2px rgba(10,10,10,0.25), 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
}
.sss-thumb {
  position: relative;
  width: 6rem; height: 4rem;
  background: rgba(255,255,255,0.88);
  overflow: hidden;
  border-radius: 0.65rem;
}
@media (min-width: 640px) {
  .sss-thumb { height: 4.5rem; width: 6.75rem; }
}

/* 左右 + 号按钮 */
.sss-insert {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #1d63e8;
  color: #fff;
  border: 2px solid #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; padding: 0;
  opacity: 0; pointer-events: none;
  transition: opacity 0.15s, background 0.15s, transform 0.15s;
  z-index: 3;
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
}
.sss-insert-left { left: 0; }
.sss-insert-right { left: 100%; }
.sss-card:hover .sss-insert {
  opacity: 1; pointer-events: auto;
}
.sss-insert:hover {
  background: #0a4dc7;
  transform: translate(-50%, -50%) scale(1.15);
}

/* 右上角删除按钮 */
.sss-delete {
  position: absolute;
  top: 0; right: 0;
  transform: translate(40%, -40%);
  width: 18px; height: 18px;
  border-radius: 50%;
  background: rgba(239,68,68,0.95);
  color: #fff;
  border: 2px solid #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; padding: 0;
  opacity: 0; pointer-events: none;
  transition: opacity 0.15s, background 0.15s, transform 0.15s;
  z-index: 4;
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
}
.sss-card:hover .sss-delete {
  opacity: 1; pointer-events: auto;
}
.sss-delete:hover {
  background: rgb(220,38,38);
  transform: translate(40%, -40%) scale(1.15);
}

/* 生成中遮罩 */
.sss-gen-mask {
  position: absolute; inset: 0;
  background: rgba(255,255,255,0.45);
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
}
.sss-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(29,99,232,0.25);
  border-top-color: #1d63e8;
  border-radius: 50%;
  animation: sss-spin 0.8s linear infinite;
}
@keyframes sss-spin {
  to { transform: rotate(360deg); }
}
.sss-img { width: 100%; height: 100%; object-fit: cover; }
.sss-video-ph {
  width: 100%; height: 100%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: linear-gradient(135deg, rgba(191,219,254,0.9), rgba(147,197,253,0.7));
  color: #1e40af; font-size: 10px; font-weight: 500; gap: 0.15rem;
}
.sss-empty-ph {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, rgba(229,231,235,0.9), rgba(209,213,219,0.7));
  font-size: 10px; font-weight: 500; color: #52525b;
}
.sss-dot {
  position: absolute; top: 2px; left: 2px;
  width: 8px; height: 8px; border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.2);
}
.sss-play-badge {
  position: absolute; top: 2px; right: 2px;
  width: 20px; height: 20px; border-radius: 50%;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
}
.sss-overlay {
  position: absolute; left: 0; right: 0; bottom: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.6), transparent);
  padding: 0.25rem;
  pointer-events: none;
  display: flex; align-items: center; justify-content: space-between;
}
.sss-overlay-title {
  font-size: 10px; font-weight: 600; color: #fff;
  filter: drop-shadow(0 1px 1px rgba(0,0,0,0.3));
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sss-overlay-dur {
  font-size: 10px; font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: rgba(255,255,255,0.9);
  filter: drop-shadow(0 1px 1px rgba(0,0,0,0.3));
  flex-shrink: 0;
}
</style>
