<template>
  <div class="asset-toolbar">
    <!-- 导演模式专属：批量上传 + 资产中心导入 -->
    <div v-if="directorMode" class="toolbar-left">
      <!-- 批量上传：点击打开弹框，弹框内选类型 + 拖拽上传 -->
      <button
        class="glass-btn-base glass-btn-secondary toolbar-btn"
        @click="$emit('batchUpload')"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <span>批量上传</span>
      </button>
      <button
        class="glass-btn-base glass-btn-secondary toolbar-btn"
        :disabled="batchImporting"
        @click="$emit('batchImport')"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="m8 12 4 4 4-4"/></svg>
        <span>{{ batchImporting ? '导入中...' : '从资产中心导入' }}</span>
      </button>
    </div>
    <div class="toolbar-right">
      <!-- 导演模式：批量同步（火山/BytePlus）；全局模式：批量生成 -->
      <button
        v-if="directorMode"
        class="glass-btn-base glass-btn-secondary toolbar-btn"
        :disabled="stats.completed === 0 || batchSyncing"
        @click="$emit('batchSync')"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          :class="{ 'spin-anim': batchSyncing }"
        ><path d="M18 10h-1.26A8 8 0 1 0 9 20h9"/><path d="M22 4 12 14l-3-3"/></svg>
        <span>{{ batchSyncLabel }}</span>
      </button>
      <button
        v-else
        class="glass-btn-base glass-btn-secondary toolbar-btn"
        :disabled="stats.generating > 0 || isBatchGenerating || (stats.pending === 0 && stats.failed === 0)"
        @click="$emit('batchGenerate')"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
        <span>{{ isBatchGenerating ? '生成中...' : '批量生成' }}</span>
      </button>
      <button
        class="glass-btn-base glass-btn-secondary toolbar-btn"
        :disabled="stats.completed === 0"
        @click="$emit('batchDownload')"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        <span>批量下载</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, required: true },
  allReady: Boolean,
  isBatchGenerating: Boolean,
  // 导演模式专属开关：显示「批量上传」+「从资产中心导入」+「批量同步」入口
  directorMode: { type: Boolean, default: false },
  batchImporting: { type: Boolean, default: false },
  batchSyncing: { type: Boolean, default: false },
  // 批量同步进度（对齐资产中心交互）：batchSyncTotal>0 时显示 "同步中 N/M"
  batchSyncTotal: { type: Number, default: 0 },
  batchSyncDone: { type: Number, default: 0 },
  batchSyncPending: { type: Boolean, default: false },
})

defineEmits(['batchGenerate', 'batchSync', 'batchDownload', 'batchUpload', 'batchImport'])

// 三态文案：等待 started 事件期间显示"同步中..."，已 started 后显示"同步中 N/M"
const batchSyncLabel = computed(() => {
  if (props.batchSyncPending) return '同步中...'
  if (props.batchSyncTotal > 0) return `同步中 ${props.batchSyncDone}/${props.batchSyncTotal}`
  return '批量同步'
})
</script>

<style scoped>
.asset-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  gap: 0.5rem;
}

.toolbar-right {
  display: flex;
  gap: 0.5rem;
}

.toolbar-btn {
  height: 2.25rem;
  padding: 0 0.875rem;
  font-size: 0.8125rem;
  gap: 0.375rem;
  border-radius: var(--glass-radius-md);
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spin-anim {
  animation: spin-rotate 1s linear infinite;
}
@keyframes spin-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

<style scoped>
.asset-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}

.toolbar-right {
  display: flex;
  gap: 0.5rem;
}

.toolbar-btn {
  height: 2.25rem;
  padding: 0 0.875rem;
  font-size: 0.8125rem;
  gap: 0.375rem;
  border-radius: var(--glass-radius-md);
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
