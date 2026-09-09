<template>
  <AppLayout>
    <div class="ep-page">

      <!-- 顶部布局：项目浮标 + 胶囊 + 右上操作（创作 / 导演两种模式共用） -->

      <!-- 左上项目浮标（fixed） -->
      <div class="ep-project-badge">
        <div class="ep-project-badge-inner">
          <div class="ep-project-badge-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
          </div>
          <span class="ep-project-badge-name">{{ projectTitle || '未命名项目' }}</span>
        </div>
      </div>

      <!-- 顶部胶囊（fixed 居中） -->
      <div class="ep-capsule-float">
        <div class="ep-capsule-inner">
          <!-- 故事 Tab：仅创作模式 -->
          <button
            v-if="!isDirectorMode"
            class="ep-capsule-item"
            :class="{ 'ep-capsule-item-active': activeTab === 'story' }"
            @click="onTabClick('story')"
          >
            <span class="ep-capsule-label">故事</span>
            <span v-if="activeTab === 'story'" class="ep-capsule-indicator" />
          </button>
          <button
            class="ep-capsule-item"
            :class="{ 'ep-capsule-item-active': activeTab === 'assets' }"
            @click="onTabClick('assets')"
          >
            <span class="ep-capsule-label">资产库</span>
            <span v-if="activeTab === 'assets'" class="ep-capsule-indicator" />
          </button>
          <button
            class="ep-capsule-item"
            :class="{ 'ep-capsule-item-active': activeTab === 'episodes' }"
            @click="onTabClick('episodes')"
          >
            <span class="ep-capsule-label">剧集</span>
            <span v-if="activeTab === 'episodes'" class="ep-capsule-indicator" />
          </button>
        </div>
      </div>

      <!-- 右上操作按钮（fixed） -->
      <div class="ep-top-actions">
        <button
          class="glass-btn-base glass-btn-secondary ep-action-btn"
          title="项目配置"
          @click="settingsVisible = true"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          <span>项目配置</span>
        </button>
        <button
          class="glass-btn-base glass-btn-secondary ep-action-btn"
          :disabled="refreshing"
          title="刷新"
          @click="handleRefresh"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ 'animate-spin': refreshing }"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
        </button>
      </div>

      <!-- 主区：限宽居中（对齐全局模式 .workspace-main） -->
      <main class="ep-main" :class="{ 'ep-main--asset': isDirectorMode && activeTab === 'assets' }">
      <!-- 导演模式：资产库 Tab 内联展示（不走弹框，全手动创建，无故事分析依赖） -->
      <div v-if="isDirectorMode && activeTab === 'assets'" class="ep-asset-inline">
        <ProjectAssetLibrary :project-id="projectId" show-sections-when-empty />
      </div>

      <!-- 剧集 Tab / 全局模式：剧集列表/Loading/空状态 -->
      <template v-else>
      <!-- Loading -->
      <div v-if="loading" class="ep-loading">
        <div class="ep-spinner" />
        <p>加载剧集列表...</p>
      </div>

      <!-- 空状态（仅小说模式；导演模式直接走列表，含尾部新增卡片） -->
      <div v-else-if="episodes.length === 0 && !isDirectorMode" class="ep-empty">
        <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.35">
          <rect width="20" height="14" x="2" y="7" rx="2"/><path d="m2 7 8.7-5a2 2 0 0 1 2.6 0L22 7"/><circle cx="12" cy="14" r="3"/>
        </svg>
        <p>暂无剧集数据</p>
        <span>完成故事分析后将自动生成剧集</span>
      </div>

      <!-- 剧集列表 -->
      <div v-else class="ep-list">
        <div v-for="ep in episodes" :key="ep.id" class="ep-card glass-surface" @click="goToStoryboard(ep)">
          <div class="ep-card-hover-overlay" />
          <!-- 右上角更多操作（仅导演模式）：编辑 / 删除。hover 触发，鼠标移开自动隐藏 -->
          <el-dropdown
            v-if="isDirectorMode"
            class="ep-card-corner-dd"
            popper-class="ep-card-menu-popper"
            trigger="hover"
            placement="bottom-end"
            :hide-on-click="true"
            @command="onCardMenuCommand($event, ep)"
            @click.stop
          >
            <button
              type="button"
              class="ep-card-corner-btn"
              title="更多操作"
              aria-label="更多操作"
              :disabled="Boolean(savingEpId === ep.id || deletingEpId === ep.id)"
              @click.stop
            >
              <span v-if="savingEpId === ep.id || deletingEpId === ep.id" class="ep-btn-spinner" style="width:13px;height:13px;border-width:2px;margin:0;" />
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/></svg>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                  <span>编辑</span>
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>
                  <span>删除</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div class="ep-card-body">
            <!-- 左侧首帧图片区域 -->
            <div class="ep-card-cover">
              <img
                v-if="ep.cover_url"
                :src="ep.cover_url"
                alt="首帧"
                class="ep-cover-img"
              />
              <div v-else class="ep-cover-placeholder">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <rect width="20" height="14" x="2" y="5" rx="2" />
                  <polygon points="10 9 15 12 10 15" />
                </svg>
                <span>暂无视频</span>
              </div>
            </div>
            <!-- 右侧信息区域 -->
            <div class="ep-card-info">
              <div class="ep-card-top">
                <span class="ep-number">第 {{ ep.episode_number }} 集<template v-if="ep.title">: {{ ep.title }}</template></span>
                <span v-if="!isDirectorMode" class="ep-status" :class="`eps-${ep.status}`">{{ epStatusLabel(ep.status) }}</span>
              </div>
              <p v-if="ep.outline" class="ep-outline">{{ ep.outline }}</p>

              <div class="ep-card-actions">
                <div class="ep-video-count">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><polygon points="10 9 15 12 10 15"/></svg>
                  <span>{{ ep.video_count || 0 }}</span>
                </div>
                <template v-if="isDirectorMode">
                  <button
                    class="ep-btn ep-btn-accent"
                    @click.stop="goToStoryboard(ep)"
                  >
                    编辑分镜
                  </button>
                </template>
                <template v-else-if="showActions(ep)">
                  <button
                    class="ep-btn ep-btn-ghost"
                    :disabled="submittingEpId === ep.id"
                    @click.stop="handleGenerateScript(ep)"
                  >
                    <span v-if="submittingEpId === ep.id" class="ep-btn-spinner" />
                    重新生成
                  </button>
                  <button
                    class="ep-btn ep-btn-accent"
                    @click.stop="goToStoryboard(ep)"
                  >
                    进入成片
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
        <!-- 新增剧集卡片（导演模式，列表末尾） -->
        <div
          v-if="isDirectorMode"
          class="ep-create-card glass-surface"
          :class="{ 'is-creating': creating }"
          @click="handleCreateEpisode"
        >
          <div class="ep-create-icon-wrap">
            <span v-if="creating" class="ep-btn-spinner" />
            <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14" /><path d="M12 5v14" /></svg>
          </div>
          <span class="ep-create-text">新增剧集</span>
        </div>
      </div>
      </template>
      </main>
    </div>

    <!-- 新增/编辑剧集弹框（导演模式专属） -->
    <el-dialog
      v-model="editDialogVisible"
      width="520px"
      align-center
      :show-close="true"
      class="ep-edit-dialog"
      :title="editingEp ? `编辑第 ${editingEp.episode_number} 集` : '新增剧集'"
    >
      <el-form label-position="top" class="ep-edit-form" @submit.prevent>
        <el-form-item label="剧集标题">
          <el-input
            v-model="editForm.title"
            placeholder="给这一集起个名字"
            maxlength="100"
            show-word-limit
            clearable
          />
        </el-form-item>
        <el-form-item label="剧情大纲">
          <el-input
            v-model="editForm.outline"
            type="textarea"
            :rows="5"
            placeholder="简单描述这一集要演什么，留空也行"
            maxlength="2000"
            show-word-limit
            resize="vertical"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="ep-edit-footer">
          <button class="glass-btn-base glass-btn-secondary" @click="editDialogVisible = false">取消</button>
          <button
            class="glass-btn-base glass-btn-primary"
            :disabled="editSaving"
            @click="saveEditDialog"
          >
            {{ editSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 项目配置抽屉（复用工作区组件，两种模式共用） -->
    <ProjectSettingsDrawer
      v-model:visible="settingsVisible"
      :project-id="projectId"
    />

    <ConfirmDialog
      v-model="confirmVisible"
      title="确认重新生成"
      message="重新生成将覆盖之前已经生成的分镜脚本，是否确定重新生成？"
      confirm-text="确定"
      @confirm="handleGenerateScriptConfirm"
    />

    <!-- 删除剧集确认（与资产库删除弹框同款 glass 风格） -->
    <ConfirmDialog
      :model-value="!!deleteEpisodeTarget"
      type="danger"
      title="删除剧集"
      :message="deleteEpisodeTarget ? `确定删除「第 ${deleteEpisodeTarget.episode_number} 集${deleteEpisodeTarget.title ? ': ' + deleteEpisodeTarget.title : ''}」？关联的分镜将一并清理，操作不可恢复。` : ''"
      confirm-text="删除"
      cancel-text="取消"
      @confirm="confirmDeleteEpisodeDialog"
      @cancel="deleteEpisodeTarget = null"
    />
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '@/layout/AppLayout.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ProjectAssetLibrary from '@/views/Workspace/components/ProjectAssetLibrary/ProjectAssetLibrary.vue'
import ProjectSettingsDrawer from '@/views/Workspace/components/ProjectSettingsDrawer.vue'
import { getEpisodes, createEpisode, deleteEpisode, updateEpisode } from '@/api/episode'
import { getProjectDetail } from '@/api/project'
import { generateScript as apiGenerateScript } from '@/api/video'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/store/user'
import { useProjectAssetWs } from '@/composables/useProjectAssetWs'
import { WSEventType, ScriptTaskStatus } from '@/constants/ws'

const props = defineProps({ projectId: { type: String, required: true } })
const route = useRoute()
const router = useRouter()
const ws = useWebSocket()
const handleProjectAssetEvent = useProjectAssetWs(() => props.projectId)

const loading = ref(false)
const episodes = ref([])
const submittingEpId = ref(null)
const projectConfig = ref(null)
const projectTitle = ref('')
const creating = ref(false)
const deletingEpId = ref(null)

// 剧集信息编辑弹框（导演模式专属，支持改标题和剧情大纲）
const editDialogVisible = ref(false)
const editingEp = ref(null)
const editForm = ref({ title: '', outline: '' })
const editSaving = ref(false)
const savingEpId = ref(null)

// 项目配置抽屉
const settingsVisible = ref(false)
const refreshing = ref(false)

const isDirectorMode = computed(() => projectConfig.value?.mode === 'director')

// 顶部胶囊 Tab：
// - 导演模式：资产库（内联）/ 剧集，默认资产库
// - 创作模式：故事 / 资产库 / 剧集，故事与资产库点击跳转到工作区页，默认剧集
const activeTab = ref(null)

watch(isDirectorMode, (isDir) => {
  if (activeTab.value) return
  if (isDir) {
    const persisted = sessionStorage.getItem(`ep-tab-${props.projectId}`)
    activeTab.value = persisted === 'episodes' ? 'episodes' : 'assets'
  } else {
    activeTab.value = 'episodes'
  }
}, { immediate: true })

function onTabClick(tab) {
  if (isDirectorMode.value) {
    activeTab.value = tab
    sessionStorage.setItem(`ep-tab-${props.projectId}`, tab)
    return
  }
  // 创作模式：故事 / 资产库 跳转到工作区页（项目工作区即故事 + 资产库）；剧集留在当前页
  if (tab === 'episodes') {
    activeTab.value = 'episodes'
    sessionStorage.setItem(`ep-tab-${props.projectId}`, 'episodes')
  } else {
    router.push(`/workspace/${props.projectId}`)
  }
}

function epStatusLabel(status) {
  const map = {
    pending: '待生成', generating: '生成中',
    completed: '生成完成', failed: '生成失败',
  }
  return map[status] || status
}

async function fetchEpisodes(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    const res = await getEpisodes(props.projectId)
    episodes.value = res || []
  } catch {
    if (showLoading) episodes.value = []
  } finally {
    if (showLoading) loading.value = false
  }
}

async function handleRefresh() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await Promise.all([fetchEpisodes(false), loadProjectConfig()])
  } finally {
    refreshing.value = false
  }
}

