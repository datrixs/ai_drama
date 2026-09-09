<template>
  <el-drawer
    :model-value="visible"
    direction="rtl"
    size="420px"
    :modal="false"
    :show-close="true"
    @close="handleClose"
  >
    <template #header>
      <div class="drawer-header-inner">
        <span class="drawer-title">项目配置</span>
        <span :class="['save-chip', saveStatus === 'saved' ? 'save-chip-saved' : 'save-chip-idle']">
          <svg v-if="saveStatus === 'saved'" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"></path></svg>
          {{ saveStatus === 'saved' ? '已保存' : '自动保存' }}
        </span>
      </div>
    </template>

    <div v-if="drawerLoading" class="drawer-loading">
      <span class="drawer-spinner" />
      <span>加载中...</span>
    </div>
    <div v-else-if="config" class="drawer-content">
      <div class="drawer-body">
        <ProjectBasicSettings
          :title="config.title || ''"
          :resolved="config.resolved"
          @change="handleBasicChange"
        />

        <div class="section-divider"></div>

        <ProjectModelSettings
          :resolved="config.resolved"
          :defaults="config.defaults"
          :overrides="config.overrides"
          :model-options="modelOptions"
          @change="handleModelChange"
          @reset="handleModelReset"
        />
      </div>
    </div>
    <div v-else class="drawer-loading">加载配置失败</div>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getModelOptions } from '@/api/aiModel'
import { getProjectConfig, updateProjectConfig } from '@/api/project'
import ProjectBasicSettings from './ProjectBasicSettings.vue'
import ProjectModelSettings from './ProjectModelSettings.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  projectId: { type: String, required: true },
})

const emit = defineEmits(['update:visible', 'config-updated'])

const drawerLoading = ref(false)
const config = ref(null)
const saveStatus = ref('idle')
let saveTimer = null

const modelOptions = ref({
  text: [],
  image: [],
  video: [],
  audio: [],
})

function showSaved() {
  saveStatus.value = 'saved'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => { saveStatus.value = 'idle' }, 2000)
}

async function loadConfig() {
  drawerLoading.value = true
  try {
    const [cfg, textModels, imageModels, videoModels] = await Promise.all([
      getProjectConfig(props.projectId),
      getModelOptions('text').catch(() => []),
      getModelOptions('image').catch(() => []),
      getModelOptions('video').catch(() => []),
    ])
    config.value = cfg
    modelOptions.value = {
      text: textModels || [],
      image: imageModels || [],
      video: videoModels || [],
      audio: [],
    }
  } catch {
    config.value = null
  } finally {
    drawerLoading.value = false
  }
}

async function saveConfig(data) {
  try {
    const res = await updateProjectConfig(props.projectId, data)
    config.value = res
    emit('config-updated', res)
    showSaved()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

function handleBasicChange(field, value) {
  saveConfig({ [field]: value })
}

function handleModelChange(field, value) {
  saveConfig({ [field]: value })
}

function handleModelReset(field) {
  saveConfig({ [field]: null })
}

function handleClose() {
  emit('update:visible', false)
}

watch(() => props.visible, (val) => {
  if (val) loadConfig()
})
</script>

<style scoped>
.drawer-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 200px;
  color: var(--glass-text-tertiary);
  font-size: 14px;
}

.drawer-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drawer-header-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--glass-text-primary);
  line-height: 1;
}

.save-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  transition: all 0.3s;
}

.save-chip-idle {
  background: var(--glass-tone-neutral-bg);
  color: var(--glass-text-tertiary);
}

.save-chip-saved {
  background: var(--glass-tone-success-bg);
  color: var(--glass-tone-success-fg);
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-divider {
  height: 1px;
  background: var(--glass-stroke-base);
  margin: 0;
}

:deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 8px 20px;
  border-bottom: 1px solid var(--glass-stroke-base);
  display: flex;
  align-items: center;
}

:deep(.el-drawer__body) {
  padding: 4px 16px;
}

.drawer-body :deep(.basic-settings) {
  padding: 8px;
}
</style>
