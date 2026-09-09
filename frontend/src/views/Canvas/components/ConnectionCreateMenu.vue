<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="conn-create-menu"
      :style="menuStyle"
      @click.stop
      @mousedown.stop
      @contextmenu.prevent
    >
      <!-- 顶部提示文字 -->
      <div class="ccm-hint">引用该节点生成</div>

      <!-- 文本节点 -->
      <button
        class="ccm-card"
        type="button"
        :disabled="creatingItem"
        @click.stop="onPick('text')"
      >
        <span class="ccm-icon ccm-icon-text">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <path d="M14 2v6h6" />
            <path d="M10 9H8" />
            <path d="M16 13H8" />
            <path d="M16 17H8" />
          </svg>
        </span>
        <span class="ccm-card-body">
          <span class="ccm-card-title">文本节点</span>
          <span class="ccm-card-desc">输入文本内容</span>
        </span>
      </button>

      <!-- 图片节点 -->
      <button
        class="ccm-card"
        type="button"
        :disabled="creatingItem"
        @click.stop="onPick('image')"
      >
        <span class="ccm-icon ccm-icon-image">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="18" x="3" y="3" rx="2" />
            <circle cx="9" cy="9" r="2" />
            <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
          </svg>
        </span>
        <span class="ccm-card-body">
          <span class="ccm-card-title">图片节点</span>
          <span class="ccm-card-desc">生成画面或上传素材</span>
        </span>
      </button>

      <!-- 视频节点 -->
      <button
        class="ccm-card"
        type="button"
        :disabled="creatingItem"
        @click.stop="onPick('video')"
      >
        <span class="ccm-icon ccm-icon-video">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect width="15" height="14" x="1" y="5" rx="2" />
          </svg>
        </span>
        <span class="ccm-card-body">
          <span class="ccm-card-title">视频节点</span>
          <span class="ccm-card-desc">生成动态视频片段</span>
        </span>
      </button>

      <!-- 音频节点 -->
      <button
        class="ccm-card"
        type="button"
        :disabled="creatingItem"
        @click.stop="onPick('audio')"
      >
        <span class="ccm-icon ccm-icon-audio">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" x2="12" y1="19" y2="22" />
          </svg>
        </span>
        <span class="ccm-card-body">
          <span class="ccm-card-title">音频节点</span>
          <span class="ccm-card-desc">上传本地音频文件</span>
        </span>
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount } from 'vue'

// 组件 props：visible 控制显隐，position 为屏幕坐标 {x,y}，creatingItem 为全局"正在创建"锁
const props = defineProps({
  visible: { type: Boolean, default: false },
  position: { type: Object, default: () => ({ x: 0, y: 0 }) },
  creatingItem: { type: Boolean, default: false },
})

const emit = defineEmits(['pick', 'close'])

// 菜单尺寸估算，用于边界检测
const MENU_WIDTH = 240
const MENU_HEIGHT_ESTIMATE = 260

// 边界检测：超出右侧贴边，超出底部向上展开，避免被屏幕裁切
// zIndex 1200 高于 pane-ctx-menu(1100)，避免被遮挡
const menuStyle = computed(() => {
  let { x, y } = props.position || { x: 0, y: 0 }
  if (typeof window !== 'undefined') {
    if (x + MENU_WIDTH > window.innerWidth - 8) {
      x = window.innerWidth - 8 - MENU_WIDTH
    }
    if (x < 8) x = 8
    if (y + MENU_HEIGHT_ESTIMATE > window.innerHeight - 8) {
      y = (props.position?.y ?? 0) - MENU_HEIGHT_ESTIMATE
    }
    if (y < 8) y = 8
  }
  return {
    position: 'fixed',
    left: `${x}px`,
    top: `${y}px`,
    zIndex: 1200,
  }
})

// 选中某类型卡片 → 通知父组件创建对应节点
function onPick(type) {
  emit('pick', type)
}

// 下一次按下菜单外部 → 关闭
// 注意：必须用 mousedown 而非 click。本菜单由"左键拖拽连线松开"触发显示，
// 若监听 click，则显示菜单那一次操作的 click 会立即冒泡到 document，误判为"点外部"而瞬间关闭。
// 用 mousedown 可避开：拖拽开始的 mousedown 早已过去不会重放，只有用户下次主动按下才关闭。
function onDocMousedown(e) {
  if (!props.visible) return
  if (e.target.closest('.conn-create-menu')) return
  emit('close')
}

// ESC → 关闭
function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  document.addEventListener('mousedown', onDocMousedown)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocMousedown)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style>
/* 连接拖拽空抛弹出的"引用该节点生成"新建框 */
.conn-create-menu {
  width: 240px;
  background: #ffffff;
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 14px;
  padding: 10px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.18);
  font-family: inherit;
  animation: ccmIn 0.15s ease-out;
  transform-origin: top left;
}

@keyframes ccmIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.conn-create-menu .ccm-hint {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  padding: 4px 8px 8px;
  margin-bottom: 4px;
  border-bottom: 1px solid rgba(34, 57, 98, 0.06);
  letter-spacing: 0.2px;
}

.conn-create-menu .ccm-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px;
  border: 1px solid transparent;
  background: #fafbfc;
  border-radius: 10px;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  margin-top: 6px;
  transition: background 0.14s ease, border-color 0.14s ease, transform 0.14s ease, box-shadow 0.14s ease;
}

.conn-create-menu .ccm-card:first-of-type {
  margin-top: 0;
}

.conn-create-menu .ccm-card:hover:not(:disabled) {
  background: #ffffff;
  border-color: rgba(47, 123, 255, 0.25);
  box-shadow: 0 4px 14px rgba(47, 123, 255, 0.1);
  transform: translateX(2px);
}

.conn-create-menu .ccm-card:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.conn-create-menu .ccm-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.conn-create-menu .ccm-icon-text {
  background: rgba(47, 123, 255, 0.12);
  color: #2f7bff;
}

.conn-create-menu .ccm-icon-image {
  background: rgba(22, 163, 74, 0.12);
  color: #16a34a;
}

.conn-create-menu .ccm-icon-video {
  background: rgba(147, 51, 234, 0.12);
  color: #9333ea;
}

.conn-create-menu .ccm-icon-audio {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}

.conn-create-menu .ccm-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.conn-create-menu .ccm-card-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.2;
}

.conn-create-menu .ccm-card-desc {
  font-size: 11.5px;
  color: #9ca3af;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
