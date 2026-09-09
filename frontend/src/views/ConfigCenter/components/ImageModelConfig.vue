<template>
  <div class="sub-section">
    <div class="sub-title-row">
      <span class="sub-title-icon indigo">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"></path>
          <path d="m14 7 3 3"></path>
          <path d="M5 6v4"></path>
          <path d="M19 14v4"></path>
          <path d="M10 2v2"></path>
          <path d="M7 8H3"></path>
          <path d="M21 16h-4"></path>
          <path d="M11 3H9"></path>
        </svg>
      </span>
      <h3 class="sub-title">全局图像模型配置</h3>
    </div>

    <div class="form-row">
      <span class="form-label">图像流程并发</span>
      <el-input-number v-model="modelConfig.imageConcurrency" :min="1" :max="10" size="small" />
    </div>

    <p class="info-text">推荐使用 Google Banana 系列模型，目前其他图像模型生成效果有限。</p>

    <div class="batch-config">
      <div class="batch-header">
        <div>
          <div class="batch-title">批量配置图像模型</div>
          <div class="batch-desc">设置负责整个系统所有地方图像生成/编辑的模型</div>
        </div>
        <div class="relative" ref="imageDropdownRef">
          <button
            type="button"
            class="model-select-trigger"
            :class="{ 'model-select-trigger-active': imageDropdownOpen }"
            @click="toggleImageDropdown"
          >
            <span class="model-select-label">{{ imageModelDisplayName }}</span>
            <svg
              xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
              class="model-select-chevron"
              :class="{ 'rotate-180': imageDropdownOpen }"
            >
              <path d="m6 9 6 6 6-6"></path>
            </svg>
          </button>
          <Transition name="dropdown">
            <div v-if="imageDropdownOpen" class="model-select-dropdown">
              <div class="model-dropdown-inner">
                <div
                  v-for="item in imageModelOptions"
                  :key="item.id"
                  class="model-dropdown-item"
                  :class="{ 'model-dropdown-item-active': modelConfig.imageModel === item.label }"
                  @click="selectImageModel(item)"
                >
                  <div class="model-item-header">
                    <span class="model-item-name">{{ item.name }}</span>
                    <span v-if="modelConfig.imageModel === item.label" class="model-item-check">
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

    <div class="image-models">
      <div
        v-for="(item, index) in imageModelList"
        :key="item.label"
        class="image-model-item"
      >
        <span class="image-model-label">{{ item.label }}</span>
        <div class="relative scene-dropdown-wrap" :ref="el => { if (el) sceneDropdownRefs[index] = el }">
          <button
            type="button"
            class="model-select-trigger scene-trigger"
            :class="{ 'model-select-trigger-active': sceneDropdownIndex === index }"
            @click="toggleSceneDropdown(index)"
          >
            <span class="model-select-label">{{ getSceneModelDisplayName(index) }}</span>
            <svg
              xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
              class="model-select-chevron"
              :class="{ 'rotate-180': sceneDropdownIndex === index }"
            >
              <path d="m6 9 6 6 6-6"></path>
            </svg>
          </button>
          <Transition name="dropdown">
            <div v-if="sceneDropdownIndex === index" class="model-select-dropdown scene-dropdown">
              <div class="model-dropdown-inner">
                <div
                  v-for="opt in imageModelOptions"
                  :key="opt.id"
                  class="model-dropdown-item"
                  :class="{ 'model-dropdown-item-active': item.model === opt.label }"
                  @click="selectSceneModel(index, opt)"
                >
                  <div class="model-item-header">
                    <span class="model-item-name">{{ opt.name }}</span>
                    <span v-if="item.model === opt.label" class="model-item-check">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M20 6 9 17l-5-5"></path>
                      </svg>
                    </span>
                  </div>
                  <div v-if="opt.pricing" class="model-item-pricing">{{ opt.pricing }}</div>
                  <div class="model-item-id">{{ opt.id }}</div>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { updateUserApiConfig } from '@/api/userApiConfig'

const SCENE_FIELD_MAP = ['character_model', 'location_model', 'edit_model']

