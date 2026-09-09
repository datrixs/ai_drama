<template>
  <div ref="containerRef" :class="['segmented-control', { 'segmented-control--compact': layout === 'compact', 'segmented-control--fill': layout === 'fill' }]">
    <div class="segmented-indicator" :style="indicatorStyle" />
    <button
      v-for="option in options"
      :key="option.value"
      :ref="(el) => setButtonRef(option.value, el)"
      :class="['segmented-btn', { 'segmented-btn--active': modelValue === option.value }]"
      :style="layout === 'fill' ? 'flex: 1' : ''"
      @click="$emit('update:modelValue', option.value)"
    >
      <component v-if="option.icon" :is="option.icon" :size="14" class="segmented-btn-icon" />
      <span>{{ option.label }}</span>
    </button>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  options: { type: Array, default: () => [] },
  modelValue: { type: [String, Number], default: '' },
  layout: { type: String, default: 'fill' }
})

defineEmits(['update:modelValue'])

const containerRef = ref(null)
const buttonRefs = {}
const indicatorStyle = reactive({ left: '0px', width: '0px', opacity: 0 })

function setButtonRef(value, el) {
  if (el) buttonRefs[value] = el
}

function updateIndicator() {
  const btn = buttonRefs[props.modelValue]
  if (!btn) {
    indicatorStyle.opacity = 0
    return
  }
  indicatorStyle.left = btn.offsetLeft + 'px'
  indicatorStyle.width = btn.offsetWidth + 'px'
  indicatorStyle.opacity = 1
}

watch(() => props.modelValue, () => nextTick(updateIndicator))
watch(() => props.options, () => nextTick(updateIndicator), { deep: true })

onMounted(() => nextTick(updateIndicator))
</script>

<style scoped>
.segmented-control {
  display: inline-flex;
  position: relative;
  padding: 3px;
  border-radius: 14px;
  background: #e8e8ed;
}

.segmented-indicator {
  position: absolute;
  top: 3px;
  bottom: 3px;
  border-radius: 10px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: left 0.25s cubic-bezier(0.25, 0.1, 0.25, 1),
              width 0.25s cubic-bezier(0.25, 0.1, 0.25, 1),
              opacity 0.15s ease;
}

.segmented-btn {
  position: relative;
  z-index: 1;
  padding: 6px 14px;
  border: none;
  background: none;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s ease;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.segmented-btn-icon {
  flex-shrink: 0;
}

.segmented-btn--active {
  color: #0a0a0a;
}

.segmented-control--compact {
  display: inline-grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(96px, max-content);
}

.segmented-control--fill {
  width: 100%;
}
</style>
