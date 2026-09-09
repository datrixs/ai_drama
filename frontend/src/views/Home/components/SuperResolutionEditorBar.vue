<template>
  <div
    class="sr-bar"
    :class="{
      'sr-mode-inline': editorMode === 'inline',
      'sr-mode-mini': editorMode === 'mini',
      'sr-mode-floating': editorMode === 'floating',
      'sr-dragover': isDragging,
    }"
    @focusin="onFocusIn"
    @focusout="onFocusOut"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- ========== 迷你状态 ========== -->
    <template v-if="editorMode === 'mini'">
      <div class="sr-mini-content" @click="handleMiniClick">
        <button class="sr-mini-add" @click.stop="pickFile">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
        </button>
        <span class="sr-mini-text">
          {{ miniDisplayText }}
        </span>
        <button
          class="sr-mini-send"
          :disabled="!store.canGenerate"
          @click.stop="handleSubmit"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </template>

    <!-- ========== 展开状态 ========== -->
    <template v-else>
    <div class="sr-expanded">
      <!-- 左：场景 / 参数 -->
      <div class="sr-config-col">
        <!-- 场景卡片网格(对应火山 scene 字段) -->
        <div class="sr-template-grid">
          <button
            v-for="s in SR_SCENES"
            :key="s.value"
            type="button"
            class="sr-template-card"
            :class="{ 'sr-template-active': store.params.scene === s.value }"
            @click="store.applyScene(s.value)"
          >
            <div class="sr-template-title-row">
              <div class="sr-template-icon">
                <!-- 通用 -->
                <svg v-if="s.icon === 'general'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 3v18M3 12h18" />
                </svg>
                <!-- UGC 短视频 -->
                <svg v-else-if="s.icon === 'ugc'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="5" width="18" height="14" rx="2" />
                  <path d="M10 9v6l5-3z" />
                </svg>
                <!-- AIGC -->
                <svg v-else-if="s.icon === 'aigc'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2" />
                  <circle cx="12" cy="12" r="4" />
                </svg>
                <!-- 短剧 -->
                <svg v-else-if="s.icon === 'drama'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4 21c0-4 4-7 8-7s8 3 8 7" />
                </svg>
                <!-- 老片修复 -->
                <svg v-else-if="s.icon === 'old_film'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 7h18M3 17h18M7 3v4M7 17v4M17 3v4M17 17v4" />
                </svg>
              </div>
              <span class="sr-template-label">{{ s.label }}</span>
            </div>
            <span class="sr-template-desc">{{ s.desc }}</span>
          </button>
        </div>

        <!-- 参数行(字段名/类型/value 与火山 API 完全对齐) -->
        <div class="sr-params">
          <div class="sr-param">
            <label class="sr-param-label">工具版本</label>
            <SuperResolutionSelect v-model="store.params.tool_version" :options="SR_TOOL_VERSIONS" />
          </div>

          <div class="sr-param">
            <label class="sr-param-label">目标分辨率</label>
            <SuperResolutionSelect v-model="store.params.resolution" :options="SR_RESOLUTIONS" />
          </div>

          <div class="sr-param">
            <label class="sr-param-label">帧率 ({{ SR_FPS_RANGE.min }}-{{ SR_FPS_RANGE.max }} fps)</label>
            <SuperResolutionSelect v-model="store.params.fps" :options="SR_FPS_OPTIONS" />
          </div>

          <div class="sr-param">
            <label class="sr-param-label">码率</label>
            <SuperResolutionSelect v-model="store.params.bitrate_level" :options="SR_BITRATE_LEVELS" />
          </div>
        </div>
      </div>

      <!-- 右：源视频 / 提交 -->
      <div class="sr-source-col">
        <!-- 顶部模式选择器：本地上传 / 在线URL（下拉式，参考短视频 EditorBar 的 mode selector） -->
        <div class="sr-mode-wrap">
          <button type="button" class="sr-mode-trigger" @click.stop="toggleModeDropdown($event)">
            <span class="sr-mode-icon" v-html="currentModeIcon" />
            <span class="sr-mode-label">{{ currentModeLabel }}</span>
            <svg class="sr-mode-arrow" :class="{ 'sr-mode-arrow-open': showModeDropdown }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <Teleport to="body">
            <div v-if="showModeDropdown" class="sr-mode-backdrop" @mousedown="closeModeDropdown" />
            <div v-if="showModeDropdown" class="sr-mode-popup" :style="modePopupStyle">
              <div
                v-for="opt in modeOptions"
                :key="opt.value"
                class="sr-mode-option"
                :class="{ 'sr-mode-option-active': uploadMode === opt.value }"
                @mousedown.prevent="selectMode(opt.value)"
              >
                <span class="sr-mode-opt-icon" v-html="opt.icon" />
                <div class="sr-mode-opt-text">
                  <span class="sr-mode-opt-title">{{ opt.label }}</span>
                  <span class="sr-mode-opt-desc">{{ opt.desc }}</span>
                </div>
                <svg v-if="uploadMode === opt.value" class="sr-mode-opt-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>
              </div>
            </div>
          </Teleport>
        </div>

        <!-- 本地上传 -->
        <template v-if="uploadMode === 'local'">
          <button
            v-if="!store.sourceVideoUrl && !isUploading"
            class="sr-upload-btn"
            @click="pickFile"
          >
            <svg class="sr-upload-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span class="sr-upload-label">选择本地视频</span>
            <span class="sr-upload-hint">支持 mp4 / flv / ts / avi / mov / wmv / mkv</span>
            <span class="sr-upload-hint-secondary">最大 1GB · 最高 2K 分辨率</span>
          </button>

          <div v-if="isUploading" class="sr-source-card sr-source-uploading">
            <div class="sr-source-thumb sr-source-thumb-loading" />
            <div class="sr-source-info">
              <div class="sr-source-name">上传中… {{ uploadProgressText }}</div>
              <div class="sr-source-meta">{{ pendingFileName }}</div>
            </div>
          </div>

          <div v-else-if="store.sourceVideoUrl" class="sr-source-card">
            <div class="sr-source-thumb">
              <video
                v-if="store.sourceVideoUrl"
                :src="store.sourceVideoUrl"
                class="sr-source-thumb-video"
                muted
                preload="metadata"
                @loadeddata="onThumbLoaded"
              />
              <div class="sr-source-thumb-overlay">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </div>
            </div>
            <div class="sr-source-info">
              <div class="sr-source-name" :title="store.sourceVideoName">{{ store.sourceVideoName || '源视频' }}</div>
              <div class="sr-source-meta">
                <span v-if="store.sourceVideoDuration != null">{{ formatDuration(store.sourceVideoDuration) }}</span>
                <span v-if="store.sourceVideoSize != null">{{ formatSize(store.sourceVideoSize) }}</span>
              </div>
            </div>
            <button class="sr-source-remove" title="移除" @click="handleClearSource">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
            </button>
          </div>
        </template>

        <!-- 在线 URL -->
        <template v-else>
          <div class="sr-url-wrap">
            <div class="sr-url-input-row">
              <svg class="sr-url-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
              <input
                v-model="urlInput"
                type="url"
                class="sr-url-input"
                placeholder="粘贴视频 HTTP/HTTPS 链接"
                @input="onUrlInput"
              />
              <button
                v-if="urlInput"
                type="button"
                class="sr-url-clear"
                title="清除"
                @click="clearUrl"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
              </button>
              <button
                type="button"
                class="sr-url-paste"
                @click="pasteFromClipboard"
              >粘贴</button>
            </div>
            <div class="sr-url-hint">
              支持 mp4 / flv / ts / avi / mov · 最大 10GB · 最高 2K
            </div>
          </div>
        </template>

        <!-- 提交按钮：源视频区下方 -->
        <button
          class="sr-submit-btn"
          :disabled="!store.canGenerate"
          @click="handleSubmit"
        >
          开始超分
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </button>
      </div>
    </div>
    </template>

    <!-- 拖拽上传遮罩 -->
    <div v-if="isDragging" class="sr-drop-overlay">
      <div class="sr-drop-inner">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <p class="sr-drop-title">松开鼠标上传视频</p>
        <p class="sr-drop-hint">支持 {{ SR_INPUT_LIMITS.acceptedExts.join(' / ') }} · 最大 1GB</p>
      </div>
    </div>

    <!-- 隐藏 file input -->
    <input
      ref="fileInputRef"
      type="file"
      :accept="SR_INPUT_LIMITS.acceptedMimes"
      class="sr-file-input"
      @change="handleFileChange"
    />
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { useSuperResolutionStore } from '@/store/superResolution'
import { directUpload } from '@/utils/cosUpload'
import SuperResolutionSelect from './SuperResolutionSelect.vue'
import {
  SR_SCENES,
  SR_TOOL_VERSIONS,
  SR_RESOLUTIONS,
  SR_FPS_OPTIONS,
  SR_FPS_RANGE,
  SR_BITRATE_LEVELS,
  SR_INPUT_LIMITS,
} from '@/constants/superResolution'

