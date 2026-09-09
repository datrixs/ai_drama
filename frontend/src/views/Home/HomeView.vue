<template>
  <AppLayout>
    <div class="home-content" :class="{ 'home-content--sv': activeTab === 'short-video' || activeTab === 'super-resolution' }">
      <!-- Tab 切换 -->
      <div class="home-tabs">
        <div class="home-tab-bar">
          <button
            v-for="opt in tabOptions"
            :key="opt.value"
            class="home-tab-btn"
            :class="{ 'home-tab-active': activeTab === opt.value }"
            @click="activeTab = opt.value"
          >
            <svg v-if="opt.value === 'drama'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="20" height="20" rx="2.5"/><path d="M7 2v20"/><path d="M17 2v20"/><path d="M2 12h20"/></svg>
            <svg v-else-if="opt.value === 'short-video'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>
            <span>{{ opt.label }}</span>
          </button>
        </div>
      </div>

      <!-- 短剧创作 Tab -->
      <template v-if="activeTab === 'drama'">
        <!-- 取景框视觉壳 -->
        <div class="visual-shell">
          <!-- 四角线 -->
          <span class="bracket bracket-tl" />
          <span class="bracket bracket-tr" />
          <span class="bracket bracket-bl" />
          <span class="bracket bracket-br" />

          <!-- REC 指示器 -->
          <span class="rec-indicator">
            <span class="rec-dot" />
            <span class="rec-text">REC</span>
          </span>

          <!-- 打字机标题 -->
          <TypewriterHero title="从灵感到银幕" subtitle="将来视界，让世界看到将来的样子" />

          <!-- 呼吸光晕 -->
          <div class="glow-shell">
            <div class="glow glow-1" />
            <div class="glow glow-2" />
            <div class="glow glow-3" />

            <!-- 输入区域 -->
            <div class="input-area relative z-[1]">
              <div class="story-input-composer glass-surface-elevated">
                <!-- 文本框区 -->
                <div class="input-textarea-wrap">
                  <textarea
                    ref="textareaRef"
                    v-model="novelText"
                    class="glass-textarea-base novel-textarea"
                    placeholder="输入你的故事创意、小说片段或剧本大纲..."
                    rows="3"
                  />
                </div>

                <!-- 工具栏 -->
                <div class="input-toolbar">
                  <div class="toolbar-left">
                    <label class="glass-btn-base glass-btn-soft upload-btn cursor-pointer">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                      上传文件
                      <input type="file" accept=".txt,.docx" style="display:none" :disabled="uploading" @change="handleFileChange" />
                    </label>
                  </div>
                  <div class="toolbar-right">
                    <button
                      class="glass-btn-base ai-write-btn"
                      :disabled="creating"
                      @click="aiWriteOpen = true"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>
                      <span class="ai-write-text">AI 帮我写</span>
                    </button>
                    <button
                      class="glass-btn-base glass-btn-primary create-btn"
                      :disabled="!canCreate"
                      @click="handleCreate"
                    >
                      <span v-if="creating" class="btn-loading" />
                      <template v-else>
                        开始创作
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                      </template>
                    </button>
                  </div>
                </div>

                <!-- 底部提示 -->
                <div v-if="novelText.length > 0 && novelText.length < 20" class="input-footer">
                  <p class="hint-warn-card">
                    故事创意至少需要 20 个字（当前 {{ novelText.length }} 个字）
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 短视频 Tab -->
      <div v-if="activeTab === 'short-video'" class="sv-container">
        <ShortVideoPanel
          ref="shortVideoPanelRef"
          :pickerOpen="showProjectPicker || showAssetCenter"
          @open-project-picker="showProjectPicker = true"
          @open-asset-center="showAssetCenter = true"
        />
      </div>

      <!-- 视频超分 Tab -->
      <div v-if="activeTab === 'super-resolution'" class="sv-container">
        <SuperResolutionPanel ref="superResolutionPanelRef" />
      </div>

      <!-- 最近项目列表 -->
      <RecentProjects v-show="activeTab !== 'short-video' && activeTab !== 'super-resolution'" />

      <!-- AI 帮我写弹窗 -->
      <div v-if="aiWriteOpen" class="glass-overlay" @click.self="closeAiWrite">
        <div class="glass-surface-modal ai-write-modal animate-fadeInDown" @click.stop>
          <div class="ai-write-header">
            <div class="ai-write-header-left">
              <div class="ai-write-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>
              </div>
              <div>
                <h3 class="ai-write-title">AI 创作助手</h3>
                <p class="ai-write-subtitle">输入你的创意，让 AI 帮你生成完整故事</p>
              </div>
            </div>
            <button class="ai-write-close" :disabled="aiWriteLoading" @click="closeAiWrite">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>

          <div class="ai-write-body">
            <label class="ai-write-label">输入你的创意内容</label>
            <textarea
              v-model="aiWritePrompt"
              class="glass-textarea-base ai-write-textarea"
              placeholder="输入关键词、故事大纲或简短创意...&#10;&#10;例如：&#10;• 古代宫廷 复仇 悬疑 女主角&#10;• 第一幕：女主回到京城，暗访旧宅；第二幕：宫廷宴会偶遇仇人之子"
              :disabled="aiWriteLoading"
              rows="6"
            />
            <p class="ai-write-hint" :class="{ 'hint-warn': aiWritePrompt.trim().length > 0 && aiWritePrompt.trim().length < 20 }">
              故事创意至少需要 20 个字（当前 {{ aiWritePrompt.trim().length }} 个字）
            </p>
          </div>

          <div class="ai-write-tip">
            可以输入关键词、故事大纲、创意描述，AI 会根据你的输入扩展生成完整的故事内容
          </div>

          <div class="ai-write-footer">
            <button
              class="ai-write-cancel"
              :disabled="aiWriteLoading"
              @click="closeAiWrite"
            >
              取消
            </button>
            <button
              class="ai-write-start"
              :disabled="!aiWritePrompt.trim() || aiWriteLoading || aiWritePrompt.trim().length < 20"
              @click="handleAiWrite"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>
              <span>{{ aiWriteLoading ? '...' : '开始 AI 创作' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 项目资产库弹窗 -->
      <ProjectAssetPicker
        v-if="showProjectPicker"
        @close="showProjectPicker = false"
        @select="handleProjectAssetSelect"
      />

      <!-- 资产中心弹窗 -->
      <AssetCenterPicker
        v-if="showAssetCenter"
        @close="showAssetCenter = false"
        @select="handleAssetCenterSelect"
      />
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '@/layout/AppLayout.vue'
import SegmentedControl from '@/components/SegmentedControl.vue'
import TypewriterHero from './components/TypewriterHero.vue'
import ShortVideoPanel from './components/ShortVideoPanel.vue'
import SuperResolutionPanel from './components/SuperResolutionPanel.vue'
import ProjectAssetPicker from './components/ProjectAssetPicker.vue'
import AssetCenterPicker from './components/AssetCenterPicker.vue'
import RecentProjects from './components/RecentProjects.vue'
import { useProjectStore } from '@/store/project'
import { useShortVideoStore } from '@/store/shortVideo'
import { useSuperResolutionStore } from '@/store/superResolution'
import { useUserStore } from '@/store/user'
import { useWebSocket } from '@/composables/useWebSocket'
import { uploadNovel } from '@/api/project'
import { aiExpandStory, checkModelConfig } from '@/api/project/analyze'

const router = useRouter()
const projectStore = useProjectStore()
const shortVideoStore = useShortVideoStore()
const superResolutionStore = useSuperResolutionStore()
const userStore = useUserStore()
const ws = useWebSocket()

// Tab 切换
const activeTab = ref('drama')
const tabOptions = [
  { value: 'drama', label: '短剧创作' },
  { value: 'short-video', label: '短视频' },
  { value: 'super-resolution', label: '视频超分' },
]

// 短视频/视频超分 Tab 下锁定外层滚动
watch(activeTab, (tab) => {
  const lockTabs = tab === 'short-video' || tab === 'super-resolution'
  document.body.style.overflow = lockTabs ? 'hidden' : ''
  if (tab === 'short-video') {
    nextTick(() => {
      shortVideoPanelRef.value?.scrollToBottom?.()
    })
  } else if (tab === 'super-resolution') {
    nextTick(() => {
      superResolutionPanelRef.value?.scrollToBottom?.()
    })
  }
}, { immediate: true })

// 资产选择器状态
const showProjectPicker = ref(false)
const showAssetCenter = ref(false)
const shortVideoPanelRef = ref(null)
const superResolutionPanelRef = ref(null)

// 短剧创作相关状态
const novelText = ref('')
const creating = ref(false)
const uploading = ref(false)
const aiWriteOpen = ref(false)
const aiWriteLoading = ref(false)
const aiWritePrompt = ref('')
const textareaRef = ref(null)

watch(novelText, () => {
  nextTick(autoResizeTextarea)
})

function autoResizeTextarea() {
  const el = textareaRef.value
  if (!el) return
  const maxHeight = window.innerHeight * 0.5
  el.style.height = 'auto'
  const target = Math.min(el.scrollHeight, maxHeight)
  el.style.height = target + 'px'
  el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'
}

const canCreate = computed(() => novelText.value.length >= 20 && !creating.value)
const fileName = ref('')

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const res = await uploadNovel(file)
    novelText.value = res.extracted_text
    fileName.value = file.name
    ElMessage.success(`文件解析成功，共 ${res.char_count} 个字符`)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function handleCreate() {
  if (!canCreate.value || creating.value) return
  creating.value = true
  try {
    await checkModelConfig()
    const payload = { novel_text: novelText.value }
    if (fileName.value) {
      payload.file_name = fileName.value
    }
    const res = await projectStore.create(payload)
    router.push(`/workspace/${res.id}?tab=story`)
  } catch {
    // 拦截器已统一弹窗
  } finally {
    creating.value = false
  }
}

function closeAiWrite() {
  if (aiWriteLoading.value) return
  aiWritePrompt.value = ''
  aiWriteOpen.value = false
}

async function handleAiWrite() {
  const prompt = aiWritePrompt.value.trim()
  if (!prompt || aiWriteLoading.value || prompt.length < 20) return
  aiWriteLoading.value = true
  try {
    const data = await aiExpandStory(prompt)
    if (data.expanded_text) {
      novelText.value = data.expanded_text
      aiWriteOpen.value = false
      aiWritePrompt.value = ''
      ElMessage.success('AI 故事生成成功')
    } else {
      ElMessage.error('AI 故事生成失败')
    }
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    aiWriteLoading.value = false
  }
}

// 资产选择回调
function handleProjectAssetSelect(assets) {
  let addedCount = 0
  let dupCount = 0
  for (const asset of assets) {
    const type = asset.asset_type || 'image'
    const added = shortVideoStore.addReference(type, {
      url: asset.image_url || asset.audio_url || asset.url,
      name: asset.name,
      thumbnail_url: asset.thumbnail_url || null,
      volc_asset_id: asset.volc_asset_id || null,
      duration: asset.duration || null,
    })
    if (added) {
      addedCount++
    } else {
      dupCount++
    }
  }
  if (dupCount > 0) {
    ElMessage.warning(`${dupCount} 个资产已存在于引用区，已跳过`)
  }
}

function handleAssetCenterSelect(assets) {
  let addedCount = 0
  let dupCount = 0
  for (const asset of assets) {
    const type = asset.asset_type || 'image'
    const added = shortVideoStore.addReference(type, {
      url: asset.image_url || asset.audio_url || asset.url,
      name: asset.name,
      thumbnail_url: asset.thumbnail_url || null,
      volc_asset_id: asset.volc_asset_id || null,
      duration: asset.duration || null,
    })
    if (added) {
      addedCount++
    } else {
      dupCount++
    }
  }
  if (dupCount > 0) {
    ElMessage.warning(`${dupCount} 个资产已存在于引用区，已跳过`)
  }
}

// WebSocket 连接与事件监听
let removeWsListener = null

onMounted(async () => {
  if (!userStore.loaded.value) {
    await userStore.fetchUser()
  }
  const userId = userStore.userInfo.value?.id
  if (userId) {
    removeWsListener = ws.onEvent((event) => {
      shortVideoStore.handleWsEvent(event)
      superResolutionStore.handleWsEvent(event)
    })
    ws.connect(userId)
  }
})

onUnmounted(() => {
  if (removeWsListener) {
    removeWsListener()
    removeWsListener = null
  }
  // 恢复 body 滚动，防止残留 overflow: hidden
  document.body.style.overflow = ''
})
</script>

<style scoped>
.home-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 2rem;
  padding-bottom: 3rem;
  padding-left: 1rem;
  padding-right: 1rem;
  max-width: 64rem;
  margin: 0 auto;
  width: 100%;
}

.home-tabs {
  margin-bottom: 1.5rem;
  display: flex;
  justify-content: center;
}

.home-tab-bar {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.home-tab-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 36px;
  padding: 0 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.45);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.home-tab-btn:hover:not(.home-tab-active) {
  color: rgba(0, 0, 0, 0.7);
  background: rgba(255, 255, 255, 0.6);
}

.home-tab-active {
  color: #fff;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.home-tab-active:hover {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
}

.sv-container {
  width: 100%;
  max-width: 64rem;
  flex: 1;
  min-height: 0;
}

.home-content--sv {
  height: calc(100vh - 4rem);
  padding-bottom: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 取景框 */
.visual-shell {
  width: 100%;
  position: relative;
  padding: 1.25rem;
}

.bracket {
  position: absolute;
  width: 1.25rem;
  height: 1.25rem;
  border-color: var(--glass-text-primary);
  pointer-events: none;
  z-index: 10;
  animation: bracket-breathe 8s ease-in-out infinite;
}

.bracket-tl { top: 0; left: 0; border-top: 1px solid; border-left: 1px solid; }
.bracket-tr { top: 0; right: 0; border-top: 1px solid; border-right: 1px solid; }
.bracket-bl { bottom: 0; left: 0; border-bottom: 1px solid; border-left: 1px solid; }
.bracket-br { bottom: 0; right: 0; border-bottom: 1px solid; border-right: 1px solid; }

/* REC 指示器 */
.rec-indicator {
  position: absolute;
  top: 0.5rem;
  right: 1.75rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  z-index: 10;
  animation: bracket-breathe 2s ease-in-out infinite;
}

.rec-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 4px rgba(239, 68, 68, 0.7);
}

.rec-text {
  font-size: 8px;
  font-family: monospace;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: rgba(239, 68, 68, 0.7);
}

/* 呼吸光晕 */
.glow-shell {
  width: 100%;
  position: relative;
}

.glow {
  position: absolute;
  border-radius: 48px;
  pointer-events: none;
}

.glow-1 {
  inset: -40px;
  border-radius: 48px;
  background: radial-gradient(ellipse 80% 60% at 30% 40%, rgba(6, 182, 212, 0.4), transparent 70%);
  animation: breathe-drift-1 8s ease-in-out infinite;
  filter: blur(30px);
}

.glow-2 {
  inset: -40px;
  border-radius: 48px;
  background: radial-gradient(ellipse 70% 80% at 70% 60%, rgba(139, 92, 246, 0.35), transparent 70%);
  animation: breathe-drift-2 10s ease-in-out infinite;
  filter: blur(35px);
}

.glow-3 {
  inset: -48px;
  border-radius: 56px;
  background: radial-gradient(ellipse 60% 50% at 50% 50%, rgba(59, 130, 246, 0.3), transparent 70%);
  animation: breathe-drift-3 12s ease-in-out infinite;
  filter: blur(40px);
}

/* 输入区域 */
.input-area {
  width: 100%;
}

.story-input-composer {
  border-radius: 1rem;
}

.input-textarea-wrap {
  padding: 1.5rem 1.5rem 1rem;
}

.novel-textarea {
  width: 100%;
  min-height: 4.5rem;
  max-height: 50vh;
  resize: none;
  padding: 1.25rem 1.25rem 0.75rem;
  font-size: 1rem;
  font-family: inherit;
  line-height: 1.5;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  outline: none;
  border-radius: 0;
  color: var(--glass-text-primary);
  vertical-align: top;
  transition: height 200ms ease-out;
  overflow-y: hidden;
}

.novel-textarea::placeholder {
  color: var(--glass-text-tertiary);
  opacity: 0.85;
  font-family: inherit;
}

.novel-textarea:focus {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  outline: none;
}

.input-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 1.25rem 1rem;
  overflow-x: auto;
  min-height: 2.75rem;
  justify-content: space-between;
}

