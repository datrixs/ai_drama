<template>
  <div class="srp-panel">
    <!-- 可滚动的结果区 -->
    <div ref="scrollRef" class="srp-scroll-area" @scroll.passive="onScroll" @wheel.passive="onWheel" @click="handleScrollAreaClick">
      <!-- 加载更多 -->
      <div v-if="store.loadingMore" class="srp-loading">
        <span class="srp-loading-spinner" />
        <span>加载中...</span>
      </div>
      <div v-if="!store.hasMoreTasks && store.tasks.length > 0" class="srp-nomore">
        没有更多记录
      </div>
      <!-- 空状态 -->
      <div v-if="store.tasks.length === 0 && !store.loadingMore" class="srp-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M10 9l5 3-5 3V9z"/></svg>
        <span>上传视频开始超分</span>
      </div>
      <!-- 任务列表（最新在底部） -->
      <SuperResolutionResultItem
        v-for="task in sortedTasks"
        :key="task.id"
        :task="task"
        @retry="store.retryTask"
      />
    </div>

    <!-- 底部编辑条 -->
    <div class="srp-bottom" :class="'srp-bottom-' + editorMode">
      <SuperResolutionEditorBar
        ref="editorBarRef"
        :editorMode="editorMode"
        @expand="handleEditorExpand"
        @focus-change="handleFocusChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import SuperResolutionEditorBar from './SuperResolutionEditorBar.vue'
import SuperResolutionResultItem from './SuperResolutionResultItem.vue'
import { useSuperResolutionStore } from '@/store/superResolution'

const store = useSuperResolutionStore()
const scrollRef = ref(null)
const editorBarRef = ref(null)

const sortedTasks = computed(() => [...store.tasks].reverse())

// 编辑器模式：参考短视频 Panel 的 inline / floating / mini 三态
// wantExpanded 是用户意图（独立于滚动位置）：
//   - 滚到底部 / 点击 mini bar / 聚焦输入 → true
//   - 向上滚 / 点击上面结果区 / 失焦     → false
// 这样可以避免 editor 展开导致 clientHeight 变化、distFromBottom 漂移时
// 在 inline / mini 之间反复横跳
const wantExpanded = ref(true)
const distFromBottom = ref(0)
let suppressScrollUntil = 0
let syncTimer = 0

const SCROLL_THRESHOLD = 60

const editorMode = computed(() => {
  // 已选源视频：保持展开（方便调整参数后直接提交）
  if (store.sourceVideoUrl) {
    return distFromBottom.value < SCROLL_THRESHOLD ? 'inline' : 'floating'
  }
  // 用户不想展开：缩小
  if (!wantExpanded.value) return 'mini'
  // 想展开：底部 inline，否则 floating
  return distFromBottom.value < SCROLL_THRESHOLD ? 'inline' : 'floating'
})

// 切到 inline 时把 scrollTop 钉到底；CSS 过渡（300ms）结束后再 sync 一次，
// 抑制期内屏蔽 scroll 事件，避免过渡中途的布局漂移触发状态切换
watch(editorMode, (newMode) => {
  if (newMode !== 'inline') return
  suppressScrollUntil = Date.now() + 380
  clearTimeout(syncTimer)
  const sync = () => {
    const el = scrollRef.value
    if (el && editorMode.value === 'inline') {
      el.scrollTop = el.scrollHeight
      distFromBottom.value = 0
    }
  }
  sync()
  syncTimer = setTimeout(sync, 360)
})

const LOAD_MORE_THRESHOLD = 80
let isLoadingMore = false

function checkLoadMore() {
  if (isLoadingMore || !store.hasMoreTasks) return
  const el = scrollRef.value
  if (!el) return
  if (el.scrollTop <= LOAD_MORE_THRESHOLD) {
    isLoadingMore = true
    store.loadMoreTasks().finally(() => {
      isLoadingMore = false
    })
  }
}

function updateDistFromBottom() {
  const el = scrollRef.value
  if (!el) return
  distFromBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight
}

function onScroll() {
  if (Date.now() < suppressScrollUntil) return
  updateDistFromBottom()
  // 滚到底部时自动展开（用户意图）
  if (distFromBottom.value < SCROLL_THRESHOLD) wantExpanded.value = true
  checkLoadMore()
}

function onWheel(e) {
  if (e.deltaY < 0) {
    // 用户主动向上滚 → 放弃展开意图，立即让出控制权
    clearTimeout(syncTimer)
    suppressScrollUntil = 0
    updateDistFromBottom()
    if (!store.sourceVideoUrl) wantExpanded.value = false
  }
}

// 点击上面结果区 → 缩小 editor（超分 editor 展开后没有可聚焦 input，
// 短视频的 focusout 在这里失效，用 click 兜底）
function handleScrollAreaClick() {
  if (!store.sourceVideoUrl) wantExpanded.value = false
}

function handleEditorExpand() {
  wantExpanded.value = true
}

function handleFocusChange(focused) {
  // 只在聚焦时展开；失焦不主动缩小——select 关闭 / 点击 sr-bar 内空白
  // 都会让焦点短暂离开 sr-bar，触发 focusout 误判。缩小交由 onWheel
  // (向上滚) 和 handleScrollAreaClick (点击结果区) 控制。
  if (!store.sourceVideoUrl && focused) wantExpanded.value = true
}

// 新任务添加时滚动到底部
watch(() => store.tasks.length, () => {
  if (isLoadingMore) return
  nextTick(scrollToBottom)
})

function scrollToBottom() {
  const el = scrollRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
    distFromBottom.value = 0
  }
}

onMounted(() => {
  store.fetchTasks()
  nextTick(scrollToBottom)
})

onUnmounted(() => {
  clearTimeout(syncTimer)
})

defineExpose({ editorBarRef, scrollToBottom })
</script>

<style scoped>
.srp-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.srp-scroll-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 8px 12px;
}

.srp-bottom {
  flex-shrink: 0;
  padding: 0 16px 20px;
  transition: padding 0.25s ease;
}

.srp-bottom-inline,
.srp-bottom-floating {
  padding: 16px 16px 20px;
}

.srp-bottom-mini {
  padding: 0 16px 20px;
}

.srp-loading {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 0;
  font-size: 12px;
  color: var(--glass-text-tertiary, #999);
  background: linear-gradient(to bottom, var(--glass-bg-surface, rgba(255, 255, 255, 0.92)) 70%, transparent);
  backdrop-filter: blur(8px);
}

.srp-loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from, #3b82f6);
  border-radius: 50%;
  animation: srp-spin 0.6s linear infinite;
}

@keyframes srp-spin { to { transform: rotate(360deg); } }

.srp-nomore {
  text-align: center;
  padding: 6px 0;
  font-size: 12px;
  color: var(--glass-text-tertiary, #999);
}

.srp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 4rem 0;
  color: var(--glass-text-tertiary, #999);
  font-size: 13px;
}
</style>
