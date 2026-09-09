<template>
  <div class="srsel-wrap">
    <button
      type="button"
      class="srsel-trigger"
      :class="{ 'srsel-trigger-open': open }"
      @click.stop="toggle"
    >
      <span class="srsel-value">{{ currentLabel }}</span>
      <svg
        class="srsel-arrow"
        :class="{ 'srsel-arrow-open': open }"
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      ><path d="m6 9 6 6 6-6"/></svg>
    </button>
    <Teleport to="body">
      <div v-if="open" class="srsel-backdrop" @mousedown="close" />
      <div v-if="open" class="srsel-popup" :style="popupStyle">
        <div
          v-for="opt in options"
          :key="opt.value"
          class="srsel-option"
          :class="{ 'srsel-option-active': modelValue === opt.value }"
          @mousedown.prevent="select(opt.value)"
        >
          <span>{{ opt.label }}</span>
          <svg
            v-if="modelValue === opt.value"
            class="srsel-check"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
          ><path d="M20 6 9 17l-5-5"/></svg>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const popupStyle = ref({})

const currentLabel = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt ? opt.label : ''
})

function toggle(e) {
  open.value = !open.value
  if (open.value && e?.currentTarget) {
    const rect = e.currentTarget.getBoundingClientRect()
    const gap = 4
    const vh = window.innerHeight
    const spaceBelow = vh - rect.bottom - gap
    const spaceAbove = rect.top - gap
    // 默认下方展开；下方空间不足且上方更宽裕时翻到上方
    const preferAbove = spaceBelow < 220 && spaceAbove > spaceBelow
    const maxH = Math.min(260, preferAbove ? spaceAbove : spaceBelow)
    const style = {
      position: 'fixed',
      left: `${rect.left}px`,
      minWidth: `${rect.width}px`,
      maxHeight: `${Math.max(120, maxH)}px`,
    }
    if (preferAbove) {
      style.bottom = `${vh - rect.top + gap}px`
    } else {
      style.top = `${rect.bottom + gap}px`
    }
    popupStyle.value = style
  }
}

function select(val) {
  if (props.modelValue !== val) emit('update:modelValue', val)
  open.value = false
}

function close() {
  open.value = false
}

onBeforeUnmount(() => {
  open.value = false
})
</script>

<style scoped>
.srsel-wrap {
  position: relative;
  width: 100%;
}

.srsel-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  height: 38px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #DCDFE6;
  background: #fff;
  color: #303133;
  font-size: 13px;
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.srsel-trigger:hover {
  border-color: #6366f1;
}

.srsel-trigger-open,
.srsel-trigger:focus-visible {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.srsel-value {
  flex: 1;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.srsel-arrow {
  flex-shrink: 0;
  color: #909399;
  transition: transform 0.18s ease;
}

.srsel-arrow-open {
  transform: rotate(180deg);
}

.srsel-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1099;
  background: transparent;
}

.srsel-popup {
  z-index: 1100;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(111, 126, 153, 0.24);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 4px;
  max-height: 260px;
  overflow-y: auto;
  animation: srsel-pop-in 0.15s ease-out;
}

@keyframes srsel-pop-in {
  from { opacity: 0; transform: translateY(4px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.srsel-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #303133;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.srsel-option:hover {
  background: #F0F0FF;
}

.srsel-option-active {
  color: #6366f1;
  background: #F0F0FF;
  font-weight: 500;
}

.srsel-check {
  color: #6366f1;
  flex-shrink: 0;
}
</style>
