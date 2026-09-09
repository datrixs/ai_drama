<template>
  <div class="config-section">
    <div class="block-title-row">
      <span class="block-icon teal">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path>
          <path d="M2 12h20"></path>
        </svg>
      </span>
      <h2 class="block-title">厂商资源池</h2>
    </div>
    <div class="provider-header-row">
      <div>
        <p class="block-desc">在此使用来自全球丰富的模型配置</p>
        <p class="block-desc" style="margin-top: 4px">按住左上角拖拽手柄可调整厂商顺序</p>
      </div>
      <button class="add-provider-btn" @click="handleAddProvider">
        <span>新增模型服务商</span>
      </button>
    </div>

    <div v-if="loading" class="provider-loading">加载中...</div>

    <div v-else class="provider-list">
      <div v-for="provider in providerList" :key="provider.name" class="provider-card">
        <div class="provider-header">
          <div class="provider-left">
            <el-icon :size="16" class="drag-handle"><Rank /></el-icon>
            <h3 class="provider-name">{{ provider.name }}</h3>
            <span v-if="provider.connected" class="provider-status connected" title="已连接">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>
            </span>
            <span v-else class="provider-status disconnected" title="未连接">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m19 5 3-3"/><path d="m2 22 3-3"/><path d="M6.3 20.3a2.4 2.4 0 0 0 3.4 0L12 18l-6-6-2.3 2.3a2.4 2.4 0 0 0 0 3.4Z"/><path d="M7.5 13.5 10 11"/><path d="M10.5 16.5 13 14"/><path d="m12 6 6 6 2.3-2.3a2.4 2.4 0 0 0 0-3.4l-2.6-2.6a2.4 2.4 0 0 0-3.4 0Z"/></svg>
            </span>
          </div>
          <div class="provider-actions-btns">
            <button
              :class="['test-btn', { 'test-btn-disabled': !provider.connected, 'test-btn-testing': provider.testState === 'testing', 'test-btn-passed': provider.testState === 'passed', 'test-btn-failed': provider.testState === 'failed' }]"
              :disabled="!provider.connected || provider.testState === 'testing'"
              @click="handleTestConnection(provider)"
            >
              <svg v-if="provider.testState === 'testing'" class="spin-icon" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
              {{ provider.testState === 'testing' ? '正在测试...' : provider.testState === 'passed' ? '连接测试通过' : provider.testState === 'failed' ? '连接测试未通过' : '测试连接' }}
            </button>
            <button class="tutorial-btn" @click="handleOpenTutorial(provider)">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/></svg>
              开通教程
            </button>
          </div>
        </div>

        <div class="provider-key-row">
          <span class="key-label">API Key</span>
          <template v-if="provider.editing">
            <input
              v-model="provider.editKey"
              class="key-input"
              type="password"
              placeholder="请输入 API Key"
              @keyup.enter="handleSaveKey(provider)"
              @keyup.escape="handleCancelEdit(provider)"
            />
            <button class="key-save-btn" @click="handleSaveKey(provider)">保存</button>
            <button class="key-cancel-btn" @click="handleCancelEdit(provider)">取消</button>
          </template>
          <template v-else-if="provider.connected">
            <span class="key-value">{{ provider.keyVisible ? provider.rawKey : provider.maskedKey }}</span>
            <button class="key-action-btn" @click="handleToggleKeyVisibility(provider)">
              {{ provider.keyVisible ? '隐藏' : '显示' }}
            </button>
            <button class="key-action-btn key-edit-btn" @click="handleStartEdit(provider)">修改</button>
          </template>
          <template v-else>
            <button class="key-connect-btn" @click="handleStartEdit(provider)">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
              连接
            </button>
          </template>
        </div>

        <div class="provider-capabilities">
          <div class="capability-tabs">
            <button
              v-for="cap in provider.capabilities"
              :key="cap"
              :class="['cap-tab', { active: provider.activeCap === cap }]"
              @click="provider.activeCap = cap"
            >{{ cap }}</button>
          </div>

          <div class="capability-content">
            <div class="cap-header">
              <span class="cap-label">{{ provider.activeCap }}</span>
              <span class="cap-count">{{ getActiveModels(provider).length }}</span>
            </div>
            <div v-for="model in getActiveModels(provider)" :key="model.id" class="model-item">
              <div class="model-info">
                <div class="model-name-row">
                  <span class="model-name">{{ model.name }}</span>
                  <el-tag v-if="model.isDefault" size="small" type="warning" class="default-tag">默认</el-tag>
                </div>
                <div class="model-id">{{ model.id }}</div>
              </div>
              <div class="model-actions">
                <el-switch
                  v-model="model.enabled"
                  :disabled="!provider.connected"
                  size="small"
                  @change="(val) => handleToggleModel(provider, model, val)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增模型服务商弹窗 -->
    <div v-if="addProviderVisible" class="add-provider-overlay" @click.self="addProviderVisible = false">
      <div class="add-provider-modal">
        <div class="add-provider-header">
          <div>
            <h2 class="add-provider-title">新增模型服务商</h2>
            <p class="add-provider-subtitle">厂商资源池</p>
          </div>
          <button class="add-provider-close-btn" @click="addProviderVisible = false">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        <div class="add-provider-divider"></div>
        <div class="add-provider-body">
          <div class="add-provider-warning">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
            <span>项目目前为测试版，由于市面上各厂商自定义 API 格式差异较大，自定义 API 兼容性尚不完善，建议优先使用官方内置 API。后续版本将持续更新以兼容更多厂商。</span>
          </div>
          <div class="add-provider-field">
            <label class="add-provider-label">API 类型</label>
            <div class="add-provider-select-wrap">
              <select v-model="addProviderForm.apiType" class="add-provider-select">
                <option value="gemini-compatible">Gemini 兼容</option>
                <option value="openai-compatible">OpenAI 兼容</option>
              </select>
              <div class="add-provider-select-arrow">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
              </div>
            </div>
          </div>
          <div class="add-provider-field">
            <label class="add-provider-label">名称</label>
            <input v-model="addProviderForm.name" placeholder="名称" class="add-provider-input" type="text" />
          </div>
          <div class="add-provider-field">
            <label class="add-provider-label">Base URL</label>
            <input v-model="addProviderForm.baseUrl" placeholder="Base URL" class="add-provider-input add-provider-input-mono" type="text" />
          </div>
          <div class="add-provider-field">
            <label class="add-provider-label">API Key</label>
            <input v-model="addProviderForm.apiKey" placeholder="API Key" class="add-provider-input" type="password" />
          </div>
        </div>
        <div class="add-provider-divider"></div>
        <div class="add-provider-footer">
          <button class="add-provider-cancel-btn" @click="handleCancelAddProvider">取消</button>
          <button class="add-provider-submit-btn" @click="handleSubmitAddProvider">添加</button>
        </div>
      </div>
    </div>

    <!-- 开通教程弹窗 -->
    <div v-if="tutorialVisible" class="tutorial-overlay" @click.self="tutorialVisible = false">
      <div class="tutorial-modal">
        <div class="tutorial-header">
          <div class="tutorial-header-left">
            <div class="tutorial-icon-badge">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/></svg>
            </div>
            <div>
              <h3 class="tutorial-title">{{ currentTutorial.name }} 开通教程</h3>
              <p class="tutorial-subtitle">按照以下步骤完成配置</p>
            </div>
          </div>
          <button class="tutorial-close-btn" @click="tutorialVisible = false">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        <div class="tutorial-body">
          <div v-for="(step, idx) in currentTutorial.steps" :key="idx" class="tutorial-step">
            <div class="step-number">{{ idx + 1 }}</div>
            <div class="step-content">
              <p class="step-text">{{ step.text }}</p>
              <a
                v-if="step.url"
                :href="step.url"
                target="_blank"
                rel="noopener noreferrer"
                class="step-link"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
                点击打开
              </a>
            </div>
          </div>
          <div class="tutorial-footer">
            <button class="tutorial-ok-btn" @click="tutorialVisible = false">我知道了</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Rank } from '@element-plus/icons-vue'
