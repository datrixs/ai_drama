<template>
  <div class="section-header">
    <h2 class="section-title">API 配置</h2>
  </div>

  <div class="config-section">
    <div class="block-title-row">
      <span class="block-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915"></path>
          <circle cx="12" cy="12" r="3"></circle>
        </svg>
      </span>
      <h2 class="block-title">默认模型配置</h2>
    </div>
    <p class="block-desc">新建项目与资产库将使用此默认配置，也可在项目设置中为单独项目自定义模型</p>

    <TextAndVideoModelConfig
      :model-config="modelConfig"
      :text-model-options="textModelOptions"
      :video-model-options="videoModelOptions"
    />

    <ImageModelConfig :model-config="modelConfig" :image-model-options="imageModelOptions" :image-model-list="imageModelList" @apply-to-all="applyImageToAll" />
  </div>

  <ProviderResourcePool @custom-models-changed="handleCustomModelsChanged" />
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getUserApiConfig, updateUserApiConfig } from '@/api/userApiConfig'
import { getModelOptions } from '@/api/aiModel'
import { useUserStore } from '@/store/user'
import TextAndVideoModelConfig from './components/TextAndVideoModelConfig.vue'
import ImageModelConfig from './components/ImageModelConfig.vue'
import ProviderResourcePool from './components/ProviderResourcePool.vue'

// 区域对应的可用视频模型
const REGION_VIDEO_MODELS = {
  domestic: ['doubao-seedance-2-0-260128', 'doubao-seedance-2-0-fast-260128'],
  overseas: ['dreamina-seedance-2-0-260128'],
}

const userStore = useUserStore()

const modelConfig = reactive({
  textConcurrency: 5,
  textModel: '',
  videoConcurrency: 5,
  videoModel: '',
  storyboardModel: '',
  imageConcurrency: 5,
  imageModel: ''
})

const textModelOptions = ref([])
const videoModelOptions = ref([])
const imageModelOptions = ref([])
const imageModelList = ref([])
const systemModelMap = ref({})

const getModelDisplayName = (modelId) => {
  if (!modelId) return ''
  return systemModelMap.value[modelId] || modelId
}

const loadUserConfig = async () => {
  try {
    const config = await getUserApiConfig()

    modelConfig.textConcurrency = config.analysis_concurrency ?? 5
    modelConfig.videoConcurrency = config.video_concurrency ?? 5
    modelConfig.imageConcurrency = config.image_concurrency ?? 5

    modelConfig.textModel = getModelDisplayName(config.analysis_model)
    modelConfig.storyboardModel = getModelDisplayName(config.storyboard_model)

    const region = userStore.userInfo.value?.region || 'domestic'
    const allowedVideoModels = REGION_VIDEO_MODELS[region] || REGION_VIDEO_MODELS.domestic
    if (config.video_model && allowedVideoModels.includes(config.video_model)) {
      modelConfig.videoModel = getModelDisplayName(config.video_model)
    } else {
      modelConfig.videoModel = ''
    }

    const imageLabel = getModelDisplayName(config.character_model)
    modelConfig.imageModel = imageLabel

    imageModelList.value = [
      { label: '角色生成', model: getModelDisplayName(config.character_model) },
      { label: '场景生成', model: getModelDisplayName(config.location_model) },
      { label: '编辑图片', model: getModelDisplayName(config.edit_model) }
    ]

    refreshCustomModelOptions(config.custom_models)
  } catch {
    // 用户未配置时使用默认值
  }
}

