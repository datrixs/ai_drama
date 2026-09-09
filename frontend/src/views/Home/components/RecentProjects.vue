<template>
  <div v-if="projects.length > 0" class="recent-projects">
    <div class="recent-title">最近项目</div>
    <div class="recent-grid">
      <router-link
        v-for="proj in projects"
        :key="proj.id"
        :to="`/workspace/${proj.id}?tab=story`"
        class="recent-card"
      >
        <div class="recent-card-title">{{ proj.title }}</div>
        <div class="recent-card-status">{{ statusText(proj.status) }}</div>
        <div class="recent-card-time">{{ formatDate(proj.update_time || proj.create_time) }}</div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getProjectList } from '@/api/project'

const projects = ref([])

onMounted(async () => {
  try {
    const res = await getProjectList({ page: 1, size: 4 })
    projects.value = res?.data || res || []
  } catch {
    // 静默处理
  }
})

function statusText(status) {
  const map = {
    draft: '草稿',
    analyzingStory: '分析中',
    storyReady: '故事就绪',
    projectCreated: '项目已创建',
    assetsReady: '资产就绪',
    producing: '制作中',
    completed: '已完成',
  }
  return map[status] || status || '未知'
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.recent-projects {
  width: 100%;
  max-width: 48rem;
  margin-top: 2rem;
}

.recent-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-text-secondary);
  margin-bottom: 0.75rem;
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}

.recent-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.875rem;
  border-radius: 0.75rem;
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-surface);
  text-decoration: none;
  transition: all 0.15s;
}

.recent-card:hover {
  border-color: var(--glass-accent-from, #3b82f6);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
}

.recent-card-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--glass-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-card-status {
  font-size: 0.6875rem;
  color: var(--glass-text-tertiary);
}

.recent-card-time {
  font-size: 0.625rem;
  color: var(--glass-text-tertiary);
}
</style>