function showActions(ep) {
  return ['completed', 'failed'].includes(ep.status)
}

const confirmVisible = ref(false)
const confirmTarget = ref(null)
// 删除剧集确认弹框（与资产库删除弹框同款 ConfirmDialog）
const deleteEpisodeTarget = ref(null)

async function handleGenerateScript(ep) {
  confirmTarget.value = ep
  confirmVisible.value = true
}

async function handleGenerateScriptConfirm() {
  const ep = confirmTarget.value
  if (!ep) return
  submittingEpId.value = ep.id
  try {
    await apiGenerateScript(props.projectId, ep.id)
    ep.status = 'generating'
    ElMessage.success(`第 ${ep.episode_number} 集分镜生成任务已提交`)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    submittingEpId.value = null
  }
}

function goToStoryboard(ep) {
  router.push({
    path: `/workspace/${props.projectId}/episodes/${ep.id}/storyboard`,
    query: { episodeNumber: ep.episode_number, episodeTitle: ep.title || '' },
  })
}

async function handleCreateEpisode() {
  // 创建中或保存中时忽略点击，避免重复触发
  if (creating.value || editSaving.value) return
  // 打开新增弹框（复用编辑弹框，editingEp 为 null 表示新增）
  openCreateDialog()
}

function openCreateDialog() {
  editingEp.value = null
  editForm.value = { title: '', outline: '' }
  editDialogVisible.value = true
}

