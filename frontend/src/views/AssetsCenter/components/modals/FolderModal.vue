<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-card glass-surface-modal">
      <div class="modal-header">
        <h3 class="modal-title">{{ isEditing ? '编辑资产组' : '新建资产组' }}</h3>
        <button class="modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>
      <div class="modal-body">
        <label class="glass-field-label">资产组名称</label>
        <input
          v-model="name"
          class="glass-input-base folder-input"
          placeholder="请输入资产组名称"
          autofocus
          @keyup.enter="onSave"
        />
      </div>
      <div class="modal-footer">
        <button class="glass-btn-base glass-btn-secondary footer-btn" @click="$emit('close')">
          取消
        </button>
        <button
          class="glass-btn-base glass-btn-primary footer-btn"
          :disabled="!name.trim()"
          @click="onSave"
        >
          保存
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { X } from '@lucide/vue'

const props = defineProps({
  folder: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save'])

const name = ref(props.folder?.name || '')
const isEditing = computed(() => !!props.folder)

function onSave() {
  const trimmed = name.value.trim()
  if (!trimmed) return
  emit('save', trimmed)
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  max-width: 400px;
  width: 100%;
  overflow: hidden;
}

.modal-header {
  border-bottom: none;
  padding: 16px 20px 0;
}

.modal-body {
  padding: 16px 20px 20px;
}

.folder-input {
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
  margin-top: 8px;
}

.modal-footer {
  border-top: none;
  background: none;
  padding: 16px 20px;
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}
</style>
