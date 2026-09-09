<template>
  <div class="seg-control">
    <div class="seg-track">
      <button
        v-for="opt in options"
        :key="opt.value"
        class="seg-btn"
        :class="{ 'seg-active': modelValue === opt.value }"
        @click="$emit('update:modelValue', opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  options: { type: Array, required: true }, // [{value, label}]
  modelValue: { type: [String, Number], required: true },
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.seg-control {
  display: inline-flex;
}

.seg-track {
  display: inline-flex;
  border-radius: 9999px;
  padding: 3px;
  background: var(--glass-bg-muted, rgba(0,0,0,0.04));
  border: 1px solid var(--glass-stroke-base, rgba(0,0,0,0.08));
}

.seg-btn {
  position: relative;
  padding: 0.375rem 1.25rem;
  border: none;
  border-radius: 9999px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--glass-text-secondary, #666);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease-out;
  white-space: nowrap;
}

.seg-btn:hover:not(.seg-active) {
  color: var(--glass-text-primary, #333);
}

.seg-active {
  color: #fff;
  background: linear-gradient(135deg, var(--glass-accent-from, #3b82f6), var(--glass-accent-to, #8b5cf6));
  box-shadow: 0 2px 8px var(--glass-accent-shadow-soft, rgba(59,130,246,0.3));
}
</style>
