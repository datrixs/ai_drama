<template>
  <div class="model-settings">
    <div class="section-title">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 8V4H8"></path><rect width="16" height="12" x="4" y="8" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path>
      </svg>
      <span>模型设置</span>
    </div>

    <div class="model-grid">
      <div v-for="field in MODEL_FIELDS" :key="field.key" class="model-field">
        <label class="field-label">
          {{ field.label }}
          <span v-if="field.desc" class="field-desc">{{ field.desc }}</span>
        </label>
        <div class="field-control">
          <ModelSelector
            :model-value="resolved[field.key]"
            :options="getOptions(field)"
            :placeholder="field.placeholder || '请选择'"
            :disabled="field.key === 'video_model'"
            @update:model-value="val => handleChange(field.key, val)"
          />
          <span v-if="isDefault(field.key)" class="default-tag">默认</span>
          <button
            v-else-if="hasOverride(field.key)"
            class="reset-btn"
            title="重置为全局配置"
            @click="handleReset(field.key)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ModelSelector from '@/components/ModelSelector/index.vue'
import { useUserStore } from '@/store/user'

const REGION_DEFAULT_VIDEO_MODEL = {
  domestic: 'doubao-seedance-2-0-260128',
  overseas: 'dreamina-seedance-2-0-260128',
}

const userStore = useUserStore()
const regionDefaultVideoModel = computed(
  () => REGION_DEFAULT_VIDEO_MODEL[userStore.userInfo.value?.region || 'domestic'] || ''
)

const MODEL_FIELDS = [
  { key: 'analysis_model', label: '文本分析模型', desc: '负责剧本解析、分镜构建等全流程文本分析', type: 'text', placeholder: '请选择分析模型' },
  { key: 'character_model', label: '人物生成模型', type: 'image' },
  { key: 'location_model', label: '场景生成模型', type: 'image' },
  { key: 'storyboard_model', label: '分镜脚本生成模型', type: 'text' },
  { key: 'edit_model', label: '图片编辑模型', type: 'image' },
  { key: 'video_model', label: '视频模型', desc: '负责将图像与指令合成为最终视频片段；按当前区域固定，国内版为 Doubao Seedance 2.0，国际版为 Dreamina Seedance 2.0', type: 'video' },
  { key: 'audio_model', label: '语音合成模型', type: 'audio', placeholder: '请选择语音模型' },
]

const props = defineProps({
  resolved: { type: Object, required: true },
  defaults: { type: Object, required: true },
  overrides: { type: Object, default: () => ({}) },
  modelOptions: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['change', 'reset'])

function getOptions(field) {
  const opts = props.modelOptions[field.type] || []
  // 视频模型按当前用户区域固定展示对应模型
  if (field.key === 'video_model' && regionDefaultVideoModel.value) {
    return opts.filter(o => o.id === regionDefaultVideoModel.value)
  }
  return opts
}

function isDefault(key) {
  return !(key in props.overrides)
}

function hasOverride(key) {
  return key in props.overrides
}

function handleChange(key, value) {
  emit('change', key, value)
}

function handleReset(key) {
  emit('reset', key)
}
</script>

<style scoped>
.model-settings {
  padding: 20px;
  background: var(--glass-bg-muted);
  border-radius: 16px;
  border: 1px solid var(--glass-stroke-soft);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--glass-text-primary);
  margin-bottom: 16px;
}

.section-title svg {
  color: var(--glass-accent-from);
}

.model-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.model-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--glass-text-secondary);
}

.field-desc {
  display: block;
  font-size: 12px;
  font-weight: 400;
  color: var(--glass-text-tertiary);
  margin-top: 2px;
}

.field-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-control :deep(.model-selector) {
  flex: 1;
}

.default-tag {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--glass-tone-neutral-bg);
  color: var(--glass-tone-neutral-fg);
  white-space: nowrap;
  flex-shrink: 0;
}

.reset-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--glass-text-tertiary);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.reset-btn:hover {
  background: var(--glass-tone-neutral-bg);
  color: var(--glass-text-secondary);
}
</style>
