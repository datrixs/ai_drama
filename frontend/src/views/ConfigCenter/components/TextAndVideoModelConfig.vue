<template>
  <div class="sub-section">
    <div class="sub-title-row">
      <span class="sub-title-icon blue">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"></path>
        </svg>
      </span>
      <h3 class="sub-title">文本分析与视频能力</h3>
    </div>

    <div class="form-row">
      <span class="form-label">分析流程并发</span>
      <el-input-number v-model="modelConfig.textConcurrency" :min="1" :max="10" size="small" />
    </div>

    <div class="model-block">
      <div class="model-block-title-row">
        <span class="model-block-icon blue">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"></path>
            <path d="M14 2v5a1 1 0 0 0 1 1h5"></path>
            <path d="M10 9H8"></path>
            <path d="M16 13H8"></path>
            <path d="M16 17H8"></path>
          </svg>
        </span>
        <h4 class="model-block-title">文本分析模型</h4>
      </div>
      <p class="model-block-desc">负责剧本解析、分镜构建等全流程文本分析能力。</p>
      <div class="relative" ref="textDropdownRef">
        <button
          type="button"
          class="model-select-trigger"
          :class="{ 'model-select-trigger-active': textDropdownOpen }"
          @click="toggleTextDropdown"
        >
          <span class="model-select-label">{{ textModelDisplayName }}</span>
          <svg
            xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            class="model-select-chevron"
            :class="{ 'rotate-180': textDropdownOpen }"
          >
            <path d="m6 9 6 6 6-6"></path>
          </svg>
        </button>
        <Transition name="dropdown">
          <div v-if="textDropdownOpen" class="model-select-dropdown">
            <div class="model-dropdown-inner">
              <div
                v-for="item in textModelOptions"
                :key="item.id"
                class="model-dropdown-item"
                :class="{ 'model-dropdown-item-active': modelConfig.textModel === item.label }"
                @click="selectTextModel(item)"
              >
                <div class="model-item-header">
                  <span class="model-item-name">{{ item.name }}</span>
                  <span v-if="modelConfig.textModel === item.label" class="model-item-check">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M20 6 9 17l-5-5"></path>
                    </svg>
                  </span>
                </div>
                <div v-if="item.pricing" class="model-item-pricing">{{ item.pricing }}</div>
                <div class="model-item-id">{{ item.id }}</div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <div class="form-row">
      <span class="form-label">视频流程并发</span>
      <el-input-number v-model="modelConfig.videoConcurrency" :min="1" :max="10" size="small" />
    </div>

    <div class="model-block">
      <div class="model-block-title-row">
        <span class="model-block-icon purple">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m12.296 3.464 3.02 3.956"></path>
            <path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3z"></path>
            <path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <path d="m6.18 5.276 3.1 3.899"></path>
          </svg>
        </span>
        <h4 class="model-block-title">视频生成模型</h4>
      </div>
      <p class="model-block-desc">负责将图像与指令合成为最终视频片段。</p>
      <div class="relative" ref="videoDropdownRef">
        <button
          type="button"
          class="model-select-trigger"
          :class="{ 'model-select-trigger-active': videoDropdownOpen }"
          @click="toggleVideoDropdown"
        >
          <span class="model-select-label">{{ videoModelDisplayName }}</span>
          <svg
            xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            class="model-select-chevron"
            :class="{ 'rotate-180': videoDropdownOpen }"
          >
            <path d="m6 9 6 6 6-6"></path>
          </svg>
        </button>
        <Transition name="dropdown">
          <div v-if="videoDropdownOpen" class="model-select-dropdown">
            <div class="model-dropdown-inner">
              <div
                v-for="item in videoModelOptions"
                :key="item.id"
                class="model-dropdown-item"
                :class="{ 'model-dropdown-item-active': modelConfig.videoModel === item.label }"
                @click="selectVideoModel(item)"
              >
                <div class="model-item-header">
                  <span class="model-item-name">{{ item.name }}</span>
                  <span v-if="modelConfig.videoModel === item.label" class="model-item-check">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M20 6 9 17l-5-5"></path>
                    </svg>
                  </span>
                </div>
                <div v-if="item.pricing" class="model-item-pricing">{{ item.pricing }}</div>
                <div class="model-item-id">{{ item.id }}</div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <div class="model-block">
      <div class="model-block-title-row">
        <span class="model-block-icon teal">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="18" x="3" y="3" rx="2"></rect>
            <path d="m3 9 18 0"></path>
            <path d="m9 21 0-18"></path>
          </svg>
        </span>
        <h4 class="model-block-title">分镜生成模型</h4>
      </div>
      <p class="model-block-desc">负责将剧本解析为分镜脚本，仅支持文本分析类模型。</p>
      <div class="relative" ref="storyboardDropdownRef">
        <button
          type="button"
          class="model-select-trigger"
          :class="{ 'model-select-trigger-active': storyboardDropdownOpen }"
          @click="toggleStoryboardDropdown"
        >
          <span class="model-select-label">{{ storyboardModelDisplayName }}</span>
          <svg
            xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            class="model-select-chevron"
            :class="{ 'rotate-180': storyboardDropdownOpen }"
          >
            <path d="m6 9 6 6 6-6"></path>
          </svg>
        </button>
        <Transition name="dropdown">
          <div v-if="storyboardDropdownOpen" class="model-select-dropdown">
            <div class="model-dropdown-inner">
              <div
                v-for="item in textModelOptions"
                :key="item.id"
                class="model-dropdown-item"
                :class="{ 'model-dropdown-item-active': modelConfig.storyboardModel === item.label }"
                @click="selectStoryboardModel(item)"
              >
                <div class="model-item-header">
                  <span class="model-item-name">{{ item.name }}</span>
                  <span v-if="modelConfig.storyboardModel === item.label" class="model-item-check">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M20 6 9 17l-5-5"></path>
                    </svg>
                  </span>
                </div>
                <div v-if="item.pricing" class="model-item-pricing">{{ item.pricing }}</div>
                <div class="model-item-id">{{ item.id }}</div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { updateUserApiConfig } from '@/api/userApiConfig'

