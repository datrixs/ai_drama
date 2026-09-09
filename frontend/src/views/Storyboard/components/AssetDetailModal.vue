<template>
  <div v-if="asset" class="glass-overlay" @click.self="$emit('close')">
    <div class="glass-surface-modal adm-card">
      <button class="modal-close-btn" @click="$emit('close')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
      </button>
      <img v-if="asset.imageUrl" :src="asset.imageUrl" class="adm-img" />
      <h3 class="adm-name">{{ asset.name }}</h3>
      <p v-if="asset.description" class="adm-desc">{{ asset.description }}</p>
      <p v-if="asset.appearanceDescription" class="adm-desc">{{ asset.appearanceDescription }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  asset: { type: Object, default: null },
})
defineEmits(['close'])
</script>

<style scoped>
.adm-card {
  position: relative;
  max-width: 360px;
  width: 90%;
  padding: 1.5rem;
}

.adm-card .modal-close-btn {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
}

.adm-img {
  width: 100%;
  max-height: 240px;
  object-fit: contain;
  border-radius: 12px;
  margin-bottom: 1rem;
}

.adm-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0 0 0.5rem;
}

.adm-desc {
  font-size: 14px;
  color: var(--glass-text-tertiary);
  margin: 0 0 0.35rem;
  line-height: 1.5;
}
</style>
