<template>
  <div
    ref="barRef"
    class="eb-bar"
    :class="{
      'eb-mode-inline': editorMode === 'inline',
      'eb-mode-mini': editorMode === 'mini',
      'eb-mode-floating': editorMode === 'floating',
      'eb-dragover': isDragging,
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
      <div class="eb-mini-content" @click="handleMiniClick">
        <button class="eb-mini-add" @click.stop="handleAddReference">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
        </button>
        <span class="eb-mini-text">图片/视频/音频</span>
        <button
          class="glass-btn-base glass-btn-primary eb-mini-send"
          :disabled="!store.canGenerate"
          @click.stop="handleSubmit"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </template>

    <!-- ========== 展开状态 - 参考模式 ========== -->
    <template v-else-if="store.generationType === 'reference'">
      <div class="eb-ref-layout">
        <!-- 第一行：上传按钮 + 备选素材横排 -->
        <div class="eb-ref-top-row">
          <button class="eb-upload-btn" @click="handleAddReference">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
            <span class="eb-upload-btn-text">图片/视频/音频</span>
          </button>
          <div v-if="store.totalRefCount > 0 || isUploading" class="eb-ref-scroll">
            <ReferenceMediaBar
              :images="store.referenceImages"
              :videos="store.referenceVideos"
              :audios="store.referenceAudios"
              :uploading="isUploading"
              @remove="handleRemoveReference"
            />
          </div>
        </div>

        <!-- 第二行：编辑器 -->
        <div class="eb-ref-editor">
          <PromptEditor ref="promptEditorRef" :placeholder="refPlaceholder" compact />
        </div>

        <!-- 参数栏 -->
        <div class="eb-params">
          <div class="eb-param-group">
            <div class="eb-mode-wrap">
              <button class="eb-mode-trigger" @click.stop="toggleModeDropdown($event)">
                <span class="eb-mode-icon" v-html="modeOptions.find(o => o.value === store.generationType)?.icon" />
                <span class="eb-mode-label">{{ currentModeLabel }}</span>
                <svg class="eb-mode-arrow" :class="{ 'eb-mode-arrow-open': showModeDropdown }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
              </button>
              <Teleport to="body">
                <div v-if="showModeDropdown" class="eb-mode-popup" :style="modePopupStyle">
                  <div
                    v-for="opt in modeOptions" :key="opt.value"
                    class="eb-mode-option"
                    :class="{ 'eb-mode-option-active': store.generationType === opt.value }"
                    @click.stop="selectMode(opt.value)"
                  >
                    <span class="eb-mode-opt-icon" v-html="opt.icon" />
                    <div class="eb-mode-opt-text">
                      <span class="eb-mode-opt-title">{{ opt.label }}</span>
                      <span class="eb-mode-opt-desc">{{ opt.desc }}</span>
                    </div>
                    <svg v-if="store.generationType === opt.value" class="eb-mode-opt-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>
                  </div>
                </div>
              </Teleport>
            </div>
            <select v-model="store.ratio" class="eb-select">
              <option v-for="r in ratios" :key="r" :value="r">{{ r === 'adaptive' ? '自适应' : r }}</option>
            </select>
            <select v-model="store.resolution" class="eb-select">
              <option value="480p">480p</option>
              <option value="720p">720p</option>
              <option value="1080p">1080p</option>
            </select>
            <select v-model="store.duration" class="eb-select">
              <option v-for="d in durations" :key="d" :value="d">{{ d }}s</option>
            </select>
            <label class="eb-checkbox">
              <span class="eb-checkbox-box" :class="{ 'eb-checkbox-on': store.generateAudio }" @click.prevent="store.generateAudio = !store.generateAudio">
                <svg v-if="store.generateAudio" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              </span>
              <span>音频</span>
            </label>
          </div>
          <button class="eb-clear-btn" @click="handleClear">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            全部清空
          </button>
          <span class="eb-cost-hint">
            <svg class="eb-cost-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5l1.95 6.18a3 3 0 0 0 1.91 1.91L22 12.5l-6.14 1.91a3 3 0 0 0-1.91 1.91L12 22.5l-1.95-6.18a3 3 0 0 0-1.91-1.91L2 12.5l6.14-1.91a3 3 0 0 0 1.91-1.91L12 2.5z"/></svg>
            {{ costText }}
          </span>
          <button
            class="glass-btn-base glass-btn-primary eb-generate-btn"
            :disabled="!store.canGenerate"
            @click="handleSubmit"
          >
            生成视频
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
          </button>
        </div>
      </div>
    </template>

    <!-- ========== 展开状态 - 首尾帧模式 ========== -->
    <template v-else>
      <div class="eb-frame-layout">
        <!-- 主编辑区 -->
        <div class="eb-frame-main">
          <!-- 左侧：首尾帧选择 -->
          <div class="eb-frame-left">
            <!-- 首帧 -->
            <div class="eb-frame-card">
              <div class="eb-frame-thumb-wrap" @click="store.firstFrameUrl ? previewFrame(store.firstFrameUrl) : pickFrame('first')">
                <div v-if="frameUploading === 'first'" class="eb-frame-loading" />
                <img v-else-if="store.firstFrameUrl" :src="store.firstFrameUrl" class="eb-frame-thumb" />
                <div v-else class="eb-frame-placeholder">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
                </div>
                <span class="eb-frame-tag eb-frame-tag-first">首帧</span>
                <button v-if="store.firstFrameUrl" class="eb-frame-remove" @click.stop="removeFrame('first')">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
                </button>
              </div>
              <span class="eb-frame-label">首帧</span>
            </div>
            <!-- 交换按钮 -->
            <button class="eb-frame-swap" @click="swapFrames" :disabled="!store.firstFrameUrl && !store.lastFrameUrl">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M7 16l-4-4 4-4"/><path d="M17 8l4 4-4 4"/><path d="M3 12h18"/></svg>
            </button>
            <!-- 尾帧 -->
            <div class="eb-frame-card">
              <div class="eb-frame-thumb-wrap" @click="store.lastFrameUrl ? previewFrame(store.lastFrameUrl) : pickFrame('last')">
                <div v-if="frameUploading === 'last'" class="eb-frame-loading" />
                <img v-else-if="store.lastFrameUrl" :src="store.lastFrameUrl" class="eb-frame-thumb" />
                <div v-else class="eb-frame-placeholder">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
                </div>
                <span class="eb-frame-tag eb-frame-tag-last">尾帧</span>
                <button v-if="store.lastFrameUrl" class="eb-frame-remove" @click.stop="removeFrame('last')">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
                </button>
              </div>
              <span class="eb-frame-label">尾帧</span>
            </div>
          </div>
          <!-- 右侧：编辑器 -->
          <div class="eb-frame-right">
            <PromptEditor ref="promptEditorRef" :placeholder="framePlaceholder" compact />
          </div>
        </div>

        <!-- 参数栏 -->
        <div class="eb-params">
          <div class="eb-param-group">
            <div class="eb-mode-wrap">
              <button class="eb-mode-trigger" @click.stop="toggleModeDropdown($event)">
                <span class="eb-mode-icon" v-html="modeOptions.find(o => o.value === store.generationType)?.icon" />
                <span class="eb-mode-label">{{ currentModeLabel }}</span>
                <svg class="eb-mode-arrow" :class="{ 'eb-mode-arrow-open': showModeDropdown }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
              </button>
              <Teleport to="body">
                <div v-if="showModeDropdown" class="eb-mode-popup" :style="modePopupStyle">
                  <div
                    v-for="opt in modeOptions" :key="opt.value"
                    class="eb-mode-option"
                    :class="{ 'eb-mode-option-active': store.generationType === opt.value }"
                    @click.stop="selectMode(opt.value)"
                  >
                    <span class="eb-mode-opt-icon" v-html="opt.icon" />
                    <div class="eb-mode-opt-text">
                      <span class="eb-mode-opt-title">{{ opt.label }}</span>
                      <span class="eb-mode-opt-desc">{{ opt.desc }}</span>
                    </div>
                    <svg v-if="store.generationType === opt.value" class="eb-mode-opt-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>
                  </div>
                </div>
              </Teleport>
            </div>
            <select v-model="store.ratio" class="eb-select">
              <option v-for="r in ratios" :key="r" :value="r">{{ r === 'adaptive' ? '自适应' : r }}</option>
            </select>
            <select v-model="store.resolution" class="eb-select">
              <option value="480p">480p</option>
              <option value="720p">720p</option>
              <option value="1080p">1080p</option>
            </select>
            <select v-model="store.duration" class="eb-select">
              <option v-for="d in durations" :key="d" :value="d">{{ d }}s</option>
            </select>
            <label class="eb-checkbox">
              <span class="eb-checkbox-box" :class="{ 'eb-checkbox-on': store.generateAudio }" @click.prevent="store.generateAudio = !store.generateAudio">
                <svg v-if="store.generateAudio" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              </span>
              <span>音频</span>
            </label>
          </div>
          <button class="eb-clear-btn" @click="handleClear">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            全部清空
          </button>
          <span class="eb-cost-hint">
            <svg class="eb-cost-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5l1.95 6.18a3 3 0 0 0 1.91 1.91L22 12.5l-6.14 1.91a3 3 0 0 0-1.91 1.91L12 22.5l-1.95-6.18a3 3 0 0 0-1.91-1.91L2 12.5l6.14-1.91a3 3 0 0 0 1.91-1.91L12 2.5z"/></svg>
            {{ costText }}
          </span>
          <button
            class="glass-btn-base glass-btn-primary eb-generate-btn"
            :disabled="!store.canGenerate"
            @click="handleSubmit"
          >
            生成视频
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
          </button>
        </div>
      </div>
    </template>
  </div>

  <!-- 拖拽上传遮罩 -->
  <div v-if="isDragging" class="eb-drop-overlay">
    <div class="eb-drop-inner">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <p class="eb-drop-title">松开鼠标上传到编辑区</p>
      <p class="eb-drop-hint">{{ dropHintText }}</p>
    </div>
  </div>

  <!-- 隐藏文件上传 input -->
  <input ref="fileInputRef" type="file" :accept="fileAccept" style="display:none" @change="handleFileChange" />

  <!-- 首尾帧预览弹窗 -->
  <Teleport to="body">
    <div v-if="framePreviewUrl" class="eb-frame-preview-mask" @click="framePreviewUrl = null">
      <div class="eb-frame-preview-box" @click.stop>
        <img :src="framePreviewUrl" class="eb-frame-preview-img" />
        <button class="eb-frame-preview-close" @click="framePreviewUrl = null">×</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import ReferenceMediaBar from './ReferenceMediaBar.vue'