.toolbar-left {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 0.5rem;
  min-width: max-content;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
  min-width: max-content;
}

.input-footer {
  padding: 0 1.5rem 1rem;
}

.hint-warn-card {
  border-radius: 0.75rem;
  border: 1px solid rgba(245, 158, 11, 0.2);
  background: rgba(245, 158, 11, 0.1);
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  color: #92400e;
}

:root.dark .hint-warn-card {
  color: #fcd34d;
}

.hint-warn { color: #f59e0b; }
.hint-ok { color: var(--glass-tone-success-fg); }

.btn-loading {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.upload-btn {
  height: 40px;
  padding: 0 16px;
  font-size: 14px;
}

/* ===== AI 帮我写按钮 ===== */
.ai-write-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 12px;
  font-size: 14px;
  border: none;
  background: transparent;
  transition: all 0.2s;
  flex-shrink: 0;
}

.create-btn {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  flex-shrink: 0;
}

.create-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-write-btn:hover {
  opacity: 0.8;
}

.ai-write-btn svg {
  color: #7c3aed;
}

.ai-write-text {
  font-weight: 500;
  background: linear-gradient(135deg, #3b82f6, #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ===== AI 写作弹窗 ===== */
.ai-write-modal {
  max-width: 32rem;
  width: 90%;
  padding: 1.5rem;
}

.ai-write-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.ai-write-header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.ai-write-icon-box {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.15));
}

.ai-write-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--glass-text-primary);
}