const props = defineProps({
  editorMode: { type: String, default: 'inline', validator: v => ['inline', 'mini', 'floating'].includes(v) },
})

const emit = defineEmits(['expand', 'focusChange'])

const store = useSuperResolutionStore()

// 迷你模式显示文字：有源视频时显示文件名，否则显示提示
const miniDisplayText = computed(() => {
  if (isUploading.value) return `上传中… ${uploadProgressText.value}`
  if (store.sourceVideoUrl) return store.sourceVideoName || '已选视频'
  return '上传视频开始超分'
})

function handleMiniClick() {
  // 点击迷你状态展开
  emit('expand')
}

// select / mode-trigger 在关闭下拉时，焦点会极短暂地离开 sr-bar（转移到 body）
// 用 setTimeout 延迟检测，onFocusIn 取消定时器，避免短暂的焦点漂移
// 触发 wantExpanded = false → editorMode = mini → 整个 sr-bar v-if 重建（"闪一下"）
let focusOutTimer = null

function onFocusIn() {
  clearTimeout(focusOutTimer)
  emit('focusChange', true)
}

function onFocusOut() {
  clearTimeout(focusOutTimer)
  focusOutTimer = setTimeout(() => {
    const bar = document.activeElement?.closest?.('.sr-bar')
    if (!bar) emit('focusChange', false)
  }, 120)
}

