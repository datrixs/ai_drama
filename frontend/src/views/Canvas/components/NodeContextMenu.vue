<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="node-ctx-menu"
      :style="menuStyle"
      @click.stop
      @mousedown.stop
      @contextmenu.prevent
    >
      <button
        class="ncm-item"
        type="button"
        @click.stop="onAction('copy-node')"
      >
        <span class="ncm-label">复制节点</span>
        <span class="ncm-shortcut">Ctrl+C</span>
      </button>
      <button
        v-if="itemType === 'text' || itemType === 'image'"
        class="ncm-item"
        type="button"
        @click.stop="onAction('copy-content')"
      >
        <span class="ncm-label">复制{{ contentLabel }}</span>
      </button>
      <button
        class="ncm-item"
        type="button"
        @click.stop="onAction('duplicate')"
      >
        <span class="ncm-label">创建副本</span>
      </button>
      <div class="ncm-hint">附带节点相关连线信息</div>
      <template v-if="itemType === 'image'">
        <div class="ncm-sep"></div>
        <div class="ncm-subhead">标记为资产</div>
        <button
          class="ncm-item"
          :class="{ 'ncm-item-active': currentTag === 'character' }"
          type="button"
          @click.stop="onAction('mark-asset', 'character')"
        >
          <span class="ncm-icon-badge ncm-badge-character">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
          </span>
          <span class="ncm-label">角色</span>
        </button>
        <button
          class="ncm-item"
          :class="{ 'ncm-item-active': currentTag === 'location' }"
          type="button"
          @click.stop="onAction('mark-asset', 'location')"
        >
          <span class="ncm-icon-badge ncm-badge-location">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></svg>
          </span>
          <span class="ncm-label">场景</span>
        </button>
        <button
          class="ncm-item"
          :class="{ 'ncm-item-active': currentTag === 'prop' }"
          type="button"
          @click.stop="onAction('mark-asset', 'prop')"
        >
          <span class="ncm-icon-badge ncm-badge-prop">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" /><path d="m3.3 7 8.7 5 8.7-5" /><path d="M12 22V12" /></svg>
          </span>
          <span class="ncm-label">道具</span>
        </button>
        <button
          v-if="currentTag"
          class="ncm-item"
          type="button"
          @click.stop="onAction('mark-asset', null)"
        >
          <span class="ncm-label">清除标记</span>
        </button>
      </template>
      <template v-if="itemType === 'image' || itemType === 'video' || itemType === 'audio'">
        <div class="ncm-sep"></div>
        <button
          v-if="hasOutput"
          class="ncm-item"
          type="button"
          @click.stop="onAction('save-asset')"
        >
          <span class="ncm-label">{{ savedToAssetCenter ? '重新保存到资产中心' : '保存到资产中心' }}</span>
        </button>
        <button
          class="ncm-item"
          type="button"
          :disabled="synced || syncing"
          @click.stop="(!synced && !syncing) && onAction('sync-volcano')"
        >
          <span class="ncm-label">
            <template v-if="synced">已同步</template>
            <template v-else-if="syncing">同步中…</template>
            <template v-else>同步火山</template>
          </span>
        </button>
      </template>
      <div class="ncm-sep"></div>
      <button
        class="ncm-item ncm-item-danger"
        type="button"
        @click.stop="onAction('delete')"
      >
        <span class="ncm-label">删除</span>
        <span class="ncm-shortcut">Delete</span>
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  position: { type: Object, default: () => ({ x: 0, y: 0 }) },
  itemType: { type: String, default: 'text' },
  hasOutput: { type: Boolean, default: false },
  synced: { type: Boolean, default: false },
  syncing: { type: Boolean, default: false },
  currentTag: { type: String, default: null },
  savedToAssetCenter: { type: Boolean, default: false },
})

const emit = defineEmits(['action', 'close'])

const MENU_WIDTH = 200
const MENU_HEIGHT_ESTIMATE = 320

const contentLabel = computed(() => {
  if (props.itemType === 'text') return '文本'
  if (props.itemType === 'image') return '图片'
  if (props.itemType === 'video') return '视频'
  if (props.itemType === 'audio') return '音频'
  return ''
})

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

function onAction(key, payload) {
  emit('action', key, payload)
  emit('close')
}

function onDocClick(e) {
  if (!props.visible) return
  if (e.target.closest('.node-ctx-menu')) return
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
.node-ctx-menu {
  background: #fff;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(34, 57, 98, 0.18);
  min-width: 200px;
  max-width: 240px;
  padding: 6px;
  font-family: inherit;
  animation: ncmIn 0.15s ease-out;
  transform-origin: top left;
}

@keyframes ncmIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.node-ctx-menu .ncm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 36px;
  padding: 0 12px;
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

.node-ctx-menu .ncm-item:hover {
  background: #eef4ff;
  color: #2f7bff;
}

.node-ctx-menu .ncm-item-danger:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.node-ctx-menu .ncm-item:disabled,
.node-ctx-menu .ncm-item[disabled] {
  cursor: not-allowed;
  color: #9ca3af;
  background: transparent;
}

.node-ctx-menu .ncm-item:disabled:hover,
.node-ctx-menu .ncm-item[disabled]:hover {
  background: transparent;
  color: #9ca3af;
}

.node-ctx-menu .ncm-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-ctx-menu .ncm-shortcut {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
  flex-shrink: 0;
}

.node-ctx-menu .ncm-item-danger .ncm-shortcut {
  color: rgba(239, 68, 68, 0.55);
}

.node-ctx-menu .ncm-sep {
  height: 1px;
  background: rgba(34, 57, 98, 0.06);
  margin: 4px 6px;
}

.node-ctx-menu .ncm-subhead {
  padding: 6px 12px 2px;
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
}

.node-ctx-menu .ncm-hint {
  padding: 0 12px 4px;
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.3;
  white-space: normal;
}

.node-ctx-menu .ncm-item-active {
  background: #eef4ff;
  color: #2f7bff;
}

.node-ctx-menu .ncm-item-active:hover {
  background: #eef4ff;
  color: #2f7bff;
}

.node-ctx-menu .ncm-item .ncm-icon-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 5px;
  flex-shrink: 0;
  margin-right: 2px;
}

.node-ctx-menu .ncm-badge-character {
  background: #fbe3e3;
  color: #b44545;
}

.node-ctx-menu .ncm-badge-location {
  background: #e3ecfb;
  color: #3a5fb4;
}

.node-ctx-menu .ncm-badge-prop {
  background: #e9f3e6;
  color: #4f7a3d;
}
</style>
