<template>
  <div class="candidate-grid">
    <div
      v-for="(item, idx) in items"
      :key="idx"
      class="candidate-grid__item"
      :class="{ 'candidate-grid__item--selected': idx === modelValue }"
      @click="$emit('preview', item.url)"
    >
      <MediaImageWithLoading
        :src="item.url"
        :thumbnail-src="item.thumbnailUrl || ''"
        container-class="candidate-grid__img-container"
        img-class="candidate-grid__img"
      />
      <!-- 左下角编号标签 -->
      <div
        class="candidate-grid__label"
        :class="idx === modelValue ? 'candidate-grid__label--selected' : 'candidate-grid__label--neutral'"
      >
        {{ idx + 1 }}
      </div>
      <!-- 右上角选择按钮 -->
      <button
        class="candidate-grid__select-btn"
        :class="idx === modelValue ? 'candidate-grid__select-btn--selected' : 'candidate-grid__select-btn--default'"
        @click.stop="$emit('select', idx)"
      >
        <Check :size="12" />
      </button>
    </div>
    <!-- 确认按钮 -->
    <div v-if="modelValue !== null && modelValue !== undefined" class="candidate-grid__confirm">
      <button
        class="glass-btn-base candidate-grid__confirm-btn"
        @click.stop="$emit('confirm', modelValue)"
      >
        <Check :size="14" />
        <span>确认选择第 {{ modelValue + 1 }} 张</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { Check } from '@lucide/vue'
import MediaImageWithLoading from './MediaImageWithLoading.vue'

defineProps({
  items: {
    type: Array,
    required: true,
  },
  modelValue: {
    type: Number,
    default: null,
  },
  minHeight: {
    type: String,
    default: '96px',
  },
})

defineEmits(['select', 'confirm', 'preview'])
</script>

<style scoped>
.candidate-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.candidate-grid__item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid var(--glass-stroke-base, rgba(255, 255, 255, 0.1));
  min-height: v-bind(minHeight);
  cursor: pointer;
  transition: border-color 0.15s;
}

.candidate-grid__item:hover {
  border-color: var(--glass-stroke-focus, rgba(255, 255, 255, 0.3));
}

.candidate-grid__item--selected {
  border-color: var(--glass-tone-success-fg, #22c55e);
  box-shadow: 0 0 0 2px var(--glass-success-ring, rgba(34, 197, 94, 0.25));
}

.candidate-grid__img-container {
  width: 100%;
  height: 100%;
}

.candidate-grid__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.candidate-grid__label {
  position: absolute;
  bottom: 4px;
  left: 4px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.candidate-grid__label--selected {
  background: var(--glass-tone-success-fg, #22c55e);
  color: white;
}

.candidate-grid__label--neutral {
  background: rgba(0, 0, 0, 0.5);
  color: rgba(255, 255, 255, 0.8);
}

.candidate-grid__select-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: opacity 0.15s, background 0.15s;
  opacity: 0;
}

.candidate-grid__item:hover .candidate-grid__select-btn,
.candidate-grid__item--selected .candidate-grid__select-btn {
  opacity: 1;
}

.candidate-grid__select-btn--selected {
  background: var(--glass-tone-success-fg, #22c55e);
  color: white;
  opacity: 1;
}

.candidate-grid__select-btn--default {
  background: rgba(0, 0, 0, 0.5);
  color: white;
}

.candidate-grid__select-btn--default:hover {
  background: rgba(0, 0, 0, 0.7);
}

.candidate-grid__confirm {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  padding-top: 4px;
}

.candidate-grid__confirm-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  font-size: 13px;
  border-radius: 8px;
  background: var(--glass-tone-success-fg, #22c55e);
  color: white;
  cursor: pointer;
  transition: opacity 0.15s;
}

.candidate-grid__confirm-btn:hover {
  opacity: 0.9;
}
</style>
