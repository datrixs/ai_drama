<template>
  <div class="pe-container">
    <div
      ref="editorRef"
      class="pe-editor"
      :class="{ 'pe-editor-compact': compact }"
      contenteditable="true"
      @input="onInput"
      @keydown="onKeydown"
      @paste="onPaste"
      @dragover.prevent
      @drop.prevent
      @compositionstart="isComposing = true"
      @compositionend="onCompositionEnd"
    ></div>
    <div v-if="isEmpty" class="pe-placeholder">{{ placeholder }}</div>
  </div>

  <!-- @ 自动补全弹窗 —— Teleport 到 body，不受父级 overflow 裁切 -->
  <Teleport to="body">
    <div v-if="showAutocomplete && autocompleteItems.length > 0" class="at-popup" :style="popupStyle">
      <div
        v-for="(item, aidx) in autocompleteItems"
        :key="item.refLabel"
        class="at-item"
        :class="{ 'at-item-active': aidx === activeAutocompleteIdx }"
        @mousedown.prevent="selectAutocomplete(item)"
        @mouseenter="activeAutocompleteIdx = aidx"
      >
        <img v-if="item.assetType === 'image' && item.url" :src="item.thumbnail_url || item.url" class="at-item-thumb" />
        <img v-else-if="item.assetType === 'video' && item.thumbnail_url" :src="item.thumbnail_url" class="at-item-thumb" />
        <div v-else-if="item.assetType === 'video'" class="at-item-thumb at-item-icon">▶</div>
        <div v-else class="at-item-thumb at-item-icon">♪</div>
        <span class="at-item-name">{{ item.refLabel }}</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useShortVideoStore } from '@/store/shortVideo'

const props = defineProps({
  placeholder: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const store = useShortVideoStore()
const editorRef = ref(null)
const isComposing = ref(false)
const isEmpty = ref(true)
let isInternalUpdate = false
let currentAudio = null

// ── 自动补全状态 ──
const showAutocomplete = ref(false)
const activeAutocompleteIdx = ref(0)
const popupStyle = ref({})

const autocompleteItems = computed(() => [
  ...store.referenceImages.map(r => ({ ...r, assetType: 'image' })),
  ...store.referenceVideos.map(r => ({ ...r, assetType: 'video' })),
  ...store.referenceAudios.map(r => ({ ...r, assetType: 'audio' })),
])

// ════════════════════════════════════
//  DOM ↔ PromptText 转换
// ════════════════════════════════════

function domToPrompt() {
  if (!editorRef.value) return ''
  let result = ''
  const walk = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      result += node.textContent || ''
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      if (node.dataset?.refLabel) {
        result += `@${node.dataset.refLabel}`
      } else if (node.tagName === 'BR') {
        result += '\n'
      } else {
        for (const child of node.childNodes) walk(child)
      }
    }
  }
  for (const child of editorRef.value.childNodes) walk(child)
  return result
}

function promptToDom(text) {
  if (!editorRef.value) return

  const refs = autocompleteItems.value
  let remaining = text || ''
  const frag = document.createDocumentFragment()

  while (remaining.length > 0) {
    let earliestIdx = -1
    let matchRef = null
    for (const ref of refs) {
      const tag = `@${ref.refLabel}`
      const i = remaining.indexOf(tag)
      if (i !== -1 && (earliestIdx === -1 || i < earliestIdx)) {
        earliestIdx = i
        matchRef = ref
      }
    }

    if (earliestIdx === -1) {
      appendTextWithBreaks(frag, remaining)
      break
    }

    if (earliestIdx > 0) {
      appendTextWithBreaks(frag, remaining.slice(0, earliestIdx))
    }

    frag.appendChild(createRefCardEl(matchRef))
    remaining = remaining.slice(earliestIdx + `@${matchRef.refLabel}`.length)
  }

  if (frag.childNodes.length === 0) {
    frag.appendChild(document.createTextNode(''))
  }

  editorRef.value.innerHTML = ''
  editorRef.value.appendChild(frag)
  updateEmpty()
}

function appendTextWithBreaks(parent, text) {
  if (!text) return
  const parts = text.split('\n')
  for (let i = 0; i < parts.length; i++) {
    if (parts[i]) parent.appendChild(document.createTextNode(parts[i]))
    if (i < parts.length - 1) parent.appendChild(document.createElement('br'))
  }
}

