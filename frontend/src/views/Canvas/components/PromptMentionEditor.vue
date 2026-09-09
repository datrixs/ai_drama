<template>
  <div class="pme-wrap">
    <div ref="shellRef" class="pme-shell">
      <div
        ref="editableRef"
        class="pme-editor"
        :class="{ 'is-disabled': disabled }"
        contenteditable="true"
        :data-placeholder="placeholder"
        @focus="onFocus"
        @compositionstart="isComposing = true"
        @compositionend="onCompositionEnd"
        @input="onInput"
        @keydown="onKeydown"
        @click="onClick"
        @blur="onBlur"
        @paste="onPaste"
      ></div>

    </div>

    <Teleport to="body">
      <div
        v-if="pickerOpen"
        class="pme-picker"
        :class="pickerPlacementClass"
        :style="pickerStyle"
        @mousedown.stop
      >
        <div class="pme-picker-header">
          <span class="pme-picker-title">引用节点</span>
          <span class="pme-picker-count">{{ pickerItems.length }}</span>
        </div>
        <div v-if="pickerItems.length" class="pme-picker-list">
          <button
            v-for="(item, idx) in pickerItems"
            :key="item.id"
            type="button"
            class="pme-picker-item"
            :class="{ 'is-active': idx === activeIdx, 'is-upstream': item.is_upstream, 'is-empty': !item.has_output && item.item_type !== 'text' }"
            @mousedown.prevent="insertMention(item)"
          >
            <span v-if="item.item_type === 'image' && item.previewUrl" class="pme-pi-thumb-wrap">
              <img class="pme-pi-thumb" :src="item.previewUrl" :alt="item.title || ''" />
            </span>
            <span v-else class="pme-pi-type">{{ typeBadgeOf(item.item_type) }}</span>
            <span class="pme-pi-body">
              <span class="pme-pi-title">
                {{ displayTitleOf(item) }}
                <span v-if="item.is_upstream" class="pme-pi-upstream-badge" title="已连线的资产">已连线</span>
                <span v-if="!item.has_output && item.item_type !== 'text'" class="pme-pi-empty-badge" title="该节点尚未生成/上传">未生成</span>
              </span>
              <span class="pme-pi-meta">{{ typeLabelOf(item.item_type) }}</span>
            </span>
            <span class="pme-pi-action">{{ idx === activeIdx ? 'Enter' : '+' }}</span>
          </button>
        </div>
        <div v-else class="pme-picker-empty">
          <div>暂无可引用节点</div>
          <div class="pme-picker-hint">{{ query ? '没匹配到结果' : '画布中暂无其他可引用节点（需先在画布中创建并连线其他节点）' }}</div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  tokens: { type: Array, default: () => [] },
  availableNodes: { type: Array, default: () => [] },
  placeholder: { type: String, default: '输入内容，输入 @ 引用上游节点' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:tokens', 'focus-item'])

const editableRef = ref(null)
const shellRef = ref(null)

const pickerOpen = ref(false)
const query = ref('')
const activeIdx = ref(0)
const mentionRange = ref(null)
const pickerPlacement = ref('above')
const pickerMaxHeight = ref(280)
const pickerRect = ref({ left: 0, top: 0, width: 0 })
const isComposing = ref(false)
const isSyncing = ref(false)
const localTokens = ref([])
const localSig = ref('[]')

const ROLE_CYCLE = ['first_frame', 'last_frame', 'reference']
const ROLE_LABEL = { first_frame: '首', last_frame: '尾', reference: '参' }

const pickerItems = computed(() => {
  const kw = query.value.toLowerCase().trim()
  const list = props.availableNodes.filter(n => n && n.id)
  if (!kw) return list
  // 标题或正文模糊匹配，覆盖文本节点（标题常为空，靠 body 识别）
  return list.filter(n => {
    if (String(n.title || '').toLowerCase().includes(kw)) return true
    if (String(n.previewText || '').toLowerCase().includes(kw)) return true
    return false
  })
})

// 标题兜底：text 节点标题常为空，用正文前若干字作为可识别文案
function displayTitleOf(item) {
  if (item.title) return item.title
  if (item.item_type === 'text' && item.previewText) {
    const plain = String(item.previewText).replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
    if (plain) return plain.slice(0, 24) + (plain.length > 24 ? '…' : '')
  }
  return '(未命名)'
}

// 节点类型的 picker 显示文案 / 图标：保证 image/video/audio/text 都有正确呈现
function typeBadgeOf(t) {
  if (t === 'image') return '图'
  if (t === 'video') return '视'
  if (t === 'audio') return '音'
  return '文'
}
function typeLabelOf(t) {
  if (t === 'image') return '图片节点'
  if (t === 'video') return '视频节点'
  if (t === 'audio') return '音频节点'
  return '文本节点'
}

const pickerPlacementClass = computed(() => pickerPlacement.value === 'below' ? 'is-below' : 'is-above')

// 浮层定位样式：fixed 坐标基于 shell 边界矩形计算，跟随 shell 滚动/resize
const pickerStyle = computed(() => ({
  position: 'fixed',
  left: `${pickerRect.value.left}px`,
  top: `${pickerRect.value.top}px`,
  width: `${pickerRect.value.width}px`,
  '--picker-max-height': `${pickerMaxHeight.value}px`,
}))

// ── 渲染 ────────────────────────────────
const escapeHtml = (v = '') => String(v)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

function renderTextToken(tok) {
  return escapeHtml(tok.value || '').replace(/\n/g, '<br>')
}

function renderMentionToken(tok) {
  const title = escapeHtml(tok.node_title || tok.node_id || '')
  const nodeType = escapeHtml(tok.node_type || '')
  const nodeId = escapeHtml(tok.node_id || '')
  const role = tok.node_type === 'image' ? String(tok.role || 'reference') : ''
  const roleAttr = role ? `data-role="${escapeHtml(role)}"` : ''
  const roleBadge = ''
  const kind = renderKindIcon(tok.node_type)
  return `<span class="pme-chip" contenteditable="false" data-token-type="mention" data-node-id="${nodeId}" data-node-type="${nodeType}" data-node-title="${title}" ${roleAttr}>${kind}<span class="pme-chip-label">@${title}</span>${roleBadge}<span class="pme-chip-x" data-action="remove" title="移除">×</span></span>`
}

function renderKindIcon(nodeType) {
  if (nodeType === 'image') {
    return '<span class="pme-chip-kind"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg></span>'
  }
  if (nodeType === 'audio') {
    return '<span class="pme-chip-kind"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg></span>'
  }
  if (nodeType === 'video') {
    return '<span class="pme-chip-kind"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m10 8 6 4-6 4z"/></svg></span>'
  }
  return '<span class="pme-chip-kind"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><polyline points="10 9 9 9 8 9"/></svg></span>'
}

async function renderEditor(tokens = localTokens.value) {
  if (!editableRef.value) return
  const html = tokens.map(t => t.type === 'mention' ? renderMentionToken(t) : renderTextToken(t)).join('')
  isSyncing.value = true
  editableRef.value.innerHTML = html || ''
  await nextTick()
  isSyncing.value = false
}

// ── DOM → tokens 解析 ────────────────────
function pushText(tokens, text) {
  if (!text) return
  const last = tokens[tokens.length - 1]
  if (last && last.type === 'text') {
    last.value += text
  } else {
    tokens.push({ type: 'text', value: text })
  }
}

function isBlockElement(n) {
  return !!n && n.nodeType === Node.ELEMENT_NODE && (n.tagName === 'DIV' || n.tagName === 'P')
}

function parseNode(node, tokens) {
  if (!node) return
  if (node.nodeType === Node.TEXT_NODE) {
    pushText(tokens, node.textContent || '')
    return
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return
  const el = node
  if (el.dataset?.tokenType === 'mention') {
    tokens.push({
      type: 'mention',
      node_id: el.dataset.nodeId || '',
      node_type: el.dataset.nodeType || '',
      node_title: el.dataset.nodeTitle || '',
      role: el.dataset.role || null,
    })
    return
  }
  if (el.tagName === 'BR') {
    pushText(tokens, '\n')
    return
  }
  parseChildren(el, tokens)
}

// 遍历某个父元素的子节点：在块级（DIV/P）与文本/行内元素的边界处补 '\n'，
// 覆盖 Chrome contenteditable 的多种 DOM 变体：
//   line1<div>line2</div> / <div>line1</div>line2 / <div>line1</div><div>line2</div>
// 旧逻辑只在 DIV 有 nextSibling 时 push '\n'，会丢掉 line1→DIV 这条边界。
function parseChildren(parent, tokens) {
  const kids = Array.from(parent?.childNodes || [])
  kids.forEach((kid, i) => {
    if (i > 0 && (isBlockElement(kid) || isBlockElement(kids[i - 1]))) {
      pushText(tokens, '\n')
    }
    parseNode(kid, tokens)
  })
}

function readTokensFromDom() {
  if (!editableRef.value) return []
  const tokens = []
  parseChildren(editableRef.value, tokens)
  return tokens
}

function serialize(tokens) {
  return JSON.stringify(tokens || [])
}

function syncFromDom(force = false) {
  if (!editableRef.value || isSyncing.value) return
  const next = readTokensFromDom()
  const sig = serialize(next)
  if (!force && sig === localSig.value) return
  localTokens.value = next
  // composing 期间既不 emit 也不更新 localSig：避免候选词选择时频繁上报；
  // 更关键的是防止 onInput 把 localSig 提前更新成最新 DOM 后，compositionend 时
  // sig===localSig 被误判"无变化"而跳过 emit，导致中文输入内容丢失（不保存）。
  if (!isComposing.value) {
    localSig.value = sig
    emit('update:tokens', next)
  }
}

// ── Picker ──────────────────────────────
function selectionInside(node) {
  return editableRef.value && node && editableRef.value.contains(node)
}

function closePicker() {
  pickerOpen.value = false
  query.value = ''
  mentionRange.value = null
  activeIdx.value = 0
}

function updatePickerLayout() {
  if (!shellRef.value || !pickerOpen.value) return
  const rect = shellRef.value.getBoundingClientRect()
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800
  const pad = 16
  const gap = 10
  const preferred = 280
  const above = Math.max(0, rect.top - pad - gap)
  const below = Math.max(0, vh - rect.bottom - pad - gap)
  const openBelow = below >= above
  pickerPlacement.value = openBelow ? 'below' : 'above'
  pickerMaxHeight.value = Math.max(120, Math.min(preferred, openBelow ? below : above))
  // 浮层在 body 下用 fixed 定位，与 shell 同宽；上下方向由 top 计算
  const top = openBelow ? rect.bottom + gap : Math.max(pad, rect.top - gap - pickerMaxHeight.value)
  pickerRect.value = { left: rect.left, top, width: rect.width }
}

function walkToLastText(node) {
  let cur = node
  while (cur) {
    if (cur.nodeType === Node.TEXT_NODE) return cur
    const kids = cur.childNodes || []
    cur = kids.length ? kids[kids.length - 1] : null
  }
  return null
}

function caretTextContext(container, offset) {
  if (!editableRef.value || !container) return null
  if (container.nodeType === Node.TEXT_NODE) {
    return { node: container, offset: Math.min(offset, String(container.textContent || '').length) }
  }
  if (container.nodeType !== Node.ELEMENT_NODE) return null
  const kids = Array.from(container.childNodes || [])
  const prev = offset > 0 ? kids[offset - 1] : null
  const tn = walkToLastText(prev)
  if (!tn) return null
  return { node: tn, offset: String(tn.textContent || '').length }
}

function updateMentionQuery() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return closePicker()
  const range = sel.getRangeAt(0)
  if (!range.collapsed || !selectionInside(range.endContainer)) return closePicker()

  const ctx = caretTextContext(range.endContainer, range.endOffset)
  if (!ctx?.node) return closePicker()

  const before = String(ctx.node.textContent || '').slice(0, ctx.offset)
  const m = before.match(/@([^\s@]*)$/)
  if (!m) return closePicker()

  const q = m[1] || ''
  const mention = `@${q}`
  const start = before.lastIndexOf(mention)
  if (start < 0) return closePicker()

  const r = document.createRange()
  r.setStart(ctx.node, start)
  r.setEnd(ctx.node, ctx.offset)
  mentionRange.value = r
  query.value = q
  pickerOpen.value = true
  updatePickerLayout()
  if (activeIdx.value >= pickerItems.value.length) activeIdx.value = 0
}

function scheduleUpdateQuery() {
  if (typeof window === 'undefined') return updateMentionQuery()
  window.requestAnimationFrame(() => updateMentionQuery())
}

function placeCaretAfter(node) {
  const sel = window.getSelection()
  if (!sel || !node) return
  const r = document.createRange()
  r.setStartAfter(node)
  r.collapse(true)
  sel.removeAllRanges()
  sel.addRange(r)
}

function insertMention(item) {
  if (!editableRef.value || props.disabled) return
  editableRef.value.focus()
  const sel = window.getSelection()
  const range = mentionRange.value || (sel && sel.rangeCount > 0 ? sel.getRangeAt(0) : null)
  if (!range) return

  range.deleteContents()
  const chip = document.createElement('span')
  chip.className = 'pme-chip'
  chip.contentEditable = 'false'
  chip.dataset.tokenType = 'mention'
  chip.dataset.nodeId = item.id
  chip.dataset.nodeType = item.item_type
  chip.dataset.nodeTitle = item.title || item.id
  if (item.item_type === 'image') chip.dataset.role = 'reference'
  chip.innerHTML = renderMentionTokenInner(item)
  const trail = document.createTextNode(' ')
  range.insertNode(trail)
  range.insertNode(chip)
  placeCaretAfter(trail)
  closePicker()
  syncFromDom()
}

function renderMentionTokenInner(item) {
  const title = escapeHtml(item.title || item.id)
  const kind = renderKindIcon(item.item_type)
  return `${kind}<span class="pme-chip-label">@${title}</span><span class="pme-chip-x" data-action="remove" title="移除">×</span>`
}

function removeChip(chipEl) {
  if (!chipEl) return
  // 同时移除尾部空格
  const next = chipEl.nextSibling
  if (next && next.nodeType === Node.TEXT_NODE && next.textContent === ' ') {
    next.remove()
  }
  chipEl.remove()
  syncFromDom()
  scheduleUpdateQuery()
}

function cycleChipRole(chipEl) {
  if (!chipEl) return
  const cur = chipEl.dataset.role || 'reference'
  const idx = ROLE_CYCLE.indexOf(cur)
  const nextRole = ROLE_CYCLE[(idx + 1) % ROLE_CYCLE.length]
  chipEl.dataset.role = nextRole
  const badge = chipEl.querySelector('.pme-chip-role')
  if (badge) badge.textContent = ROLE_LABEL[nextRole] || '参'
  syncFromDom()
}

// ── 事件 ────────────────────────────────
function onFocus() { scheduleUpdateQuery() }
function onCompositionEnd() {
  isComposing.value = false
  syncFromDom()
  scheduleUpdateQuery()
}
function onInput() {
  if (props.disabled) return
  // 强制 emit：mention chip 之后立即输入文字时，浏览器把字符 append 到 trail 文本节点，
  // 在某些边界下 sig 比较会误判未变化、跳过 emit，导致父组件 watch 收不到更新、不会自动保存。
  // 强制走 emit 路径保证父组件 promptTokens 实时同步。
  syncFromDom(true)
  scheduleUpdateQuery()
}
function onKeydown(e) {
  if (props.disabled) { e.preventDefault(); return }
  if (pickerOpen.value && e.key === 'Escape') { e.preventDefault(); closePicker(); return }
  if (!pickerOpen.value || pickerItems.value.length === 0) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIdx.value = (activeIdx.value + 1) % pickerItems.value.length
    return
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIdx.value = (activeIdx.value - 1 + pickerItems.value.length) % pickerItems.value.length
    return
  }
  if (e.key === 'Enter' || e.key === 'Tab') {
    e.preventDefault()
    const item = pickerItems.value[activeIdx.value] || pickerItems.value[0]
    if (item) insertMention(item)
  }
}
function onClick(e) {
  const removeBtn = e.target.closest('[data-action="remove"]')
  if (removeBtn) {
    removeChip(removeBtn.closest('.pme-chip'))
    return
  }
  const roleBtn = e.target.closest('[data-action="cycle-role"]')
  if (roleBtn) {
    cycleChipRole(roleBtn.closest('.pme-chip'))
    return
  }
  const chip = e.target.closest('.pme-chip')
  if (chip?.dataset?.nodeId) emit('focus-item', chip.dataset.nodeId)
  scheduleUpdateQuery()
}
function onBlur() {
  syncFromDom()
  setTimeout(() => {
    const active = document.activeElement
    if (active && active.closest && active.closest('.pme-picker')) return
    closePicker()
  }, 0)
}
function onPaste(e) {
  e.preventDefault()
  const txt = e.clipboardData?.getData('text/plain') || ''
  document.execCommand('insertText', false, txt)
  scheduleUpdateQuery()
}

