<template>
  <div class="ci-item" :class="'ci-' + task.status">
    <div class="ci-body">
      <!-- 时间 -->
      <div class="ci-time">{{ formattedTime }}</div>

      <!-- 提示词文本（含内联 @tag） -->
      <div class="ci-text" v-html="renderedPrompt" @mouseenter="onThumbEnter" @mouseleave="onThumbLeave" @mousemove="onThumbMove" />

      <!-- 元信息 -->
      <div class="ci-meta">
        <span class="ci-tag">
          <svg v-if="task.generation_type === 'reference'" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          <svg v-else width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="8" height="16" rx="1"/><path d="M14 12h6"/><path d="m17 9 3 3-3 3"/><rect x="14" y="4" width="8" height="4" rx="1" opacity="0.4"/><rect x="14" y="16" width="8" height="4" rx="1" opacity="0.4"/></svg>
          {{ task.generation_type === 'reference' ? '参考生成' : '首尾帧' }}
        </span>
        <span class="ci-tag">{{ task.ratio }}</span>
        <span v-if="task.resolution" class="ci-tag">{{ task.resolution }}</span>
        <span class="ci-tag">{{ task.duration }}s</span>
        <span v-if="task.generate_audio" class="ci-tag">含音频</span>
        <button
          v-if="task.status === 'succeeded' && task.api_task_id"
          class="ci-tag ci-cgtid-btn"
          title="复制 cgtid"
          @mousedown.prevent
          @click.stop="handleCopyCgtid"
        >cgtid</button>
      </div>

      <!-- 视频区域 -->
      <div class="ci-video-area">
        <!-- 生成中 -->
        <div v-if="isProcessing" class="ci-generating">
          <div class="ci-gen-spinner" />
          <span class="ci-gen-text">生成中 {{ task.progress || 0 }}%</span>
        </div>
        <!-- 失败：和生成中一样的容器，内容为错误信息+重试 -->
        <div v-else-if="task.status === 'failed'" class="ci-generating">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          <span class="ci-gen-text">{{ displayError }}</span>
          <button class="ci-retry-btn" @click="$emit('retry', task.id)">重试</button>
        </div>
        <!-- 成功：悬停播放 -->
        <VideoHoverPlayer
          v-else-if="task.video_url"
          :src="task.video_url"
          :poster="task.thumbnail_url"
        />
      </div>

      <!-- 操作按钮 -->
      <div class="ci-actions">
        <button v-if="isCancellable" class="ci-action-btn ci-cancel-btn"
                :disabled="cancelling" @mousedown.prevent @click="handleCancel">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          {{ cancelling ? '取消中...' : '取消生成' }}
        </button>
        <button class="ci-action-btn" @mousedown.prevent @click="handleReedit">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
          重新编辑
        </button>
      </div>
    </div>

    <!-- 悬停大图弹框 -->
    <Teleport to="body">
      <div v-if="hoverImgUrl" class="ci-hover-preview" :style="hoverPreviewStyle">
        <img :src="hoverImgUrl" class="ci-hover-preview-img" />
      </div>
    </Teleport>

    <!-- 取消生成确认 -->
    <ConfirmDialog
      v-model="cancelConfirmVisible"
      title="提示"
      message="是否要取消生成任务？"
      confirm-text="确定"
      type="warning"
      @confirm="executeCancel"
    />
  </div>
</template>

<script setup>
import { computed, ref, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import VideoHoverPlayer from './VideoHoverPlayer.vue'
import { useShortVideoStore } from '@/store/shortVideo'
import { useUserStore } from '@/store/user'

const props = defineProps({
  task: { type: Object, required: true },
})

defineEmits(['retry'])

const shortVideoStore = useShortVideoStore()
const userStore = useUserStore()

function handleReedit() {
  // 跨区域禁止重新编辑：历史任务里的资产 ID 是提交时区域专属，跨区域复用会把 ID 发给错误模型
  const currentRegion = userStore.userInfo.value?.region || 'domestic'
  if (props.task.region && props.task.region !== currentRegion) {
    ElMessage.warning('不允许跨区域重新编辑，请重新上传')
    return
  }
  shortVideoStore.restoreFromTask(props.task)
}

const isProcessing = computed(() =>
  ['pending', 'submitted', 'queued', 'processing'].includes(props.task.status)
)

// 生成中均展示取消按钮；PROCESSING 时火山 running 后实际无法中断，点击会失败
const isCancellable = computed(() =>
  ['pending', 'submitted', 'queued', 'processing'].includes(props.task.status)
)

const cancelling = ref(false)
const cancelConfirmVisible = ref(false)

function handleCancel() {
  cancelConfirmVisible.value = true
}

async function executeCancel() {
  cancelling.value = true
  try {
    await shortVideoStore.cancelTask(props.task.id)
    ElMessage.success('已取消')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    cancelling.value = false
  }
}

async function handleCopyCgtid() {
  const cgtid = props.task.api_task_id
  if (!cgtid) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(cgtid)
    } else {
      const ta = document.createElement('textarea')
      ta.value = cgtid
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    ElMessage.success('已复制cgtid')
  } catch {
    ElMessage.error('复制失败')
  }
}