async function handleDeleteEpisode(ep) {
  deletingEpId.value = ep.id
  try {
    await deleteEpisode(props.projectId, ep.id)
    ElMessage.success(`第 ${ep.episode_number} 集已删除`)
    await fetchEpisodes(false)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    deletingEpId.value = null
  }
}

// 右上角三点菜单：编辑 / 删除
function onCardMenuCommand(cmd, ep) {
  if (cmd === 'edit') openEditDialog(ep)
  else if (cmd === 'delete') confirmDeleteEpisode(ep)
}

function confirmDeleteEpisode(ep) {
  deleteEpisodeTarget.value = ep
}

async function confirmDeleteEpisodeDialog() {
  const ep = deleteEpisodeTarget.value
  if (!ep) return
  deleteEpisodeTarget.value = null
  await handleDeleteEpisode(ep)
}

// 编辑信息弹框
function openEditDialog(ep) {
  editingEp.value = ep
  editForm.value = {
    title: ep.title || '',
    outline: ep.outline || '',
  }
  editDialogVisible.value = true
}

async function saveEditDialog() {
  const ep = editingEp.value
  const newTitle = editForm.value.title.trim()
  const newOutline = editForm.value.outline.trim()
  // 编辑模式：没有任何改动直接关闭
  if (ep && newTitle === (ep.title || '') && newOutline === (ep.outline || '')) {
    editDialogVisible.value = false
    return
  }
  editSaving.value = true
  try {
    if (ep) {
      // 编辑：只传变更字段
      const payload = {}
      if (newTitle !== (ep.title || '')) payload.title = newTitle
      if (newOutline !== (ep.outline || '')) payload.outline = newOutline
      const res = await updateEpisode(props.projectId, ep.id, payload)
      if (res) {
        ep.title = res.title ?? newTitle
        ep.outline = res.outline ?? newOutline
      }
      ElMessage.success('已保存')
    } else {
      // 新增
      creating.value = true
      await createEpisode(props.projectId, { title: newTitle, outline: newOutline })
      ElMessage.success('已新增剧集')
      await fetchEpisodes(false)
    }
    editDialogVisible.value = false
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    editSaving.value = false
    savingEpId.value = null
    creating.value = false
  }
}

