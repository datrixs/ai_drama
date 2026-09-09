<template>
  <el-dialog
    v-model="visible"
    width="560px"
    align-center
    :show-close="true"
    class="mode-dialog"
    @close="handleClose"
  >
    <template #header>
      <div class="mode-dialog-title">选择创建模式</div>
    </template>
    <div class="mode-cards">
      <button
        type="button"
        class="mode-card"
        @click="choose('novel')"
      >
        <div class="mode-icon mode-icon-novel">📖</div>
        <div class="mode-info">
          <div class="mode-name">创作模式</div>
          <div class="mode-desc">输入故事创意、小说片段或剧本大纲，一站式生成剧本、解析资产、生成分集剧情</div>
        </div>
      </button>
      <button
        type="button"
        class="mode-card"
        @click="choose('director')"
      >
        <div class="mode-icon mode-icon-director">🎬</div>
        <div class="mode-info">
          <div class="mode-name">导演模式</div>
          <div class="mode-desc">跳过剧情分析，自由编排分镜剧本，生成剧集</div>
        </div>
      </button>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'select'])

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

function choose(mode) {
  emit('select', mode)
  visible.value = false
}

function handleClose() {
  visible.value = false
}
</script>

<style scoped>
.mode-dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--glass-text-primary);
}
.mode-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0 4px;
}
.mode-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  border-radius: 14px;
  background: var(--glass-bg-surface, rgba(255, 255, 255, 0.88));
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
}
.mode-card:hover {
  border-color: #2f7bff;
  background: linear-gradient(135deg, rgba(47, 123, 255, 0.12) 0%, rgba(255, 255, 255, 0.94) 70%);
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(47, 123, 255, 0.16);
}
.mode-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}
.mode-icon-novel {
  background: rgba(47, 123, 255, 0.12);
}
.mode-icon-director {
  background: rgba(124, 58, 237, 0.12);
}
.mode-info {
  flex: 1;
  min-width: 0;
}
.mode-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--glass-text-primary, #0a0a0a);
  margin-bottom: 4px;
}
.mode-desc {
  font-size: 13px;
  line-height: 1.6;
  color: var(--glass-text-tertiary, #4b5563);
}
</style>

<style>
.mode-dialog {
  border-radius: 22px !important;
  overflow: hidden;
}
.mode-dialog .el-dialog__header {
  margin: 0;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(111, 126, 153, 0.18);
}
.mode-dialog .el-dialog__body {
  padding: 20px 24px 24px;
}
</style>
