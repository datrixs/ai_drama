<template>
  <nav class="sidebar-nav">
    <button
      v-for="tab in menuItems"
      :key="tab.key"
      :class="['nav-item', { active: modelValue === tab.key }]"
      @click="$emit('update:modelValue', tab.key)"
    >
      <component :is="tab.icon" :size="18" class="nav-icon" />
      <span>{{ tab.label }}</span>
    </button>
  </nav>
</template>

<script setup>
defineProps({
  menuItems: {
    type: Array,
    required: true
  },
  modelValue: {
    type: String,
    required: true
  }
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-secondary, #111827);
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
}

.nav-icon {
  flex-shrink: 0;
}

.nav-item:hover {
  background: var(--glass-bg-muted, #f3f4f6);
}

.nav-item.active {
  background: var(--glass-tone-info-bg, rgba(47, 123, 255, 0.12));
  color: var(--glass-tone-info-fg, #1d63e8);
}
</style>