async function loadProjectConfig() {
  try {
    const res = await getProjectDetail(props.projectId)
    projectConfig.value = res?.config || null
    projectTitle.value = res?.title || ''
  } catch {
    projectConfig.value = null
    projectTitle.value = ''
  }
}

// WebSocket
let removeWsListener = null

function setupWebSocket() {
  const userStore = useUserStore()
  const userId = userStore.userInfo.value?.id
  if (!userId) return

  const handleEvent = async (event) => {
    if (event.project_id && event.project_id !== props.projectId) return

    // 委托处理项目资产库相关事件（批量同步、生成进度、自动同步）
    await handleProjectAssetEvent(event)

    if (event.event_type === WSEventType.SCRIPT_PROGRESS) {
      const d = event.data || {}
      const epNumber = d.episode_number
      if (!epNumber) return

      const ep = episodes.value.find(e => e.episode_number === epNumber)
      if (!ep) {
        console.warn('[EpisodePage] 未找到 episode_number=', epNumber)
        return
      }

      if (d.status === ScriptTaskStatus.GENERATING) {
        ep.status = 'generating'
      } else if (d.status === ScriptTaskStatus.COMPLETED) {
        ep.status = 'completed'
      } else if (d.status === ScriptTaskStatus.FAILED) {
        ep.status = 'failed'
      }
    }
  }

  removeWsListener = ws.onEvent(handleEvent)
  ws.connect(userId)
}