onBeforeUnmount(() => {
  clearTimeout(focusOutTimer)
})

const fileInputRef = ref(null)
const isUploading = ref(false)
const uploadProgressText = ref('')
const pendingFileName = ref('')

// 上传模式：local / url
const uploadMode = ref('local')
// URL 输入（在线模式）
const urlInput = ref('')

// 模式选择器配置
const modeOptions = [
  {
    value: 'local',
    label: '本地上传',
    desc: '从设备选择视频文件上传',
    icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
  },
  {
    value: 'url',
    label: '在线URL',
    desc: '粘贴视频直链（HTTP/HTTPS）',
    icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
  },
]

const currentModeLabel = computed(() => {
  const opt = modeOptions.find(o => o.value === uploadMode.value)
  return opt ? opt.label : ''
})

const currentModeIcon = computed(() => {
  const opt = modeOptions.find(o => o.value === uploadMode.value)
  return opt ? opt.icon : ''
})

const showModeDropdown = ref(false)
const modePopupStyle = ref({})

function toggleModeDropdown(e) {
  showModeDropdown.value = !showModeDropdown.value
  if (showModeDropdown.value && e?.currentTarget) {
    const rect = e.currentTarget.getBoundingClientRect()
    modePopupStyle.value = {
      position: 'fixed',
      left: `${rect.left}px`,
      bottom: `${window.innerHeight - rect.top + 4}px`,
    }
  }
}

function selectMode(val) {
  if (uploadMode.value === val) {
    showModeDropdown.value = false
    return
  }
  switchMode(val)
  showModeDropdown.value = false
}