import { getModelsGrouped } from '@/api/aiModel'
import { getUserApiConfig, updateUserApiConfig, testProviderConnection } from '@/api/userApiConfig'

const loading = ref(true)
const providerList = ref([])

const emit = defineEmits(['customModelsChanged'])
const tutorialVisible = ref(false)
const currentTutorial = ref({ name: '', steps: [] })

/**
 * 厂商开通教程数据
 */
const TUTORIAL_MAP = {
  'volcengine': {
    name: '火山引擎 Ark',
    steps: [
      { text: '进入火山引擎控制台，开通 API Key', url: 'https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D' },
      { text: '在模型管理页面，点击右上角「一键开通所有模型」', url: 'https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM=%7B%7D&advancedActiveKey=model' },
      { text: '复制 API Key，粘贴到上方输入框中' },
    ],
  },
  'Google': {
    name: 'Google AI Studio',
    steps: [
      { text: '进入 Google AI Studio，创建 API Key', url: 'https://aistudio.google.com/api-keys' },
      { text: '复制 API Key，粘贴到上方输入框中' },
    ],
  },
  'Ali': {
    name: '阿里云百炼',
    steps: [
      { text: '进入阿里云百炼控制台，开通 API Key', url: 'https://bailian.console.aliyun.com/' },
      { text: '复制 API Key，粘贴到上方输入框中' },
    ],
  },
  'OpenRouter': {
    name: 'OpenRouter',
    steps: [
      { text: '进入 OpenRouter，创建 API Key', url: 'https://openrouter.ai/settings/keys' },
      { text: '复制 API Key，粘贴到上方输入框中' },
    ],
  },
  'MiniMax': {
    name: '海螺 MiniMax',
    steps: [
      { text: '进入海螺开放平台，创建 API Key', url: 'https://platform.minimaxi.com/' },
      { text: '复制 API Key，粘贴到上方输入框中' },
    ],
  },
  'Vidu': {
    name: '生数科技 Vidu',
    steps: [
      { text: '进入生数科技控制台，开通 API Key', url: 'https://platform.vidu.cn/' },
      { text: '复制 API Key，粘贴到上方输入框中' },
    ],
  },
  'FAL': {
    name: 'FAL',
    steps: [
      { text: '进入 FAL 控制台，创建 API Key', url: 'https://fal.ai/dashboard/keys' },
      { text: '复制 API Key，粘贴到上方输入框中' },
    ],
  },
}