onMounted(async () => {
  await Promise.all([fetchEpisodes(), loadProjectConfig()])
  setupWebSocket()
})

onUnmounted(() => {
  if (removeWsListener) removeWsListener()
})
</script>

<style scoped>
.ep-page {
  /* 减去 AppLayout 顶部 sticky 导航 4rem，否则 body 会出现多余滚动条 */
  min-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
  background: var(--glass-bg-canvas);
}

/* 主区：剧集列表铺满；资产库在自身容器内限宽居中 */
.ep-main {
  flex: 1;
  position: relative;
  padding: 7rem 1.5rem 4rem;
  width: 100%;
}

/* 资产库 Tab 下减小顶部留白，对齐全局模式 .workspace-main 的 5rem */
.ep-main--asset {
  padding-top: 5rem;
}

/* 左上项目浮标（fixed，对齐 .project-badge） */
.ep-project-badge {
  position: fixed;
  top: 5rem;
  left: 1.5rem;
  z-index: 40;
}
.ep-project-badge-inner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 1.5rem;
  background: var(--glass-bg-surface-strong, #fff);
  border: 1px solid var(--glass-stroke-soft, rgba(111, 126, 153, 0.16));
  box-shadow: var(--glass-shadow-sm, 0 1px 3px rgba(15, 23, 42, 0.04));
  backdrop-filter: blur(var(--glass-blur-lg, 12px));
  -webkit-backdrop-filter: blur(var(--glass-blur-lg, 12px));
}
.ep-project-badge-icon {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  background: var(--glass-bg-muted, rgba(244, 247, 252, 0.6));
  color: var(--glass-tone-info-fg, #2f7bff);
  flex-shrink: 0;
}
.ep-project-badge-name {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--glass-text-primary, #0a0a0a);
}

/* 导演模式：顶部胶囊（fixed 居中，对齐 .capsule-nav） */
.ep-capsule-float {
  position: fixed;
  top: 5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 40;
}
.ep-capsule-inner {
  display: flex;
  border-radius: 9999px;
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(24px) saturate(1.6);
  -webkit-backdrop-filter: blur(24px) saturate(1.6);
  border: 1px solid rgba(255, 255, 255, 0.45);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.06),
    0 1.5px 6px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}
