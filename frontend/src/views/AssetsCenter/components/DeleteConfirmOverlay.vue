<template>
  <div class="delete-confirm-overlay glass-overlay" @click.self="$emit('cancel')">
    <div class="delete-confirm-card glass-surface-modal">
      <p class="delete-confirm-message">{{ message }}</p>
      <div class="delete-confirm-actions">
        <button
          class="glass-btn-base glass-btn-secondary delete-confirm-btn"
          @click="$emit('cancel')"
        >
          {{ cancelText }}
        </button>
        <button
          class="glass-btn-base glass-btn-danger delete-confirm-btn"
          @click="$emit('confirm')"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: '确认删除？此操作不可撤销' },
  confirmText: { type: String, default: '删除' },
  cancelText: { type: String, default: '取消' }
})

defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
.delete-confirm-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-confirm-card {
  padding: 20px;
  width: 85%;
}

.delete-confirm-message {
  font-size: 15px;
  color: var(--glass-text-primary);
  margin-bottom: 20px;
  line-height: 1.5;
}

.delete-confirm-actions {
  display: flex;
  flex-direction: row;
  gap: 12px;
  justify-content: flex-end;
}

.delete-confirm-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
</style>