// 解析错误信息，提取可读 message
const displayError = computed(() => {
  const raw = props.task.error_message
  if (!raw) return '生成失败'

  // SeedanceAPIError 格式: "Seedance API Error [statusCode]: {json_body} (task_id=...)"
  const errRe = new RegExp('Seedance API Error \\[\\d+\\]:\\s*(.+?)(?:\\s*\\(task_id=)')
  const apiMatch = raw.match(errRe)
  if (apiMatch) {
    const body = apiMatch[1].trim()
    try {
      const parsed = JSON.parse(body)
      const msg = parsed?.error?.message || parsed?.message || body
      return msg
    } catch {
      return body
    }
  }

  return raw
})

// 解析引用素材 URL 映射（兼容新旧格式），返回 { url, thumbnail_url } 数组
function resolveRefMap() {
  const json = props.task.reference_media_json
  if (!json) return { image: [], video: [], audio: [] }
  try {
    const data = typeof json === 'string' ? JSON.parse(json) : json
    // 新格式 images: [{url, thumbnail_url, volc_asset_id}]
    const images = (data.images || []).map(item => {
      if (typeof item === 'string') return { url: item, thumbnail_url: '' }
      return { url: item?.url || '', thumbnail_url: item?.thumbnail_url || '' }
    }).filter(r => r.url)
    // 旧格式 imageUrls: [url, url]
    const legacyImages = (data.imageUrls || []).filter(Boolean).map(url => ({ url, thumbnail_url: '' }))
    const videos = (data.videos || []).map(item => {
      if (typeof item === 'string') return { url: item, thumbnail_url: '' }
      return { url: item?.url || '', thumbnail_url: item?.thumbnail_url || '' }
    }).filter(r => r.url)
    const legacyVideos = (data.videoUrls || []).filter(Boolean).map(url => ({ url, thumbnail_url: '' }))
    const audios = (data.audios || []).map(item => {
      if (typeof item === 'string') return { url: item, thumbnail_url: '' }
      return { url: item?.url || '', thumbnail_url: '' }
    }).filter(r => r.url)
    const legacyAudios = (data.audioUrls || []).filter(Boolean).map(url => ({ url, thumbnail_url: '' }))
    return {
      image: [...images, ...legacyImages],
      video: [...videos, ...legacyVideos],
      audio: [...audios, ...legacyAudios],
    }
  } catch {
    return { image: [], video: [], audio: [] }
  }
}

// 渲染 prompt_text，将 @图片N/@视频N/@音频N 替换为内联 chip
const renderedPrompt = computed(() => {
  const text = props.task.prompt_text || ''
  if (!text) return ''

  const refMap = resolveRefMap()

  // 转义 HTML 特殊字符
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  return esc(text).replace(/@(图片|视频|音频)(\d+)/g, (match, type, numStr) => {
    const typeKey = type === '图片' ? 'image' : type === '视频' ? 'video' : 'audio'
    const refs = refMap[typeKey]
    const idx = parseInt(numStr, 10) - 1
    const ref = refs[idx]

    if (ref) {
      const url = ref.url
      const thumbUrl = ref.thumbnail_url || url
      if (typeKey === 'image') {
        // 内联展示缩略图，data-original-url 保留原图 URL 供悬停预览使用；缩略图加载失败时回退到原图
        return `<span class="ci-inline-ref"><img class="ci-inline-ref-thumb" src="${esc(thumbUrl)}" data-original-url="${esc(url)}" loading="lazy" onerror="if(!this.dataset.fb&&this.dataset.originalUrl&&this.src!==this.dataset.originalUrl){this.dataset.fb='1';this.src=this.dataset.originalUrl}" /><span class="ci-inline-ref-label">${esc(match)}</span></span>`
      }
      if (typeKey === 'video') {
        return `<span class="ci-inline-ref ci-inline-ref-${typeKey}"><svg class="ci-inline-ref-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span class="ci-inline-ref-label">${esc(match)}</span></span>`
      }
      return `<span class="ci-inline-ref ci-inline-ref-${typeKey}"><svg class="ci-inline-ref-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg><span class="ci-inline-ref-label">${esc(match)}</span></span>`
    }
    return esc(match)
  })
})

