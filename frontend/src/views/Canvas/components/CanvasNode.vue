<template>
  <div class="cn-node" :class="[`cn-type-${data?.item_type}`, {
    'cn-selected': selected,
    'cn-running': isRunning,
    'cn-failed': isFailed,
    'cn-editing': isEditing,
    'cn-dimmed': dimmed,
    'cn-asset': !!data?.asset_tag,
    [`cn-asset-${data?.asset_tag}`]: !!data?.asset_tag,
  }]">
    <!-- 节点上方浮动资产操作条（图片/视频/音频节点，hover/选中时显示） -->
    <div
      v-if="data?.item_type === 'image' || data?.item_type === 'video' || data?.item_type === 'audio'"
      class="cn-top-actions"
      :style="topActionsScale ? { '--zoom-comp': topActionsScale } : undefined"
      @click.stop
      @mousedown.stop
    >
      <button
        class="cn-top-btn cn-top-upload"
        type="button"
        :title="data?.item_type === 'video' ? '上传视频' : data?.item_type === 'audio' ? '上传音频' : '上传图片'"
        @click.stop="emit('upload-request', { id: props.id })"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m17 8-5-5-5 5" /><path d="M12 3v12" />
        </svg>
        <span>上传</span>
      </button>
      <button
        v-if="data?.item_type !== 'video'"
        class="cn-top-btn cn-top-asset"
        type="button"
        title="从资产中心选择"
        @click.stop="emit('open-asset-picker', { id: props.id })"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        </svg>
        <span>资产中心</span>
      </button>
    </div>

    <Handle
      id="left"
      type="target"
      :position="Position.Left"
      title="点击新增 / 拖拽连线"
      @click.stop="onHandleClick($event, 'before')"
    />

    <div class="cn-header">
      <span v-if="data?.asset_tag" class="cn-asset-badge" :class="`cn-asset-${data.asset_tag}`" :title="assetTagLabel">
        <svg v-if="data?.asset_tag === 'character'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
        <svg v-else-if="data?.asset_tag === 'location'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></svg>
        <svg v-else-if="data?.asset_tag === 'prop'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" /><path d="m3.3 7 8.7 5 8.7-5" /><path d="M12 22V12" /></svg>
      </span>
      <span v-if="data?.asset_tag" class="cn-asset-tag-text" :class="`cn-asset-tag-${data.asset_tag}`">{{ assetTagLabel }}</span>
      <span v-else class="cn-type-icon" :class="`cn-type-icon-${data?.item_type}`" :title="typeLabel + '节点'">
        <template v-if="data?.item_type === 'text'">T</template>
        <svg v-else-if="data?.item_type === 'image'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></svg>
        <svg v-else-if="data?.item_type === 'video'" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7" /><rect width="15" height="14" x="1" y="5" rx="2" /></svg>
        <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" x2="12" y1="19" y2="22" /></svg>
      </span>
      <span v-if="data?.title" class="cn-title">{{ data.title }}</span>
      <span v-if="isRunning" class="cn-status cn-status-running" title="生成中">
        <span class="cn-spinner"></span>
      </span>
      <span v-else-if="isFailed" class="cn-status cn-status-failed" :title="data?.last_run_error || '生成失败'">!</span>
      <span v-else-if="isCompleted" class="cn-status cn-status-done" title="已生成">✓</span>
    </div>
    <div class="cn-body">
      <template v-if="data?.item_type === 'text'">
        <div class="cn-text">{{ textPreview }}</div>
      </template>
      <template v-else-if="data?.item_type === 'image'">
        <div class="cn-media">
          <img v-if="imageUrl" :src="coverUrl || imageUrl" alt="" />
          <div v-else class="cn-media-ph">
            <span v-if="isRunning" class="cn-ph-spinner"></span>
            <svg v-else class="cn-ph-icon" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></svg>
          </div>
          <!-- 资产节点的火山同步状态角标 -->
          <span
            v-if="data?.asset_tag && imageUrl && !isRunning"
            class="cn-volc-badge"
            :class="volcSyncing ? 'cn-volc-syncing' : (volcSynced ? 'cn-volc-synced' : 'cn-volc-unsynced')"
            @click.stop="(!volcSynced && !volcSyncing) && emit('sync-volc', { id: props.id })"
          >
            <template v-if="volcSyncing">同步中</template>
            <template v-else-if="volcSynced">已同步</template>
            <template v-else>未同步</template>
          </span>
          <!-- 已保存到资产中心角标 -->
          <span
            v-if="data?.saved_to_asset_center && hasOutputMedia"
            class="cn-assetcenter-badge"
            title="已保存到资产中心"
          >已入库</span>
        </div>
      </template>
      <template v-else-if="data?.item_type === 'video'">
        <div class="cn-media">
          <video
            v-if="videoUrl"
            :src="videoSrcForPreview"
            :poster="coverUrl || undefined"
            controls
            preload="metadata"
          />
          <div v-else class="cn-media-ph">
            <span v-if="isRunning" class="cn-ph-spinner"></span>
            <svg v-else class="cn-ph-icon" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7" /><rect width="15" height="14" x="1" y="5" rx="2" /></svg>
          </div>
          <!-- 已保存到资产中心角标 -->
          <span
            v-if="data?.saved_to_asset_center && hasOutputMedia"
            class="cn-assetcenter-badge"
            title="已保存到资产中心"
          >已入库</span>
        </div>
      </template>
      <template v-else-if="data?.item_type === 'audio'">
        <div class="cn-audio">
          <audio v-if="audioUrl" :src="audioUrl" controls preload="metadata" />
          <div v-else class="cn-audio-ph">
            <span v-if="isRunning" class="cn-ph-spinner"></span>
            <svg v-else class="cn-ph-icon" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" x2="12" y1="19" y2="22" /></svg>
            <span v-if="!isRunning" class="cn-audio-hint">拖入音频文件或上传</span>
          </div>
          <div v-if="audioUrl && audioName" class="cn-audio-name" :title="audioName">{{ audioName }}</div>
          <!-- 已保存到资产中心角标 -->
          <span
            v-if="data?.saved_to_asset_center && hasOutputMedia"
            class="cn-assetcenter-badge"
            title="已保存到资产中心"
          >已入库</span>
        </div>
      </template>
    </div>

    <!-- 整节点遮罩：上传中优先于生成中，覆盖 body 区域，避免遮挡 header 状态与 handle -->
    <div v-if="isUploading || isRunning" class="cn-overlay">
      <div class="cn-overlay-spinner"></div>
      <div class="cn-overlay-text">{{ runningText }}</div>
    </div>
    <!-- 失败遮罩：在原"生成中"区域显示 error msg，便于一眼看到失败原因 -->
    <div v-else-if="isFailed" class="cn-overlay cn-overlay-error">
      <div class="cn-overlay-error-icon">!</div>
      <div class="cn-overlay-error-text">{{ errorMessage }}</div>
    </div>

    <Handle
      id="right"
      type="source"
      :position="Position.Right"
      title="点击新增 / 拖拽连线"
      @click.stop="onHandleClick($event, 'after')"
    />

    <Teleport to="body">
      <div
        v-if="menuOpen"
        class="cn-handle-menu"
        :style="menuStyle"
        @click.stop
        @mousedown.stop
      >
        <div class="hm-header">{{ menuSide === 'before' ? '在前面插入' : '在后面插入' }}</div>
        <button class="hm-item" type="button" @click.stop="onSelect('text')">
          <span class="hm-icon hm-icon-text">T</span>
          <span>文本节点</span>
        </button>
        <button class="hm-item" type="button" @click.stop="onSelect('image')">
          <span class="hm-icon hm-icon-image">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></svg>
          </span>
          <span>图片节点</span>
        </button>
        <button class="hm-item" type="button" @click.stop="onSelect('video')">
          <span class="hm-icon hm-icon-video">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7" /><rect width="15" height="14" x="1" y="5" rx="2" /></svg>
          </span>
          <span>视频节点</span>
        </button>
        <button class="hm-item" type="button" @click.stop="onSelect('audio')">
          <span class="hm-icon hm-icon-audio">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" x2="12" y1="19" y2="22" /></svg>
          </span>
          <span>音频节点</span>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  isEditing: { type: Boolean, default: false },
  dimmed: { type: Boolean, default: false },
  volcSynced: { type: Boolean, default: false },
  volcSyncing: { type: Boolean, default: false },
  viewportZoom: { type: Number, default: 1 },
})

