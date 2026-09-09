<template>
  <div class="sv-panel">
    <!-- 可滚动的对话历史区域 -->
    <div ref="scrollRef" class="sv-scroll-area">
      <ChatArea />
    </div>

    <!-- 底部编辑区域 -->
    <div class="sv-bottom" :class="'sv-bottom-' + editorMode">
      <!-- 资产按钮栏（仅非迷你模式且参考模式时显示） -->
      <div
        v-if="editorMode !== 'mini' && store.generationType === 'reference'"
        class="sv-asset-toolbar"
      >
        <button class="sv-asset-btn" @mousedown.prevent @click="$emit('openProjectPicker')">项目资产库</button>
        <button class="sv-asset-btn" @mousedown.prevent @click="$emit('openAssetCenter')">资产中心</button>
      </div>
      <EditorBar
        ref="editorBarRef"
        :editorMode="editorMode"
        @expand="handleEditorExpand"
        @focus-change="handleFocusChange"
        @open-project-picker="$emit('openProjectPicker')"
        @open-asset-center="$emit('openAssetCenter')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import ChatArea from './ChatArea.vue'
import EditorBar from './EditorBar.vue'
import { useShortVideoStore } from '@/store/shortVideo'

defineEmits(['openProjectPicker', 'openAssetCenter'])

const props = defineProps({
  pickerOpen: { type: Boolean, default: false },
})

const store = useShortVideoStore()
const editorBarRef = ref(null)
const scrollRef = ref(null)
const isComposerFocused = ref(false)
// 用户主动滚离底部的像素距离（不受编辑框高度变化影响）
const distFromBottom = ref(0)
// 模式切换时抑制 scroll 事件（防止布局变化导致的假滚动重置状态）
let suppressScrollUntil = 0

defineExpose({ editorBarRef, scrollToBottom })

const SCROLL_THRESHOLD = 60

// 编辑器模式计算：inline | mini | floating
const editorMode = computed(() => {
  if (distFromBottom.value < SCROLL_THRESHOLD) return 'inline'
  if (isComposerFocused.value || props.pickerOpen) return 'floating'
  // 有内容时保持展开
  const hasContent = store.promptText.trim().length > 0
    || store.totalRefCount > 0
    || store.firstFrameUrl
    || store.lastFrameUrl
  if (hasContent) return 'floating'
  return 'mini'
})

// 模式切换时抑制 scroll 事件 300ms
watch(editorMode, () => {
  suppressScrollUntil = Date.now() + 300
})

// 加载更多阈值：距离顶部 80px 以内触发
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

function onScroll() {
  if (Date.now() < suppressScrollUntil) return
  updateDistFromBottom()
  checkLoadMore()
}

function updateDistFromBottom() {
  const el = scrollRef.value
  if (!el) return
  distFromBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight
}

function handleEditorExpand() {
  isComposerFocused.value = true
}

function handleFocusChange(focused) {
  isComposerFocused.value = focused
}

// 新任务添加时滚动到底部
watch(() => store.tasks.length, () => {
  if (isLoadingMore) return
  nextTick(scrollToBottom)
})

// 任务列表加载完成后滚动到底部
watch(() => store.tasks, () => {
  if (isLoadingMore) return
  nextTick(scrollToBottom)
}, { deep: false })

function scrollToBottom() {
  const el = scrollRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
    distFromBottom.value = 0
  }
}

onMounted(() => {
  store.fetchTasks()
  // scroll 事件用 passive 提升性能，wheel 事件作为兜底
  const el = scrollRef.value
  if (el) {
    el.addEventListener('scroll', onScroll, { passive: true })
    el.addEventListener('wheel', onWheel, { passive: true })
  }
  nextTick(scrollToBottom)
})

function onWheel(e) {
  if (e.deltaY < 0) {
    // 用户主动向上滚，立即响应
    updateDistFromBottom()
  }
}

onUnmounted(() => {
  const el = scrollRef.value
  if (el) {
    el.removeEventListener('scroll', onScroll)
    el.removeEventListener('wheel', onWheel)
  }
})
</script>

<style scoped>
.sv-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sv-scroll-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.sv-bottom {
  flex-shrink: 0;
  width: 100%;
  transition: padding 0.25s ease;
}

.sv-bottom-inline {
  padding: 0 16px 20px;
}

.sv-bottom-mini {
  padding: 0 16px 20px;
}

.sv-bottom-floating {
  padding: 0 16px 20px;
}

.sv-asset-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px 0 4px;
  flex-shrink: 0;
}

.sv-asset-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 6px;
  border: 1px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  background: var(--glass-bg-surface, rgba(255, 255, 255, 0.88));
  color: #6b7280;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.sv-asset-btn:hover {
  color: #374151;
  border-color: var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  background: rgba(0, 0, 0, 0.03);
}
</style>
