<template>
  <div class="model-selector" ref="dropdownRef">
    <button
      type="button"
      class="model-select-trigger glass-input-base"
      :class="{ 'model-select-trigger-active': isOpen, 'model-select-trigger-disabled': disabled }"
      :disabled="disabled"
      @click="toggle"
    >
      <span class="model-select-label">{{ displayName }}</span>
      <svg class="model-select-chevron" :class="{ 'rotate-180': isOpen }" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="m6 9 6 6 6-6"></path>
      </svg>
    </button>
    <Transition name="dropdown">
      <div v-if="isOpen" class="model-select-dropdown glass-surface-modal">
        <div class="model-dropdown-inner">
          <div
            v-for="item in options"
            :key="item.id"
            class="model-dropdown-item"
            :class="{ 'model-dropdown-item-active': modelValue === item.id }"
            @click="select(item)"
          >
            <div class="model-item-header">
              <span class="model-item-name">{{ item.name }}</span>
              <span v-if="modelValue === item.id" class="model-item-check">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 6 9 17l-5-5"></path>
                </svg>
              </span>
            </div>
            <!-- <div v-if="item.pricing" class="model-item-pricing">{{ item.pricing }}</div> -->
            <div class="model-item-id">{{ item.id }}</div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: null },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择模型' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const dropdownRef = ref(null)

const displayName = computed(() => {
  if (!props.modelValue) return props.placeholder
  const item = props.options.find(o => o.id === props.modelValue)
  return item ? item.name : props.modelValue
})

function toggle() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
}

function select(item) {
  emit('update:modelValue', item.id)
  isOpen.value = false
}

function handleClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
.model-selector {
  position: relative;
}

.model-select-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 14px;
  cursor: pointer;
  font-size: 14px;
  text-align: left;
  height: 40px;
}

.model-select-trigger:hover {
  border-color: rgba(47, 123, 255, 0.4);
}

.model-select-trigger-disabled,
.model-select-trigger-disabled:hover {
  cursor: not-allowed;
  opacity: 0.7;
  border-color: var(--glass-stroke-soft);
  background: var(--glass-bg-muted);
}

.model-select-trigger-active {
  border-color: rgba(47, 123, 255, 0.6) !important;
  box-shadow: 0 0 0 3px rgba(47, 123, 255, 0.08) !important;
}

.model-select-label {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  color: var(--glass-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-select-chevron {
  flex-shrink: 0;
  color: var(--glass-text-tertiary);
  transition: transform 0.3s;
}

.model-select-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 50;
  overflow: hidden;
}

.model-dropdown-inner {
  max-height: 320px;
  overflow-y: auto;
  padding: 6px;
}

.model-dropdown-item {
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.model-dropdown-item:hover {
  background: var(--glass-bg-muted);
}

.model-dropdown-item-active {
  background: rgba(47, 123, 255, 0.06);
}

.model-dropdown-item-active:hover {
  background: rgba(47, 123, 255, 0.1);
}

.model-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.model-item-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--glass-text-primary);
}

.model-item-check {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  color: var(--glass-tone-info-fg);
}

.model-item-pricing {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  margin-top: 2px;
}

.model-item-id {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  margin-top: 2px;
  font-family: monospace;
  opacity: 0.7;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