/**
 * 厂商 code 与用户配置中 API Key 字段的映射
 */
const PROVIDER_KEY_MAP = {
  'volcengine': 'ark_api_key',
  'Google': 'google_api_key',
  'Ali': 'qwen_api_key',
  'FAL': 'fal_api_key',
  'JD': 'jd_api_key',
}

/**
 * 模型类型映射为中文能力标签
 */
const MODEL_TYPE_LABELS = {
  'text': '文本',
  'image': '图像',
  'video': '视频',
  'audio': '音频等',
}

/**
 * 加载厂商列表和用户配置
 */
const loadData = async () => {
  loading.value = true
  try {
    const [modelsData, configData] = await Promise.all([
      getModelsGrouped(),
      getUserApiConfig().catch(() => ({}))
    ])

    const userConfig = configData || {}

    const apiKeyMap = {}
    for (const [code, field] of Object.entries(PROVIDER_KEY_MAP)) {
      apiKeyMap[code] = userConfig[field] || null
    }

    const customProviderMap = {}
    for (const cp of (userConfig.custom_providers || [])) {
      if (cp.api_key) {
        customProviderMap[cp.id] = cp.api_key
      }
    }
    for (const [id, apiKey] of Object.entries(customProviderMap)) {
      if (!apiKeyMap[id]) {
        apiKeyMap[id] = apiKey
      }
    }

    const enabledMap = {}
    for (const cm of (userConfig.custom_models || [])) {
      if (cm.enabled) {
        enabledMap[`${cm.provider_id}::${cm.model}`] = true
      }
    }

    providerList.value = (modelsData || []).map(group => {
      const provider = group.provider || {}
      const models = group.models || []
      const apiKey = apiKeyMap[provider.code]
      const connected = !!(apiKey && apiKey.trim())
      const maskedKey = connected
        ? (apiKey.length > 8 ? apiKey.slice(0, 4) + '••••••••••••' + apiKey.slice(-4) : '••••••••')
        : ''

      const capSet = new Set()
      const modelsByType = {}
      for (const m of models) {
        const label = MODEL_TYPE_LABELS[m.model_type] || m.model_type
        capSet.add(label)
        if (!modelsByType[label]) modelsByType[label] = []
        modelsByType[label].push({
          name: m.name,
          id: m.model_name,
          modelType: m.model_type,
          isDefault: false,
          enabled: !!enabledMap[`${provider.code}::${m.model_name}`],
        })
      }

      const capabilities = Array.from(capSet)
      const activeCap = capabilities[0] || '文本'

      return {
        name: provider.name || '未知厂商',
        code: provider.code,
        connected,
        maskedKey,
        rawKey: apiKey || '',
        keyVisible: false,
        editing: false,
        editKey: '',
        testState: 'idle',
        activeCap,
        capabilities,
        models: modelsByType,
      }
    })
  } catch (e) {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

const getActiveModels = (provider) => {
  return provider.models[provider.activeCap] || []
}

const handleToggleKeyVisibility = (provider) => {
  provider.keyVisible = !provider.keyVisible
}

const handleStartEdit = (provider) => {
  provider.editing = true
  provider.editKey = ''
}

const handleCancelEdit = (provider) => {
  provider.editing = false
  provider.editKey = ''
}

const handleSaveKey = async (provider) => {
  const key = provider.editKey.trim()
  if (!key) {
    ElMessage.warning('请输入 API Key')
    return
  }
  try {
    const PROVIDER_FIELD_MAP = {
      'volcengine': 'ark_api_key',
      'Google': 'google_api_key',
      'Ali': 'qwen_api_key',
      'FAL': 'fal_api_key',
      'JD': 'jd_api_key',
    }

    const configData = await getUserApiConfig().catch(() => ({}))
    const existingProviders = (configData?.custom_providers || []).map((p) => ({
      id: p.id,
      name: p.name,
      base_url: p.base_url || '',
      enabled: p.enabled !== false,
    }))

    const targetIdx = existingProviders.findIndex((p) => p.id === provider.code)
    const providerEntry = {
      id: provider.code,
      name: provider.name,
      base_url: '',
      api_key: key,
      enabled: true,
    }
    if (targetIdx >= 0) {
      existingProviders[targetIdx] = { ...existingProviders[targetIdx], api_key: key }
    } else {
      existingProviders.push(providerEntry)
    }

    const updatePayload = { custom_providers: existingProviders }

    const field = PROVIDER_FIELD_MAP[provider.code]
    if (field) {
      updatePayload[field] = key
    }

    await updateUserApiConfig(updatePayload)
    provider.rawKey = key
    provider.maskedKey = key.length > 8 ? key.slice(0, 4) + '••••••••••••' + key.slice(-4) : '••••••••'
    provider.connected = true
    provider.editing = false
    provider.editKey = ''
    provider.keyVisible = false
    ElMessage.success(`${provider.name} API Key 保存成功`)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

const handleTestConnection = async (provider) => {
  provider.testState = 'testing'
  try {
    console.log(`[连接测试] 开始测试 ${provider.name}，provider_code: ${provider.code}`)
    const res = await testProviderConnection(provider.code)
    console.log(`[连接测试] ${provider.name} 返回结果:`, res)
    const success = res?.success
    if (success) {
      provider.testState = 'passed'
      provider.connected = true
      console.log(`[连接测试] ${provider.name} 连接成功`)
      ElMessage.success(`${provider.name} 连接测试通过`)
    } else {
      provider.testState = 'failed'
      provider.connected = false
      console.warn(`[连接测试] ${provider.name} 连接失败，返回数据:`, res?.data)
      ElMessage.error(`${provider.name} 连接测试未通过`)
    }
  } catch (err) {
    provider.testState = 'failed'
    provider.connected = false
    console.error(`[连接测试] ${provider.name} 请求异常:`, err)
  }
}

const handleOpenTutorial = (provider) => {
  const tutorial = TUTORIAL_MAP[provider.code]
  if (tutorial) {
    currentTutorial.value = tutorial
    tutorialVisible.value = true
  } else {
    ElMessage.info(`${provider.name} 开通教程`)
  }
}

const handleToggleModel = async (provider, model, enabled) => {
  try {
    const configData = await getUserApiConfig().catch(() => ({}))
    const existing = configData?.custom_models || []
    const key = `${provider.code}::${model.id}`
    let updated
    const idx = existing.findIndex(m => `${m.provider_id}::${m.model}` === key)
    if (idx >= 0) {
      existing[idx].enabled = enabled
      updated = existing
    } else {
      updated = [
        ...existing,
        {
          provider_id: provider.code,
          model: model.id,
          model_name: model.name,
          model_type: model.modelType,
          enabled,
          price: null,
        },
      ]
    }
    await updateUserApiConfig({ custom_models: updated })
    ElMessage.success(`${enabled ? '已启用' : '已禁用'} ${model.name}`)
    emit('customModelsChanged')
  } catch {
    model.enabled = !model.enabled
    // 错误提示由 request 拦截器统一处理
  }
}

const addProviderVisible = ref(false)
const addProviderForm = ref({
  apiType: 'gemini-compatible',
  name: '',
  baseUrl: '',
  apiKey: '',
})

const handleAddProvider = () => {
  addProviderForm.value = { apiType: 'gemini-compatible', name: '', baseUrl: '', apiKey: '' }
  addProviderVisible.value = true
}

const handleCancelAddProvider = () => {
  addProviderVisible.value = false
}

const handleSubmitAddProvider = () => {
  const form = addProviderForm.value
  if (!form.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  if (!form.baseUrl.trim()) {
    ElMessage.warning('请输入 Base URL')
    return
  }
  if (!form.apiKey.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }
  ElMessage.success(`服务商「${form.name}」添加成功`)
  addProviderVisible.value = false
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.config-section {
  padding: 24px;
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
  flex-shrink: 0;
}

.block-icon.teal {
  background: rgba(20, 184, 166, 0.1);
  color: #14b8a6;
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

.provider-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.add-provider-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 8px 20px rgba(47, 123, 255, 0.24);
}

.add-provider-btn:hover {
  opacity: 0.9;
  box-shadow: 0 8px 24px rgba(47, 123, 255, 0.36);
}

.provider-loading {
  text-align: center;
  padding: 40px;
  color: #6b7280;
  font-size: 14px;
}

.provider-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.provider-card {
  background: #f9fafb;
  border-radius: 16px;
  border: 0.667px solid rgba(111, 126, 153, 0.18);
  padding: 20px;
  transition: border-color 0.15s;
}

.provider-card:hover {
  border-color: rgba(47, 123, 255, 0.3);
}

.provider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.provider-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.drag-handle {
  cursor: grab;
  color: #9ca3af;
}

.provider-name {
  font-size: 16px;
  font-weight: 600;
  color: #0a0a0a;
}

.provider-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  flex-shrink: 0;
}

.provider-status.connected {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}

.provider-status.disconnected {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.provider-actions-btns {
  display: flex;
  align-items: center;
  gap: 6px;
}

.test-btn,
.tutorial-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 8px;
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  background: transparent;
  color: #374151;
}

.test-btn:hover:not(:disabled),
.tutorial-btn:hover {
  border-color: rgba(111, 126, 153, 0.48);
  background: rgba(0, 0, 0, 0.03);
  color: #111827;
}

.test-btn-disabled {
  cursor: not-allowed;
  color: #9ca3af;
  opacity: 0.4;
}

.test-btn-testing {
  color: #2563eb;
  border-color: rgba(37, 99, 235, 0.3);
  background: rgba(37, 99, 235, 0.06);
}

.test-btn-passed {
  color: #16a34a;
  border-color: rgba(34, 197, 94, 0.3);
  background: rgba(34, 197, 94, 0.06);
}

.test-btn-failed {
  color: #dc2626;
  border-color: rgba(220, 38, 38, 0.3);
  background: rgba(220, 38, 38, 0.06);
}

.test-btn-failed:hover:not(:disabled) {
  border-color: rgba(220, 38, 38, 0.5);
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spin-icon {
  animation: spin 1s linear infinite;
}

.provider-key-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 10px;
  border: 0.667px solid rgba(111, 126, 153, 0.12);
  margin-bottom: 16px;
  font-size: 13px;
}

.key-label {
  color: #4b5563;
  font-weight: 500;
  flex-shrink: 0;
}

.key-value {
  color: #0a0a0a;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.key-input {
  flex: 1;
  min-width: 0;
  padding: 6px 10px;
  border-radius: 8px;
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  background: #fff;
  color: #0a0a0a;
}

.key-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.key-input::placeholder {
  color: #9ca3af;
}

.key-save-btn,
.key-cancel-btn {
  padding: 5px 12px;
  border-radius: 8px;
  border: none;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.key-save-btn {
  background: #2563eb;
  color: #fff;
}

.key-save-btn:hover {
  background: #1d4ed8;
}

.key-cancel-btn {
  background: transparent;
  color: #6b7280;
  border: 0.667px solid rgba(111, 126, 153, 0.24);
}

.key-cancel-btn:hover {
  background: rgba(0, 0, 0, 0.03);
  color: #374151;
}

.key-action-btn {
  padding: 4px 8px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.key-action-btn:hover {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.06);
}

.key-edit-btn:hover {
  color: #2563eb;
}

.key-connect-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 8px;
  border: none;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.key-connect-btn:hover {
  background: rgba(37, 99, 235, 0.18);
}

.provider-capabilities {
  border-top: 0.667px solid rgba(111, 126, 153, 0.12);
  padding-top: 16px;
}

.capability-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
}

.cap-tab {
  padding: 6px 16px;
  border-radius: 10px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.15s;
}

.cap-tab.active {
  background: rgba(47, 123, 255, 0.12);
  color: #1d63e8;
}

.cap-tab:hover:not(.active) {
  background: rgba(0, 0, 0, 0.04);
}

.cap-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 0.667px solid rgba(111, 126, 153, 0.12);
}

.cap-label {
  font-size: 14px;
  font-weight: 600;
  color: #0a0a0a;
}

.cap-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 8px;
  background: rgba(47, 123, 255, 0.12);
  color: #1d63e8;
  font-size: 12px;
  font-weight: 600;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-radius: 10px;
  border: 0.667px solid rgba(111, 126, 153, 0.12);
  margin-bottom: 8px;
  transition: border-color 0.15s;
}

.model-item:hover {
  border-color: rgba(47, 123, 255, 0.3);
}

.model-item:last-child {
  margin-bottom: 0;
}

.model-info {
  flex: 1;
  min-width: 0;
}

.model-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-size: 14px;
  font-weight: 600;
  color: #0a0a0a;
}

.default-tag {
  font-size: 11px;
}

.model-id {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 2px;
  font-family: monospace;
}

.model-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 12px;
}

.tutorial-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
}