.ai-write-subtitle {
  font-size: 0.6875rem;
  color: var(--glass-text-tertiary);
}

.ai-write-close {
  background: transparent;
  border: none;
  color: var(--glass-text-tertiary);
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
}

.ai-write-close:hover {
  color: var(--glass-text-secondary);
}

.ai-write-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--glass-text-secondary);
  display: block;
  margin-bottom: 0.5rem;
}

.ai-write-textarea {
  height: 9rem;
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  resize: none;
}

.ai-write-hint {
  margin-top: 0.375rem;
  font-size: 0.6875rem;
  color: var(--glass-text-tertiary);
}

.ai-write-tip {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  color: var(--glass-text-tertiary);
  line-height: 1.5;
  background: linear-gradient(135deg, rgba(59,130,246,0.06), rgba(139,92,246,0.06));
}

.ai-write-footer {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.ai-write-cancel {
  flex: 1;
  padding: 0.625rem;
  font-size: 0.875rem;
  color: var(--glass-text-tertiary);
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: 0.75rem;
  transition: color 0.15s;
}

.ai-write-cancel:hover {
  color: var(--glass-text-secondary);
}

.ai-write-start {
  flex: 1;
  padding: 0.75rem;
  border-radius: 0.75rem;
  color: #fff;
  font-weight: 600;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: none;
  cursor: pointer;
  background: linear-gradient(135deg, #3b82f6, #7c3aed);
  transition: all 0.15s;
}

.ai-write-start:hover:not(:disabled) {
  opacity: 0.9;
}

.ai-write-start:active:not(:disabled) {
  transform: scale(0.98);
}

.ai-write-start:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 短视频页面响应式 ===== */
@media (max-height: 700px) {
  .home-content {
    padding-top: 0.75rem;
    padding-bottom: 0.5rem;
  }
  .home-tabs {
    margin-bottom: 0.5rem;
  }
  .home-content--sv {
    height: calc(100vh - 4rem);
  }
}

@media (max-height: 500px) {
  .home-content--sv {
    height: calc(100vh - 4rem);
  }
}
</style>