function onDocSelectionChange() {
  const sel = typeof window !== 'undefined' ? window.getSelection() : null
  if (!sel || sel.rangeCount === 0) return
  if (!selectionInside(sel.anchorNode)) return
  scheduleUpdateQuery()
}

function onWinResize() { updatePickerLayout() }

// 滚动（含祖先容器）时重新计算浮层位置；capture: true 捕获画布祖先滚动
function onAnyScroll() {
  if (!pickerOpen.value) return
  updatePickerLayout()
}

// ── 外部 tokens → DOM 同步 ───────────────
watch(
  () => props.tokens,
  (toks) => {
    if (isComposing.value) return
    const next = Array.isArray(toks) ? toks : []
    const sig = serialize(next)
    if (sig === localSig.value) return
    localTokens.value = next
    localSig.value = sig
    renderEditor(next)
  },
  // flush:'sync'：切换节点时父 promptTokens 立即变化，需同步重建 contenteditable DOM，
  // 否则旧节点的内容会残留在 DOM 里，被后续 syncFromDom 读回 emit，造成内容串到新节点。
  { deep: true, immediate: true, flush: 'sync' }
)

watch(pickerItems, (items) => {
  if (!items.length) { activeIdx.value = 0; return }
  updatePickerLayout()
  if (activeIdx.value >= items.length) activeIdx.value = 0
})