const props = defineProps({
  modelConfig: {
    type: Object,
    required: true
  },
  textModelOptions: {
    type: Array,
    default: () => []
  },
  videoModelOptions: {
    type: Array,
    default: () => []
  }
})

const textDropdownOpen = ref(false)
const videoDropdownOpen = ref(false)
const storyboardDropdownOpen = ref(false)
const textDropdownRef = ref(null)
const videoDropdownRef = ref(null)
const storyboardDropdownRef = ref(null)

const textModelDisplayName = computed(() => {
  const item = props.textModelOptions.find(i => i.label === props.modelConfig.textModel)
  return item ? item.name : props.modelConfig.textModel
})

const videoModelDisplayName = computed(() => {
  const item = props.videoModelOptions.find(i => i.label === props.modelConfig.videoModel)
  return item ? item.name : props.modelConfig.videoModel
})

const storyboardModelDisplayName = computed(() => {
  const item = props.textModelOptions.find(i => i.label === props.modelConfig.storyboardModel)
  return item ? item.name : props.modelConfig.storyboardModel
})

const closeOtherDropdowns = (keep) => {
  if (keep !== 'text') textDropdownOpen.value = false
  if (keep !== 'video') videoDropdownOpen.value = false
  if (keep !== 'storyboard') storyboardDropdownOpen.value = false
}

const toggleTextDropdown = () => {
  textDropdownOpen.value = !textDropdownOpen.value
  if (textDropdownOpen.value) closeOtherDropdowns('text')
}

const toggleVideoDropdown = () => {
  videoDropdownOpen.value = !videoDropdownOpen.value
  if (videoDropdownOpen.value) closeOtherDropdowns('video')
}

