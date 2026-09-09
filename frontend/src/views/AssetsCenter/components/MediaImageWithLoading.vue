<template>
  <div
    :class="containerClass"
    class="media-image-container"
    style="position: relative; overflow: hidden;"
    @click="$emit('click')"
  >
    <!-- Loading placeholder -->
    <div v-if="!loaded && !hasError" class="media-image-placeholder">
      <div class="media-image-pulse"></div>
    </div>

    <!-- Broken image icon -->
    <div v-if="hasError" class="media-image-error">
      <ImageIcon :size="32" color="var(--glass-text-tertiary)" />
    </div>

    <!-- Actual image -->
    <img
      v-show="loaded && !hasError"
      :src="currentSrc"
      :alt="alt"
      :class="imgClass"
      class="media-image"
      @load="onLoad"
      @error="onError"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Image as ImageIcon } from '@lucide/vue'

const props = defineProps({
  src: { type: String, required: true },
  thumbnailSrc: { type: String, default: '' },
  alt: { type: String, default: '' },
  containerClass: { type: String, default: '' },
  imgClass: { type: String, default: '' }
})

defineEmits(['click'])

const loaded = ref(false)
const hasError = ref(false)
const triedOriginal = ref(false)

const currentSrc = computed(() => {
  if (!triedOriginal.value && props.thumbnailSrc) return props.thumbnailSrc
  return props.src
})

function onLoad() {
  loaded.value = true
}

function onError() {
  if (!triedOriginal.value && props.thumbnailSrc) {
    triedOriginal.value = true
    loaded.value = false
    return
  }
  hasError.value = true
}
</script>

<style scoped>
.media-image-container {
  width: 100%;
  height: 100%;
}

.media-image-placeholder {
  position: absolute;
  inset: 0;
  background: var(--glass-bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}

.media-image-pulse {
  position: absolute;
  inset: 0;
  background: var(--glass-bg-muted);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.media-image-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-bg-muted);
}

.media-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