import PromptEditor from './PromptEditor.vue'
import { useShortVideoStore, INPUT_LIMITS } from '@/store/shortVideo'
import { directUpload, directUploadWithThumbnail, isHeicFile, convertHeicToJpegFile } from '@/utils/cosUpload'
import { uploadShortVideoAsset } from '@/api/shortVideo'

const props = defineProps({
  editorMode: { type: String, default: 'inline', validator: v => ['inline', 'mini', 'floating'].includes(v) },
})

const emit = defineEmits(['expand', 'focusChange', 'openProjectPicker', 'openAssetCenter'])

const refPlaceholder = '使用@可快速引用上传的文件，如：参考@视频1 中的动作，生成@图片2 和@图片3 中的角色打斗的视频。（不支持真实人像）'
const framePlaceholder = '输入你想要生成的内容画面，或结合图片输入创意描述（可选）。（不支持真实人像）'

const store = useShortVideoStore()
const ratios = ['16:9', '9:16', '1:1', '4:3', '3:4', '21:9', 'adaptive']
const durations = Array.from({ length: 12 }, (_, i) => i + 4)

const barRef = ref(null)
const fileInputRef = ref(null)
const promptEditorRef = ref(null)
const pendingFrameType = ref(null)
const isUploading = ref(false)
const frameUploading = ref(null) // 'first' | 'last' | null
const showModeDropdown = ref(false)
const framePreviewUrl = ref(null)