.tutorial-modal {
  margin: 0 16px;
  width: 100%;
  max-width: 480px;
  overflow: hidden;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.tutorial-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 0.667px solid rgba(111, 126, 153, 0.12);
}

.tutorial-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tutorial-icon-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: #2563eb;
  color: #fff;
}

.tutorial-title {
  font-size: 14px;
  font-weight: 600;
  color: #0a0a0a;
  margin: 0;
}

.tutorial-subtitle {
  font-size: 12px;
  color: #6b7280;
  margin: 2px 0 0;
}

.tutorial-close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.tutorial-close-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #111827;
}

.tutorial-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tutorial-step {
  display: flex;
  gap: 12px;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  background: #f3f4f6;
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
}

.step-content {
  flex: 1;
  padding-top: 2px;
}

.step-text {
  font-size: 14px;
  line-height: 1.6;
  color: #4b5563;
  margin: 0;
}

.step-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
  text-decoration: none;
  transition: color 0.15s;
}

.step-link:hover {
  color: #111827;
  text-decoration: underline;
}

.tutorial-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
  border-top: 0.667px solid rgba(111, 126, 153, 0.12);
  margin-top: 4px;
}

.tutorial-ok-btn {
  padding: 8px 20px;
  border-radius: 10px;
  border: none;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.tutorial-ok-btn:hover {
  background: #1d4ed8;
}

.add-provider-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 16, 30, 0.46);
}

