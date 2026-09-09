<template>
  <div class="sr-item" :class="'sr-' + task.status">
    <div class="sr-body">
      <!-- 时间 -->
      <div class="sr-time">{{ formattedTime }}</div>

      <!-- 参数标签 -->
      <div class="sr-meta">
        <span class="sr-tag sr-tag-template">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>
          {{ sceneLabel }}
        </span>
        <span v-if="toolVersionLabel" class="sr-tag">{{ toolVersionLabel }}</span>
        <span v-if="resolutionLabel" class="sr-tag">{{ resolutionLabel }}</span>
        <span v-if="resolutionLimitLabel" class="sr-tag">{{ resolutionLimitLabel }}</span>
        <span v-if="fpsLabel" class="sr-tag">{{ fpsLabel }}</span>
        <span v-if="bitrateLabel" class="sr-tag">{{ bitrateLabel }}</span>
      </div>

      <!-- 对比视频区 -->
      <div class="sr-video-area">
        <!-- 生成中 -->
        <div v-if="isProcessing" class="sr-generating">
          <div class="sr-gen-spinner" />
          <span class="sr-gen-text">超分处理中 {{ task.progress || 0 }}%</span>
        </div>
        <!-- 失败 -->
        <div v-else-if="task.status === 'failed'" class="sr-generating">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          <span class="sr-gen-text">{{ displayError }}</span>
          <button class="sr-retry-btn" @click="$emit('retry', task.id)">重试</button>
        </div>
        <!-- 成功或处理中（结果未就绪但有源视频）：对比播放器 -->
        <CompareVideoPlayer
          v-else
          :beforeSrc="task.source_video_url"
          :afterSrc="task.result_video_url"
          :beforePoster="task.source_thumbnail_url"
          :afterPoster="task.result_thumbnail_url"
          :emptyText="task.status === 'succeeded' && !task.result_video_url ? '结果生成中…' : '处理中…'"
        />
      </div>

      <!-- 操作按钮 -->
      <div v-if="task.result_video_url" class="sr-actions">
        <a
          class="sr-action-btn"
          :href="task.result_video_url"
          target="_blank"
          rel="noopener"
          download
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          下载结果
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import CompareVideoPlayer from './CompareVideoPlayer.vue'
import {
  SR_SCENES,
  SR_TOOL_VERSIONS,
  SR_BITRATE_LEVELS,
} from '@/constants/superResolution'

const props = defineProps({
  task: { type: Object, required: true },
})

defineEmits(['retry'])

const isProcessing = computed(() =>
  ['pending', 'submitted', 'processing'].includes(props.task.status)
)

const params = computed(() => props.task.params || {})

const sceneLabel = computed(() => {
  const v = params.value.scene
  const s = SR_SCENES.find(x => x.value === v)
  return s ? s.label : v || '通用'
})

const toolVersionLabel = computed(() => {
  const v = params.value.tool_version
  if (!v) return ''
  const t = SR_TOOL_VERSIONS.find(x => x.value === v)
  return t ? t.label : v
})

const resolutionLabel = computed(() => {
  const v = params.value.resolution
  if (!v) return ''
  return v.toUpperCase()
})

const resolutionLimitLabel = computed(() => {
  const v = params.value.resolution_limit
  if (v == null) return ''
  return `短边≤${v}px`
})

const fpsLabel = computed(() => {
  const v = params.value.fps
  if (v == null) return ''
  return `${v} fps`
})

const bitrateLabel = computed(() => {
  const v = params.value.bitrate_level
  if (!v) return ''
  const t = SR_BITRATE_LEVELS.find(x => x.value === v)
  return t ? t.label : v
})

const displayError = computed(() => {
  const raw = props.task.error_message
  if (!raw) return '超分失败'
  return raw
})

const formattedTime = computed(() => {
  const iso = props.task.create_time
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const time = `${hh}:${mm}`
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return time
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return `昨天 ${time}`
  const MM = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${MM}-${dd} ${time}`
})
</script>

<style scoped>
.sr-item {
  padding: 1rem 0;
}

.sr-item + .sr-item {
  border-top: 1px solid var(--glass-stroke-soft, rgba(0, 0, 0, 0.05));
}

.sr-time {
  font-size: 12px;
  color: var(--glass-text-tertiary, #999);
  margin-bottom: 0.375rem;
}

.sr-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.375rem;
  font-size: 12px;
  color: var(--glass-text-tertiary, #999);
  margin-bottom: 0.5rem;
}

.sr-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(107, 114, 180, 0.07);
  color: #6b7280;
}

.sr-tag-template {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.sr-video-area {
  max-width: 720px;
  margin-bottom: 0.375rem;
}

.sr-generating {
  aspect-ratio: 16/9;
  border-radius: 0.5rem;
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  border: 1px dashed var(--glass-stroke-base, rgba(0, 0, 0, 0.1));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.sr-gen-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from, #3b82f6);
  border-radius: 50%;
  animation: sr-spin 0.8s linear infinite;
}

@keyframes sr-spin {
  to { transform: rotate(360deg); }
}

.sr-gen-text {
  font-size: 0.75rem;
  color: var(--glass-text-secondary);
  text-align: center;
  word-break: break-all;
}

.sr-retry-btn {
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid rgba(239, 68, 68, 0.3);
  background: transparent;
  color: #dc2626;
  font-size: 0.6875rem;
  cursor: pointer;
  transition: background 0.15s;
}

.sr-retry-btn:hover {
  background: rgba(239, 68, 68, 0.06);
}

.sr-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.sr-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 7px;
  border: none;
  background: rgba(107, 114, 180, 0.06);
  color: #9ca3af;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;
}

.sr-action-btn:hover {
  background: rgba(107, 114, 180, 0.09);
  color: #6b7280;
}
</style>
