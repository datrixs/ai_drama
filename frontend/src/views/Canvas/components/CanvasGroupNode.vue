<template>
  <div
    class="cn-group"
    :class="{ 'cn-group-selected': selected }"
    :style="{ width: typeof width === 'number' ? width + 'px' : null, height: typeof height === 'number' ? height + 'px' : null }"
  >
    <Handle
      id="right"
      type="source"
      :position="Position.Right"
      title="拖拽连线到视频节点（组内资产将作为参考）"
    />
    <div class="cn-group-header" @mousedown.stop="emit('ungroup-check', id)">
      <span class="cn-group-icon">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      </span>
      <span class="cn-group-title">{{ title }}</span>
      <button
        v-if="selected"
        class="cn-group-ungroup-btn"
        type="button"
        title="解组"
        @click.stop="emit('ungroup', id)"
        @mousedown.stop
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 14 4 9l5-5" />
          <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11" />
        </svg>
        <span>解组</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
  width: { type: [Number, String], default: null },
  height: { type: [Number, String], default: null },
})

const emit = defineEmits(['ungroup', 'ungroup-check'])

const title = computed(() => {
  const t = props.data?.title
  if (t) return t
  const count = props.data?.child_count
  if (typeof count === 'number') return `组合 · ${count} 个节点`
  return '组合节点'
})
</script>

<style scoped>
.cn-group {
  width: 100%;
  height: 100%;
  min-width: 200px;
  min-height: 120px;
  border: 1.5px dashed #6366f1;
  border-radius: 12px;
  background: rgba(99, 102, 241, 0.06);
  pointer-events: all;
  display: flex;
  flex-direction: column;
  transition: background 0.15s, border-color 0.15s;
}
.cn-group:hover {
  background: rgba(99, 102, 241, 0.10);
}
.cn-group-selected {
  border-color: #4f46e5;
  background: rgba(99, 102, 241, 0.14);
}
.cn-group-header {
  height: 28px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: grab;
  user-select: none;
  color: #4f46e5;
  font-size: 12px;
}
.cn-group-header:active {
  cursor: grabbing;
}
.cn-group-icon {
  display: inline-flex;
  align-items: center;
}
.cn-group-title {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cn-group-ungroup-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border: none;
  border-radius: 6px;
  background: #4f46e5;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  cursor: pointer;
  pointer-events: all;
}
.cn-group-ungroup-btn:hover {
  background: #4338ca;
}

/* ── 右侧连线 Handle ── */
.cn-group :deep(.vue-flow__handle) {
  width: 20px;
  height: 100%;
  background: transparent;
  border: none;
  border-radius: 0;
  cursor: crosshair;
  opacity: 1;
}
.cn-group :deep(.vue-flow__handle-right) {
  right: -10px;
}
.cn-group :deep(.vue-flow__handle)::before {
  content: '+';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 2px solid #6366f1;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 700;
  color: #6366f1;
  line-height: 1;
  pointer-events: none;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.25);
  opacity: 0;
  transition: opacity 0.15s ease;
}
.cn-group:hover :deep(.vue-flow__handle)::before {
  opacity: 1;
}
.cn-group :deep(.vue-flow__handle:hover)::before {
  background: #6366f1;
  color: #fff;
}
.cn-group :deep(.vue-flow__handle.connectingto),
.cn-group :deep(.vue-flow__handle.valid) {
  background: transparent;
  border-color: transparent;
}
.cn-group :deep(.vue-flow__handle.connectingto::before),
.cn-group :deep(.vue-flow__handle.valid::before) {
  content: none;
}
</style>
