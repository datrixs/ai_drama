<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    width="640px"
    top="8vh"
    :close-on-click-modal="true"
    destroy-on-close
    append-to-body
    class="concat-history-dialog"
  >
    <template #header>
      <div class="chd-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span>合成历史</span>
      </div>
    </template>

    <div v-loading="loading" class="chd-body">
      <div v-if="!loading && records.length === 0" class="chd-empty">
        暂无合成记录
      </div>

      <div v-for="r in records" :key="r.id" class="chd-item" :class="`chd-item-${r.status}`">
        <div class="chd-item-main">
          <div class="chd-item-row">
            <span class="chd-time">{{ formatTime(r.create_time) }}</span>
            <span class="chd-badge" :class="`chd-badge-${r.status}`">
              {{ statusLabel(r.status) }}
            </span>
          </div>
          <div class="chd-item-meta">
            <span>{{ r.segment_count }} 个片段</span>
            <span v-if="r.duration_sec">· 时长 {{ formatDuration(r.duration_sec) }}</span>
          </div>
          <div v-if="r.status === 'failed' && r.error_message" class="chd-error">
            失败原因：{{ r.error_message }}
          </div>
        </div>
        <div class="chd-item-actions">
          <button
            v-if="r.status === 'completed' && r.result_video_url"
            class="chd-btn"
            title="播放视频"
            @click="emit('play', { url: r.result_video_url, title: `合成记录 ${formatTime(r.create_time)}` })"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            播放
          </button>
          <button
            v-if="r.status === 'completed' && r.result_video_url"
            class="chd-btn"
            title="下载"
            @click="downloadVideo(r.result_video_url, r.id)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            下载
          </button>
          <span v-if="r.status === 'processing' || r.status === 'pending'" class="chd-spinner-wrap">
            <svg class="chd-spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.2-8.6"/></svg>
          </span>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getConcatRecords } from '@/api/video'

const props = defineProps({
  modelValue: Boolean,
  projectId: { type: String, required: true },
  episodeId: { type: String, required: true },
})

defineEmits(['update:modelValue', 'play'])

const records = ref([])
const loading = ref(false)

async function fetchRecords() {
  if (!props.projectId || !props.episodeId) return
  loading.value = true
  try {
    const res = await getConcatRecords(props.projectId, props.episodeId)
    records.value = res.items || []
  } catch {
    records.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.modelValue, (v) => {
  if (v) fetchRecords()
})

// 父组件可通过 ref 调用此方法刷新（WS 完成事件触发）
defineExpose({ refresh: fetchRecords })

function statusLabel(s) {
  return ({ pending: '等待中', processing: '合成中', completed: '已完成', failed: '失败' })[s] || s
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatDuration(sec) {
  if (!sec || sec <= 0) return ''
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
}

async function downloadVideo(url, id) {
  try {
    const a = document.createElement('a')
    a.href = url
    a.download = `episode_concat_${id}.mp4`
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } catch {
    ElMessage.error('下载失败，请尝试在新窗口打开')
  }
}
</script>

<style scoped>
.chd-header {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 1rem; font-weight: 600; color: #111;
}
.chd-body {
  max-height: 65vh; overflow-y: auto; padding: 0.25rem;
}
.chd-empty {
  text-align: center; padding: 3rem 1rem; color: #9ca3af; font-size: 0.875rem;
}

.chd-item {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.875rem; margin-bottom: 0.5rem;
  border: 1px solid rgba(111,126,153,0.16);
  border-radius: 0.625rem;
  background: #fff;
  transition: border-color 0.15s;
}
.chd-item:hover { border-color: rgba(47,123,255,0.4); }
.chd-item-failed { background: rgba(239,68,68,0.04); border-color: rgba(239,68,68,0.2); }

.chd-item-main { flex: 1; min-width: 0; }
.chd-item-row { display: flex; align-items: center; gap: 0.5rem; }
.chd-time { font-size: 0.85rem; font-weight: 600; color: #111; font-variant-numeric: tabular-nums; }
.chd-badge {
  font-size: 0.6875rem; font-weight: 700;
  padding: 0.125rem 0.5rem; border-radius: 999px;
}
.chd-badge-pending { color: #6b7280; background: rgba(107,114,128,0.12); }
.chd-badge-processing { color: #1d63e8; background: rgba(47,123,255,0.12); }
.chd-badge-completed { color: #0f9f62; background: rgba(16,185,129,0.12); }
.chd-badge-failed { color: #cb3a3a; background: rgba(239,68,68,0.1); }

.chd-item-meta {
  margin-top: 0.25rem;
  font-size: 0.75rem; color: #6b7280;
  display: flex; gap: 0.375rem;
}
.chd-error {
  margin-top: 0.375rem; font-size: 0.75rem; color: #cb3a3a;
  word-break: break-all; line-height: 1.4;
}

.chd-item-actions { display: flex; gap: 0.375rem; flex-shrink: 0; }
.chd-btn {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.35rem 0.65rem; border-radius: 6px;
  font-size: 0.78rem; font-weight: 500;
  border: 1px solid rgba(111,126,153,0.24); background: #fff;
  color: #0a0a0a; cursor: pointer; white-space: nowrap;
  transition: all 0.15s;
}
.chd-btn:hover { border-color: rgba(47,123,255,0.64); color: #1d63e8; }

.chd-spinner-wrap { display: inline-flex; padding: 0.35rem 0.5rem; color: #1d63e8; }
.chd-spinner { animation: chd-spin 1.2s linear infinite; }
@keyframes chd-spin { to { transform: rotate(360deg); } }
</style>

<style>
.concat-history-dialog .el-dialog__header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(111,126,153,0.16);
  margin: 0;
}
.concat-history-dialog .el-dialog__body {
  padding: 1rem 1.25rem;
}
</style>