// ── 创建引用卡片 DOM 元素 ──

function createRefCardEl(item) {
  const span = document.createElement('span')
  span.contentEditable = 'false'
  span.className = `pe-ref-card pe-ref-${item.assetType}`
  span.dataset.refLabel = item.refLabel
  span.dataset.refType = item.assetType
  span.dataset.refUrl = item.url || ''

  if (item.assetType === 'image' && item.url) {
    const img = document.createElement('img')
    img.src = item.thumbnail_url || item.url
    img.className = 'pe-ref-thumb'
    span.appendChild(img)
  } else if (item.assetType === 'video') {
    if (item.thumbnail_url) {
      const img = document.createElement('img')
      img.src = item.thumbnail_url
      img.className = 'pe-ref-thumb'
      span.appendChild(img)
    } else {
      const thumb = document.createElement('span')
      thumb.className = 'pe-ref-thumb pe-ref-thumb-video'
      thumb.innerHTML = '<svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
      span.appendChild(thumb)
    }
  } else if (item.assetType === 'audio') {
    const btn = document.createElement('button')
    btn.className = 'pe-audio-play'
    btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
    btn.addEventListener('click', (e) => {
      e.preventDefault()
      e.stopPropagation()
      toggleAudioPlay(item.url, btn)
    })
    span.appendChild(btn)
  }

  const label = document.createElement('span')
  label.className = 'pe-ref-label'
  label.textContent = `@${item.refLabel}`
  span.appendChild(label)

  return span
}

function removeRefCard(el) {
  el.remove()
  syncToStore()
}

// ── 音频播放 ──

function toggleAudioPlay(url, btn) {
  if (!url) return
  if (currentAudio && currentAudio.src.endsWith(url) && !currentAudio.paused) {
    currentAudio.pause()
    currentAudio = null
    btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
    return
  }
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
  const audio = new Audio(url)
  audio.onended = () => {
    currentAudio = null
    btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
  }
  audio.play()
  currentAudio = audio
  btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>'
}

function updateEmpty() {
  const el = editorRef.value
  if (!el) { isEmpty.value = true; return }
  const text = (el.textContent || '').trim()
  const hasCards = el.querySelectorAll('[data-ref-label]').length > 0
  isEmpty.value = !text && !hasCards
}

function syncToStore() {
  isInternalUpdate = true
  store.promptText = domToPrompt()
  nextTick(() => { isInternalUpdate = false })
  updateEmpty()
}

// ════════════════════════════════════
//  事件处理
// ════════════════════════════════════

function onInput() {
  if (isComposing.value) return
  syncToStore()
  checkAtBeforeCursor()
}

function checkAtBeforeCursor() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) { showAutocomplete.value = false; return }

  const range = sel.getRangeAt(0)
  if (!range.collapsed) { showAutocomplete.value = false; return }

  const node = range.startContainer
  if (node.nodeType !== Node.TEXT_NODE) { showAutocomplete.value = false; return }

  const text = node.textContent || ''
  const offset = range.startOffset
  const beforeCursor = text.slice(0, offset)
  const atIdx = beforeCursor.lastIndexOf('@')

  if (atIdx >= 0) {
    const query = beforeCursor.slice(atIdx + 1)
    if (!query.includes(' ') && query.length < 20) {
      if (autocompleteItems.value.length === 0) { showAutocomplete.value = false; return }
      showAutocomplete.value = true
      activeAutocompleteIdx.value = 0
      positionPopup(node, atIdx)
      return
    }
  }

  showAutocomplete.value = false
}

function positionPopup(textNode, atIdx) {
  const range = document.createRange()
  const start = Math.min(atIdx, textNode.length)
  range.setStart(textNode, start)
  range.collapse(true)

  let rect = range.getBoundingClientRect()
  if (rect.height === 0 && editorRef.value) {
    rect = editorRef.value.getBoundingClientRect()
  }

  const POPUP_HEIGHT = 200
  const spaceBelow = window.innerHeight - rect.bottom
  const spaceAbove = rect.top

  // 下方空间不够时向上弹
  if (spaceBelow < POPUP_HEIGHT && spaceAbove > spaceBelow) {
    popupStyle.value = {
      position: 'fixed',
      bottom: `${window.innerHeight - rect.top + 4}px`,
      left: `${Math.max(8, rect.left)}px`,
    }
  } else {
    popupStyle.value = {
      position: 'fixed',
      top: `${rect.bottom + 4}px`,
      left: `${Math.max(8, rect.left)}px`,
    }
  }
}