const emit = defineEmits(['quick-add', 'upload-request', 'open-asset-picker', 'sync-volc'])

const TYPE_LABELS = {
  text: '文本',
  image: '图片',
  video: '视频',
  audio: '音频',
}

const topActionsScale = computed(() => {
  const z = props.viewportZoom
  if (z === 1) return undefined
  return `scale(${1 / z})`
})

const typeLabel = computed(() => TYPE_LABELS[props.data?.item_type] || '节点')

const ASSET_TAG_META = {
  character: { label: '角色' },
  location: { label: '场景' },
  prop: { label: '道具' },
}
const assetTagLabel = computed(() => ASSET_TAG_META[props.data?.asset_tag]?.label || '')

const runStatus = computed(() => props.data?.last_run_status || 'idle')
const isRunning = computed(() => runStatus.value === 'pending' || runStatus.value === 'processing' || runStatus.value === 'uploading')
const isFailed = computed(() => runStatus.value === 'failed')
const isCompleted = computed(() => runStatus.value === 'completed')
// 本地文件上传中（图片/视频/音频）：由父组件在上传前后切换 data.is_uploading
const isUploading = computed(() => !!props.data?.is_uploading)

const runningText = computed(() => {
  if (isUploading.value) {
    const t = props.data?.item_type
    if (t === 'video') return '视频上传中…'
    if (t === 'image') return '图片上传中…'
    if (t === 'audio') return '音频上传中…'
    return '上传中…'
  }
  const t = props.data?.item_type
  if (t === 'video') return '视频生成中…'
  if (t === 'image') return '图片生成中…'
  return '文本生成中…'
})

