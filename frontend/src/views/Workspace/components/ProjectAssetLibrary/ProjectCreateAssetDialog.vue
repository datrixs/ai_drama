<template>
  <Teleport to="body">
    <div v-if="visible" class="glass-overlay" @click.self="handleClose">
      <div class="glass-surface-modal edit-dialog animate-fadeIn">
        <div class="edit-header">
          <h3>{{ titleText }}</h3>
          <button class="glass-btn-base glass-btn-soft close-btn" @click="handleClose">
            <X :size="16" />
          </button>
        </div>

        <div class="edit-body">
          <label class="edit-field">
            <span class="field-label">名称 <span class="required">*</span></span>
            <input
              v-model="form.name"
              class="glass-input-base"
              :placeholder="namePlaceholder"
              maxlength="256"
            />
          </label>

          <label v-if="assetType === 'character'" class="edit-field">
            <span class="field-label">别名</span>
            <input
              v-model="form.aliases"
              class="glass-input-base"
              placeholder="角色别名/曾用名"
              maxlength="1000"
            />
          </label>

          <div v-if="assetType === 'location'" class="edit-row">
            <label class="edit-field">
              <span class="field-label">地点</span>
              <input
                v-model="form.place"
                class="glass-input-base"
                placeholder="如：伦敦郊外"
                maxlength="1000"
              />
            </label>
            <label class="edit-field">
              <span class="field-label">时间</span>
              <input
                v-model="form.time"
                class="glass-input-base"
                placeholder="如：白天/深夜/清晨"
                maxlength="500"
              />
            </label>
          </div>

          <label v-if="assetType === 'prop'" class="edit-field">
            <span class="field-label">别名</span>
            <input
              v-model="form.aliases"
              class="glass-input-base"
              placeholder="道具别名/英文名"
              maxlength="1000"
            />
          </label>

          <label class="edit-field">
            <span class="field-label">描述</span>
            <textarea
              v-model="form.description"
              class="glass-textarea-base"
              :placeholder="descPlaceholder"
              maxlength="2000"
              rows="4"
            />
          </label>
        </div>

        <div class="edit-footer">
          <button class="glass-btn-base glass-btn-secondary footer-btn" @click="handleClose">取消</button>
          <button
            class="glass-btn-base glass-btn-tone-info footer-btn"
            :disabled="submitting"
            @click="handleSubmit(false)"
          >
            仅添加
          </button>
          <button
            class="glass-btn-base glass-btn-primary footer-btn"
            :disabled="!form.name.trim() || submitting"
            @click="handleSubmit(true)"
          >
            生成图片
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { X } from '@lucide/vue'

const props = defineProps({
  visible: Boolean,
  assetType: { type: String, default: 'character' },
})

const emit = defineEmits(['close', 'created'])

const form = ref({ name: '', aliases: '', place: '', time: '', description: '' })
const submitting = ref(false)

const titleText = computed(() => {
  const map = { character: '添加角色', location: '添加场景', prop: '添加道具' }
  return map[props.assetType] || '添加资产'
})

const namePlaceholder = computed(() => {
  const map = { character: '输入角色名称', location: '输入场景名称', prop: '输入道具名称' }
  return map[props.assetType] || '输入名称'
})

const descPlaceholder = computed(() => {
  const map = { character: '描述角色的外观特征、性格等', location: '描述场景的环境特征', prop: '描述道具的外观和用途' }
  return map[props.assetType] || '输入描述'
})

watch(() => props.visible, (val) => {
  if (val) {
    form.value = { name: '', aliases: '', place: '', time: '', description: '' }
    submitting.value = false
  }
})

function handleClose() {
  emit('close')
}

function handleSubmit(generateImage) {
  if (!form.value.name.trim()) return
  submitting.value = true
  emit('created', {
    assetType: props.assetType,
    data: {
      name: form.value.name.trim(),
      ...(props.assetType === 'character' && form.value.aliases ? { aliases: form.value.aliases.trim() } : {}),
      ...(props.assetType === 'location' ? {
        ...(form.value.place ? { place: form.value.place.trim() } : {}),
        ...(form.value.time ? { time: form.value.time.trim() } : {}),
      } : {}),
      ...(props.assetType === 'prop' && form.value.aliases ? { aliases: form.value.aliases.trim() } : {}),
      ...(form.value.description ? { description: form.value.description.trim() } : {}),
    },
    generateImage,
  })
  submitting.value = false
}
</script>

<style scoped>
.edit-dialog {
  max-width: 32rem;
  width: 90%;
  border-radius: var(--glass-radius-xl);
  overflow: hidden;
}

.edit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--glass-stroke-base);
}

.edit-header h3 {
  font-weight: 700;
  font-size: 1rem;
  color: var(--glass-text-primary);
}

.edit-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.edit-row {
  display: flex;
  gap: 0.75rem;
}

.edit-row .edit-field {
  flex: 1;
  min-width: 0;
}

.field-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-text-primary);
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--glass-text-tertiary);
}
.close-btn:hover {
  color: var(--glass-text-secondary);
}

.required {
  color: var(--glass-tone-danger-fg);
}

.edit-body .glass-input-base {
  padding: 8px 12px;
}

.edit-body .glass-textarea-base {
  padding: 8px 12px;
  resize: none;
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}

.edit-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem;
  border-top: 1px solid var(--glass-stroke-base);
}
</style>