const formattedTime = computed(() => {
  const iso = props.task.create_time
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const time = `${hh}:${mm}`

  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return time

  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return `昨天 ${time}`

  const MM = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${MM}-${dd} ${time}`
})

// 悬停大图预览
const hoverImgUrl = ref('')
const hoverPreviewStyle = ref({})
let hoverTimer = null

function findThumbImg(el) {
  if (el && el.classList && el.classList.contains('ci-inline-ref-thumb')) return el
  if (el && el.parentElement && el.parentElement.classList.contains('ci-inline-ref')) {
    return el.parentElement.querySelector('.ci-inline-ref-thumb')
  }
  return null
}

// 悬停预览优先展示原图（data-original-url），未设置时回退到 img.src（缩略图）
function getOriginalUrl(img) {
  if (!img) return ''
  return img.getAttribute('data-original-url') || img.src || ''
}

function onThumbEnter(e) {
  const img = findThumbImg(e.target)
  if (!img) return
  hoverImgUrl.value = getOriginalUrl(img)
  updatePreviewPos(e)
}

function onThumbMove(e) {
  const img = findThumbImg(e.target)
  if (img) {
    const url = getOriginalUrl(img)
    if (url !== hoverImgUrl.value) hoverImgUrl.value = url
  } else {
    hoverImgUrl.value = ''
    return
  }
  updatePreviewPos(e)
}

function onThumbLeave(e) {
  const img = findThumbImg(e.relatedTarget || e.target)
  if (img) return
  hoverImgUrl.value = ''
}

function updatePreviewPos(e) {
  const offset = 12
  let left = e.clientX + offset
  let top = e.clientY + offset
  if (left + 260 > window.innerWidth) left = e.clientX - 260
  if (top + 260 > window.innerHeight) top = e.clientY - 260
  hoverPreviewStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
  }
}

onBeforeUnmount(() => {
  hoverImgUrl.value = ''
})
</script>

<style scoped>
.ci-item {
  padding: 1rem 0;
}

.ci-item + .ci-item {
  border-top: 1px solid var(--glass-stroke-soft, rgba(0, 0, 0, 0.05));
}

.ci-time {
  font-size: 12px;
  color: var(--glass-text-tertiary, #999);
  margin-bottom: 0.25rem;
}

.ci-body {
  min-width: 0;
}

.ci-text {
  font-size: 16px;
  color: var(--glass-text-primary);
  line-height: 1.5;
  word-break: break-word;
  margin-bottom: 0.5rem;
}

/* 内联引用 chip */
:deep(.ci-inline-ref) {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  padding: 0 0.25rem;
  border-radius: 0.25rem;
  border: 1px solid var(--glass-stroke-soft, rgba(0, 0, 0, 0.1));
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  vertical-align: middle;
  user-select: none;
  margin: 0 1px;
}

:deep(.ci-inline-ref-thumb) {
  width: 1.125rem;
  height: 1.125rem;
  border-radius: 0.125rem;
  object-fit: cover;
}

:deep(.ci-inline-ref-icon) {
  width: 0.75rem;
  height: 0.75rem;
  flex-shrink: 0;
  color: var(--glass-accent-from, #3b82f6);
}

:deep(.ci-inline-ref-label) {
  font-size: 0.6875rem;
  color: var(--glass-text-secondary);
  white-space: nowrap;
}

:deep(.ci-inline-ref-video),
:deep(.ci-inline-ref-audio) {
  background: rgba(59, 130, 246, 0.06);
  border-color: rgba(59, 130, 246, 0.2);
}

:deep(.ci-inline-ref-thumb) {
  cursor: zoom-in;
}

/* 悬停大图弹框 */
.ci-hover-preview {
  position: fixed;
  z-index: 2000;
  width: 250px;
  height: 250px;
  border-radius: 10px;
  overflow: hidden;
  background: var(--glass-bg-surface, #fff);
  border: 1px solid var(--glass-stroke-soft, rgba(255, 255, 255, 0.22));
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  pointer-events: none;
  animation: ci-hover-in 0.15s ease-out;
}

.ci-hover-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

@keyframes ci-hover-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.ci-video-area {
  max-width: 560px;
  margin-bottom: 0.375rem;
}

/* 生成中 */
.ci-generating {
  aspect-ratio: 16/9;
  border-radius: 0.5rem;
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  border: 1px dashed var(--glass-stroke-base, rgba(0, 0, 0, 0.1));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.ci-gen-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from, #3b82f6);
  border-radius: 50%;
  animation: ci-spin 0.8s linear infinite;
}

@keyframes ci-spin {
  to { transform: rotate(360deg); }
}

.ci-gen-text {
  font-size: 0.75rem;
  color: var(--glass-text-secondary);
  text-align: center;
  word-break: break-all;
}

.ci-retry-btn {
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  border: 1px solid rgba(239, 68, 68, 0.3);
  background: transparent;
  color: #dc2626;
  font-size: 0.6875rem;
  cursor: pointer;
  transition: background 0.15s;
}

.ci-retry-btn:hover {
  background: rgba(239, 68, 68, 0.06);
}

/* 操作按钮 */
.ci-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.ci-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 7px;
  border: none;
  background: rgba(107, 114, 180, 0.06);
  color: #9ca3af;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.ci-action-btn:hover {
  background: rgba(107, 114, 180, 0.09);
  color: #6b7280;
}

.ci-cancel-btn:hover {
  background: rgba(220, 38, 38, 0.08);
  color: #dc2626;
}

.ci-cancel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 元信息 */
.ci-meta {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 12px;
  color: var(--glass-text-tertiary, #999);
  margin-bottom: 0.5rem;
  max-width: 560px;
}

.ci-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(107, 114, 180, 0.07);
  color: #6b7280;
}

.ci-cgtid-btn {
  margin-left: auto;
  border: none;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.ci-cgtid-btn:hover {
  background: rgba(107, 114, 180, 0.16);
  color: #4b5563;
}
</style>