const errorMessage = computed(() => props.data?.last_run_error || '生成失败')

const textPreview = computed(() => {
  // 优先展示已生成文本；其次展示用户在 body 编辑器里写的内容；再是 prompt 草稿；都没有就占位
  const generated = stripHtml(props.data?.content_json?.text || '')
  if (generated) return generated.length > 200 ? generated.slice(0, 200) + '...' : generated
  const body = stripHtml(props.data?.content_json?.body || '')
  if (body) return body.length > 200 ? body.slice(0, 200) + '...' : body
  const prompt = props.data?.content_json?.prompt || ''
  if (prompt) return prompt.length > 100 ? prompt.slice(0, 100) + '...' : prompt
  if (isUploading.value) return '导入中...'
  if (isRunning.value) return '生成中...'
  return '（双击编辑，输入 prompt 后点发送）'
})

function stripHtml(html) {
  // body 是富文本 HTML，画布上预览时去掉标签
  return String(html || '').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim()
}

const imageUrl = computed(() => props.data?.last_output_json?.url || '')
const videoUrl = computed(() => props.data?.last_output_json?.url || '')
const videoSrcForPreview = computed(() => {
  // #t=0.1 让浏览器渲染首帧作为预览封面（cover_url 缺失时兜底）
  const url = videoUrl.value
  if (!url || url.includes('#')) return url
  return `${url}#t=0.1`
})
const coverUrl = computed(() => props.data?.cover_url || props.data?.last_output_json?.thumbnail_url || '')
const audioUrl = computed(() => props.data?.last_output_json?.url || '')
const hasOutputMedia = computed(() => !!(imageUrl.value || videoUrl.value || audioUrl.value))
const audioName = computed(() => {
  const src = props.data?.last_output_json?.url || ''
  if (!src) return ''
  try {
    const u = new URL(src, window.location.origin)
    const parts = u.pathname.split('/')
    return decodeURIComponent(parts[parts.length - 1] || '')
  } catch {
    return ''
  }
})

const menuOpen = ref(false)
const menuSide = ref(null)
const menuStyle = ref({})

function onHandleClick(event, side) {
  const rect = event.target.getBoundingClientRect()
  const MENU_WIDTH = 160
  const MENU_HEIGHT = 212
  let left
  if (side === 'before') {
    left = rect.left - MENU_WIDTH - 8
    if (left < 8) left = rect.right + 8
  } else {
    left = rect.right + 8
    if (left + MENU_WIDTH > window.innerWidth - 8) left = rect.left - MENU_WIDTH - 8
  }
  let top = rect.top + rect.height / 2 - MENU_HEIGHT / 2
  if (top < 8) top = 8
  if (top + MENU_HEIGHT > window.innerHeight - 8) top = window.innerHeight - 8 - MENU_HEIGHT

  menuStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    zIndex: 1000,
  }
  menuSide.value = side
  menuOpen.value = true
}

