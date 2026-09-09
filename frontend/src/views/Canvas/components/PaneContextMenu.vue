<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="pane-ctx-menu"
      :style="menuStyle"
      @click.stop
      @mousedown.stop
      @contextmenu.prevent
    >
      <button
        class="pcm-item"
        type="button"
        @click.stop="onAction('upload')"
      >
        <span class="pcm-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" x2="12" y1="3" y2="15" />
          </svg>
        </span>
        <span class="pcm-label">上传文件</span>
      </button>

      <button
        class="pcm-item"
        type="button"
        title="把画布中已标记的资产批量入库"
        @click.stop="onAction('batch-save-asset')"
      >
        <span class="pcm-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v16l7-3 7 3z" />
          </svg>
        </span>
        <span class="pcm-label">批量保存到资产中心</span>
        <span v-if="batchCandidateCount > 0" class="pcm-shortcut">{{ batchCandidateCount }}</span>
      </button>

      <div class="pcm-sub-wrap">
        <button
          class="pcm-item"
          type="button"
          @click.stop="toggleSub('create')"
        >
          <span class="pcm-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 5v14" /><path d="M5 12h14" />
            </svg>
          </span>
          <span class="pcm-label">创建节点</span>
          <span class="pcm-arrow">{{ subOpen === 'create' ? '▸' : '▾' }}</span>
        </button>
        <div v-if="subOpen === 'create'" class="pcm-sub">
          <button class="pcm-sub-item" type="button" @click.stop="onAction('create-text')">
            <span class="pcm-sub-icon pcm-sub-icon-text">T</span>
            <span>文本节点</span>
          </button>
          <button class="pcm-sub-item" type="button" @click.stop="onAction('create-image')">
            <span class="pcm-sub-icon pcm-sub-icon-image">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></svg>
            </span>
            <span>图片节点</span>
          </button>
          <button class="pcm-sub-item" type="button" @click.stop="onAction('create-video')">
            <span class="pcm-sub-icon pcm-sub-icon-video">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7" /><rect width="15" height="14" x="1" y="5" rx="2" /></svg>
            </span>
            <span>视频节点</span>
          </button>
          <button class="pcm-sub-item" type="button" @click.stop="onAction('create-audio')">
            <span class="pcm-sub-icon pcm-sub-icon-audio">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></svg>
            </span>
            <span>音频节点</span>
          </button>
        </div>
      </div>

      <div class="pcm-sep"></div>

      <button
        class="pcm-item"
        type="button"
        :disabled="!canPaste"
        :class="{ 'pcm-item-disabled': !canPaste }"
        @click.stop="onAction('paste')"
      >
        <span class="pcm-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
          </svg>
        </span>
        <span class="pcm-label">粘贴</span>
        <span class="pcm-shortcut">Ctrl+V</span>
      </button>
      <button
        class="pcm-item"
        type="button"
        :disabled="!canUndo"
        :class="{ 'pcm-item-disabled': !canUndo }"
        @click.stop="onAction('undo')"
      >
        <span class="pcm-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 14 4 9l5-5" />
            <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11" />
          </svg>
        </span>
        <span class="pcm-label">撤销</span>
        <span class="pcm-shortcut">Ctrl+Z</span>
      </button>
      <button
        class="pcm-item"
        type="button"
        :disabled="!canRedo"
        :class="{ 'pcm-item-disabled': !canRedo }"
        @click.stop="onAction('redo')"
      >
        <span class="pcm-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 14 5-5-5-5" />
            <path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v0A5.5 5.5 0 0 0 9.5 20H13" />
          </svg>
        </span>
        <span class="pcm-label">重做</span>
        <span class="pcm-shortcut">Ctrl+Y</span>
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  position: { type: Object, default: () => ({ x: 0, y: 0 }) },
  canPaste: { type: Boolean, default: false },
  canUndo: { type: Boolean, default: false },
  canRedo: { type: Boolean, default: false },
  batchCandidateCount: { type: Number, default: 0 },
})

const emit = defineEmits(['action', 'close'])

const MENU_WIDTH = 220
const MENU_HEIGHT_ESTIMATE = 280
const subOpen = ref(null)

const menuStyle = computed(() => {
  let { x, y } = props.position
  if (x + MENU_WIDTH > window.innerWidth - 8) {
    x = window.innerWidth - 8 - MENU_WIDTH
  }
  if (x < 8) x = 8
  if (y + MENU_HEIGHT_ESTIMATE > window.innerHeight - 8) {
    y = props.position.y - MENU_HEIGHT_ESTIMATE
  }
  if (y < 8) y = 8
  return {
    position: 'fixed',
    left: `${x}px`,
    top: `${y}px`,
    zIndex: 1100,
  }
})

watch(() => props.visible, (v) => {
  if (!v) subOpen.value = null
})

function toggleSub(key) {
  subOpen.value = subOpen.value === key ? null : key
}

function onAction(action) {
  emit('action', action)
  emit('close')
}

function onDocClick(e) {
  if (!props.visible) return
  if (e.target.closest('.pane-ctx-menu')) return
  emit('close')
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
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

<style>
.pane-ctx-menu {
  background: #fff;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(34, 57, 98, 0.18);
  min-width: 220px;
  max-width: 260px;
  padding: 6px;
  font-family: inherit;
  animation: pcmIn 0.15s ease-out;
  transform-origin: top left;
}

@keyframes pcmIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.pane-ctx-menu .pcm-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 36px;
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

.pane-ctx-menu .pcm-item:hover {
  background: #eef4ff;
  color: #2f7bff;
}

.pane-ctx-menu .pcm-item-disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

.pane-ctx-menu .pcm-item-disabled:hover {
  background: transparent;
  color: #c0c4cc;
}

.pane-ctx-menu .pcm-icon {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: rgba(47, 123, 255, 0.1);
  color: #2f7bff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.pane-ctx-menu .pcm-item-disabled .pcm-icon {
  background: rgba(15, 23, 42, 0.04);
  color: #c0c4cc;
}

.pane-ctx-menu .pcm-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pane-ctx-menu .pcm-shortcut {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
  flex-shrink: 0;
}

.pane-ctx-menu .pcm-item-disabled .pcm-shortcut {
  color: #d1d5db;
}

.pane-ctx-menu .pcm-arrow {
  font-size: 10px;
  color: #9ca3af;
  flex-shrink: 0;
}

.pane-ctx-menu .pcm-sep {
  height: 1px;
  background: rgba(34, 57, 98, 0.06);
  margin: 4px 6px;
}

.pane-ctx-menu .pcm-sub {
  padding: 2px 0 2px 30px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pane-ctx-menu .pcm-sub-item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 10px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12.5px;
  color: #1f2a44;
  font-family: inherit;
  text-align: left;
}

.pane-ctx-menu .pcm-sub-item:hover {
  background: #eef4ff;
  color: #2f7bff;
}

.pane-ctx-menu .pcm-sub-icon {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.pane-ctx-menu .pcm-sub-icon-text {
  background: rgba(47, 123, 255, 0.12);
  color: #2f7bff;
}

.pane-ctx-menu .pcm-sub-icon-image {
  background: rgba(22, 163, 74, 0.12);
  color: #16a34a;
}

.pane-ctx-menu .pcm-sub-icon-video {
  background: rgba(147, 51, 234, 0.12);
  color: #9333ea;
}

.pane-ctx-menu .pcm-sub-icon-audio {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}
</style>
