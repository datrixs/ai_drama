<template>
  <transition name="np-fade">
    <div v-if="visible" class="glass-overlay" @click.self="handleClose">
      <div class="glass-surface-modal np-card">
        <div class="np-icon-wrap">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
        </div>
        <h3 class="np-title">暂无权限</h3>
        <p class="np-desc">{{ message }}</p>
        <button class="glass-btn-primary glass-btn-base np-btn" @click="handleClose">我知道了</button>
      </div>
    </div>
  </transition>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  message: {
    type: String,
    default: '你当前没有该功能的访问权限，请联系主账号管理员开通。'
  }
})

const emit = defineEmits(['close'])

function handleClose() {
  emit('close')
}
</script>

<style scoped>
.np-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 400px;
  width: 90%;
  padding: 40px 32px 32px;
  text-align: center;
}

.np-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

.np-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0 0 8px;
}

.np-desc {
  font-size: 14px;
  color: var(--glass-text-tertiary);
  line-height: 1.6;
  margin: 0 0 28px;
}

.np-btn {
  width: 100%;
  height: 40px;
  border-radius: 10px;
}

.np-fade-enter-active,
.np-fade-leave-active {
  transition: opacity 0.2s ease;
}

.np-fade-enter-from,
.np-fade-leave-to {
  opacity: 0;
}
</style>