const toggleStoryboardDropdown = () => {
  storyboardDropdownOpen.value = !storyboardDropdownOpen.value
  if (storyboardDropdownOpen.value) closeOtherDropdowns('storyboard')
}

const selectTextModel = async (item) => {
  props.modelConfig.textModel = item.label
  textDropdownOpen.value = false
  try {
    await updateUserApiConfig({ analysis_model: item.id })
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

const selectVideoModel = async (item) => {
  props.modelConfig.videoModel = item.label
  videoDropdownOpen.value = false
  try {
    await updateUserApiConfig({ video_model: item.id })
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

const selectStoryboardModel = async (item) => {
  props.modelConfig.storyboardModel = item.label
  storyboardDropdownOpen.value = false
  try {
    await updateUserApiConfig({ storyboard_model: item.id })
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

let debounceTimer = null

const saveConcurrency = (localField, apiField, value) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(async () => {
    try {
      await updateUserApiConfig({ [apiField]: value })
    } catch {
      // 错误提示由 request 拦截器统一处理
    }
  }, 600)
}

watch(() => props.modelConfig.textConcurrency, (val) => {
  saveConcurrency('textConcurrency', 'analysis_concurrency', val)
})

watch(() => props.modelConfig.videoConcurrency, (val) => {
  saveConcurrency('videoConcurrency', 'video_concurrency', val)
})

const handleClickOutside = (event) => {
  if (textDropdownRef.value && !textDropdownRef.value.contains(event.target)) {
    textDropdownOpen.value = false
  }
  if (videoDropdownRef.value && !videoDropdownRef.value.contains(event.target)) {
    videoDropdownOpen.value = false
  }
  if (storyboardDropdownRef.value && !storyboardDropdownRef.value.contains(event.target)) {
    storyboardDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.sub-section {
  margin-bottom: 28px;
  padding: 20px;
  background: #f9fafb;
  border-radius: 16px;
  border: 0.667px solid rgba(111, 126, 153, 0.18);
}

.sub-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.sub-title-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  flex-shrink: 0;
}

.sub-title-icon.blue {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.sub-title {
  font-size: 17px;
  font-weight: 600;
  color: #0a0a0a;
  margin-bottom: 0;
}

.form-row {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.model-block {
  margin-bottom: 20px;
}

.model-block-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.model-block-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  flex-shrink: 0;
}

.model-block-icon.blue {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.model-block-icon.purple {
  background: rgba(168, 85, 247, 0.1);
  color: #a855f7;
}

.model-block-icon.teal {
  background: rgba(20, 184, 166, 0.1);
  color: #14b8a6;
}

.model-block-title {
  font-size: 14px;
  font-weight: 600;
  color: #0a0a0a;
  margin-bottom: 0;
}

.model-block-desc {
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 10px;
}

.relative {
  position: relative;
}

.model-select-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 14px;
  border: 1px solid rgba(111, 126, 153, 0.24);
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  text-align: left;
}

.model-select-trigger:hover {
  border-color: rgba(59, 130, 246, 0.4);
}

.model-select-trigger-active {
  border-color: rgba(59, 130, 246, 0.6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

.model-select-label {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-select-chevron {
  flex-shrink: 0;
  color: #6b7280;
  transition: transform 0.3s;
}

.model-select-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 50;
  border-radius: 14px;
  border: 1px solid rgba(111, 126, 153, 0.18);
  background: #fff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.model-dropdown-inner {
  max-height: 320px;
  overflow-y: auto;
  padding: 6px;
}

.model-dropdown-item {
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.model-dropdown-item:hover {
  background: #f3f4f6;
}

.model-dropdown-item-active {
  background: rgba(59, 130, 246, 0.06);
}

.model-dropdown-item-active:hover {
  background: rgba(59, 130, 246, 0.1);
}

.model-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.model-item-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.model-item-check {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  color: #3b82f6;
}

.model-item-pricing {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.model-item-id {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
  font-family: monospace;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