function onSelect(itemType) {
  emit('quick-add', { id: props.id, direction: menuSide.value, itemType })
  closeMenu()
}

function closeMenu() {
  menuOpen.value = false
  menuSide.value = null
}

function onDocClick(e) {
  if (!menuOpen.value) return
  if (e.target.closest('.cn-handle-menu')) return
  if (e.target.closest('.vue-flow__handle')) return
  closeMenu()
}

function onKeydown(e) {
  if (e.key === 'Escape') closeMenu()
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.cn-node {
  position: relative;
  width: 240px;
  background: #fff;
  border: none;
  border-radius: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px rgba(15, 23, 42, 0.08);
  font-size: 12px;
  overflow: visible;
  transition: box-shadow 0.15s ease;
}

.cn-node:hover {
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 12px 32px rgba(15, 23, 42, 0.12);
}

.cn-node.cn-selected,
.cn-node.cn-selected:hover {
  box-shadow: 0 0 0 2px rgba(47, 123, 255, 0.4), 0 8px 24px rgba(15, 23, 42, 0.12);
}

.cn-node:has(.vue-flow__handle.connectingto),
.cn-node:has(.vue-flow__handle.valid) {
  box-shadow: 0 6px 18px rgba(47, 123, 255, 0.18);
  transform: scale(1.02);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  z-index: 10;
}

/* ── 节点上方浮动资产操作条（图片/视频节点） ── */
.cn-top-actions {
  position: absolute;
  left: 50%;
  bottom: 100%;
  margin-bottom: 16px;
  transform: translateX(-50%) var(--zoom-comp, );
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 4px;
  background: #fff;
  border-radius: 999px;
  border: 1px solid rgba(34, 57, 98, 0.08);
  box-shadow: 0 6px 18px -4px rgba(15, 23, 42, 0.18), 0 2px 6px -2px rgba(15, 23, 42, 0.08);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease, transform 0.15s ease;
  z-index: 20;
  white-space: nowrap;
  transform-origin: bottom center;
}

.cn-node.cn-editing .cn-top-actions {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateY(-2px);
}

.cn-top-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 24px;
  padding: 0;
  border: none;
  background: transparent;
  color: #1f2a44;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  font-family: inherit;
  transition: all 0.15s ease;
}

/* 上传：胶囊按钮，深色字 + 上传图标 */
.cn-top-upload {
  padding: 0 10px;
  border-radius: 999px;
  color: #1f2a44;
}

.cn-top-upload:hover {
  background: rgba(15, 23, 42, 0.06);
}

/* 资产中心：胶囊按钮，深色字 */
.cn-top-asset {
  padding: 0 10px;
  border-radius: 999px;
  color: #1f2a44;
}

.cn-top-asset:hover {
  background: rgba(15, 23, 42, 0.06);
}

.cn-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 6px;
  background: transparent;
  border-radius: 16px 16px 0 0;
}

/* 节点类型小图标：统一深灰圆形底 + 白色图标（参考图样式） */
.cn-type-icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #1f2937;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  line-height: 1;
}

/* 三种类型都用统一深灰底，不按类型分色（参考图样式） */
.cn-type-icon-text,
.cn-type-icon-image,
.cn-type-icon-video,
.cn-type-icon-audio {
  background: #1f2937;
}

/* 资产徽章：替代类型图标，尺寸对齐 cn-type-icon（26x26 圆形） */
.cn-asset-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  flex-shrink: 0;
  line-height: 1;
}

.cn-asset-character {
  background: #fbe3e3;
  color: #b44545;
}

.cn-asset-location {
  background: #e3ecfb;
  color: #3a5fb4;
}

.cn-asset-prop {
  background: #e9f3e6;
  color: #4f7a3d;
}

/* header 里的资产类型文字标签 */
.cn-asset-tag-text {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.2px;
  flex-shrink: 0;
  margin-right: 2px;
}