const refreshCustomModelOptions = (customModels) => {
  const models = customModels || []
  const region = userStore.userInfo.value?.region || 'domestic'
  const allowedVideoModels = REGION_VIDEO_MODELS[region] || REGION_VIDEO_MODELS.domestic
  const enabledText = models.filter(m => m.enabled && m.model_type === 'text')
  const enabledVideo = models.filter(m => m.enabled && m.model_type === 'video' && allowedVideoModels.includes(m.model))
  const enabledImage = models.filter(m => m.enabled && m.model_type === 'image')

  textModelOptions.value = enabledText.map(m => ({
    name: systemModelMap.value[m.model] || m.model_name,
    pricing: m.price,
    id: m.model,
    label: systemModelMap.value[m.model] || m.model_name
  }))
  videoModelOptions.value = enabledVideo.map(m => ({
    name: systemModelMap.value[m.model] || m.model_name,
    pricing: m.price,
    id: m.model,
    label: systemModelMap.value[m.model] || m.model_name
  }))
  imageModelOptions.value = enabledImage.map(m => ({
    name: systemModelMap.value[m.model] || m.model_name,
    pricing: m.price,
    id: m.model,
    label: systemModelMap.value[m.model] || m.model_name
  }))
}

const handleCustomModelsChanged = async () => {
  try {
    const configData = await getUserApiConfig()
    refreshCustomModelOptions(configData?.custom_models)

    const textIds = new Set(textModelOptions.value.map(o => o.label))
    const videoIds = new Set(videoModelOptions.value.map(o => o.label))
    const imageIds = new Set(imageModelOptions.value.map(o => o.label))

    const updates = {}
    if (modelConfig.textModel && !textIds.has(modelConfig.textModel)) {
      modelConfig.textModel = ''
      updates.analysis_model = ''
    }
    if (modelConfig.videoModel && !videoIds.has(modelConfig.videoModel)) {
      modelConfig.videoModel = ''
      updates.video_model = ''
    }
    if (modelConfig.imageModel && !imageIds.has(modelConfig.imageModel)) {
      modelConfig.imageModel = ''
      updates.character_model = ''
      updates.location_model = ''
      updates.storyboard_model = ''
      updates.edit_model = ''
      imageModelList.value.forEach(item => { item.model = '' })
    } else {
      const sceneFieldMap = ['character_model', 'location_model', 'storyboard_model', 'edit_model']
      imageModelList.value.forEach((item, i) => {
        if (item.model && !imageIds.has(item.model)) {
          item.model = ''
          updates[sceneFieldMap[i]] = ''
        }
      })
    }
    if (Object.keys(updates).length > 0) {
      await updateUserApiConfig(updates)
    }
  } catch {
    // 忽略
  }
}

const loadModelOptions = async () => {
  const [textData, videoData, imageData] = await Promise.all([
    getModelOptions('text'),
    getModelOptions('video'),
    getModelOptions('image')
  ])

  const allModels = [
    ...(textData || []),
    ...(videoData || []),
    ...(imageData || [])
  ]
  const map = {}
  for (const m of allModels) {
    map[m.model_name] = m.name
  }
  systemModelMap.value = map
}

const applyImageToAll = (selectedModel) => {
  const displayName = (() => {
    const item = imageModelOptions.value.find(i => i.label === selectedModel)
    return item ? item.label : selectedModel
  })()
  imageModelList.value.forEach(item => {
    item.model = displayName
  })
}

onMounted(async () => {
  await loadModelOptions()
  await loadUserConfig()
})
</script>

<style scoped>
.section-header {
  padding: 16px 24px;
  border-bottom: 0.667px solid rgba(111, 126, 153, 0.12);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.98);
  z-index: 1;
  border-radius: 16px 16px 0 0;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #0a0a0a;
}

.config-section {
  padding: 24px;
}

.config-section + .config-section {
  border-top: 0.667px solid rgba(111, 126, 153, 0.12);
}

.block-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.block-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: rgba(22, 35, 64, 0.05) 0px 2px 10px 0px;
  color: #111827;
  flex-shrink: 0;
}

.block-title {
  font-size: 20px;
  font-weight: 700;
  color: #0a0a0a;
  margin-bottom: 0;
}

.block-desc {
  font-size: 14px;
  color: #4b5563;
  margin-bottom: 20px;
}
</style>