.ep-capsule-item {
  position: relative;
  display: flex;
  min-height: 52px;
  align-items: center;
  gap: 0.25rem;
  padding: 0.875rem 1.5rem 1rem;
  background: none;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease-out;
}
.ep-capsule-item-active {
  color: var(--glass-tone-info-fg, #2f7bff);
  cursor: default;
}
.ep-capsule-item:not(.ep-capsule-item-active) {
  color: var(--glass-text-tertiary, #6b7280);
}
.ep-capsule-item:not(.ep-capsule-item-active):hover {
  color: var(--glass-text-primary, #0a0a0a);
}
.ep-capsule-label {
  font-size: 1rem;
  font-weight: 600;
}
.ep-capsule-indicator {
  position: absolute;
  bottom: 0.375rem;
  left: 50%;
  transform: translateX(-50%);
  height: 3px;
  width: 1.5rem;
  border-radius: 9999px;
  background: linear-gradient(to right, var(--glass-accent-from, #2f7bff), var(--glass-accent-to, #5ca8ff));
  box-shadow: 0 2px 8px var(--glass-accent-shadow-soft, rgba(47, 123, 255, 0.24));
}

/* 导演模式：右上操作按钮（fixed，对齐 .workspace-top-actions） */
.ep-top-actions {
  position: fixed;
  top: 6rem;
  right: 1.5rem;
  z-index: 40;
  display: flex;
  gap: 0.75rem;
}
.ep-action-btn {
  padding: 0.75rem 1rem;
  border-radius: 1.5rem;
  font-size: 0.875rem;
  gap: 0.375rem;
}

/* 导演模式：资产库 Tab 内联展示容器（限宽 56rem 居中，对齐全局模式） */
.ep-asset-inline {
  max-width: 56rem;
  margin: 1.5rem auto 0;
}


.ep-create-card {
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
  min-height: 8rem;
  border-radius: var(--glass-radius, 14px);
  background: linear-gradient(135deg, rgba(47,123,255,0.05), rgba(92,168,255,0.05), rgba(47,123,255,0.06));
  transition: all 0.3s;
}
.ep-create-card:hover {
  background: linear-gradient(135deg, rgba(47,123,255,0.1), rgba(92,168,255,0.1), rgba(47,123,255,0.12));
  border-color: rgba(47, 123, 255, 0.3);
}
.ep-create-card.is-creating {
  cursor: progress;
  opacity: 0.7;
}
.ep-create-card .ep-btn-spinner {
  width: 24px;
  height: 24px;
  border-width: 3px;
  border-top-color: #fff;
  border-left-color: rgba(255,255,255,0.4);
  border-right-color: rgba(255,255,255,0.4);
  border-bottom-color: rgba(255,255,255,0.4);
}
.ep-create-icon-wrap {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, var(--glass-accent-from), var(--glass-accent-to));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px var(--glass-accent-shadow-soft);
  transition: all 0.3s;
}
.ep-create-card:hover .ep-create-icon-wrap {
  transform: scale(1.1);
  box-shadow: 0 6px 16px var(--glass-accent-shadow-strong);
}
.ep-create-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--glass-text-secondary);
  transition: color 0.3s;
}
.ep-create-card:hover .ep-create-text {
  color: var(--glass-text-primary);
}

.ep-loading, .ep-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 0.75rem;
  color: #9ca3af;
}
.ep-spinner {
  width: 32px; height: 32px;
  border: 3px solid rgba(99,102,241,0.15);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: ep-spin 0.8s linear infinite;
}
.ep-empty p { margin: 0; font-size: 0.95rem; color: #4b5563; }
.ep-empty span { font-size: 0.85rem; }

.ep-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.ep-card {
  position: relative;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s;
}
.ep-card:hover {
  border-color: rgba(47, 123, 255, 0.3);
}

.ep-card-hover-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(47,123,255,0.05), rgba(168,85,247,0.05));
  opacity: 0;
  transition: opacity 0.5s;
  pointer-events: none;
  border-radius: inherit;
}
.ep-card:hover .ep-card-hover-overlay {
  opacity: 1;
}

.ep-card-body {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: row;
  padding: 1.25rem;
  gap: 1rem;
}