const modeOptions = [
  { value: 'reference', label: '参考生成', desc: '上传图片/视频/音频作为参考', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>' },
  { value: 'first_last_frame', label: '首尾帧', desc: '上传首帧和尾帧图片生成视频', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="8" height="16" rx="1"/><path d="M14 12h6"/><path d="m17 9 3 3-3 3"/><rect x="14" y="4" width="8" height="4" rx="1" opacity="0.4"/><rect x="14" y="16" width="8" height="4" rx="1" opacity="0.4"/></svg>' },
]

const currentModeLabel = computed(() => {
  const opt = modeOptions.find(o => o.value === store.generationType)
  return opt ? opt.label : ''
})

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

const modePopupStyle = ref({})

function selectMode(val) {
  store.generationType = val
  showModeDropdown.value = false
}

function onClickOutsideMode(e) {
  if (showModeDropdown.value) {
    const trigger = document.querySelector('.eb-mode-trigger')
    const popup = document.querySelector('.eb-mode-popup')
    if (trigger && trigger.contains(e.target)) return
    if (popup && popup.contains(e.target)) return
    showModeDropdown.value = false
  }
}

document.addEventListener('click', onClickOutsideMode, true)
onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutsideMode, true)
})

defineExpose({ promptEditorRef })

const fileAccept = computed(() => {
  if (pendingFrameType.value) return '.jpeg,.jpg,.png,.webp,.bmp,.tiff,.gif,.heic,.heif'
  return '.jpeg,.jpg,.png,.webp,.bmp,.tiff,.gif,.heic,.heif,.mp4,.mov,.mp3,.wav'
})

const dropHintText = computed(() => {
  if (store.generationType === 'first_last_frame') {
    return '首尾帧模式仅支持图片（自动填充首帧 / 尾帧空位）'
  }
  return '支持图片 / 视频 / 音频'
})

// 每秒积分消耗：是否添加视频 + 分辨率决定
const CREDITS_PER_SECOND = {
  noVideo: { '1080p': 410, '720p': 164, '480p': 76 },
  withVideo: { '1080p': 246, '720p': 98, '480p': 46 },
}

const costText = computed(() => {
  const hasVideo = store.referenceVideos.length > 0
  const tbl = hasVideo ? CREDITS_PER_SECOND.withVideo : CREDITS_PER_SECOND.noVideo
  const n = tbl[store.resolution] ?? 0
  return hasVideo ? `${n}/秒（含输入时长）` : `${n}/秒`
})

// 从迷你状态切换到展开状态时自动聚焦编辑器
watch(() => props.editorMode, async (newMode) => {
  if (newMode !== 'mini') {
    await nextTick()
    if (promptEditorRef.value) {
      promptEditorRef.value.focus()
    }
  }
})

// 切换模式时清空引用
watch(() => store.generationType, (newType) => {
  if (newType === 'first_last_frame') {
    store.referenceImages.splice(0)
    store.referenceVideos.splice(0)
    store.referenceAudios.splice(0)
    store.promptText = ''
  }
})