function closeModeDropdown() {
  showModeDropdown.value = false
}

function switchMode(mode) {
  if (uploadMode.value === mode) return
  uploadMode.value = mode
  // 切换来源时清掉之前的输入，避免两种来源混淆
  urlInput.value = ''
  store.clearSourceVideo()
}

function urlToFilename(url) {
  try {
    const u = new URL(url)
    const path = u.pathname
    const i = path.lastIndexOf('/')
    const name = i >= 0 ? decodeURIComponent(path.slice(i + 1)) : ''
    return name || u.hostname
  } catch {
    return url
  }
}

function syncUrlToSource(url) {
  const trimmed = (url || '').trim()
  if (!trimmed) {
    store.clearSourceVideo()
    return
  }
  // 简单校验 HTTP/HTTPS
  if (!/^https?:\/\//i.test(trimmed)) return
  // 先同步设置 URL + 文件名,让用户立即看到反馈并允许提交
  store.setSourceVideo({
    url: trimmed,
    name: urlToFilename(trimmed),
    is_local_upload: false,  // 在线 URL:后端原样存储,不转 COS 永久 URL
  })
  // 异步补全视频时长,保存到 video_super_res_task.source_video_duration
  fetchUrlVideoDuration(trimmed)
}

let urlDurationToken = 0
async function fetchUrlVideoDuration(url) {
  const token = ++urlDurationToken
  try {
    const duration = await loadVideoDuration(url)
    // 输入竞态:用户在加载期间又改了 URL,丢弃旧结果
    if (token !== urlDurationToken) return
    // URL 没变才更新,避免覆盖用户已切换到的新 URL
    if (store.sourceVideoUrl !== url) return
    store.setSourceVideo({
      url,
      name: urlToFilename(url),
      duration: duration ? Math.round(duration) : null,
      is_local_upload: false,
    })
  } catch {
    // CORS 或解码失败:静默回退,不阻塞提交(后端按无源时长处理)
  }
}

function onUrlInput() {
  syncUrlToSource(urlInput.value)
}

function clearUrl() {
  urlInput.value = ''
  store.clearSourceVideo()
}

async function pasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText()
    if (text) {
      urlInput.value = text.trim()
      syncUrlToSource(urlInput.value)
    }
  } catch {
    ElMessage.warning('无法读取剪贴板，请手动粘贴（Ctrl/Cmd+V）')
  }
}

function pickFile() {
  fileInputRef.value?.click()
}

/**
 * 加载视频时长(秒)
 * - 本地 file:调用方负责 createObjectURL + revokeObjectURL
 * - 在线 URL:浏览器可能因 CORS 拒绝读取,调用方需 try/catch
 */
function loadVideoDuration(src) {
  return new Promise((resolve, reject) => {
    const v = document.createElement('video')
    v.preload = 'metadata'
    v.onloadedmetadata = () => resolve(v.duration)
    v.onerror = () => reject(new Error('无法读取视频时长'))
    v.src = src
  })
}

async function getMediaDuration(file) {
  const url = URL.createObjectURL(file)
  try {
    return await loadVideoDuration(url)
  } finally {
    URL.revokeObjectURL(url)
  }
}

function extOf(name) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

