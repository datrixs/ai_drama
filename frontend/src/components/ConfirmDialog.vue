<template>
  <Teleport to="body">
    <Transition name="cf-fade">
      <div v-if="modelValue" class="glass-overlay" @click.self="handleCancel">
        <div class="glass-surface-modal confirm-dialog" :class="`size-${size}`" @click.stop>
          <div class="confirm-body">
            <div v-if="type === 'warning'" class="confirm-icon warning">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                <path d="M12 9v4"/><path d="M12 17h.01"/>
              </svg>
            </div>
            <div v-else-if="type === 'danger'" class="confirm-icon danger">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>
              </svg>
            </div>
            <div class="confirm-text">
              <h3 class="confirm-title">{{ title }}</h3>
              <p v-if="message" class="confirm-message">{{ message }}</p>
            </div>
          </div>
          <div class="modal-footer">
            <button class="glass-btn-secondary glass-btn-base" @click="handleCancel">
              {{ cancelText }}
            </button>
            <button
              :class="type === 'danger' ? 'glass-btn-danger' : 'glass-btn-primary'"
              class="glass-btn-base"
              @click="handleConfirm"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: '确认' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  type: { type: String, default: 'warning' },
  size: { type: String, default: 'default' }, // default | large
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

function handleConfirm() {
  emit('confirm')
  emit('update:modelValue', false)
}

function handleCancel() {
  emit('cancel')
  emit('update:modelValue', false)
}
</script>

<style scoped>
.confirm-dialog {
  max-width: 400px;
  width: 90%;
  padding: 24px;
}

/* large 尺寸：文案较长时使用 */
.confirm-dialog.size-large {
  max-width: 540px;
  padding: 32px;
}
.confirm-dialog.size-large .confirm-icon {
  width: 44px;
  height: 44px;
}
.confirm-dialog.size-large .confirm-title {
  font-size: 17px;
}
.confirm-dialog.size-large .confirm-message {
  font-size: 15px;
  line-height: 1.7;
}

.confirm-body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.confirm-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.confirm-icon.warning {
  background: rgba(234, 179, 8, 0.12);
  color: #b45309;
}

.confirm-icon.danger {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}

.confirm-text {
  flex: 1;
  min-width: 0;
}

.confirm-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0;
}

.confirm-message {
  font-size: 14px;
  color: var(--glass-text-tertiary);
  margin: 8px 0 0;
  line-height: 1.5;
  white-space: pre-line;
}

.confirm-dialog .modal-footer {
  border-top: none;
  background: none;
  margin-top: 20px;
  padding: 0;
}

.cf-fade-enter-active,
.cf-fade-leave-active {
  transition: opacity 0.2s ease;
}

.cf-fade-enter-from,
.cf-fade-leave-to {
  opacity: 0;
}
</style>