.add-provider-modal {
  margin: 0 16px;
  width: 100%;
  max-width: 672px;
  overflow: hidden;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.97);
  border: 0.667px solid rgba(255, 255, 255, 0.22);
  box-shadow: rgba(15, 32, 66, 0.14) 0px 14px 34px 0px;
}

.add-provider-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 24px;
}

.add-provider-title {
  font-size: 20px;
  font-weight: 600;
  color: #0a0a0a;
  margin: 0;
}

.add-provider-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 4px 0 0;
}

.add-provider-close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.add-provider-close-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #111827;
}

.add-provider-divider {
  height: 0.667px;
  background: rgba(111, 126, 153, 0.12);
}

.add-provider-body {
  padding: 16px 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.add-provider-warning {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  color: #b45309;
}

.add-provider-warning svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.add-provider-warning span {
  font-size: 12px;
  line-height: 1.6;
}

.add-provider-field {
  display: flex;
  flex-direction: column;
}

.add-provider-label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #0a0a0a;
}

.add-provider-select-wrap {
  position: relative;
}

.add-provider-select {
  width: 100%;
  cursor: pointer;
  appearance: none;
  padding: 10px 32px 10px 12px;
  border-radius: 16px;
  border: 0.667px solid transparent;
  background: rgba(255, 255, 255, 0.86);
  font-size: 14px;
  color: #0a0a0a;
  outline: none;
  transition: border-color 0.15s;
}

.add-provider-select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.add-provider-select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-provider-input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 16px;
  border: 0.667px solid transparent;
  background: rgba(255, 255, 255, 0.86);
  font-size: 14px;
  color: #0a0a0a;
  outline: none;
  transition: border-color 0.15s;
}

.add-provider-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.add-provider-input::placeholder {
  color: #9ca3af;
}

.add-provider-input-mono {
  font-family: monospace;
}

.add-provider-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
}

.add-provider-cancel-btn {
  padding: 6px 12px;
  border-radius: 16px;
  border: none;
  background: rgba(255, 255, 255, 0.94);
  color: #0a0a0a;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.add-provider-cancel-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.add-provider-submit-btn {
  padding: 6px 12px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  box-shadow: 0 8px 20px rgba(47, 123, 255, 0.24);
}

.add-provider-submit-btn:hover {
  opacity: 0.9;
  box-shadow: 0 8px 24px rgba(47, 123, 255, 0.36);
}
</style>