async function uploadOneVideo(file) {
  // 校验扩展名
  const ext = extOf(file.name)
  if (!SR_INPUT_LIMITS.acceptedExts.includes(ext)) {
    ElMessage.error(`不支持的格式：${file.name}（仅支持 ${SR_INPUT_LIMITS.acceptedExts.join('/')}）`)
    return false
  }

  if (file.size > SR_INPUT_LIMITS.maxFileSize) {
    const gb = SR_INPUT_LIMITS.maxFileSize / 1024 / 1024 / 1024
    ElMessage.error(`文件超过大小限制（最大 ${gb}GB）`)
    return false
  }

  if (file.name.length > SR_INPUT_LIMITS.maxFileNameLength) {
    ElMessage.error(`文件名长度不能超过 ${SR_INPUT_LIMITS.maxFileNameLength} 个字符`)
    return false
  }

  let duration = null
  try {
    duration = await getMediaDuration(file)
  } catch {
    ElMessage.error('无法读取视频时长，请检查文件是否损坏')
    return false
  }

  isUploading.value = true
  uploadProgressText.value = '0%'
  pendingFileName.value = file.name

  // 简单进度模拟：COS 直传 fetch 无法精确监听进度，这里给一个轻微的视觉反馈
  const fakeTimer = setInterval(() => {
    const cur = parseInt(uploadProgressText.value, 10) || 0
    if (cur < 80) uploadProgressText.value = `${cur + 10}%`
  }, 300)

  try {
    const { url } = await directUpload(file, {
      category: 'upload',
      biz: 'super-resolution-source',
      maxSize: SR_INPUT_LIMITS.maxFileSize,
    })
    uploadProgressText.value = '100%'

    store.setSourceVideo({
      url,
      name: file.name,
      duration: duration ? Math.round(duration) : null,
      size: file.size,
      thumbnail_url: null,
      is_local_upload: true,  // 本地上传:COS 资源,后端转永久 URL
    })
    // 注:暂不在前端抓第一帧缩略图(blob URL 不能落库),
    // 后续如需缩略图,可改为前端 directUpload 缩略图后传 URL。
    return true
  } catch (err) {
    console.error('[superResolution] upload failed:', err)
    // 错误提示由 request 拦截器统一处理（凭证接口失败时）
    return false
  } finally {
    clearInterval(fakeTimer)
    isUploading.value = false
    uploadProgressText.value = ''
    pendingFileName.value = ''
  }
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    await uploadOneVideo(file)
  } finally {
    e.target.value = ''
  }
}

// ── 拖拽上传 ──
const dragCounter = ref(0)
const isDragging = computed(() => dragCounter.value > 0)

function onDragEnter(e) {
  if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) {
    dragCounter.value++
  }
}

function onDragLeave() {
  dragCounter.value = Math.max(0, dragCounter.value - 1)
}

async function onDrop(e) {
  dragCounter.value = 0
  if (isUploading.value) {
    ElMessage.warning('当前已有视频正在上传，请等待完成')
    return
  }
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length === 0) return

  // 迷你模式下先触发展开
  if (props.editorMode === 'mini') {
    emit('expand')
  }

  // URL 模式下切回本地（拖入的是本地文件）
  if (uploadMode.value === 'url') {
    uploadMode.value = 'local'
    urlInput.value = ''
  }

  // 仅支持单个视频：多文件时只取第一个
  if (files.length > 1) {
    ElMessage.warning(`仅支持上传单个视频，已采用第一个文件：${files[0].name}`)
  }

  await uploadOneVideo(files[0])
}

function onThumbLoaded() {
  // 预留：可用于解码后做尺寸读取
}

function handleClearSource() {
  store.clearSourceVideo()
}

async function handleSubmit() {
  if (!store.canGenerate) return
  const res = await store.submit()
  if (res?.task_id) ElMessage.success('已提交超分任务')
}

