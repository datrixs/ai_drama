<template>
    <div class="vp-page">

      <!-- 顶部工具栏：与主区域三栏对齐（侧栏 / 编辑器 / 预览），按钮右边界天然对齐编辑器右边界 -->
      <div class="vp-top-bar">
        <!-- 左：logo + 返回（对齐 StudioAssetSidebar 宽度 15.5rem） -->
        <div class="vp-top-side">
          <router-link to="/" class="vp-logo" title="返回首页">
            <img src="/pipixia-logo2.png" alt="皮皮虾短剧" class="vp-logo-img" />
          </router-link>
          <button class="vp-back-btn" @click="goBack">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          </button>
        </div>

        <!-- 中：工具栏（对齐编辑器列宽 flex:1），按钮 #actions 在工具栏右侧 -->
        <VideoToolbar
          class="vp-top-editor"
          :total-segments="segments.length"
          :running-count="runningCount"
          :completed-count="completedCount"
          :failed-count="failedCount"
        >
          <template #actions>
            <el-tooltip
              v-if="episodeVideoUrl"
              content="播放整集视频"
              placement="top"
              :show-after="200"
            >
              <button
                class="vp-btn vp-btn-outline vp-btn-sm vp-btn-pill"
                @click="openEpisodeVideo"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
                播放整集
              </button>
            </el-tooltip>
            <el-tooltip
              :content="canConcat ? '将所有片段按顺序拼接为整集视频' : concatDisabledReason"
              placement="top"
              :show-after="200"
            >
              <span class="vp-btn-wrap">
                <button
                  class="vp-btn vp-btn-primary vp-btn-sm"
                  :disabled="!canConcat"
                  @click="handleConcatVideo"
                >
                  {{ concatenating ? '合成中...' : (episodeVideoUrl ? '重新合成' : '合成整集') }}
                </button>
              </span>
            </el-tooltip>
          </template>
        </VideoToolbar>

        <!-- 右：剧集信息（对齐 vp-preview 宽度 22% min 240px） -->
        <div class="vp-top-preview">
          <span class="vp-ep-info">第 {{ episodeNumber }} 集<template v-if="episodeTitle">: {{ episodeTitle }}</template></span>
          <span v-if="episodeStatus" class="vp-ep-tag" :class="`eps-${episodeStatus}`">
            <svg v-if="episodeStatus === 'generating'" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.2-8.6"/></svg>
            <svg v-else-if="episodeStatus === 'completed'" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            <svg v-else-if="episodeStatus === 'failed'" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            {{ episodeStatusLabel }}
          </span>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="vp-center-state">
        <div class="vp-spinner" />
        <p>加载分镜数据...</p>
      </div>

      <!-- 空状态：仅全局（小说）模式下、脚本未生成时分流到这里。导演模式自动新建片段，不会进入此分支 -->
      <div v-else-if="!isDirectorMode && segments.length === 0" class="vp-center-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.35">
          <rect x="2" y="2" width="20" height="20" rx="2"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/>
        </svg>
        <p>暂无分镜数据</p>
        <span>请返回剧集列表生成脚本</span>
      </div>

      <!-- 主内容：导演模式始终显示三栏（即使片段为空也会自动新建一个） -->
      <template v-else>
        <div class="vp-main">
          <!-- 左栏：资产侧边栏 -->
          <StudioAssetSidebar
            :characters="projectAssets.characters"
            :locations="projectAssets.locations"
            :props="projectAssets.props"
            @asset-click="openDetail"
            @open-project-assets="assetDialogVisible = true"
          />

          <!-- 中栏：编辑器 -->
          <MultimodalPanelCard
            ref="panelCardRef"
            :project-id="projectId"
            :episode-id="episodeId"
            :segments="segments"
            :active-segment-index="currentIndex"
            :segment-plain-text="currentSegmentText"
            :active-segment="activeSegment"
            :video-form="videoForm"
            :saving-script="savingScript"
            :assets="projectAssets"
            :parse-error="null"
            @save-script="handleSaveScript"
            @generate-video="handleGenerateVideo"
            @cancel-task="handleCancelTask"
            @select-segment="handleSelectSegment"
            @update:segment-plain-text="handleSegmentTextUpdate"
            @update:video-form="handleVideoFormUpdate"
          />

          <!-- 右栏：视频预览 -->
          <div class="vp-preview">
            <div class="vp-preview-inner">
              <!-- 生成中 -->
              <div v-if="activeSegment?._generating" class="vp-gen">
                <div class="vp-gen-rings">
                  <div class="vp-gen-ring-outer" />
                  <div class="vp-gen-ring-inner" />
                  <div class="vp-gen-dot" />
                </div>
                <div class="vp-gen-text">
                  <span class="vp-gen-label">视频生成中...</span>
                  <span class="vp-gen-hint">{{ activeSegment._progress || 0 }}%</span>
                </div>
                <div class="vp-gen-bar"><div class="vp-gen-shimmer" /></div>
              </div>

              <!-- 生成失败 -->
              <div v-else-if="activeSegment?.status === 'failed'" class="vp-preview-failed">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                <span class="vp-failed-title">视频生成失败</span>
                <span class="vp-failed-msg">{{ activeSegment.gen_error || '未知错误' }}</span>
              </div>

              <!-- 已完成 -->
              <video v-else-if="activeSegment?.video_url" :src="activeSegment.video_url"
                controls playsinline preload="auto" :key="activeSegment.video_url" class="vp-video" />

              <!-- 空 -->
              <div v-else class="vp-preview-empty">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.4">
                  <polygon points="23 7 16 12 23 17"/><rect x="1" y="5" width="15" height="14" rx="2"/>
                </svg>
                <span>暂无视频预览</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部：片段切换条 -->
        <StudioSegmentStrip
          :segments="segments"
          :active-index="currentIndex"
          :is-director-mode="isDirectorMode"
          @select="handleSelectSegment"
          @insert-before="(idx) => handleInsertSegment(idx, 'before')"
          @insert-after="(idx) => handleInsertSegment(idx, 'after')"
          @delete="handleDeleteSegment"
        />
      </template>

      <!-- 资产详情弹窗 -->
      <AssetDetailModal :asset="detailAsset" @close="detailAsset = null" />

      <!-- 项目资产库弹窗 -->
      <el-dialog
        v-model="assetDialogVisible"
        width="90%"
        top="3vh"
        :close-on-click-modal="true"
        destroy-on-close
        append-to-body
        class="asset-library-dialog"
      >
        <template #header>
          <div class="ald-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
            <span>项目资产库</span>
          </div>
        </template>
        <ProjectAssetLibrary :project-id="projectId" />
      </el-dialog>

      <ConfirmDialog
        v-model="unsavedConfirmVisible"
        title="未保存修改"
        message="当前片段有未保存的修改，是否保存并继续生成视频？"
        confirm-text="保存并继续"
        @confirm="handleUnsavedConfirm"
      />

      <ConfirmDialog
        v-model="deleteConfirmVisible"
        type="danger"
        title="删除所选片段"
        message="所选片段被删除后，将不可恢复。&#10;&#10;是否确定删除？"
        confirm-text="删除"
        @confirm="confirmDeleteSegment"
      />

      <ConfirmDialog
        v-model="concatConfirmVisible"
        size="large"
        :title="concatDialogTitle"
        :message="concatDialogMessage"
        :confirm-text="concatConfirmText"
        @confirm="confirmConcatVideo"
      />

      <ConcatHistoryDialog
        ref="concatHistoryRef"
        v-model="concatHistoryVisible"
        :project-id="projectId"
        :episode-id="episodeId"
        @play="openPlayer"
      />

      <VideoPlayerDialog
        v-model="playerVisible"
        :url="playerUrl"
        :title="playerTitle"
      />
    </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { getStoryboards, generateStoryboardVideo, insertStoryboard, deleteStoryboard, createStoryboard } from '@/api/storyboard'