// 焦点跟踪
function onFocusIn() {
  emit('focusChange', true)
}

function onFocusOut() {
  requestAnimationFrame(() => {
    if (barRef.value && !barRef.value.contains(document.activeElement)) {
      emit('focusChange', false)
    }
  })
}

function handleMiniClick() {
  emit('expand')
}

async function handleSubmit() {
  const res = await store.submit()
  if (res) ElMessage.success('任务已提交')
}

function handleClear() {
  store.clearEditor()
}

function pickFrame(type) {
  pendingFrameType.value = type
  nextTick(() => fileInputRef.value?.click())
}

function swapFrames() {
  const tmp = store.firstFrameUrl
  store.firstFrameUrl = store.lastFrameUrl
  store.lastFrameUrl = tmp
}

function removeFrame(type) {
  if (type === 'first') store.firstFrameUrl = null
  else store.lastFrameUrl = null
}

function previewFrame(url) {
  if (url) framePreviewUrl.value = url
}

function handleAddReference() {
  pendingFrameType.value = null
  nextTick(() => fileInputRef.value?.click())
}

function handleRemoveReference(type, index) {
  const listMap = { image: store.referenceImages, video: store.referenceVideos, audio: store.referenceAudios }
  const list = listMap[type]
  const removedLabel = list[index]?.refLabel
  const oldLabels = list.map(r => r.refLabel)

  store.removeReference(type, index)

  const newLabels = list.map(r => r.refLabel)
  let text = store.promptText

  if (removedLabel) {
    text = text.split(`@${removedLabel}`).join('')
  }
  for (let oi = 0, ni = 0; oi < oldLabels.length; oi++) {
    if (oi === index) continue
    if (oldLabels[oi] !== newLabels[ni]) {
      text = text.split(`@${oldLabels[oi]}`).join(`@${newLabels[ni]}`)
    }
    ni++
  }
  text = text.replace(/\s+/g, ' ').trim()
  store.promptText = text
}

// 文件校验
const ALLOWED_FORMATS = {
  image: { exts: ['.jpeg', '.jpg', '.png', '.webp', '.bmp', '.tiff', '.gif', '.heic', '.heif'], maxSize: 30 * 1024 * 1024 },
  video: { exts: ['.mp4', '.mov'], maxSize: 50 * 1024 * 1024 },
  audio: { exts: ['.mp3', '.wav'], maxSize: 15 * 1024 * 1024 },
}

// 火山引擎素材约束（前端只卡可量化的明确边界）
// 分辨率档位（480p/720p/1080p）语义模糊、前端无法准确判定，交给火山 API 兜底
const MEDIA_CONSTRAINTS = {
  image: { aspectMin: 0.4, aspectMax: 2.5, dimMin: 300, dimMax: 6000 },
  video: {
    aspectMin: 0.4, aspectMax: 2.5,
    dimMin: 300, dimMax: 6000,
    pixelsMin: 409600, pixelsMax: 2086876,
  },
}

function getFileType(file) {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  for (const [type, cfg] of Object.entries(ALLOWED_FORMATS)) {
    if (cfg.exts.includes(ext)) return type
  }
  return null
}

// 读取媒体元数据：图片读宽高，视频读宽高+时长，音频读时长
// HEIC/HEIF 在多数浏览器无法解码，返回 dimensionReadable:false，校验阶段跳过尺寸检查由后端兜底
function getMediaMetadata(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const type = getFileType(file)
    if (type === 'image') {
      const img = new Image()
      img.onload = () => {
        URL.revokeObjectURL(url)
        resolve({ duration: null, width: img.naturalWidth, height: img.naturalHeight })
      }
      img.onerror = () => {
        URL.revokeObjectURL(url)
        resolve({ duration: null, width: null, height: null, dimensionReadable: false })
      }
      img.src = url
    } else if (type === 'video' || type === 'audio') {
      const media = type === 'video' ? document.createElement('video') : document.createElement('audio')
      media.onloadedmetadata = () => {
        URL.revokeObjectURL(url)
        resolve({
          duration: media.duration,
          width: type === 'video' ? media.videoWidth : null,
          height: type === 'video' ? media.videoHeight : null,
        })
      }
      media.onerror = () => {
        URL.revokeObjectURL(url)
        reject(new Error('无法读取文件元数据'))
      }
      media.src = url
    } else {
      URL.revokeObjectURL(url)
      reject(new Error('不支持的文件类型'))
    }
  })
}