.cn-asset-tag-character { color: #b44545; }
.cn-asset-tag-location  { color: #3a5fb4; }
.cn-asset-tag-prop      { color: #4f7a3d; }

/* 资产节点容器：柔和色边框 + 微背景，区分于普通节点 */
.cn-node.cn-asset {
  border: 1.5px solid transparent;
  background-clip: padding-box;
}

.cn-node.cn-asset.cn-asset-character {
  border-color: #f0c8c8;
  background: linear-gradient(180deg, #fff7f7 0%, #fff 30%);
}

.cn-node.cn-asset.cn-asset-location {
  border-color: #c8d8f0;
  background: linear-gradient(180deg, #f6f9ff 0%, #fff 30%);
}

.cn-node.cn-asset.cn-asset-prop {
  border-color: #cee0c2;
  background: linear-gradient(180deg, #f5faf2 0%, #fff 30%);
}

/* 资产节点的 hover/selected 不破坏色边 */
.cn-node.cn-asset:hover {
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 12px 32px rgba(15, 23, 42, 0.12);
}

.cn-node.cn-asset.cn-selected,
.cn-node.cn-asset.cn-selected:hover {
  box-shadow: 0 0 0 2px rgba(47, 123, 255, 0.4), 0 8px 24px rgba(15, 23, 42, 0.12);
}

/* 火山同步状态角标（图片资产节点右下角） */
.cn-volc-badge {
  position: absolute;
  right: 6px;
  bottom: 6px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  line-height: 1.2;
  z-index: 3;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  user-select: none;
}

.cn-volc-unsynced {
  color: #d97706;
  background: rgba(245, 158, 11, 0.18);
  border: 1px solid rgba(245, 158, 11, 0.4);
  cursor: pointer;
  transition: background 0.15s ease;
}

.cn-volc-unsynced:hover {
  background: rgba(245, 158, 11, 0.32);
}

.cn-volc-syncing {
  color: #2563eb;
  background: rgba(59, 130, 246, 0.18);
  border: 1px solid rgba(59, 130, 246, 0.4);
}

.cn-volc-synced {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.18);
  border: 1px solid rgba(34, 197, 94, 0.4);
}

/* 已保存到资产中心角标（媒体节点左下角，避免与 cn-volc-badge 右下角冲突） */
.cn-assetcenter-badge {
  position: absolute;
  left: 6px;
  bottom: 6px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.2;
  color: #2563eb;
  background: rgba(59, 130, 246, 0.18);
  border: 1px solid rgba(59, 130, 246, 0.4);
  z-index: 3;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  user-select: none;
}

/* 筛选未匹配时变暗 */
.cn-node.cn-dimmed {
  opacity: 0.22;
  transition: opacity 0.18s ease;
}

.cn-node.cn-dimmed:hover {
  opacity: 0.5;
}

.cn-title {
  font-size: 12px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.cn-status {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.cn-status-running {
  background: rgba(47, 123, 255, 0.12);
}

.cn-status-failed {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.cn-status-done {
  background: rgba(22, 163, 74, 0.12);
  color: #16a34a;
}

.cn-spinner {
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(47, 123, 255, 0.25);
  border-top-color: #2f7bff;
  border-radius: 50%;
  animation: cnSpin 0.8s linear infinite;
}

@keyframes cnSpin {
  to { transform: rotate(360deg); }
}

.cn-node.cn-running {
  box-shadow: 0 0 0 2px rgba(47, 123, 255, 0.3), 0 8px 24px rgba(47, 123, 255, 0.12);
}

.cn-node.cn-failed {
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.3), 0 8px 24px rgba(239, 68, 68, 0.1);
}

.cn-body {
  padding: 10px;
  min-height: 60px;
}

.cn-text {
  font-size: 12px;
  color: #374151;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  overflow-y: auto;
}

.cn-media {
  position: relative;
  width: 100%;
  min-height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  border-radius: 10px;
  overflow: hidden;
}

.cn-media img,
.cn-media video {
  display: block;
  width: 100%;
  height: auto;
  max-height: 320px;
  object-fit: contain;
}

.cn-media-ph {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #b5bac2;
}

.cn-audio {
  width: 100%;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f0f2f5;
  border-radius: 10px;
  padding: 12px;
}

.cn-audio audio {
  width: 100%;
}

.cn-audio-ph {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  min-height: 40px;
  color: #b5bac2;
}

.cn-audio-hint {
  font-size: 11.5px;
  color: #9ca3af;
}

.cn-audio-name {
  font-size: 11.5px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cn-ph-icon {
  color: #b5bac2;
}

.cn-ph-spinner {
  width: 22px;
  height: 22px;
  border: 2.5px solid rgba(47, 123, 255, 0.2);
  border-top-color: #2f7bff;
  border-radius: 50%;
  animation: cnSpin 0.8s linear infinite;
  display: inline-block;
}

/* ── 生成中遮罩（覆盖 body 区，露出 header 与 handle） ── */
.cn-overlay {
  position: absolute;
  left: 0;
  right: 0;
  top: 33px; /* header 高度约 33px，从其下方开始遮罩 */
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  border-radius: 0 0 9px 9px;
  z-index: 2;
  pointer-events: none;
}

.cn-overlay-spinner {
  width: 22px;
  height: 22px;
  border: 2.5px solid rgba(47, 123, 255, 0.22);
  border-top-color: #2f7bff;
  border-radius: 50%;
  animation: cnSpin 0.8s linear infinite;
}

.cn-overlay-text {
  font-size: 11px;
  color: #355ce0;
  font-weight: 500;
}

/* ── 失败遮罩（与"生成中"遮罩同区域，呈现失败原因） ── */
.cn-overlay-error {
  background: rgba(239, 68, 68, 0.06);
  border-radius: 0 0 15px 15px;
}

.cn-overlay-error-icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #ef4444;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  line-height: 1;
}

.cn-overlay-error-text {
  font-size: 11.5px;
  color: #b3285a;
  line-height: 1.5;
  text-align: center;
  padding: 0 10px;
  max-height: 72px;
  overflow: hidden;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
}

/* ── 统一的 handle：点击新增 / 拖拽连线 ── */
.cn-node :deep(.vue-flow__handle) {
  width: 24px;
  height: 100%;
  background: transparent;
  border: none;
  border-radius: 0;
  cursor: pointer;
  opacity: 1;
}

.cn-node :deep(.vue-flow__handle-left) {
  left: -12px;
}

.cn-node :deep(.vue-flow__handle-right) {
  right: -12px;
}

/* 两侧：hover 节点时显示小加号，提示可点击/拖拽连线 */
.cn-node :deep(.vue-flow__handle)::before {
  content: '+';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 2px solid #2f7bff;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 700;
  color: #2f7bff;
  line-height: 1;
  pointer-events: none;
  box-shadow: 0 2px 6px rgba(47, 123, 255, 0.25);
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.cn-node:hover :deep(.vue-flow__handle)::before {
  opacity: 1;
}

.cn-node :deep(.vue-flow__handle:hover)::before {
  background: #2f7bff;
  color: #fff;
}

/* 连线过程中：不再显示绿色块，靠整个节点高亮提示 */
.cn-node :deep(.vue-flow__handle.connectingto),
.cn-node :deep(.vue-flow__handle.valid) {
  background: transparent;
  border-color: transparent;
}

.cn-node :deep(.vue-flow__handle.connectingto::before),
.cn-node :deep(.vue-flow__handle.valid::before) {
  content: none;
}
</style>

<style>
/* 菜单（teleport 到 body，必须非 scoped） */
.cn-handle-menu {
  background: #fff;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(34, 57, 98, 0.18);
  min-width: 160px;
  padding: 6px;
  font-family: inherit;
  animation: cnMenuIn 0.15s ease-out;
  transform-origin: top center;
}

@keyframes cnMenuIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.cn-handle-menu .hm-header {
  font-size: 11px;
  color: #6b7280;
  padding: 6px 10px 4px;
  margin-bottom: 2px;
  border-bottom: 1px solid rgba(34, 57, 98, 0.06);
  font-weight: 500;
}

.cn-handle-menu .hm-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 36px;
  padding: 0 10px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #1f2a44;
  font-family: inherit;
  text-align: left;
  transition: background 0.12s ease, color 0.12s ease;
}

.cn-handle-menu .hm-item:hover {
  background: #eef4ff;
  color: #2f7bff;
}

.cn-handle-menu .hm-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.cn-handle-menu .hm-icon-text {
  background: rgba(47, 123, 255, 0.12);
  color: #2f7bff;
}

.cn-handle-menu .hm-icon-image {
  background: rgba(22, 163, 74, 0.12);
  color: #16a34a;
}

.cn-handle-menu .hm-icon-video {
  background: rgba(147, 51, 234, 0.12);
  color: #9333ea;
}

.cn-handle-menu .hm-icon-audio {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}
</style>
