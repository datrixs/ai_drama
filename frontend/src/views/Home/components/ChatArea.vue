<template>
  <div class="ca-area">
    <!-- 加载更多指示器 -->
    <div v-if="store.loadingMore" class="ca-loading">
      <span class="ca-loading-spinner" />
      <span>加载中...</span>
    </div>
    <div v-if="!store.hasMoreTasks && store.tasks.length > 0" class="ca-nomore">
      没有更多记录
    </div>
    <!-- 空状态 -->
    <div v-if="store.tasks.length === 0 && !store.loadingMore" class="ca-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M10 9l5 3-5 3V9z"/></svg>
      <span>还没有生成记录，开始创作吧</span>
    </div>
    <!-- 对话记录列表（按时间升序，最新在底部） -->
    <ChatItem
      v-for="task in sortedTasks"
      :key="task.id"
      :task="task"
      @retry="store.retryTask"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useShortVideoStore } from '@/store/shortVideo'
import ChatItem from './ChatItem.vue'

const store = useShortVideoStore()

const sortedTasks = computed(() => [...store.tasks].reverse())
</script>

<style scoped>
.ca-area {
  padding: 8px 12px;
}

.ca-loading {
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

.ca-loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from, #3b82f6);
  border-radius: 50%;
  animation: ca-spin 0.6s linear infinite;
}

@keyframes ca-spin {
  to { transform: rotate(360deg); }
}

.ca-nomore {
  text-align: center;
  padding: 6px 0;
  font-size: 12px;
  color: var(--glass-text-tertiary, #999);
}

.ca-empty {
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