function validateFile(file, meta = {}) {
  const type = getFileType(file)
  if (!type) {
    ElMessage.error(`不支持的文件格式：${file.name}`)
    return null
  }
  const cfg = ALLOWED_FORMATS[type]
  if (file.size > cfg.maxSize) {
    ElMessage.error(`${file.name} 超过大小限制（${cfg.maxSize / 1024 / 1024}MB）`)
    return null
  }
  const countMap = { image: store.referenceImages.length, video: store.referenceVideos.length, audio: store.referenceAudios.length }
  if (store.totalRefCount >= INPUT_LIMITS.maxTotal) {
    ElMessage.warning(`总文件数已达上限（${INPUT_LIMITS.maxTotal}个）`)
    return null
  }
  const typeLimit = type === 'image' ? INPUT_LIMITS.maxImages : type === 'video' ? INPUT_LIMITS.maxVideos : INPUT_LIMITS.maxAudios
  if (countMap[type] >= typeLimit) {
    ElMessage.warning(`${type === 'image' ? '图片' : type === 'video' ? '视频' : '音频'}数量已达上限`)
    return null
  }

  // 时长校验（视频/音频，统一取整避免浮点偏差）
  const roundedDuration = meta.duration != null ? Math.round(meta.duration) : null
  if (type === 'video' && roundedDuration != null) {
    if (roundedDuration < 2 || roundedDuration > 15) {
      ElMessage.error(`视频时长需在 2-15 秒之间（当前 ${roundedDuration} 秒）`)
      return null
    }
    const existingDuration = store.referenceVideos.reduce((sum, v) => sum + Math.round(v.duration || 0), 0)
    if (existingDuration + roundedDuration > 15) {
      ElMessage.error(`上传后视频总时长将超过 15 秒限制（已有 ${existingDuration} 秒）`)
      return null
    }
  }
  if (type === 'audio' && roundedDuration != null) {
    if (roundedDuration < 2 || roundedDuration > 15) {
      ElMessage.error(`音频时长需在 2-15 秒之间（当前 ${roundedDuration} 秒）`)
      return null
    }
    const existingDuration = store.referenceAudios.reduce((sum, a) => sum + Math.round(a.duration || 0), 0)
    if (existingDuration + roundedDuration > 15) {
      ElMessage.error(`上传后音频总时长将超过 15 秒限制（已有 ${existingDuration} 秒）`)
      return null
    }
  }

  // 尺寸校验（图片/视频，HEIC/HEIF 等浏览器无法解码时跳过由后端兜底）
  if ((type === 'image' || type === 'video') && meta.dimensionReadable !== false && meta.width && meta.height) {
    const c = MEDIA_CONSTRAINTS[type]
    const w = meta.width
    const h = meta.height
    const ratio = w / h
    if (w < c.dimMin || w > c.dimMax || h < c.dimMin || h > c.dimMax) {
      ElMessage.error(`${file.name} 像素需在 ${c.dimMin}-${c.dimMax}px 之间（当前 ${w}×${h}）`)
      return null
    }
    if (ratio < c.aspectMin || ratio > c.aspectMax) {
      ElMessage.error(`${file.name} 宽高比需在 ${c.aspectMin}-${c.aspectMax} 之间（当前 ${ratio.toFixed(2)}）`)
      return null
    }
    if (type === 'video') {
      const pixels = w * h
      if (pixels < c.pixelsMin || pixels > c.pixelsMax) {
        ElMessage.error(`${file.name} 总像素数需在 ${c.pixelsMin}-${c.pixelsMax} 之间（当前 ${pixels}）`)
        return null
      }
    }
  }

  return type
}