onMounted(async () => {
  await nextTick()
  await renderEditor(localTokens.value)
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', onWinResize)
    window.addEventListener('scroll', onAnyScroll, { capture: true, passive: true })
    document.addEventListener('selectionchange', onDocSelectionChange)
  }
})

onBeforeUnmount(() => {
  // 注意：这里不再 flush tokens 给父组件。改由父组件 NodeEditorPanel 在 doSave 前通过
  // ref 主动调 flushTokens() 捕获 contenteditable 最新内容（含 composing 中未 emit 的输入）。
  // 若在子组件卸载时 emit，跨节点类型切换（image↔video 用不同 editor 实例）时旧实例卸载
  // 会把旧内容 emit 回去，覆盖父已 reset 的新节点 promptTokens，造成内容串台。
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', onWinResize)
    window.removeEventListener('scroll', onAnyScroll, { capture: true })
    document.removeEventListener('selectionchange', onDocSelectionChange)
  }
})

defineExpose({
  flushTokens: () => {
    const next = readTokensFromDom()
    localTokens.value = next
    localSig.value = serialize(next)
    emit('update:tokens', next)
    return next
  },
  swapImageChips: () => {
    const el = editableRef.value
    if (!el) return false
    const chips = Array.from(el.querySelectorAll('.pme-chip[data-node-type="image"]'))
    if (chips.length < 2) return false
    const c1 = chips[0]
    const c2 = chips[1]
    const placeholder = el.ownerDocument.createElement('span')
    c1.parentNode.insertBefore(placeholder, c1)
    c2.parentNode.insertBefore(c1, c2)
    placeholder.parentNode.insertBefore(c2, placeholder)
    placeholder.parentNode.removeChild(placeholder)
    if (c1.dataset.role) c1.dataset.role = 'last_frame'
    if (c2.dataset.role) c2.dataset.role = 'first_frame'
    // 不在这里 emit，让外层先做缩略图 DOM 交换，最后统一更新 tokens，
    // 否则 Vue 的 v-for diff 会先于缩略图 DOM 交换跑到，触发 img 重新挂载
    localTokens.value = readTokensFromDom()
    localSig.value = serialize(localTokens.value)
    return true
  },
  readTokens: () => readTokensFromDom(),
})
</script>