import {
  generateMultimodalVideo,
  generateScript as apiGenerateScript,
  updateScriptText,
  cancelVideoTask,
  concatEpisodeVideo,
} from '@/api/video'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/store/user'
import { useProjectAssetWs } from '@/composables/useProjectAssetWs'
import { WSEventType, VideoTaskStatus, ScriptTaskStatus } from '@/constants/ws'
import { getProjectAssets } from '@/api/project/asset'
import { getProjectDetail, getProjectConfig } from '@/api/project'
import VideoToolbar from './components/VideoToolbar.vue'
import StudioAssetSidebar from './components/StudioAssetSidebar.vue'
import MultimodalPanelCard from './components/MultimodalPanelCard.vue'
import StudioSegmentStrip from './components/StudioSegmentStrip.vue'
import AssetDetailModal from './components/AssetDetailModal.vue'
import ConcatHistoryDialog from './components/ConcatHistoryDialog.vue'
import VideoPlayerDialog from './components/VideoPlayerDialog.vue'
import ProjectAssetLibrary from '@/views/Workspace/components/ProjectAssetLibrary/ProjectAssetLibrary.vue'

const props = defineProps({
  projectId: { type: String, required: true },
  episodeId: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()
const ws = useWebSocket()
const handleProjectAssetEvent = useProjectAssetWs(() => props.projectId)

// ============ 项目资产 ============

const projectAssets = ref({ characters: [], locations: [], props: [] })
const projectConfig = ref(null)
const isDirectorMode = computed(() => projectConfig.value?.mode === 'director')

async function fetchProjectAssets() {
  try {
    const res = await getProjectAssets(props.projectId)
    projectAssets.value = {
      characters: res.characters || [],
      locations: res.locations || [],
      props: res.props || [],
    }
  } catch {
    projectAssets.value = { characters: [], locations: [], props: [] }
  }
}

async function loadProjectConfig() {
  try {
    const [detail, cfg] = await Promise.all([
      getProjectDetail(props.projectId),
      getProjectConfig(props.projectId).catch(() => null),
    ])
    projectConfig.value = detail?.config || null
    // 视频参数面板的 ratio 默认取项目配置（合并后 resolved）的 video_ratio
    const ratio = cfg?.resolved?.video_ratio
    if (ratio) videoForm.value.ratio = ratio
  } catch {
    projectConfig.value = null
  }
}

// ============ 状态 ============

const loading = ref(false)
const segments = ref([])
const currentIndex = ref(0)
const generatingScript = ref(false)
const batchGenerating = ref(false)
const concatenating = ref(false)
const concatConfirmVisible = ref(false)
const episodeVideoUrl = ref('')
const concatHistoryVisible = ref(false)
const concatHistoryRef = ref(null)
const playerVisible = ref(false)
const playerUrl = ref('')
const playerTitle = ref('')
const savingScript = ref(false)
const episodeStatus = ref('')
const detailAsset = ref(null)
const panelCardRef = ref(null)
const assetDialogVisible = ref(false)

const userStore = useUserStore()
const currentRegion = computed(() => userStore.userInfo.value?.region || 'domestic')
// 区域 → 默认视频模型；与 backend/app/utils/region.py 保持一致
const REGION_DEFAULT_VIDEO_MODEL = {
  domestic: 'doubao-seedance-2-0-260128',
  overseas: 'dreamina-seedance-2-0-260128',
}

const videoForm = ref({
  model: REGION_DEFAULT_VIDEO_MODEL[currentRegion.value] || 'doubao-seedance-2-0-260128',
  resolution: '720p',
  ratio: '16:9',
  duration: null,
  generate_audio: true,
})

const taskSegmentMap = ref({})
const unsavedConfirmVisible = ref(false)
const dirtySegmentTexts = ref(new Map())
const lastSavedSegmentTexts = ref(new Map())
const deleteConfirmVisible = ref(false)
const pendingDeleteIdx = ref(-1)

// ============ 计算属性 ============

// 当前片段的纯文本：优先取脏数据，否则取 video_prompt
const currentSegmentText = computed(() => {
  const seg = segments.value[currentIndex.value]
  if (!seg) return ''
  const dirty = dirtySegmentTexts.value.get(seg.segment_index)
  if (dirty !== undefined) return dirty
  return seg.video_prompt || ''
})

const episodeNumber = computed(() => route.query.episodeNumber || 1)
const episodeTitle = computed(() => route.query.episodeTitle || '')
const activeSegment = computed(() => segments.value[currentIndex.value] || null)
const hasCompletedVideos = computed(() => segments.value.some(s => s.status === 'video_completed' && s.video_url))

const runningCount = computed(() => segments.value.filter(s => s._generating).length)
const completedCount = computed(() => segments.value.filter(s => s.status === 'video_completed').length)
const failedCount = computed(() => segments.value.filter(s => s.status === 'failed').length)

// 是否可执行整集合成：至少 2 个片段、所有片段 video_completed 且有 video_url、未在合成中
const canConcat = computed(() =>
  segments.value.length >= 2 &&
  segments.value.every(s => s.status === 'video_completed' && s.video_url) &&
  !concatenating.value
)

// 合成按钮禁用时的原因文案
const concatDisabledReason = computed(() => {
  if (concatenating.value) return '合成进行中...'
  if (segments.value.length === 0) return '暂无分镜片段'
  if (segments.value.length < 2) return '至少需要 2 个片段才能合成整集'
  const incomplete = segments.value.filter(s => s.status !== 'video_completed' || !s.video_url).length
  if (incomplete > 0) return `还有 ${incomplete} 个片段未完成视频生成`
  return ''
})

// 合成确认弹框：根据是否已合成过切换文案
const concatDialogTitle = computed(() =>
  episodeVideoUrl.value ? '确认重新合成' : '确认合成整集'
)
const concatDialogMessage = computed(() =>
  episodeVideoUrl.value
    ? '当前剧集已进行过整集合成操作，重新合成将覆盖之前内容，是否确定重新合成？\n（建议您先下载当前整集视频到本地后再进行此操作）'
    : `当前剧集已生成 ${segments.value.length} 个片段，是否确认合成整集视频？`
)
const concatConfirmText = computed(() =>
  episodeVideoUrl.value ? '确认重新合成' : '确认合成'
)

const episodeStatusLabel = computed(() => {
  const map = {
    pending: '待生成', generating: '生成中',
    completed: '生成完成', failed: '生成失败',
  }
  return map[episodeStatus.value] || ''
})

// ============ 数据加载 ============

async function fetchStoryboards() {
  loading.value = true
  try {
    const res = await getStoryboards(props.projectId, props.episodeId)
    segments.value = (res.items || []).map(seg => ({
      ...seg,
      _generating: seg.status === 'video_generating',
      _progress: 0,
      _taskId: null,
    }))
    if (currentIndex.value >= segments.value.length) currentIndex.value = 0
    // 初始化每个片段的已保存文本基线
    lastSavedSegmentTexts.value.clear()
    for (const seg of segments.value) {
      lastSavedSegmentTexts.value.set(seg.segment_index, seg.video_prompt || '')
    }
    // 回填整集合成产物（刷新后仍可见）
    episodeVideoUrl.value = res.episode_video_url || ''
    // 刷新恢复：若最新合成记录在 pending/processing，恢复 loading 状态等待 WS 后续事件
    const cs = res.episode_concat_status
    concatenating.value = (cs === 'processing' || cs === 'pending')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

// ============ 片段切换 ============

function flushCurrentEditor() {
  if (!panelCardRef.value) return
  const result = panelCardRef.value.flushEditor()
  if (result?.plainText === undefined) return
  const seg = segments.value[currentIndex.value]
  if (!seg) return
  const savedText = lastSavedSegmentTexts.value.get(seg.segment_index) || ''
  if (result.plainText.trim() !== savedText.trim()) {
    dirtySegmentTexts.value.set(seg.segment_index, result.plainText)
  } else {
    dirtySegmentTexts.value.delete(seg.segment_index)
  }
}

function handleSelectSegment(idx) {
  flushCurrentEditor()
  currentIndex.value = idx
}

// ============ 片段插入/删除 ============

async function handleInsertSegment(idx, position) {
  const seg = segments.value[idx]
  if (!seg) return
  try {
    await insertStoryboard(props.projectId, props.episodeId, {
      anchor_segment_id: seg.id,
      position,
    })
    ElMessage.success('已插入新片段')
    // 清掉脏文本基线（segment_index 即将变化）
    dirtySegmentTexts.value.clear()
    lastSavedSegmentTexts.value.clear()
    await fetchStoryboards()
    // 切到新片段
    currentIndex.value = position === 'before' ? idx : idx + 1
  } catch (e) {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleDeleteSegment(idx) {
  const seg = segments.value[idx]
  if (!seg) return
  pendingDeleteIdx.value = idx
  deleteConfirmVisible.value = true
}

async function confirmDeleteSegment() {
  const idx = pendingDeleteIdx.value
  pendingDeleteIdx.value = -1
  const seg = segments.value[idx]
  if (!seg) return
  try {
    await deleteStoryboard(props.projectId, seg.id)
    ElMessage.success('删除成功')
    dirtySegmentTexts.value.clear()
    lastSavedSegmentTexts.value.clear()
    const newIndex = Math.max(0, Math.min(currentIndex.value, segments.value.length - 2))
    await fetchStoryboards()
    currentIndex.value = newIndex
  } catch (e) {
    // 错误提示由 request 拦截器统一处理
  }
}

function handleSegmentTextUpdate(text) {
  const seg = segments.value[currentIndex.value]
  if (!seg) return
  const savedText = lastSavedSegmentTexts.value.get(seg.segment_index) || ''
  if (text.trim() !== savedText.trim()) {
    dirtySegmentTexts.value.set(seg.segment_index, text)
  } else {
    dirtySegmentTexts.value.delete(seg.segment_index)
  }
}

// ============ 操作处理 ============

async function handleGenerateScript() {
  generatingScript.value = true
  try {
    await apiGenerateScript(props.projectId, props.episodeId)
    episodeStatus.value = 'generating'
    ElMessage.success('脚本生成任务已提交')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    generatingScript.value = false
  }
}

async function handleSaveScript() {
  flushCurrentEditor()

  if (!dirtySegmentTexts.value.size) {
    ElMessage.warning('没有修改需要保存')
    return
  }

  savingScript.value = true
  try {
    const segmentsPayload = []
    for (const [idx, text] of dirtySegmentTexts.value) {
      segmentsPayload.push({
        segment_index: idx,
        plain_text: text,
      })
    }

    await updateScriptText(props.projectId, props.episodeId, segmentsPayload)
    ElMessage.success('脚本已保存')
    // 直接更新本地片段状态
    for (const [idx, text] of dirtySegmentTexts.value) {
      const seg = segments.value.find(s => s.segment_index === idx)
      if (seg) {
        seg.video_prompt = text
        seg.status = 'pending'
        seg.gen_error = null
      }
      lastSavedSegmentTexts.value.set(idx, text)
    }
    dirtySegmentTexts.value.clear()
    // 强制编辑器用纯文本重新渲染，确保保存后与刷新后显示一致
    panelCardRef.value?.forceHydrate?.()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    savingScript.value = false
  }
}

async function handleGenerateVideo(seg) {
  if (!seg) return

  // 检测未保存修改
  if (dirtySegmentTexts.value.size > 0) {
    unsavedConfirmVisible.value = true
    return
  }

  const currentText = panelCardRef.value?.flushEditor?.()?.plainText ?? currentSegmentText.value

  // 立即展示"视频生成中"状态
  const prevStatus = seg.status
  const prevGenerating = seg._generating
  seg.status = 'video_generating'
  seg._generating = true

  try {
    const payload = {
      ...videoForm.value,
      text_prompt: currentText || '',
    }
    const res = await generateStoryboardVideo(props.projectId, seg.id, payload)
    seg._progress = 0
    if (res?.task_id) {
      seg._taskId = res.task_id
      taskSegmentMap.value[res.task_id] = seg.segment_index
    }
    ElMessage.success('视频生成任务已提交')
  } catch {
    seg.status = prevStatus
    seg._generating = prevGenerating
  }
}

async function handleUnsavedConfirm() {
  await handleSaveScript()
  // 增量更新后 storyboard 不会被重建，无需全量重载
  const seg = segments.value[currentIndex.value]
  if (seg) handleGenerateVideo(seg)
}

async function handleCancelTask(seg) {
  if (!seg?._taskId) return
  try {
    await cancelVideoTask(props.projectId, seg._taskId)
    seg.status = 'pending'
    seg._generating = false
    seg._taskId = null
    ElMessage.success('已取消生成')
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleBatchGenerate() {
  batchGenerating.value = true
  try {
    const res = await generateMultimodalVideo(props.projectId, props.episodeId, { model: videoForm.value.model })
    ElMessage.success('批量视频生成任务已提交')
    segments.value.forEach(s => { s.status = 'video_generating'; s._generating = true; s._progress = 0 })
    if (res?.task_id) taskSegmentMap.value[res.task_id] = 'batch'
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    batchGenerating.value = false
  }
}

function handleConcatVideo() {
  concatConfirmVisible.value = true
}

async function confirmConcatVideo() {
  concatenating.value = true
  try {
    await concatEpisodeVideo(props.projectId, props.episodeId)
    ElMessage.success('视频拼接任务已提交')
  } catch {
    concatenating.value = false
  }
}

function openEpisodeVideo() {
  if (!episodeVideoUrl.value) return
  const title = episodeTitle.value
    ? `第 ${episodeNumber.value} 集: ${episodeTitle.value}`
    : `第 ${episodeNumber.value} 集`
  openPlayer({ url: episodeVideoUrl.value, title })
}

function openPlayer({ url, title = '视频播放' }) {
  if (!url) return
  playerUrl.value = url
  playerTitle.value = title
  playerVisible.value = true
}

function openConcatHistory() {
  concatHistoryVisible.value = true
}

function handleVideoFormUpdate(form) {
  videoForm.value = form
}

// 资产
function openDetail(d) { if (d.imageUrl) detailAsset.value = d }
function goBack() { router.push(`/workspace/${props.projectId}/episodes`) }

// ============ WebSocket ============

let removeWsListener = null

function setupWebSocket() {
  const userStore = useUserStore()
  const userId = userStore.userInfo.value?.id
  if (!userId) return

  const handleEvent = async (event) => {
    if (event.project_id && event.project_id !== props.projectId) return

    // 委托处理项目资产库相关事件（批量同步、生成进度、自动同步）
    await handleProjectAssetEvent(event)

    switch (event.event_type) {
      case WSEventType.SCRIPT_PROGRESS: {
        const d = event.data || {}
        if (d.episode_id !== props.episodeId) return
        if (d.status === ScriptTaskStatus.COMPLETED) {
          episodeStatus.value = 'completed'
          generatingScript.value = false
          await fetchStoryboards()
          ElMessage.success('脚本生成完成')
        } else if (d.status === ScriptTaskStatus.FAILED) {
          episodeStatus.value = 'failed'
          generatingScript.value = false
          ElMessage.error('脚本生成失败: ' + (d.error || ''))
        } else if (d.status === ScriptTaskStatus.GENERATING) {
          generatingScript.value = true
          episodeStatus.value = 'generating'
        }
        break
      }

      case WSEventType.VIDEO_PROGRESS: {
        const d = event.data || {}
        const taskId = d.task_id

        if (d.segment_index !== undefined) {
          const seg = segments.value.find(s => s.segment_index === d.segment_index)
          if (seg) {
            if (d.status === VideoTaskStatus.PROCESSING || d.status === VideoTaskStatus.SUBMITTED) {
              seg.status = 'video_generating'
              seg._generating = true
              seg._progress = d.progress || 0
              if (taskId) { seg._taskId = taskId; taskSegmentMap.value[taskId] = d.segment_index }
            } else if (d.status === VideoTaskStatus.SUCCESS) {
              seg.status = 'video_completed'
              seg._generating = false
              seg._progress = 100
              seg._taskId = null
              if (d.video_url) seg.video_url = d.video_url
              // 同步 cover_url：重新生成时后端先推空（清旧封面），异步任务完成后推新封面
              seg.cover_url = d.cover_url || null
            } else if (d.status === VideoTaskStatus.FAILED) {
              seg.status = 'failed'
              seg._generating = false
              seg._taskId = null
              seg.gen_error = d.error || ''
            } else if (d.status === VideoTaskStatus.CANCELLED) {
              seg.status = 'pending'
              seg._generating = false
              seg._taskId = null
            }
          }
        }

        if (d.status === VideoTaskStatus.SUCCESS && d.segment_videos) {
          batchGenerating.value = false
          for (const [segIdx, url] of Object.entries(d.segment_videos)) {
            const seg = segments.value.find(s => s.segment_index === parseInt(segIdx))
            if (seg) { seg.status = 'video_completed'; seg._generating = false; seg._progress = 100; seg.video_url = url }
          }
          ElMessage.success('批量视频生成完成')
        }

        if (d.status === VideoTaskStatus.FAILED && d.segment_index === undefined) {
          batchGenerating.value = false
        }
        break
      }

      case WSEventType.VIDEO_CONCAT: {
        // 整集合成：仅开始/完成/失败三种事件，无中间进度
        const d = event.data || {}
        if (d.episode_id && d.episode_id !== props.episodeId) return

        if (d.status === 'processing') {
          concatenating.value = true
        } else if (d.status === 'completed') {
          concatenating.value = false
          if (d.video_url) episodeVideoUrl.value = d.video_url
          ElMessage.success('视频拼接完成')
          if (concatHistoryVisible.value) concatHistoryRef.value?.refresh?.()
        } else if (d.status === 'failed') {
          concatenating.value = false
          ElMessage.error('视频拼接失败: ' + (d.error || ''))
          if (concatHistoryVisible.value) concatHistoryRef.value?.refresh?.()
        }
        break
      }
    }
  }

  removeWsListener = ws.onEvent(handleEvent)
  ws.connect(userId)
}

// ============ 生命周期 ============

onMounted(async () => {
  const userStore = useUserStore()
  if (!userStore.loaded.value) {
    try { await userStore.fetchUser() } catch { /* 忽略 */ }
  }
  setupWebSocket()
  // 先取项目配置判断模式（导演模式 vs 全局模式）
  await Promise.all([fetchStoryboards(), loadProjectConfig()])
  // 导演模式空剧集：自动新建一个空白片段，避免页面空白无法操作
  // 全局模式不动：脚本未生成时进入此页保持原空状态提示
  if (isDirectorMode.value && segments.value.length === 0) {
    try {
      await createStoryboard(props.projectId, props.episodeId, { segment_index: 1 })
      await fetchStoryboards()
    } catch {
      // 错误提示由 request 拦截器统一处理
    }
  }
  fetchProjectAssets()
})

onUnmounted(() => {
  if (removeWsListener) removeWsListener()
})
</script>

<style scoped>
/* ── 页面容器 ── */
.vp-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 1rem;
  gap: 0.75rem;
  background: #f3f4f6;
  overflow: hidden;
}

/* ── 顶部栏：三栏对齐主区域（侧栏 / 编辑器 / 预览） ── */
.vp-top-bar {
  display: flex;
  align-items: center;
  gap: 1rem; /* 同步 .vp-main 列间距，保证与下方编辑器右边界对齐 */
  flex-shrink: 0;
}
/* 左栏：logo + 返回，宽度对齐 StudioAssetSidebar */
.vp-top-side {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 15.5rem;
  flex-shrink: 0;
}
/* 中栏：工具栏，宽度对齐编辑器列（flex:1） */
.vp-top-editor {
  flex: 1;
  min-width: 0;
}
/* 右栏：剧集信息，宽度对齐 vp-preview 列 */
.vp-top-preview {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.375rem;
  width: 22%;
  min-width: 240px;
  flex-shrink: 0;
}
.vp-logo {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  border-radius: 0.5rem;
  outline: none;
  text-decoration: none;
}
.vp-logo-img {
  width: 173.42px;
  height: 48px;
  object-fit: contain;
}
.vp-back-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid rgba(111,126,153,0.24); background: #fff;
  cursor: pointer; color: #6b7280; transition: all 0.15s;
}
.vp-back-btn:hover { border-color: rgba(47,123,255,0.64); color: #1d63e8; }
.vp-ep-tag {
  display: inline-flex; align-items: center; gap: 0.25rem;
  font-size: 0.6875rem; font-weight: 700;
  padding: 0.125rem 0.5rem 0.125rem 0.375rem;
  border-radius: 999px;
}
.vp-ep-tag svg { flex-shrink: 0; }
.vp-ep-tag.eps-generating { color: #1d63e8; background: rgba(47,123,255,0.12); }
.vp-ep-tag.eps-generating svg { animation: vp-spin 1.2s linear infinite; }
.vp-ep-tag.eps-completed { color: #0f9f62; background: rgba(16,185,129,0.12); }
.vp-ep-tag.eps-failed { color: #cb3a3a; background: rgba(239,68,68,0.1); }
.vp-ep-info { font-size: 0.75rem; font-weight: 600; color: #4b5563; }

/* ── 按钮 ── */
.vp-btn {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.4rem 0.85rem; border-radius: 8px; font-size: 0.85rem;
  font-weight: 500; cursor: pointer; border: 1px solid transparent;
  transition: all 0.15s; white-space: nowrap;
}
.vp-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.vp-btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; font-weight: 600; }
.vp-btn-outline { background: #fff; border-color: rgba(111,126,153,0.24); color: #0a0a0a; }
.vp-btn-outline:hover:not(:disabled) { border-color: rgba(47,123,255,0.64); }
.vp-btn-pill { border-radius: 999px; }
.vp-btn-wrap { display: inline-flex; }
.vp-btn-primary {
  background: linear-gradient(135deg, #2f7bff 0%, #1d63e8 100%);
  border-color: transparent;
  color: #fff;
  border-radius: 999px;
  box-shadow: 0 4px 10px rgba(29, 99, 232, 0.25);
}
.vp-btn-primary:hover:not(:disabled) {
  filter: brightness(1.05);
  box-shadow: 0 6px 14px rgba(29, 99, 232, 0.35);
}
.vp-spin-icon { animation: vp-spin 1.2s linear infinite; }

/* ── Loading / 空状态 ── */
.vp-center-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  flex: 1; gap: 0.75rem; color: #9ca3af;
}
.vp-center-state p { margin: 0; font-size: 0.95rem; color: #4b5563; }
.vp-center-state span { font-size: 0.85rem; }
.vp-spinner {
  width: 32px; height: 32px;
  border: 3px solid rgba(29,99,232,0.15);
  border-top-color: #1d63e8;
  border-radius: 50%;
  animation: vp-spin 0.8s linear infinite;
}

/* ── 主内容区：三栏布局 ── */
.vp-main {
  display: flex;
  gap: 1rem;
  flex: 1;
  min-height: 0;
  align-items: stretch;
  overflow: hidden;
}

/* ── 右栏：视频预览 ── */
.vp-preview {
  width: 22%;
  min-width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: rgba(255,255,255,0.94);
  border-radius: 1rem;
  border: 1px solid rgba(111,126,153,0.24);
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  overflow: hidden;
}

.vp-preview-inner {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(to bottom, #18181b, #09090b, #000);
  padding: 0.75rem;
  position: relative;
}

.vp-video {
  max-height: 100%; width: 100%; max-width: 100%;
  object-fit: contain; border-radius: 0.25rem;
}

.vp-preview-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.5rem; padding: 2rem 0; color: #6b7280;
}
.vp-preview-empty span { font-size: 0.75rem; }

/* ── 生成失败 ── */
.vp-preview-failed {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 0.5rem; padding: 2rem 1.5rem; text-align: center;
}
.vp-failed-title { font-size: 0.875rem; font-weight: 500; color: #ef4444; }
.vp-failed-msg { font-size: 0.75rem; color: #9ca3af; word-break: break-all; }

/* ── 生成动画 ── */
.vp-gen {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.25rem;
}
.vp-gen-rings { position: relative; width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; }
.vp-gen-ring-outer {
  position: absolute; inset: 0;
  border: 2px solid transparent; border-top-color: rgba(99,179,237,0.5); border-right-color: rgba(99,179,237,0.2);
  border-radius: 50%; animation: vp-spin 1.5s linear infinite;
}
.vp-gen-ring-inner {
  position: absolute; inset: 14px;
  border: 2px solid transparent; border-bottom-color: rgba(129,230,217,0.5); border-left-color: rgba(129,230,217,0.2);
  border-radius: 50%; animation: vp-spin-rev 2s linear infinite;
}
.vp-gen-dot {
  width: 24px; height: 24px; border-radius: 50%;
  background: linear-gradient(135deg, #60a5fa, #2dd4bf);
  animation: vp-pulse 1.5s ease-in-out infinite;
}
.vp-gen-text { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; }
.vp-gen-label { font-size: 0.875rem; font-weight: 500; color: #d1d5db; }
.vp-gen-hint { font-size: 11px; color: #6b7280; }
.vp-gen-bar { width: 160px; height: 4px; border-radius: 2px; background: #27272a; overflow: hidden; }
.vp-gen-shimmer {
  height: 100%; width: 33%; border-radius: 2px;
  background: linear-gradient(90deg, transparent, rgba(96,165,250,0.8), transparent);
  animation: vp-shimmer 1.8s ease-in-out infinite;
}

@keyframes vp-spin { to { transform: rotate(360deg); } }
@keyframes vp-spin-rev { to { transform: rotate(-360deg); } }
@keyframes vp-pulse { 0%,100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.25); opacity: 1; } }
@keyframes vp-shimmer { 0% { transform: translateX(-150%); } 100% { transform: translateX(350%); } }

@media (max-width: 1024px) {
  .vp-main > :first-child { display: none; }
  .vp-preview { width: 100%; max-width: none; order: -1; }
  .vp-preview-inner { min-height: 200px; }
  /* 顶部栏同步：隐藏左侧栏占位，剧集信息取消固定宽度 */
  .vp-top-side { display: none; }
  .vp-top-preview { width: auto; min-width: 0; }
}
</style>

<style>
/* 项目资产库弹窗样式（非 scoped，因 el-dialog append-to-body） */
.asset-library-dialog .el-dialog__header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(111,126,153,0.16);
}
.asset-library-dialog .el-dialog__body {
  padding: 1rem 1.25rem;
  max-height: 75vh;
  overflow-y: auto;
}
.ald-header {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 1rem; font-weight: 600; color: #111;
}
</style>
