<template>
  <div class="image-preview-overlay glass-overlay" @click="$emit('close')" @keyup.esc="$emit('close')">
    <img
      :src="imageUrl"
      class="image-preview-img"
      @click.stop
    />
    <button class="image-preview-close glass-btn-base glass-btn-soft" @click="$emit('close')">
      <X :size="16" />
    </button>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { X } from '@lucide/vue'

defineProps({
  imageUrl: { type: String, required: true }
})

const emit = defineEmits(['close'])

function onKeydown(e) {
  if (e.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.image-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: zoom-out;
}

.image-preview-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 12px;
  cursor: default;
}

.image-preview-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
</style>
