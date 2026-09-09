<template>
  <BaseEdge
    :id="id"
    :path="pathData.path"
    :marker-end="markerEnd"
    :style="style"
    :class="{ 'cn-edge-selected': selected }"
  />

  <!-- 选中节点时：白线底色 + 沿路径弯曲的彗星流光（多层 stroke 渐变堆叠） -->
  <template v-if="showFlow">
    <path :d="pathData.path" class="cn-edge-flow-base" fill="none" />
    <path
      v-for="(layer, i) in cometLayers"
      :key="i"
      :d="pathData.path"
      class="cn-edge-flow-comet-layer"
      :style="layer.style"
      fill="none"
    />
  </template>

  <EdgeLabelRenderer>
    <div
      v-if="selected"
      class="cn-edge-delete-wrap"
      :style="{
        transform: `translate(-50%, -50%) translate(${pathData.labelX}px, ${pathData.labelY}px)`,
      }"
    >
      <button
        class="cn-edge-delete-btn"
        type="button"
        title="删除连线"
        @click.stop="onDelete"
        @mousedown.stop
        @pointerdown.stop
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round">
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      </button>
    </div>
  </EdgeLabelRenderer>
</template>

<script setup>
import { computed } from 'vue'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, useVueFlow } from '@vue-flow/core'

// CanvasEdge 是多根节点（fragment），Vue Flow 传入的 edge 属性（sourceNode/targetNode/type/
// animated/label…）未在 defineProps 声明会变成 $attrs，无法继承到 fragment 根节点而告警。
// 关闭自动继承即可消除噪音；本组件用 defineProps 显式接收所需字段，不受影响。
defineOptions({ inheritAttrs: false })

const props = defineProps([
  'id',
  'sourceX', 'sourceY',
  'targetX', 'targetY',
  'sourcePosition', 'targetPosition',
  'source', 'target',
  'data', 'selected',
  'markerEnd', 'style',
  'sourceHandleId', 'targetHandleId',
])

const emit = defineEmits(['delete'])

const { findNode } = useVueFlow()

const pathData = computed(() => {
  const [path, labelX, labelY] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  })
  return { path, labelX, labelY }
})

const showFlow = computed(() => {
  const sourceNode = findNode(props.source)
  const targetNode = findNode(props.target)
  return !!(sourceNode?.selected || targetNode?.selected)
})

// 彗星流光：6 层 stroke 沿路径同步流动，粗层用更负的 delay 让亮段领先、
// 细层落后，整体形成"前粗后细"的彗星形状，linecap round 让层间衔接平滑
const cometLayers = [
  { width: 3.0, opacity: 1.0,  delay: -0.55 },
  { width: 2.6, opacity: 0.9,  delay: -0.44 },
  { width: 2.2, opacity: 0.78, delay: -0.33 },
  { width: 1.8, opacity: 0.62, delay: -0.22 },
  { width: 1.4, opacity: 0.46, delay: -0.11 },
  { width: 1.0, opacity: 0.3,  delay: 0 },
].map((l) => ({
  style: {
    'stroke-width': `${l.width}px`,
    'stroke-opacity': `${l.opacity}`,
    'animation-delay': `${l.delay}s`,
  },
}))

function onDelete() {
  emit('delete', props.id)
}
</script>

<style>
.cn-edge-selected {
  stroke: #ef4444 !important;
  stroke-width: 2.4 !important;
}

.cn-edge-flow-base {
  pointer-events: none;
  stroke: #ffffff;
  stroke-width: 2.4;
  stroke-linecap: round;
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.7));
  opacity: 0.95;
}

/* 彗星流光：6 层 stroke 同步流动，width/opacity/delay 递减堆叠出平滑渐变形状 */
.cn-edge-flow-comet-layer {
  pointer-events: none;
  stroke: #1d4ed8;
  stroke-linecap: round;
  stroke-dasharray: 22 298;
  filter:
    drop-shadow(0 0 4px rgba(37, 99, 235, 0.85))
    drop-shadow(0 0 10px rgba(29, 78, 216, 0.5));
  animation: cnEdgeStreak 1.6s linear infinite;
}

@keyframes cnEdgeStreak {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -320; }
}

.cn-edge-delete-wrap {
  position: absolute;
  pointer-events: auto;
  z-index: 1000;
}

.cn-edge-delete-btn {
  width: 22px;
  height: 22px;
  padding: 0;
  border-radius: 50%;
  border: 2px solid #fff;
  background: #ef4444;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  animation: cnEdgeDeleteIn 0.15s ease-out;
}

.cn-edge-delete-btn:hover {
  transform: scale(1.18);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.55);
}

@keyframes cnEdgeDeleteIn {
  from {
    opacity: 0;
    transform: scale(0.6);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