// 工具
function formatDuration(sec) {
  const s = Math.round(sec)
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${String(r).padStart(2, '0')}`
}

function formatSize(bytes) {
  const MB = 1024 * 1024
  if (bytes >= MB) return `${(bytes / MB).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(0)} KB`
}
</script>

<style scoped>
.sr-bar {
  position: relative;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-radius: 16px;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  transition: max-width 0.25s ease,
              max-height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              padding 0.25s ease,
              gap 0.25s ease,
              box-shadow 0.25s ease;
}

/* 拖拽高亮 */
.sr-dragover {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.35),
              0 4px 24px rgba(0, 0, 0, 0.08) !important;
}

/* 拖拽遮罩 */
.sr-drop-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  background: rgba(99, 102, 241, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  border-radius: inherit;
}

.sr-drop-inner {
  text-align: center;
  color: #6366f1;
  padding: 8px 12px;
}

.sr-drop-title {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
}

.sr-drop-hint {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--glass-text-tertiary, #6b7280);
  line-height: 1.3;
}

/* mini 模式下遮罩紧凑显示 */
.sr-mode-mini .sr-drop-inner svg {
  width: 20px;
  height: 20px;
}
.sr-mode-mini .sr-drop-title {
  font-size: 12px;
}
.sr-mode-mini .sr-drop-hint {
  display: none;
}

/* 三种模式：参考短视频 EditorBar 的 mini/inline/floating 切换 */
.sr-mode-inline {
  max-width: 100%;
  margin: 0 auto;
  max-height: min(560px, 70vh);
}

.sr-mode-floating {
  max-width: 100%;
  margin: 0 auto;
  max-height: min(560px, 70vh);
  box-shadow: 0 10px 24px rgba(20, 35, 69, 0.12);
}

.sr-mode-mini {
  max-width: 80%;
  margin: 0 auto;
  padding: 0;
  gap: 0;
  max-height: 56px;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(19, 35, 66, 0.08);
}

/* mini 内容 */
.sr-mini-content {
  display: flex;
  align-items: center;
  height: 54px;
  padding: 0 14px;
  gap: 10px;
}

.sr-mini-add {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1.5px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  background: transparent;
  color: var(--glass-text-tertiary, #4b5563);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}

.sr-mini-add:hover {
  border-color: var(--glass-accent-from, #3b82f6);
  color: var(--glass-accent-from, #3b82f6);
}

.sr-mini-text {
  flex: 1;
  font-size: 14px;
  color: var(--glass-text-tertiary, #4b5563);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sr-mini-send {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 50%, #3b82f6 100%);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  transition: all 0.15s;
}

.sr-mini-send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

/* 展开状态：左右两列 */
.sr-expanded {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

/* 右列：源视频 + 提交 */
.sr-source-col {
  flex: 0 0 240px;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 12px;
}

/* 模式选择器（参考短视频 EditorBar 的下拉式 mode selector） */
.sr-mode-wrap {
  position: relative;
  flex-shrink: 0;
  align-self: flex-start;
}

.sr-mode-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  border-radius: 8px;
  border: none;
  background: #eef0ff;
  color: #6366f1;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.sr-mode-trigger:hover {
  background: #e0e3ff;
}

.sr-mode-icon {
  display: flex;
  align-items: center;
  color: #6366f1;
}

.sr-mode-label {
  line-height: 1;
}

.sr-mode-arrow {
  transition: transform 0.2s;
  color: #6366f1;
  flex-shrink: 0;
}

.sr-mode-arrow-open {
  transform: rotate(180deg);
}

.sr-mode-popup {
  z-index: 1100;
  min-width: 240px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid rgba(111, 126, 153, 0.24);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 4px;
  animation: sr-mode-pop-in 0.15s ease-out;
}

.sr-mode-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1099;
  background: transparent;
}

@keyframes sr-mode-pop-in {
  from { opacity: 0; transform: translateY(4px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.sr-mode-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.sr-mode-option:hover {
  background: #f5f7fa;
}

.sr-mode-option-active {
  background: #f0f0ff;
}

.sr-mode-opt-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #f0f4ff;
  color: #6366f1;
  flex-shrink: 0;
}

.sr-mode-option-active .sr-mode-opt-icon {
  background: #e0e3ff;
}

.sr-mode-opt-text {
  flex: 1;
  min-width: 0;
}

.sr-mode-opt-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  line-height: 1.3;
}

.sr-mode-option-active .sr-mode-opt-title {
  color: #6366f1;
}

.sr-mode-opt-desc {
  display: block;
  font-size: 11px;
  color: #909399;
  line-height: 1.3;
  margin-top: 1px;
}

.sr-mode-opt-check {
  color: #6366f1;
  flex-shrink: 0;
}

/* 本地上传 hint 第二行 */
.sr-upload-hint-secondary {
  font-size: 12px;
  font-weight: 400;
  color: #C0C4CC;
  line-height: 1.4;
}

/* URL 输入 */
.sr-url-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.sr-url-input-row {
  display: flex;
  align-items: center;
  height: 44px;
  background: #fff;
  border: 1px solid #DCDFE6;
  border-radius: 10px;
  padding: 0 4px 0 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.sr-url-input-row:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.sr-url-icon {
  color: #6366f1;
  flex-shrink: 0;
  margin-right: 8px;
}

.sr-url-input {
  flex: 1;
  height: 100%;
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  color: #303133;
  min-width: 0;
}

.sr-url-input::placeholder {
  color: #C0C4CC;
}

.sr-url-clear {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #C0C4CC;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
}

.sr-url-clear:hover {
  color: #606266;
  background: rgba(0, 0, 0, 0.04);
}

.sr-url-paste {
  height: 32px;
  padding: 0 14px;
  border: none;
  background: #fff;
  color: #6366f1;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  margin-left: 4px;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: all 0.15s;
}

.sr-url-paste:hover {
  background: #F0F0FF;
  color: #4f46e5;
}

.sr-url-hint {
  font-size: 12px;
  color: #C0C4CC;
  line-height: 1.5;
}

/* 右列：模板 / 参数 / 提交 */
.sr-config-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

/* 源视频上传按钮 */
.sr-upload-btn {
  width: 100%;
  min-height: 140px;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: 2px dashed #D0D0E8;
  border-radius: 12px;
  background: #FAFBFC;
  color: #909399;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.18s ease;
  padding: 16px;
  box-sizing: border-box;
}

.sr-upload-btn:hover {
  border-color: #6366f1;
  background: #F0F0FF;
}

.sr-upload-icon {
  color: #6366f1;
  margin-bottom: 4px;
}

.sr-upload-label {
  font-size: 14px;
  font-weight: 700;
  color: #333;
  line-height: 1.2;
}

.sr-upload-hint {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
  line-height: 1.4;
}

.sr-source-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border: 1px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  border-radius: 10px;
  background: var(--glass-bg-surface, rgba(255, 255, 255, 0.92));
  position: relative;
}

.sr-source-thumb {
  position: relative;
  width: 96px;
  height: 56px;
  border-radius: 6px;
  overflow: hidden;
  background: #000;
  flex-shrink: 0;
}

.sr-source-thumb-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.sr-source-thumb-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
  pointer-events: none;
}

.sr-source-thumb-loading {
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.05));
  position: relative;
}

.sr-source-thumb-loading::after {
  content: '';
  position: absolute;
  inset: 30%;
  border: 2px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  border-top-color: var(--glass-accent-from, #3b82f6);
  border-radius: 50%;
  animation: sr-spin 0.8s linear infinite;
}

@keyframes sr-spin { to { transform: rotate(360deg); } }

.sr-source-info {
  flex: 1;
  min-width: 0;
}

.sr-source-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sr-source-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 11px;
  color: var(--glass-text-tertiary, #999);
  margin-top: 2px;
}

.sr-source-remove {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--glass-text-tertiary, #999);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}

.sr-source-remove:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

/* 模板卡片网格：3 列 × 2 行（上下结构：第一行图标+标题，第二行描述） */
.sr-template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.sr-template-card {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid #E4E7ED;
  background: #F5F7FA;
  cursor: pointer;
  transition: all 0.18s ease;
  min-height: 76px;
  box-sizing: border-box;
}

.sr-template-card:hover {
  border-color: #6366f1;
  background: #F0F0FF;
}

.sr-template-active {
  border-color: transparent !important;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.28);
}

.sr-template-title-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-height: 24px;
}

.sr-template-icon {
  width: 20px;
  height: 20px;
  background: transparent;
  color: #6366f1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.18s ease;
}

.sr-template-active .sr-template-icon {
  color: #fff;
}

.sr-template-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.18s ease;
}

.sr-template-active .sr-template-label {
  color: #fff;
}

.sr-template-desc {
  font-size: 11px;
  color: #909399;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color 0.18s ease;
}

.sr-template-active .sr-template-desc {
  color: rgba(255, 255, 255, 0.85);
}

/* 算子区 */
.sr-operators {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  padding: 8px;
  background: rgba(59, 130, 246, 0.04);
  border-radius: 10px;
  border: 1px dashed rgba(59, 130, 246, 0.3);
}

.sr-operator {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.6);
  transition: background 0.15s;
}

.sr-operator:hover { background: rgba(255, 255, 255, 0.9); }

.sr-operator-on {
  background: rgba(59, 130, 246, 0.12);
}

.sr-operator input[type="checkbox"] {
  margin-top: 2px;
  accent-color: #3b82f6;
}

.sr-operator-text {
  flex: 1;
  min-width: 0;
}

.sr-operator-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--glass-text-primary);
}

.sr-operator-desc {
  font-size: 10px;
  color: var(--glass-text-tertiary, #999);
  margin-top: 1px;
  line-height: 1.3;
}

/* 参数区：4 列等宽 */
.sr-params {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.sr-param {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.sr-param-compact {
  grid-column: span 1;
}

.sr-param-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  line-height: 1.2;
}

.sr-param-hint {
  font-size: 11px;
  color: #C0C4CC;
  font-weight: 400;
}

.sr-param-bitrate {
  grid-column: 1 / -1;
}

.sr-input {
  height: 38px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #DCDFE6;
  background: #fff;
  color: #303133;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
  box-sizing: border-box;
}

.sr-input:hover {
  border-color: #6366f1;
}

.sr-input:focus {
  border-color: #6366f1;
}

.sr-bitrate-row {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
}

.sr-bitrate-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(
    to right,
    #6366f1 0%,
    #6366f1 var(--progress, 0%),
    #E4E7ED var(--progress, 0%),
    #E4E7ED 100%
  );
  outline: none;
  cursor: pointer;
  margin: 0;
}

.sr-bitrate-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #6366f1;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 1px 4px rgba(99, 102, 241, 0.2);
}

.sr-bitrate-slider:hover::-webkit-slider-thumb {
  transform: scale(1.25);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
}

.sr-bitrate-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #6366f1;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.sr-bitrate-slider:hover::-moz-range-thumb {
  transform: scale(1.25);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
}

.sr-bitrate-input-wrap {
  position: relative;
  width: 64px;
  height: 34px;
  flex-shrink: 0;
}

.sr-bitrate-input {
  width: 100%;
  height: 100%;
  padding: 0 36px 0 8px;
  border-radius: 6px;
  border: 1px solid #DCDFE6;
  background: #F5F7FA;
  color: #303133;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
  box-sizing: border-box;
  -moz-appearance: textfield;
}

.sr-bitrate-input::-webkit-outer-spin-button,
.sr-bitrate-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.sr-bitrate-input:hover {
  border-color: #6366f1;
}

.sr-bitrate-input:focus {
  border-color: #6366f1;
  background: #fff;
}

.sr-bitrate-unit {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: #909399;
  pointer-events: none;
}

.sr-bitrate-reset {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
  border: 1px solid #DCDFE6;
  background: #fff;
  color: #909399;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}

.sr-bitrate-reset:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: #F0F0FF;
}

/* 提交按钮：位于源视频列底部 */
.sr-submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 42px;
  padding: 0 18px;
  border: none;
  border-radius: 21px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
  flex-shrink: 0;
  transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.18s ease;
}

.sr-submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(99, 102, 241, 0.45);
}

.sr-submit-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 3px 10px rgba(99, 102, 241, 0.35);
}

.sr-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.sr-file-input {
  display: none;
}

/* 响应式：窄屏单列模板 */
@media (max-width: 720px) {
  .sr-expanded {
    flex-direction: column;
  }
  .sr-source-col {
    flex-basis: auto;
  }
  .sr-upload-btn {
    min-height: 80px;
  }
  .sr-params {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .sr-template-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .sr-operators {
    grid-template-columns: 1fr;
  }
}
</style>