<style scoped>
.pme-wrap { display: flex; flex-direction: column; gap: 8px; }
.pme-shell { position: relative; resize: vertical; overflow: hidden; min-height: 72px; }

.pme-editor {
  min-height: 56px;
  max-height: 100%;
  overflow-y: auto;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(34, 57, 98, 0.12);
  background: #f8fafc;
  color: #1f2a44;
  font-size: 13px;
  line-height: 1.65;
  outline: none;
  white-space: pre-wrap;
  word-break: break-word;
}
.pme-editor:focus { box-shadow: 0 0 0 3px rgba(75, 120, 255, 0.12); border-color: rgba(75, 120, 255, 0.32); }
.pme-editor.is-disabled { opacity: 0.55; pointer-events: none; }
.pme-editor:empty::before { content: attr(data-placeholder); color: #98a2b3; }

:deep(.pme-chip) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: 0 2px;
  padding: 1px 6px 1px 4px;
  border-radius: 999px;
  background: rgba(75, 120, 255, 0.12);
  color: #1f2a44;
  font-size: 12px;
  user-select: none;
}
:deep(.pme-chip-kind) {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: 50%;
  background: rgba(75, 120, 255, 0.22);
  font-size: 10px; line-height: 1;
}
:deep(.pme-chip-label) { font-weight: 500; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:deep(.pme-chip-role) {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 16px; padding: 0 4px;
  border-radius: 999px;
  background: #ff8a3d;
  color: #fff;
  font-size: 10px; line-height: 1;
  cursor: pointer;
}
:deep(.pme-chip-role[data-role="first_frame"]) { background: #2ec1c0; }
:deep(.pme-chip-role[data-role="last_frame"]) { background: #ff5b8a; }
:deep(.pme-chip-role[data-role="reference"]) { background: #ff8a3d; }
:deep(.pme-chip-x) {
  display: inline-flex; align-items: center; justify-content: center;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: rgba(31, 42, 68, 0.14);
  color: #1f2a44;
  font-size: 11px; line-height: 1;
  cursor: pointer;
}
:deep(.pme-chip-x:hover) { background: rgba(31, 42, 68, 0.28); color: #fff; }

.pme-picker {
  max-height: var(--picker-max-height, 280px);
  padding: 8px;
  border-radius: 12px;
  border: 1px solid rgba(34, 57, 98, 0.1);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 30px rgba(34, 57, 98, 0.14);
  overflow: hidden;
  z-index: 3000;
}
.pme-picker.is-above,
.pme-picker.is-below {
  /* fixed 定位由 pickerStyle 提供，这里仅保留钩子以便后续微调 */
}

.pme-picker-header { display: flex; align-items: center; gap: 8px; padding: 0 4px 6px; }
.pme-picker-title { color: #1f2a44; font-size: 12px; font-weight: 600; }
.pme-picker-count { min-width: 18px; padding: 0 6px; border-radius: 999px; background: rgba(75, 120, 255, 0.14); color: #355ce0; font-size: 10px; text-align: center; }

.pme-picker-list { display: flex; flex-direction: column; gap: 4px; max-height: calc(var(--picker-max-height, 280px) - 36px); overflow-y: auto; }
.pme-picker-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 8px; border: 1px solid rgba(34, 57, 98, 0.06); background: #fff; color: #1f2a44; text-align: left; cursor: pointer; }
.pme-picker-item.is-active { background: rgba(75, 120, 255, 0.12); border-color: rgba(75, 120, 255, 0.28); }
.pme-picker-item.is-upstream { border-color: rgba(16, 185, 129, 0.24); background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%); }
.pme-picker-item.is-upstream.is-active { background: rgba(16, 185, 129, 0.14); border-color: rgba(16, 185, 129, 0.42); }

.pme-pi-upstream-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.16);
  color: #047857;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  vertical-align: middle;
}
.pme-pi-empty-badge {
  display: inline-block;
  margin-left: 6px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.16);
  color: #b45309;
  font-size: 10px;
  font-weight: 600;
  line-height: 16px;
  vertical-align: middle;
}
.pme-picker-item.is-empty { opacity: 0.78; }
.pme-pi-thumb-wrap, .pme-pi-type { width: 24px; height: 24px; border-radius: 6px; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; background: rgba(75, 120, 255, 0.12); color: #355ce0; font-size: 11px; }
.pme-pi-thumb { width: 100%; height: 100%; border-radius: 6px; object-fit: cover; }
.pme-pi-body { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
.pme-pi-title { font-size: 12px; font-weight: 500; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pme-pi-meta { font-size: 11px; color: #667085; }
.pme-pi-action { min-width: 20px; padding: 0 6px; border-radius: 999px; background: rgba(75, 120, 255, 0.12); color: #355ce0; font-size: 10px; text-align: center; }
.pme-picker-empty { padding: 12px 6px; text-align: center; color: #667085; font-size: 12px; }
.pme-picker-hint { margin-top: 4px; color: #98a2b3; font-size: 11px; }
</style>