async function uploadOneFile(file, frameType) {
  // HEIC/HEIF 在 Chrome/Firefox 无法原生预览，先转 JPEG 后走标准流程（火山支持 JPEG）
  if (isHeicFile(file)) {
    try {
      file = await convertHeicToJpegFile(file)
    } catch (err) {
      console.warn('[heic] 转换失败:', err)
      ElMessage.error('HEIC 文件解码失败，请尝试转换为 JPEG 后再上传')
      return false
    }
  }

  // 先快速校验格式和大小（避免大文件先读取元数据再拦截）
  const assetType = getFileType(file)
  if (!assetType) {
    ElMessage.error(`不支持的文件格式：${file.name}`)
    return false
  }
  const cfg = ALLOWED_FORMATS[assetType]
  if (file.size > cfg.maxSize) {
    ElMessage.error(`${file.name} 超过大小限制（${cfg.maxSize / 1024 / 1024}MB）`)
    return false
  }

  if (file.name.length > 64) {
    ElMessage.error('文件名称长度不能超过64个字符')
    return false
  }

  // 读取媒体元数据（图片读尺寸，视频读尺寸+时长，音频读时长）
  let meta = { duration: null, width: null, height: null }
  try {
    meta = await getMediaMetadata(file)
  } catch {
    ElMessage.error('无法读取文件信息，请检查文件是否损坏')
    return false
  }
  const duration = meta.duration != null ? Math.round(meta.duration) : null

  const validatedType = validateFile(file, meta)
  if (!validatedType) {
    return false
  }

  if (frameType) {
    frameUploading.value = frameType
  } else {
    isUploading.value = true
  }
  try {
    // 直传 COS（图片类型同时直传缩略图）
    let cosKey, url, thumbnailCosKey
    if (assetType === 'image') {
      const res = await directUploadWithThumbnail(file, { category: 'upload', biz: 'temp', maxSize: cfg.maxSize })
      cosKey = res.cos_key
      url = res.url
      thumbnailCosKey = res.thumbnail_cos_key
    } else {
      const res = await directUpload(file, { category: 'upload', biz: 'temp', maxSize: cfg.maxSize })
      cosKey = res.cos_key
      url = res.url
    }

    if (!url) {
      ElMessage.error('上传失败')
      return false
    }

    let thumbnailUrl = null
    let volcAssetId = null
    try {
      const assetData = {
        asset_name: file.name,
        asset_type: assetType,
        asset_url: url,
        asset_key: cosKey,
        asset_size: file.size,
        mime_type: file.type || 'application/octet-stream',
        source: 'upload',
        duration: duration,
      }
      if (thumbnailCosKey) {
        assetData.thumbnail_key = thumbnailCosKey
      }
      const assetRes = await uploadShortVideoAsset(assetData)
      thumbnailUrl = assetRes.thumbnail_url || null
      volcAssetId = assetRes.volc_asset_id || null
    } catch (err) {
      console.warn('资产库保存失败:', err)
    }

    if (frameType === 'first') {
      store.firstFrameUrl = url
      store.firstFrameVolcId = volcAssetId
    } else if (frameType === 'last') {
      store.lastFrameUrl = url
      store.lastFrameVolcId = volcAssetId
    } else {
      const refLabel = assetType === 'image' ? `图片${store.getRefCount('image') + 1}` : assetType === 'video' ? `视频${store.getRefCount('video') + 1}` : `音频${store.getRefCount('audio') + 1}`
      const added = store.addReference(assetType, { url, name: file.name, refLabel, thumbnail_url: thumbnailUrl, cos_key: cosKey, volc_asset_id: volcAssetId, duration })
      if (!added) {
        ElMessage.warning(`该文件已存在：${file.name}`)
      }
    }
    return true
  } catch {
    // 错误提示由 request 拦截器统一处理（凭证接口失败时）
    return false
  } finally {
    isUploading.value = false
    frameUploading.value = null
  }
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    await uploadOneFile(file, pendingFrameType.value)
  } finally {
    e.target.value = ''
    pendingFrameType.value = null
  }
}

// ── 拖拽上传 ──
const dragCounter = ref(0)
const isDragging = computed(() => dragCounter.value > 0)

function onDragEnter(e) {
  // 仅在拖入文件时计数（排除内部拖拽选区等）
  if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) {
    dragCounter.value++
  }
}

function onDragLeave() {
  dragCounter.value = Math.max(0, dragCounter.value - 1)
}

async function onDrop(e) {
  dragCounter.value = 0
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length === 0) return

  // 迷你模式下先触发展开（展开后会以 floating 形式显示）
  if (props.editorMode === 'mini') {
    emit('expand')
  }

  if (store.generationType === 'first_last_frame') {
    // 首尾帧模式：只接受图片，按 [首帧空位, 尾帧空位] 顺序填充，都满则覆盖首帧
    const images = files.filter(f => getFileType(f) === 'image')
    const skipped = files.length - images.length
    if (skipped > 0) {
      ElMessage.warning(`首尾帧模式仅支持图片，已跳过 ${skipped} 个非图片文件`)
    }
    if (images.length === 0) return
    let cursor = 0
    while (cursor < images.length && cursor < 2) {
      const slot = !store.firstFrameUrl ? 'first' : (!store.lastFrameUrl ? 'last' : null)
      if (!slot) break
      await uploadOneFile(images[cursor], slot)
      cursor++
    }
    if (cursor < images.length) {
      ElMessage.warning(`首尾帧已满，已跳过 ${images.length - cursor} 张图片`)
    }
    return
  }

  // 参考模式：依次上传所有支持的文件
  for (const file of files) {
    await uploadOneFile(file, null)
  }
}
</script>

<style scoped>
/* ===== 通用容器 ===== */
.eb-bar {
  position: relative;
  background: var(--glass-bg-surface-strong, rgba(255, 255, 255, 0.94));
  border: 1px solid var(--glass-stroke-soft, rgba(255, 255, 255, 0.22));
  backdrop-filter: blur(var(--glass-blur-lg, 12px));
  overflow: hidden;
  display: flex;
  flex-direction: column;
  width: 100%;
  transition: max-width 0.25s ease,
              max-height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              border-radius 0.25s ease,
              box-shadow 0.25s ease;
}

