<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    width="min(92vw, 1100px)"
    top="6vh"
    :close-on-click-modal="false"
    destroy-on-close
    append-to-body
    class="vpp-dialog"
  >
    <template #header>
      <div class="vpp-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
        <span>{{ title || '视频播放' }}</span>
      </div>
    </template>

    <div class="vpp-body">
      <video
        v-if="url"
        :src="url"
        :key="url"
        controls
        autoplay
        playsinline
        preload="auto"
        class="vpp-video"
      />
    </div>
  </el-dialog>
</template>

<script setup>
defineProps({
  modelValue: Boolean,
  url: { type: String, default: '' },
  title: { type: String, default: '' },
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.vpp-header {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 1rem; font-weight: 600; color: #111;
}
.vpp-body {
  background: #000;
  border-radius: 0.5rem;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  min-height: 60vh;
}
.vpp-video {
  width: 100%;
  max-height: 78vh;
  display: block;
  background: #000;
}
</style>

<style>
.vpp-dialog .el-dialog__header {
  padding: 0.875rem 1.25rem;
  border-bottom: 1px solid rgba(111,126,153,0.16);
  margin: 0;
}
.vpp-dialog .el-dialog__body {
  padding: 0.75rem;
}
</style>
