<template>
  <div v-if="tasks.length > 0" class="sv-history">
    <div class="sv-history-title">生成历史</div>
    <div class="sv-history-grid">
      <div v-for="task in tasks" :key="task.id" class="sv-history-card" @click="$emit('select', task)">
        <!-- 缩略图 -->
        <div class="sv-history-thumb">
          <video v-if="task.video_url && task.status === 'succeeded'" :src="task.video_url" :poster="task.thumbnail_url || undefined" class="sv-history-video" preload="none" muted playsinline />
          <div v-else-if="task.status === 'failed'" class="sv-history-status-icon sv-history-failed">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
          </div>
          <div v-else-if="task.status === 'processing'" class="sv-history-status-icon sv-history-processing">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
          </div>
          <div v-else class="sv-history-status-icon sv-history-pending">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
          </div>
        </div>
        <!-- 信息 -->
        <div class="sv-history-info">
          <div class="sv-history-prompt">{{ task.prompt_text?.slice(0, 40) || '无提示词' }}{{ task.prompt_text?.length > 40 ? '...' : '' }}</div>
          <div class="sv-history-meta">
            <span class="sv-history-type">{{ task.generation_type === 'reference' ? '参考' : '首尾帧' }}</span>
            <span class="sv-history-time">{{ formatTime(task.create_time) }}</span>
          </div>
        </div>
        <!-- 操作 -->
        <div class="sv-history-actions">
          <button v-if="task.status === 'failed'" class="sv-history-btn" @click.stop="$emit('retry', task.id)">重试</button>
          <button class="sv-history-btn sv-history-btn-del" @click.stop="$emit('delete', task.id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tasks: { type: Array, default: () => [] },
})

defineEmits(['select', 'retry', 'delete'])

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.sv-history {
  margin-top: 0.5rem;
}

.sv-history-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-text-secondary);
  margin-bottom: 0.75rem;
}

.sv-history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.sv-history-card {
  display: flex;
  flex-direction: column;
  border-radius: 0.75rem;
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-surface);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.15s;
}

.sv-history-card:hover {
  border-color: var(--glass-accent-from, #3b82f6);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.sv-history-thumb {
  position: relative;
  aspect-ratio: 16/9;
  background: var(--glass-bg-muted);
  overflow: hidden;
}

.sv-history-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sv-history-status-icon {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sv-history-failed { color: #ef4444; }
.sv-history-processing { color: var(--glass-accent-from); animation: spin 1.5s linear infinite; }
.sv-history-pending { color: var(--glass-text-tertiary); }

.sv-history-info {
  padding: 0.5rem 0.625rem;
}

.sv-history-prompt {
  font-size: 0.75rem;
  color: var(--glass-text-primary);
  line-height: 1.4;
}

.sv-history-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
}

.sv-history-type {
  font-size: 0.625rem;
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--glass-bg-muted);
  color: var(--glass-text-tertiary);
}

.sv-history-time {
  font-size: 0.625rem;
  color: var(--glass-text-tertiary);
}

.sv-history-actions {
  display: flex;
  gap: 0.25rem;
  padding: 0 0.5rem 0.5rem;
}

.sv-history-btn {
  padding: 0.25rem 0.5rem;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  background: var(--glass-bg-muted);
  color: var(--glass-text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.sv-history-btn:hover {
  background: var(--glass-bg-surface);
  color: var(--glass-text-primary);
}

.sv-history-btn-del:hover {
  color: #ef4444;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
