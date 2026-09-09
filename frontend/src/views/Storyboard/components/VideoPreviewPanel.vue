<template>
  <div class="vpp-panel">
    <div class="vpp-monitor">
      <div class="vpp-frame" :style="frameStyle">
        <!-- 生成中 -->
        <div v-if="activeSegment?._generating" class="vpp-gen">
          <div class="vpp-gen-rings">
            <div class="vpp-gen-ring-outer" />
            <div class="vpp-gen-ring-inner" />
            <div class="vpp-gen-dot" />
          </div>
          <div class="vpp-gen-text">
            <span class="vpp-gen-label">视频生成中...</span>
            <span class="vpp-gen-hint">{{ activeSegment._progress || 0 }}%</span>
          </div>
          <div class="vpp-gen-bar"><div class="vpp-gen-shimmer" /></div>
        </div>

        <!-- 已完成 -->
        <video v-else-if="activeSegment?.video_url" :src="activeSegment.video_url"
          controls playsinline preload="auto" :key="activeSegment.video_url" class="vpp-video" />

        <!-- 空 -->
        <div v-else class="vpp-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.35">
            <polygon points="23 7 16 12 23 17"/><rect x="1" y="5" width="15" height="14" rx="2"/>
          </svg>
          <span>暂无视频预览</span>
        </div>
      </div>

      <!-- 比例标签 -->
      <div class="vpp-ratio-badge">{{ ratio }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  activeSegment: { type: Object, default: null },
  ratio: { type: String, default: '16:9' },
})

const frameStyle = computed(() => {
  const map = { '16:9': '16/9', '9:16': '9/16', '1:1': '1/1' }
  return { aspectRatio: map[props.ratio] || '16/9' }
})
</script>

<style scoped>
.vpp-panel {
  width: min(50%, 560px);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

/* 显示器区域 */
.vpp-monitor {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  background: linear-gradient(145deg, #111113 0%, #09090b 50%, #050507 100%);
  border-radius: 0.75rem;
  border: 1px solid rgba(255,255,255,0.06);
  padding: 1.25rem;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 4px 24px rgba(0,0,0,0.2);
}

/* 视频帧 */
.vpp-frame {
  width: 100%;
  max-height: 100%;
  border-radius: 0.375rem;
  overflow: hidden;
  background: #000;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.06), 0 8px 32px rgba(0,0,0,0.4);
  display: flex;
  flex-direction: column;
}

.vpp-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

/* 比例标签 */
.vpp-ratio-badge {
  position: absolute;
  bottom: 0.5rem;
  right: 0.625rem;
  font-size: 10px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
  background: rgba(0,0,0,0.4);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  pointer-events: none;
}

/* 空状态 */
.vpp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 3rem 1rem;
  color: rgba(255,255,255,0.25);
}
.vpp-empty span { font-size: 0.8rem; }

/* 生成动画 */
.vpp-gen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.25rem;
  padding: 3rem 1rem;
}
.vpp-gen-rings { position: relative; width: 72px; height: 72px; display: flex; align-items: center; justify-content: center; }
.vpp-gen-ring-outer {
  position: absolute; inset: 0;
  border: 2px solid transparent; border-top-color: rgba(99,179,237,0.5); border-right-color: rgba(99,179,237,0.2);
  border-radius: 50%; animation: vpp-spin 1.5s linear infinite;
}
.vpp-gen-ring-inner {
  position: absolute; inset: 12px;
  border: 2px solid transparent; border-bottom-color: rgba(129,230,217,0.5); border-left-color: rgba(129,230,217,0.2);
  border-radius: 50%; animation: vpp-spin-rev 2s linear infinite;
}
.vpp-gen-dot {
  width: 20px; height: 20px; border-radius: 50%;
  background: linear-gradient(135deg, #60a5fa, #2dd4bf);
  animation: vpp-pulse 1.5s ease-in-out infinite;
}
.vpp-gen-text { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; }
.vpp-gen-label { font-size: 0.85rem; font-weight: 500; color: rgba(255,255,255,0.7); }
.vpp-gen-hint { font-size: 11px; color: rgba(255,255,255,0.35); }
.vpp-gen-bar { width: 140px; height: 3px; border-radius: 2px; background: rgba(255,255,255,0.08); overflow: hidden; }
.vpp-gen-shimmer {
  height: 100%; width: 33%; border-radius: 2px;
  background: linear-gradient(90deg, transparent, rgba(96,165,250,0.6), transparent);
  animation: vpp-shimmer 1.8s ease-in-out infinite;
}

@keyframes vpp-spin { to { transform: rotate(360deg); } }
@keyframes vpp-spin-rev { to { transform: rotate(-360deg); } }
@keyframes vpp-pulse { 0%,100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.2); opacity: 1; } }
@keyframes vpp-shimmer { 0% { transform: translateX(-150%); } 100% { transform: translateX(350%); } }
</style>