function onKeydown(e) {
  // 自动补全导航
  if (showAutocomplete.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      activeAutocompleteIdx.value = (activeAutocompleteIdx.value + 1) % autocompleteItems.value.length
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      activeAutocompleteIdx.value = (activeAutocompleteIdx.value - 1 + autocompleteItems.value.length) % autocompleteItems.value.length
      return
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault()
      if (autocompleteItems.value.length > 0) {
        selectAutocomplete(autocompleteItems.value[activeAutocompleteIdx.value])
      }
      return
    }
    if (e.key === 'Escape') {
      showAutocomplete.value = false
      return
    }
  }

  // Backspace 删除引用卡片
  if (e.key === 'Backspace') {
    const sel = window.getSelection()
    if (!sel || sel.rangeCount === 0) return
    const range = sel.getRangeAt(0)
    if (!range.collapsed) return

    const node = range.startContainer

    // 光标在文本节点开头，前一个是引用卡片
    if (node.nodeType === Node.TEXT_NODE && range.startOffset === 0) {
      const prev = node.previousSibling
      if (prev && prev.nodeType === Node.ELEMENT_NODE && prev.dataset?.refLabel) {
        e.preventDefault()
        removeRefCard(prev)
        return
      }
    }

    // 光标直接在编辑器 div 内，前一个子节点是引用卡片
    if (node === editorRef.value) {
      const child = node.childNodes[range.startOffset - 1]
      if (child && child.dataset?.refLabel) {
        e.preventDefault()
        removeRefCard(child)
        return
      }
    }
  }

  // Delete 键删除引用卡片（光标后面）
  if (e.key === 'Delete') {
    const sel = window.getSelection()
    if (!sel || sel.rangeCount === 0) return
    const range = sel.getRangeAt(0)
    if (!range.collapsed) return

    const node = range.startContainer

    if (node.nodeType === Node.TEXT_NODE && range.startOffset === (node.textContent || '').length) {
      const next = node.nextSibling
      if (next && next.nodeType === Node.ELEMENT_NODE && next.dataset?.refLabel) {
        e.preventDefault()
        removeRefCard(next)
        return
      }
    }

    if (node === editorRef.value) {
      const child = node.childNodes[range.startOffset]
      if (child && child.dataset?.refLabel) {
        e.preventDefault()
        removeRefCard(child)
        return
      }
    }
  }
}

function selectAutocomplete(item) {
  showAutocomplete.value = false

  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return
  const range = sel.getRangeAt(0)
  const node = range.startContainer
  if (node.nodeType !== Node.TEXT_NODE) return

  const text = node.textContent || ''
  const offset = range.startOffset
  const beforeCursor = text.slice(0, offset)
  const atIdx = beforeCursor.lastIndexOf('@')
  if (atIdx < 0) return

  const beforeText = text.slice(0, atIdx)
  const afterText = text.slice(offset)

  const parent = node.parentNode
  const refEl = createRefCardEl(item)
  const spaceNode = document.createTextNode(' ')
  const afterNode = document.createTextNode(afterText)

  // 按 beforeText + refCard + space + afterText 顺序插入
  parent.insertBefore(afterNode, node.nextSibling)
  parent.insertBefore(spaceNode, afterNode)
  parent.insertBefore(refEl, spaceNode)
  node.textContent = beforeText

  // 光标移到 space 之后
  const newRange = document.createRange()
  newRange.setStart(afterNode, 0)
  newRange.collapse(true)
  sel.removeAllRanges()
  sel.addRange(newRange)

  syncToStore()
}

function onPaste(e) {
  e.preventDefault()
  const text = e.clipboardData?.getData('text/plain') || ''
  if (!text) return
  document.execCommand('insertText', false, text)
}

function onCompositionEnd() {
  isComposing.value = false
  syncToStore()
  checkAtBeforeCursor()
}

// ── 监听 store 外部变化 ──

watch(() => store.promptText, (newVal) => {
  if (isInternalUpdate) return
  promptToDom(newVal)
})

// ── 生命周期 ──

function handleClickOutside(e) {
  if (showAutocomplete.value && !e.target.closest('.pe-container') && !e.target.closest('.at-popup')) {
    showAutocomplete.value = false
  }
}