/* 左侧首帧图片区域 */
.ep-card-cover {
  width: 80px;
  min-width: 80px;
  height: 142px;
  border-radius: 6px;
  overflow: hidden;
  background: rgba(0,0,0,0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ep-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ep-cover-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  width: 100%;
  height: 100%;
  padding: 0.5rem;
  background:
    radial-gradient(circle at 50% 40%, rgba(47, 123, 255, 0.10), transparent 70%),
    linear-gradient(135deg, rgba(226, 232, 240, 0.45), rgba(203, 213, 225, 0.25));
  color: rgba(100, 116, 139, 0.85);
}
.ep-cover-placeholder svg {
  opacity: 0.65;
}
.ep-cover-placeholder span {
  font-size: 0.65rem;
  letter-spacing: 1px;
  color: rgba(100, 116, 139, 0.75);
}

/* 右侧信息区域 */
.ep-card-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ep-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}
.ep-number { font-weight: 700; font-size: 1rem; color: var(--glass-text-primary, #0a0a0a); transition: color 0.2s; }
.ep-card:hover .ep-number { color: var(--glass-tone-info-fg, #2f7bff); }

/* 右上角三点菜单按钮（导演模式专属） */
/* el-dropdown 包裹元素本身是 position: relative，按钮的 absolute 会相对它定位（零尺寸 → 跑到卡片外）。
   所以 absolute 放在 el-dropdown 上，按钮回归普通流。 */
.ep-card-corner-dd {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 5;
}
.ep-card-corner-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: #ffffff;
  color: #6b7280;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  transition: color 0.15s, background 0.15s, border-color 0.15s, box-shadow 0.15s;
}
.ep-card-corner-btn:hover:not(:disabled) {
  color: var(--glass-tone-info-fg, #2f7bff);
  background: rgba(47, 123, 255, 0.08);
  border-color: rgba(47, 123, 255, 0.3);
  box-shadow: 0 2px 6px rgba(47, 123, 255, 0.12);
}
.ep-card-corner-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* 编辑弹框 */
.ep-edit-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 700;
  color: var(--glass-text-primary, #0a0a0a);
  padding-bottom: 6px;
  line-height: 1.4;
}
.ep-edit-form :deep(.el-input__wrapper),
.ep-edit-form :deep(.el-textarea__inner) {
  background: var(--glass-bg-muted, rgba(244, 247, 252, 0.6));
  border-radius: 10px;
  box-shadow: inset 0 0 0 1px var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  transition: box-shadow 0.2s ease;
}
.ep-edit-form :deep(.el-input__wrapper:hover),
.ep-edit-form :deep(.el-textarea__inner:hover) {
  box-shadow: inset 0 0 0 1px var(--glass-stroke-strong, rgba(111, 126, 153, 0.45));
}
.ep-edit-form :deep(.el-input__wrapper.is-focus),
.ep-edit-form :deep(.el-textarea__inner:focus) {
  box-shadow:
    inset 0 0 0 1px var(--glass-stroke-focus, #2f7bff),
    0 0 0 3px var(--glass-focus-ring, rgba(47, 123, 255, 0.16));
  background: var(--glass-bg-surface-strong, #fff);
}
.ep-edit-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.ep-edit-footer .glass-btn-base {
  min-width: 96px;
  padding: 9px 18px;
  font-size: 14px;
  border-radius: 12px;
}
.ep-edit-footer .glass-btn-primary {
  background: linear-gradient(135deg, var(--glass-accent-from, #2f7bff), var(--glass-accent-to, #5ca8ff));
  box-shadow: 0 4px 14px var(--glass-accent-shadow-soft, rgba(47, 123, 255, 0.24));
}
.ep-edit-footer .glass-btn-primary:hover:not(:disabled) {
  filter: brightness(1.08);
  box-shadow: 0 6px 20px var(--glass-accent-shadow-strong, rgba(47, 123, 255, 0.32));
}
.ep-edit-footer .glass-btn-primary:disabled { opacity: 0.55; cursor: not-allowed; filter: grayscale(0.2); }
.ep-status {
  font-size: 0.7rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
}
.ep-status.eps-pending { color: #6b7280; background: rgba(107,114,128,0.1); }
.ep-status.eps-generating { color: #f59e0b; background: rgba(245,158,11,0.1); }
.ep-status.eps-completed { color: #22c55e; background: rgba(34,197,94,0.1); }
.ep-status.eps-failed { color: #ef4444; background: rgba(239,68,68,0.1); }

.ep-outline {
  font-size: 0.85rem;
  color: #4b5563;
  margin: 0 0 1rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ep-card-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: auto;
}
.ep-video-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: #6b7280;
  margin-right: auto;
}
.ep-video-count svg {
  opacity: 0.6;
}
.ep-btn {
  display: inline-flex;
  align-items: center;
  padding: 0.4rem 0.85rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
  white-space: nowrap;
}
.ep-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ep-btn-spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(0,0,0,0.15);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: ep-spin 0.6s linear infinite;
  margin-right: 4px;
}
.ep-btn-ghost {
  background: #fff;
  border-color: rgba(111,126,153,0.2);
  color: #0a0a0a;
}
.ep-btn-ghost:hover:not(:disabled) { border-color: #6366f1; }
.ep-btn-accent {
  background: linear-gradient(135deg, var(--glass-accent-from, #2f7bff), var(--glass-accent-to, #5ca8ff));
  color: #fff;
  border: none;
  box-shadow: 0 4px 14px var(--glass-accent-shadow-soft, rgba(47, 123, 255, 0.24));
}
.ep-btn-accent:hover:not(:disabled) {
  filter: brightness(1.08);
  box-shadow: 0 6px 20px var(--glass-accent-shadow-strong, rgba(47, 123, 255, 0.32));
}

@keyframes ep-spin { to { transform: rotate(360deg); } }
</style>

<style>
/* 编辑弹框（非 scoped：el-dialog teleport 到 body 外） */
.ep-edit-dialog {
  border-radius: 22px !important;
  overflow: hidden;
}
.ep-edit-dialog .el-dialog__header {
  margin: 0;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(111, 126, 153, 0.18);
  font-size: 16px;
  font-weight: 600;
}
.ep-edit-dialog .el-dialog__body { padding: 20px 24px 8px; }
.ep-edit-dialog .el-dialog__footer {
  padding: 12px 24px 20px;
  border-top: 1px solid rgba(111, 126, 153, 0.12);
}

/* 三点菜单 dropdown popper（白卡片风格） */
.ep-card-menu-popper.el-popper {
  width: 104px !important;
  min-width: 0 !important;
  padding: 6px !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(15, 23, 42, 0.04) !important;
}
.ep-card-menu-popper .el-dropdown-menu {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ep-card-menu-popper .el-dropdown-menu__item {
  display: flex !important;
  align-items: center;
  gap: 8px;
  padding: 8px 10px !important;
  margin: 0 !important;
  border-radius: 6px !important;
  font-size: 13px !important;
  font-weight: 500;
  color: #374151 !important;
  background: transparent !important;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
  line-height: 1.2 !important;
}
.ep-card-menu-popper .el-dropdown-menu__item svg {
  flex-shrink: 0;
  color: #6b7280;
  transition: color 0.12s;
}
.ep-card-menu-popper .el-dropdown-menu__item:hover {
  background: rgba(47, 123, 255, 0.08) !important;
  color: var(--glass-tone-info-fg, #2f7bff) !important;
}
.ep-card-menu-popper .el-dropdown-menu__item:hover svg {
  color: var(--glass-tone-info-fg, #2f7bff);
}
/* 删除项：红色调 */
.ep-card-menu-popper .el-dropdown-menu__item[data-command="delete"],
.ep-card-menu-popper .el-dropdown-menu__item:last-child {
  color: #ef3a3a !important;
}
.ep-card-menu-popper .el-dropdown-menu__item:last-child svg {
  color: #ef3a3a !important;
}
.ep-card-menu-popper .el-dropdown-menu__item:last-child:hover {
  background: rgba(239, 68, 68, 0.08) !important;
  color: #dc2626 !important;
}
.ep-card-menu-popper .el-dropdown-menu__item:last-child:hover svg {
  color: #dc2626 !important;
}
/* 分隔线 */
.ep-card-menu-popper .el-dropdown-menu__item--divided {
  margin-top: 4px !important;
  padding-top: 9px !important;
  border-top: 1px solid #f0f0f0 !important;
}
/* 隐藏 dropdown 默认箭头 */
.ep-card-menu-popper .el-popper__arrow::before {
  background: #ffffff !important;
  border-color: #e5e7eb !important;
}

/* 项目资产库弹窗样式已废弃（改为内联展示） */
</style>
