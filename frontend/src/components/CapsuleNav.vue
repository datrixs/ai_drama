<template>
  <nav class="capsule-nav animate-fadeInDown">
    <div class="capsule-inner">
      <div v-for="item in items" :key="item.id" class="nav-item-wrap">
        <button
          :disabled="item.disabled"
          class="nav-item"
          :class="{
            'nav-item-active': activeId === item.id,
            'nav-item-disabled': item.disabled,
          }"
          @click="!item.disabled && $emit('select', item.id)"
        >
          <span :class="item.disabled ? 'nav-label-disabled' : 'nav-label'">{{ item.label }}</span>
          <span class="nav-indicator" :class="activeId === item.id ? 'nav-indicator-active' : ''" />
          <span v-if="item.status === 'ready' && !item.disabled" class="status-dot status-dot-ready" :class="{ 'status-dot-active': activeId === item.id }" />
          <span v-if="item.status === 'processing' && !item.disabled" class="status-dot status-dot-processing" />
        </button>
        <div v-if="item.disabled && item.disabledLabel" class="nav-tooltip">
          <div class="nav-tooltip-inner">{{ item.disabledLabel }}</div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
defineProps({
  items: { type: Array, required: true },
  activeId: { type: String, required: true },
})

defineEmits(['select'])
</script>

<style scoped>
.capsule-nav {
  position: fixed;
  top: 5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 40;
}

.capsule-inner {
  display: flex;
  border-radius: 9999px;
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(24px) saturate(1.6);
  -webkit-backdrop-filter: blur(24px) saturate(1.6);
  border: 1px solid rgba(255, 255, 255, 0.45);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.06),
    0 1.5px 6px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.nav-item-wrap {
  position: relative;
}

.nav-item {
  position: relative;
  display: flex;
  min-height: 52px;
  align-items: center;
  gap: 0.25rem;
  padding: 0.875rem 1.5rem 1rem;
  background: none;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease-out;
}

.nav-item:not(.nav-item-disabled):active {
  transform: scale(0.98);
}

.nav-item-active {
  color: var(--glass-tone-info-fg);
}

.nav-item:not(.nav-item-active):not(.nav-item-disabled) {
  color: var(--glass-text-tertiary);
}

.nav-item:not(.nav-item-active):not(.nav-item-disabled):hover {
  color: var(--glass-text-primary);
}

.nav-item-disabled {
  cursor: not-allowed;
}

.nav-label {
  font-size: 1rem;
  font-weight: 600;
}

.nav-label-disabled {
  font-size: 1rem;
  font-weight: 500;
  color: var(--glass-text-tertiary);
  opacity: 0.8;
}

.nav-indicator {
  position: absolute;
  bottom: 0.375rem;
  left: 50%;
  transform: translateX(-50%);
  height: 3px;
  border-radius: 9999px;
  background: transparent;
  width: 0;
  transition: all 0.3s ease-out;
}

.nav-indicator-active {
  width: 1.5rem;
  background: linear-gradient(to right, var(--glass-accent-from), var(--glass-accent-to));
  box-shadow: 0 2px 8px var(--glass-accent-shadow-soft);
}

.status-dot {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot-ready {
  background: var(--glass-tone-success-fg);
}

.status-dot-ready.status-dot-active {
  background: var(--glass-tone-info-fg);
}

.status-dot-processing {
  background: var(--glass-accent-from);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.nav-tooltip {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 100%;
  margin-top: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
  z-index: 10;
}

.nav-item-wrap:hover .nav-tooltip {
  opacity: 1;
}

.nav-tooltip-inner {
  font-size: 0.75rem;
  padding: 0.5rem 0.75rem;
  white-space: nowrap;
  color: var(--glass-text-primary);
  background: var(--glass-bg-surface-strong);
  border-radius: 0.5rem;
  border: 1px solid var(--glass-stroke-base);
  box-shadow: var(--glass-shadow-sm);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.animate-fadeInDown {
  animation: fadeInDown 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
</style>