const props = defineProps({
  modelConfig: {
    type: Object,
    required: true
  },
  imageModelOptions: {
    type: Array,
    default: () => []
  },
  imageModelList: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['applyToAll'])

const imageDropdownOpen = ref(false)
const imageDropdownRef = ref(null)
const sceneDropdownIndex = ref(-1)
const sceneDropdownRefs = ref([])

const imageModelDisplayName = computed(() => {
  const item = props.imageModelOptions.find(i => i.label === props.modelConfig.imageModel)
  return item ? item.name : props.modelConfig.imageModel
})

const toggleImageDropdown = () => {
  imageDropdownOpen.value = !imageDropdownOpen.value
  sceneDropdownIndex.value = -1
}

const selectImageModel = async (item) => {
  props.modelConfig.imageModel = item.label
  imageDropdownOpen.value = false
  for (let i = 0; i < props.imageModelList.length; i++) {
    props.imageModelList[i].model = item.label
  }
  emit('applyToAll', item.label)
  try {
    await updateUserApiConfig({
      character_model: item.id,
      location_model: item.id,
      edit_model: item.id
    })
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

const applyToAllScenes = async () => {
  emit('applyToAll', props.modelConfig.imageModel)
  const selectedItem = props.imageModelOptions.find(i => i.label === props.modelConfig.imageModel)
  if (!selectedItem) return
  try {
    await updateUserApiConfig({
      character_model: selectedItem.id,
      location_model: selectedItem.id,
      edit_model: selectedItem.id
    })
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

const getSceneModelDisplayName = (index) => {
  const model = props.imageModelList[index]?.model
  if (!model) return ''
  const item = props.imageModelOptions.find(i => i.label === model)
  return item ? item.name : model
}

const toggleSceneDropdown = (index) => {
  imageDropdownOpen.value = false
  sceneDropdownIndex.value = sceneDropdownIndex.value === index ? -1 : index
}

const selectSceneModel = async (index, item) => {
  props.imageModelList[index].model = item.label
  sceneDropdownIndex.value = -1
  const field = SCENE_FIELD_MAP[index]
  if (!field) return
  try {
    await updateUserApiConfig({ [field]: item.id })
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

let debounceTimer = null

const saveConcurrency = (value) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(async () => {
    try {
      await updateUserApiConfig({ image_concurrency: value })
    } catch {
      // 错误提示由 request 拦截器统一处理
    }
  }, 600)
}

watch(() => props.modelConfig.imageConcurrency, (val) => {
  saveConcurrency(val)
})

const handleClickOutside = (event) => {
  if (imageDropdownRef.value && !imageDropdownRef.value.contains(event.target)) {
    imageDropdownOpen.value = false
  }
  if (sceneDropdownIndex.value !== -1) {
    const activeRef = sceneDropdownRefs.value[sceneDropdownIndex.value]
    if (activeRef && !activeRef.contains(event.target)) {
      sceneDropdownIndex.value = -1
    }
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

.sub-title-icon.indigo {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
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

.info-text {
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 16px;
}

.batch-config {
  margin-bottom: 16px;
}

.batch-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.batch-title {
  font-size: 14px;
  font-weight: 600;
  color: #0a0a0a;
  margin-bottom: 4px;
}

.batch-desc {
  font-size: 13px;
  color: #4b5563;
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

.model-block-icon.indigo {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
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
  min-width: 200px;
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
  border-color: rgba(99, 102, 241, 0.4);
}

.model-select-trigger-active {
  border-color: rgba(99, 102, 241, 0.6);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
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
  min-width: 200px;
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
  background: rgba(99, 102, 241, 0.06);
}

.model-dropdown-item-active:hover {
  background: rgba(99, 102, 241, 0.1);
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
  color: #6366f1;
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

.image-models {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.image-model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px;
  border: 0.667px solid rgba(111, 126, 153, 0.18);
}

.image-model-label {
  font-size: 14px;
  font-weight: 500;
  color: #0a0a0a;
}

.scene-dropdown-wrap {
  min-width: 180px;
}

.scene-trigger {
  padding: 6px 10px;
  font-size: 13px;
  border-radius: 10px;
}

.scene-dropdown {
  right: 0;
  left: auto;
  min-width: 320px;
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
