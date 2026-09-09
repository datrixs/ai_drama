<template>
  <Teleport to="body">
    <div v-if="visible" class="glass-overlay" @click.self="$emit('close')">
      <div class="glass-surface-modal edit-dialog animate-fadeIn">
        <div class="edit-header">
          <h3>编辑{{ assetType === 'location' ? '场景' : '道具' }}</h3>
          <button class="glass-btn-base glass-btn-soft close-btn" @click="$emit('close')">
            <X :size="16" />
          </button>
        </div>
        <div class="edit-content">
          <div class="edit-form">
            <label class="edit-field">
              <span class="field-label">名称</span>
              <input v-model="form.name" class="glass-input-base" placeholder="名称" maxlength="256" />
            </label>
            <div class="edit-row">
              <label class="edit-field">
                <span class="field-label">地点</span>
                <input v-model="form.place" class="glass-input-base" placeholder="如：伦敦郊外" maxlength="1000" />
              </label>
              <label class="edit-field">
                <span class="field-label">时间</span>
                <input v-model="form.time" class="glass-input-base" placeholder="如：白天/深夜/清晨" maxlength="500" />
              </label>
            </div>
            <label class="edit-field">
              <span class="field-label">描述</span>
              <textarea v-model="form.description" class="glass-textarea-base" rows="10" placeholder="描述" />
            </label>
            <label class="edit-field">
              <span class="field-label">模型系统提示词</span>
              <textarea v-model="form.image_model_system_prompt" class="glass-textarea-base" rows="4" placeholder="图片生成时的系统级提示词（可选）" />
            </label>
          </div>
          <div class="edit-preview">
            <p class="preview-label">生成图片预览</p>
            <div class="preview-image-container">
              <img v-if="location?.image_url" :src="location.image_url" alt="" class="preview-image" />
              <div v-else class="preview-placeholder">
                暂无生成图片
              </div>
            </div>
          </div>
        </div>
        <div class="edit-footer">
          <button class="glass-btn-base glass-btn-secondary footer-btn" @click="$emit('close')">取消</button>
          <button
            class="glass-btn-base glass-btn-tone-info footer-btn"
            :disabled="!form.name.trim()"
            @click="handleSave(false)"
          >
            仅保存
          </button>
          <button
            class="glass-btn-base glass-btn-primary footer-btn"
            :disabled="!form.name.trim()"
            @click="handleSave(true)"
          >
            生成图片
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { X } from '@lucide/vue'

const props = defineProps({
  visible: Boolean,
  location: Object,
  projectId: String,
  assetType: { type: String, default: 'location' },
})

const emit = defineEmits(['close', 'saved'])

const form = reactive({
  name: '',
  place: '',
  time: '',
  description: '',
  image_model_system_prompt: '',
})

watch(() => props.location, (val) => {
  if (val) {
    form.name = val.name || ''
    form.place = val.place || ''
    form.time = val.time || ''
    form.description = val.description || ''
    form.image_model_system_prompt = val.image_model_system_prompt || ''
  }
}, { immediate: true })

function handleSave(generateImage) {
  emit('saved', {
    assetType: props.assetType,
    assetId: props.location.id,
    data: {
      name: form.name,
      place: form.place || null,
      time: form.time || null,
      description: form.description,
      image_model_system_prompt: form.image_model_system_prompt || null,
    },
    generateImage,
  })
  emit('close')
}
</script>

<style scoped>
.edit-dialog {
  max-width: 64rem;
  width: 95%;
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

.edit-content {
  display: flex;
  flex-direction: column;
}

.edit-form {
  flex: 4;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  overflow-y: auto;
  min-width: 0;
}

.edit-preview {
  flex: 6;
  display: flex;
  flex-direction: column;
  padding: 1rem;
  border-top: 1px solid var(--glass-stroke-base);
  background: color-mix(in srgb, var(--glass-bg-muted) 30%, transparent);
  min-width: 0;
}

.preview-label {
  margin: 0 0 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--glass-text-tertiary);
}

.preview-image-container {
  flex: 1;
  min-height: min(50vh, 22rem);
  overflow: hidden;
  border-radius: 0.5rem;
  border: 2px solid var(--glass-stroke-base);
  background: var(--glass-bg-surface);
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  width: 100%;
  height: 100%;
  min-height: 14rem;
  object-fit: contain;
}

.preview-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 14rem;
  width: 100%;
  text-align: center;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--glass-text-tertiary);
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

.field-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-text-primary);
}

.edit-form .glass-input-base {
  padding: 8px 12px;
}

.edit-form .glass-textarea-base {
  padding: 8px 12px;
  resize: none;
}

.edit-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-surface-strong);
  flex-shrink: 0;
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}

@media (min-width: 1024px) {
  .edit-content {
    flex-direction: row;
  }

  .edit-preview {
    border-top: none;
    border-left: 1px solid var(--glass-stroke-base);
  }
}
</style>