/* 拖拽高亮 */
.eb-dragover {
  border-color: var(--glass-accent-from, #3b82f6) !important;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.35),
              var(--glass-shadow-lg, 0 10px 24px rgba(20, 35, 69, 0.1)) !important;
}

/* 拖拽遮罩 */
.eb-drop-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  background: rgba(59, 130, 246, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  border-radius: inherit;
}

.eb-drop-inner {
  text-align: center;
  color: var(--glass-accent-from, #3b82f6);
  padding: 8px 12px;
}

.eb-drop-title {
  margin: 6px 0 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
}

.eb-drop-hint {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--glass-text-tertiary, #6b7280);
  line-height: 1.3;
}

/* mini 模式下遮罩紧凑显示 */
.eb-mode-mini .eb-drop-inner svg {
  width: 20px;
  height: 20px;
}
.eb-mode-mini .eb-drop-title {
  font-size: 12px;
}
.eb-mode-mini .eb-drop-hint {
  display: none;
}

/* ===== 三种模式 ===== */
.eb-mode-inline {
  max-width: 100%;
  margin: 0 auto;
  border-radius: 16px;
  box-shadow: var(--glass-shadow-lg, 0 10px 24px rgba(20, 35, 69, 0.1));
  max-height: min(400px, 40vh);
}

.eb-mode-mini {
  max-width: 80%;
  margin: 0 auto;
  border-radius: 16px;
  box-shadow: var(--glass-shadow-md, 0 6px 18px rgba(19, 35, 66, 0.08));
  max-height: 56px;
  cursor: pointer;
}

.eb-mode-floating {
  max-width: 100%;
  margin: 0 auto;
  border-radius: 16px;
  box-shadow: var(--glass-shadow-lg, 0 10px 24px rgba(20, 35, 69, 0.1));
  max-height: min(400px, 40vh);
}

/* ===== 迷你状态内容 ===== */
.eb-mini-content {
  display: flex;
  align-items: center;
  height: 54px;
  padding: 0 14px;
  gap: 10px;
}

.eb-mini-add {
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

.eb-mini-add:hover {
  border-color: var(--glass-accent-from, #3b82f6);
  color: var(--glass-accent-from, #3b82f6);
}

.eb-mini-text {
  flex: 1;
  font-size: 14px;
  color: var(--glass-text-tertiary, #4b5563);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eb-mini-send {
  width: 36px !important;
  height: 36px !important;
  padding: 0 !important;
  border-radius: 50% !important;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 50%, #3b82f6 100%) !important;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
}

/* ===== 参数栏（共用） ===== */
.eb-params {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-top: 1px solid var(--glass-stroke-soft, rgba(255, 255, 255, 0.22));
  flex-shrink: 0;
  margin-top: auto;
}

.eb-param-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.eb-select {
  height: 34px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  background: var(--glass-bg-surface, rgba(255, 255, 255, 0.88));
  color: var(--glass-text-primary, #0a0a0a);
  font-size: 13px;
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s;
}

.eb-select:focus {
  border-color: var(--glass-accent-from, #3b82f6);
}

/* ===== 模式切换按钮 ===== */
.eb-mode-wrap {
  position: relative;
}

.eb-mode-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 34px;
  padding: 0 10px;
  border-radius: 8px;
  border: none;
  background: #e8f0fe;
  color: #3b82f6;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.eb-mode-trigger:hover {
  background: #dbeafe;
}

.eb-mode-icon {
  display: flex;
  align-items: center;
  color: #3b82f6;
}

.eb-mode-label {
  line-height: 1;
}

.eb-mode-arrow {
  transition: transform 0.2s;
  color: #3b82f6;
  flex-shrink: 0;
}

.eb-mode-arrow-open {
  transform: rotate(180deg);
}

.eb-mode-popup {
  z-index: 1100;
  min-width: 240px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 4px;
  animation: eb-mode-pop-in 0.15s ease-out;
}

@keyframes eb-mode-pop-in {
  from { opacity: 0; transform: translateY(4px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.eb-mode-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.eb-mode-option:hover {
  background: #f5f7fa;
}

.eb-mode-option-active {
  background: #eff6ff;
}

.eb-mode-opt-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #f0f4ff;
  color: #3b82f6;
  flex-shrink: 0;
}

.eb-mode-option-active .eb-mode-opt-icon {
  background: #dbeafe;
}

.eb-mode-opt-text {
  flex: 1;
  min-width: 0;
}

.eb-mode-opt-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--glass-text-primary, #0a0a0a);
  line-height: 1.3;
}

.eb-mode-option-active .eb-mode-opt-title {
  color: #3b82f6;
}

.eb-mode-opt-desc {
  display: block;
  font-size: 11px;
  color: var(--glass-text-tertiary, #999);
  line-height: 1.3;
  margin-top: 1px;
}

.eb-mode-opt-check {
  color: #3b82f6;
  flex-shrink: 0;
}

.eb-checkbox {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-primary, #0a0a0a);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}

.eb-checkbox-box {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px;
  border: 1.5px solid rgba(111,126,153,0.36);
  border-radius: 4px;
  background: #fff;
  transition: all 0.15s;
}
.eb-checkbox-on {
  background: #2f7bff;
  border-color: #2f7bff;
  color: #fff;
}
.eb-checkbox-box svg { display: block; }

.eb-cost-hint {
  font-size: 12px;
  color: #9ca3af;
  margin-right: 4px;
  margin-left: auto;
  white-space: nowrap;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.eb-cost-icon {
  color: #3b82f6;
  flex-shrink: 0;
}

.eb-generate-btn {
  height: 36px !important;
  padding: 0 20px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 50%, #3b82f6 100%) !important;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
}

.eb-generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45) !important;
}

.eb-clear-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 36px;
  padding: 0 10px;
  border: none;
  background: transparent;
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.15s;
}

.eb-clear-btn:hover {
  color: #3b82f6;
}

/* ===== 参考模式展开 ===== */
.eb-ref-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.eb-ref-top-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid var(--glass-stroke-soft);
  flex-shrink: 0;
}

.eb-upload-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 6.5rem;
  height: 3.25rem;
  padding: 0.375rem 0;
  border-radius: 8px;
  border: 1.5px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  background: transparent;
  color: var(--glass-text-tertiary, #4b5563);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.eb-upload-btn:hover {
  border-color: var(--glass-accent-from, #3b82f6);
  color: var(--glass-accent-from, #3b82f6);
}

.eb-upload-btn-text {
  font-size: 11px;
  line-height: 1.2;
  text-align: center;
  white-space: nowrap;
}

.eb-ref-scroll {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  min-width: 0;
}

.eb-ref-editor {
  flex: 1;
  min-height: 0;
  padding: 0 0.75rem;
}

/* ===== 首尾帧模式展开 ===== */
.eb-frame-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.eb-frame-main {
  display: flex;
  flex: 1;
  min-height: 0;
}

.eb-frame-left {
  flex-shrink: 0;
  padding: 0.5rem 0.5rem 0.5rem 0.75rem;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.eb-frame-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.eb-frame-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.eb-frame-thumb-wrap {
  position: relative;
  width: 72px;
  height: 72px;
  cursor: pointer;
}

.eb-frame-placeholder {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  border: 1.5px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--glass-text-tertiary, #4b5563);
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.03));
  transition: border-color 0.2s;
}

.eb-frame-placeholder:hover {
  border-color: var(--glass-accent-from, #3b82f6);
}

.eb-frame-thumb {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  object-fit: cover;
  display: block;
}

.eb-frame-loading {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  background: var(--glass-bg-muted, rgba(0, 0, 0, 0.04));
  border: 1.5px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  position: relative;
}

.eb-frame-loading::after {
  content: '';
  width: 24px;
  height: 24px;
  border: 2.5px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  border-top-color: var(--glass-accent-from, #3b82f6);
  border-radius: 50%;
  animation: eb-frame-spin 0.8s linear infinite;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

@keyframes eb-frame-spin {
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.eb-frame-tag {
  position: absolute;
  bottom: 3px;
  left: 3px;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  line-height: 1.4;
}

.eb-frame-tag-first { background: rgba(59, 130, 246, 0.85); }
.eb-frame-tag-last { background: rgba(245, 158, 11, 0.85); }

.eb-frame-remove {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.95);
  color: var(--glass-text-tertiary, #999);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  transition: all 0.15s;
  padding: 0;
}

.eb-frame-remove:hover {
  color: #ef4444;
  background: #fff;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.25);
}

.eb-frame-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--glass-text-tertiary, #666);
}

/* 交换按钮 */
.eb-frame-swap {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  background: var(--glass-bg-surface, #fff);
  color: var(--glass-text-tertiary, #999);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  padding: 0;
  flex-shrink: 0;
  align-self: center;
}

.eb-frame-swap:hover:not(:disabled) {
  border-color: var(--glass-accent-from, #3b82f6);
  color: var(--glass-accent-from, #3b82f6);
  background: #eff6ff;
}

.eb-frame-swap:disabled {
  opacity: 0.3;
  cursor: default;
}

/* 首尾帧预览弹窗 */
.eb-frame-preview-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: eb-frame-fadeIn 0.15s ease-out;
}

.eb-frame-preview-box {
  position: relative;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.eb-frame-preview-img {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 0.5rem;
}

.eb-frame-preview-close {
  position: absolute;
  top: -12px;
  right: -12px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.eb-frame-preview-close:hover {
  background: rgba(239, 68, 68, 0.8);
}

@keyframes eb-frame-fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ===== 响应式适配 ===== */
@media (min-width: 768px) {
  .eb-mode-inline,
  .eb-mode-floating {
    max-width: 960px;
  }
  .eb-mode-mini {
    max-width: 600px;
  }
}

@media (max-width: 640px) {
  .eb-mode-mini {
    max-width: 92%;
  }

  .eb-params {
    flex-wrap: wrap;
    gap: 0.25rem;
    padding: 0.25rem 0.5rem;
  }

  .eb-param-group {
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .eb-generate-btn {
    width: 100%;
    justify-content: center;
  }

  .eb-frame-main {
    flex-direction: column;
  }

  .eb-frame-left {
    border-bottom: 1px solid var(--glass-stroke-soft);
    padding: 0.375rem;
  }
}

/* 小高度屏幕：编辑框占用更少空间 */
@media (max-height: 700px) {
  .eb-mode-inline,
  .eb-mode-floating {
    max-height: min(320px, 35vh);
  }
}

@media (max-height: 500px) {
  .eb-mode-inline,
  .eb-mode-floating {
    max-height: min(240px, 30vh);
  }
}
</style>