onMounted(() => {
  promptToDom(store.promptText)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (currentAudio) { currentAudio.pause(); currentAudio = null }
})

// ── 暴露方法 ──

defineExpose({
  insertRefAtEnd(item) {
    if (!editorRef.value) return
    const el = editorRef.value

    // 编辑器为空时直接插入，不追加前导空格
    const isEmpty = !el.textContent?.trim() && el.querySelectorAll('[data-ref-label]').length === 0

    const refEl = createRefCardEl(item)
    const spaceNode = document.createTextNode(' ')
    el.appendChild(refEl)
    el.appendChild(spaceNode)

    // 光标移到末尾
    const sel = window.getSelection()
    const range = document.createRange()
    range.setStart(spaceNode, 1)
    range.collapse(true)
    sel.removeAllRanges()
    sel.addRange(range)

    syncToStore()
  },
  focus() {
    const el = editorRef.value
    if (!el) return
    el.focus()
    const sel = window.getSelection()
    const range = document.createRange()
    range.selectNodeContents(el)
    range.collapse(false)
    sel.removeAllRanges()
    sel.addRange(range)
  },
})
</script>

<style scoped>
.pe-container {
  position: relative;
}

.pe-editor {
  min-height: 5rem;
  max-height: min(20rem, 25vh);
  overflow-y: auto;
  padding: 0.5rem 0;
  cursor: text;
  outline: none;
  line-height: 1.8;
  color: var(--glass-text-primary);
  font-size: 14px;
  word-break: break-all;
}

.pe-editor-compact {
  min-height: 2.5rem;
  max-height: min(6rem, 15vh);
  font-size: 13px;
  line-height: 1.6;
  padding: 0.5rem 0;
}

.pe-placeholder {
  position: absolute;
  top: 0.5rem;
  left: 0;
  right: 0;
  pointer-events: none;
  color: var(--glass-text-tertiary, #999);
  font-size: 14px;
  line-height: 1.8;
}

/* 引用卡片 */
.pe-editor :deep(.pe-ref-card) {
  display: inline-flex;
  align-items: center;
  gap: 0.1875rem;
  padding: 1px 0.375rem 1px 2px;
  border-radius: 0.25rem;
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-muted, rgba(0,0,0,0.03));
  user-select: none;
  vertical-align: middle;
  position: relative;
  transition: border-color 0.15s;
  line-height: 1;
}

.pe-editor :deep(.pe-ref-card:hover) {
  border-color: var(--glass-accent-from, #3b82f6);
}

.pe-editor :deep(.pe-ref-thumb) {
  width: 24px;
  height: 24px;
  border-radius: 0.1875rem;
  object-fit: cover;
  flex-shrink: 0;
  display: block;
}

.pe-editor :deep(.pe-ref-thumb-video) {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
}

.pe-editor :deep(.pe-ref-label) {
  font-size: 0.6875rem;
  font-weight: 500;
  color: var(--glass-accent-from, #3b82f6);
  white-space: nowrap;
}

/* 音频卡片 */
.pe-editor :deep(.pe-ref-audio) {
  background: rgba(245, 158, 11, 0.06);
  border-color: rgba(245, 158, 11, 0.3);
}

.pe-editor :deep(.pe-audio-play) {
  width: 24px;
  height: 24px;
  border-radius: 0.1875rem;
  border: none;
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.pe-editor :deep(.pe-audio-play:hover) {
  background: rgba(245, 158, 11, 0.25);
}

/* @ 自动补全弹窗（Teleport 到 body，fixed 定位） */
.at-popup {
  position: fixed;
  z-index: 9999;
  min-width: 160px;
  max-height: 200px;
  overflow-y: auto;
  background: var(--glass-bg-surface, #fff);
  border: 1px solid var(--glass-stroke-base);
  border-radius: 0.5rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 0.25rem;
}

.at-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background 0.1s;
}

.at-item:hover,
.at-item-active {
  background: var(--glass-bg-muted, rgba(0,0,0,0.04));
}

.at-item-thumb {
  width: 28px;
  height: 28px;
  border-radius: 0.25rem;
  object-fit: cover;
  flex-shrink: 0;
}

.at-item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-bg-muted);
  color: var(--glass-text-secondary);
  font-size: 0.625rem;
}

.at-item-name {
  font-size: 0.8125rem;
  color: var(--glass-text-primary);
}
</style>
