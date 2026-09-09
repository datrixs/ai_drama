<template>
  <div class="me-wrap" @click.stop>
    <div
      ref="editorRef"
      class="me-editor"
      contenteditable="true"
      :data-placeholder="placeholder"
      spellcheck="false"
      @input="onEditorInput"
      @keydown="onEditorKeyDown"
      @paste="onEditorPaste"
      @mousedown="onEditorMouseDown"
      @mouseup="onEditorMouseUp"
    />

    <!-- @ 资产选择菜单 -->
    <div v-if="atMenuOpen" ref="atMenuRef" class="me-at-menu" :style="atMenuPos">
      <div class="me-at-hint">选择资产引用</div>
      <div class="me-at-list">
        <div v-if="filteredAssets.length === 0" class="me-at-empty">无匹配资产</div>
        <div v-for="a in filteredAssets" :key="a.key" class="me-at-row-wrap">
          <button class="me-at-row" @mousedown.prevent @click="pickAsset(a)">
            <img v-if="a.imageUrl" :src="a.thumbnailUrl || a.imageUrl" class="me-at-img" loading="lazy" referrerpolicy="no-referrer" @error="onThumbError($event, a.imageUrl)" />
            <div v-else class="me-at-noimg">{{ a.name.slice(0, 2) }}</div>
            <span class="me-at-name">{{ a.name }}</span>
            <span class="me-at-type">{{ a.typeLabel }}</span>
          </button>
          <button v-if="!a.volcId && !syncStates[a.id]?.volcId && a.imageUrl" class="me-at-sync"
            :class="{ 'me-at-syncing': syncStates[a.id]?.syncing }"
            @mousedown.prevent @click.stop="syncVolc(a)" :disabled="syncStates[a.id]?.syncing">
            {{ syncStates[a.id]?.syncing ? '同步中...' : '同步火山' }}
          </button>
          <span v-if="syncStates[a.id]?.error" class="me-at-sync-err">{{ syncStates[a.id].error }}</span>
        </div>
      </div>
      <button class="me-at-close" @mousedown.prevent @click="closeAtMenu">关闭</button>
    </div>

    <!-- 资产 chip 替换菜单 -->
    <div v-if="chipSwapUi" ref="chipSwapRef" class="me-swap-menu"
      :style="{ top: chipSwapUi.top + 'px', left: chipSwapUi.left + 'px', minWidth: chipSwapUi.minW + 'px' }">
      <div class="me-swap-hint">替换资产</div>
      <div v-if="chipSwapRows.length === 0" class="me-swap-empty">无可用替换</div>
      <button v-for="row in chipSwapRows" :key="row.key" class="me-swap-row"
        @mousedown.prevent @click="applyChipSwap(row)">
        <img v-if="row.imageUrl" :src="row.thumbnailUrl || row.imageUrl" class="me-swap-img" @error="onThumbError($event, row.imageUrl)" />
        <div v-else class="me-swap-noimg">?</div>
        <span class="me-swap-name">{{ row.name }}</span>
      </button>
      <button class="me-swap-close" @mousedown.prevent @click="chipSwapUi = null">关闭</button>
    </div>

    <!-- 资产大图悬停预览 -->
    <div v-if="hoverPreview" ref="previewRef" class="me-img-preview" :style="previewPos">
      <img :src="hoverPreview" class="me-preview-img" referrerpolicy="no-referrer" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  plainText: { type: String, default: '' },
  assets: { type: Array, default: () => [] },
  placeholder: { type: String, default: '编辑脚本内容，输入 @ 可引用资产...' },
  hydrateStamp: { type: String, default: '' },
  projectId: { type: String, default: '' },
})

const emit = defineEmits(['update:plainText', 'parse-error'])

const editorRef = ref(null)
const atMenuRef = ref(null)
const chipSwapRef = ref(null)

const atMenuOpen = ref(false)
const atFilter = ref('')
const atMenuPos = ref({ position: 'fixed', left: '0px', top: '0px' })
const chipSwapUi = ref(null)
const chipSwapAnchor = ref(null)

const previewRef = ref(null)
const hoverPreview = ref('')
const previewPos = ref({ position: 'fixed', left: '0px', top: '0px' })

// 资产同步状态（key = asset.id, value = { syncing, error, volcId }）
const syncStates = ref({})

let debounceTimer = null
let hydrating = false
let atMenuSavedRange = null

// ============ 资产列表 ============

const flatAssets = computed(() => {
  const list = []
  for (const a of props.assets) {
    if (a.characters) {
      for (const c of a.characters) {
        list.push({
          key: `char:${c.id}`, name: c.name, imageUrl: c.image_url || '',
          thumbnailUrl: c.thumbnail_url || c.image_url || '',
          type: 'role', typeLabel: '角色', id: c.id,
          volcId: c.volc_private_asset_id || '',
        })
      }
    }
    if (a.locations) {
      for (const loc of a.locations) {
        list.push({
          key: `loc:${loc.id}`, name: loc.name, imageUrl: loc.image_url || '',
          thumbnailUrl: loc.thumbnail_url || loc.image_url || '',
          type: 'scene', typeLabel: '场景', id: loc.id,
          volcId: loc.volc_private_asset_id || '',
        })
      }
    }
    if (a.props) {
      for (const p of a.props) {
        list.push({
          key: `prop:${p.id}`, name: p.name, imageUrl: p.image_url || '',
          thumbnailUrl: p.thumbnail_url || p.image_url || '',
          type: 'prop', typeLabel: '道具', id: p.id,
          volcId: p.volc_private_asset_id || '',
        })
      }
    }
  }
  return list
})

const filteredAssets = computed(() => {
  const q = atFilter.value.trim().toLowerCase()
  const base = flatAssets.value
  if (!q) return base.slice(0, 24)
  return base.filter(a => a.name.toLowerCase().includes(q)).slice(0, 24)
})

const chipSwapRows = computed(() => {
  if (!chipSwapUi.value) return []
  return flatAssets.value.filter(a => a.type === chipSwapUi.value.slot && a.imageUrl)
})

// ============ hydrate: plainText → DOM ============

// 资产数据的指纹，用于检测资产列表加载完成
const assetsFingerprint = computed(() => {
  const fa = flatAssets.value
  if (!fa.length) return ''
  return fa.map(a => `${a.id}:${a.imageUrl ? 1 : 0}`).join(',')
})

watch([() => props.plainText, () => props.hydrateStamp, assetsFingerprint], () => {
  hydrateFromPlainText()
}, { immediate: false })

function hydrateFromPlainText() {
  const el = editorRef.value
  if (!el) return

  // 编辑器聚焦时跳过 hydrate
  if (el.contains(document.activeElement)) return

  hydrating = true
  const text = props.plainText || ''
  if (!text.trim()) {
    el.innerHTML = ''
  } else {
    el.innerHTML = renderPlainTextToHtml(text)
  }
  hydrating = false
}

function renderPlainTextToHtml(text) {
  const lines = text.split('\n')

  // 预扫描：收集旧格式 shot 的 duration（新格式直接读取文本中的 start/end）
  const oldDurations = []
  for (const line of lines) {
    const legacyMatch = line.match(/^分镜(\d+)\s*@\s*([\d.]+)s\s*:\s*([\s\S]*)$/)
    if (legacyMatch) {
      oldDurations.push(Math.max(0.5, Math.min(15, parseFloat(legacyMatch[2]) || 3)))
      continue
    }
    const oldMatch = line.match(/^镜头(\d+)\s*:\s*(.*)/)
    if (oldMatch) {
      const parsed = parseShotBody(oldMatch[2])
      oldDurations.push(parsed.duration)
    }
  }

  const htmlParts = []
  let cumulative = 0
  let oldShotIdx = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (!line.trim()) {
      htmlParts.push('<div class="me-blank"><br></div>')
      continue
    }

    // 新格式镜头行: 镜头 N（start 至 end 秒）：...（直接读取文本中的时间）
    const newShotMatch = line.match(/^镜头\s*(\d+)\s*（\s*([\d.]+)\s*至\s*([\d.]+)\s*秒\s*）\s*：\s*(.*)$/)
    if (newShotMatch) {
      const shotIdxNum = newShotMatch[1]
      const start = parseFloat(newShotMatch[2])
      const end = parseFloat(newShotMatch[3])
      const dur = Math.max(0.5, Math.min(15, end - start))
      const body = newShotMatch[4] || ''

      let shotHtml = `<div class="me-shot-line">`
      shotHtml += `<div class="me-shot-header">`
      shotHtml += `<span class="me-shot-head" data-shot-duration="${dur}">`
      shotHtml += `<span class="me-shot-idx">镜头 ${shotIdxNum}（${start} 至 ${end} 秒）：</span>`
      shotHtml += `</span>`
      shotHtml += `</div>`
      shotHtml += `<div class="me-shot-detail">${body.trim() ? renderInlineContent(body) : '<br>'}</div>`
      shotHtml += `</div>`
      htmlParts.push(shotHtml)
      continue
    }

    // 旧格式镜头行: 分镜N @ Xs:... (向后兼容)
    const legacyShotMatch = line.match(/^分镜(\d+)\s*@\s*([\d.]+)s\s*:\s*([\s\S]*)$/)
    if (legacyShotMatch) {
      const shotIdxNum = legacyShotMatch[1]
      const dur = oldDurations[oldShotIdx]
      const start = cumulative
      const end = cumulative + dur
      const body = legacyShotMatch[3] || ''

      let shotHtml = `<div class="me-shot-line">`
      shotHtml += `<div class="me-shot-header">`
      shotHtml += `<span class="me-shot-head" data-shot-duration="${dur}">`
      shotHtml += `<span class="me-shot-idx">镜头 ${shotIdxNum}（${start} 至 ${end} 秒）：</span>`
      shotHtml += `</span>`
      shotHtml += `</div>`
      shotHtml += `<div class="me-shot-detail">${body.trim() ? renderInlineContent(body) : '<br>'}</div>`
      shotHtml += `</div>`
      htmlParts.push(shotHtml)
      oldShotIdx++
      cumulative = end
      continue
    }

    // 旧格式镜头行: 镜头N: ... (向后兼容)
    const shotMatch = line.match(/^镜头(\d+)\s*:\s*(.*)/)
    if (shotMatch) {
      const shotIdxNum = shotMatch[1]
      const dur = oldDurations[oldShotIdx]
      const start = cumulative
      const end = cumulative + dur
      const body = shotMatch[2]
      const parsed = parseShotBody(body)

      let shotHtml = `<div class="me-shot-line">`
      shotHtml += `<div class="me-shot-header">`
      shotHtml += `<span class="me-shot-head" data-shot-duration="${dur}">`
      shotHtml += `<span class="me-shot-idx">镜头 ${shotIdxNum}（${start} 至 ${end} 秒）：</span>`
      shotHtml += `</span>`
      shotHtml += `</div>`
      shotHtml += `<div class="me-shot-detail">${renderInlineContent(parsed.text)}</div>`
      shotHtml += `</div>`
      htmlParts.push(shotHtml)
      oldShotIdx++
      cumulative = end
      continue
    }

    // 片段边界检测：重置旧格式累加器
    if (/^画面风格和类型:/.test(line) || /^场景:/.test(line) || /^分镜过渡:/.test(line)) {
      cumulative = 0
    }

    // 画面风格和类型行
    const styleMatch = line.match(/^画面风格和类型:\s*(.*)/)
    if (styleMatch) {
      const val = styleMatch[1]
      htmlParts.push(`<div class="me-meta-line"><span class="me-meta-label">画面风格和类型:</span><span class="me-meta-value">${val.trim() ? renderInlineContent(val) : ''}</span></div>`)
      continue
    }

    // 场景/分镜过渡 标签行
    if (/^场景:\s*$/.test(line)) {
      htmlParts.push(`<div class="me-meta-line"><span class="me-meta-label">场景:</span><span class="me-meta-value"></span></div>`)
      continue
    }
    if (/^分镜过渡:\s*$/.test(line)) {
      htmlParts.push(`<div class="me-meta-line"><span class="me-meta-label">分镜过渡:</span><span class="me-meta-value"></span></div>`)
      continue
    }

    // 旧格式: 【片段意图】... / 【场景总述】...
    if (/^【/.test(line)) {
      const bracketMatch = line.match(/^【([^】]+)】(.*)/)
      if (bracketMatch) {
        htmlParts.push(`<div class="me-meta-line"><span class="me-meta-label">【${escapeHtml(bracketMatch[1])}】</span><span class="me-meta-value">${renderInlineContent(bracketMatch[2])}</span></div>`)
        continue
      }
    }

    // 普通行
    htmlParts.push(`<div class="me-text-line">${renderInlineContent(line)}</div>`)
  }

  return htmlParts.join('')
}

function parseShotBody(body) {
  const parts = body.split('|')
  let duration = 3
  const textParts = []

  for (const part of parts) {
    const trimmed = part.trim()
    const durMatch = trimmed.match(/^duration\s*=\s*([\d.]+)\s*s$/i)
    if (durMatch) {
      duration = parseFloat(durMatch[1]) || 3
    } else if (trimmed) {
      textParts.push(trimmed)
    }
  }

  return { duration: Math.max(0.5, Math.min(15, duration)), text: textParts.join(' | ') }
}

function formatShotDuration(sec) {
  return sec % 1 === 0 ? `${sec}s` : `${sec.toFixed(1)}s`
}

function renderInlineContent(text) {
  return text.replace(/\[\[([^|\]]+)\|(ROLE|LOC|SCENE|PROP)\|([^\]]+)\]\]/g, (match, name, type, id) => {
    const asset = flatAssets.value.find(a => a.id === id || a.name === name)
    const imgUrl = asset?.imageUrl || ''
    // chip 内联图片优先使用缩略图，原图 URL 通过 data-preview-url 保留供悬停预览使用
    const thumbUrl = asset?.thumbnailUrl || asset?.imageUrl || ''
    const typeClass = type === 'ROLE' ? 'me-chip-role' : 'me-chip-loc'
    let inner = ''
    if (thumbUrl && (thumbUrl.startsWith('http://') || thumbUrl.startsWith('https://') || thumbUrl.startsWith('/'))) {
      inner += `<img src="${escapeHtml(thumbUrl)}" class="me-chip-img" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-original-url="${escapeHtml(imgUrl)}" onerror="if(!this.dataset.fallback&&this.dataset.originalUrl){this.dataset.fallback='1';this.src=this.dataset.originalUrl}" />`
    } else {
      inner += `<span class="me-chip-fallback">${escapeHtml(name.slice(0, 2))}</span>`
    }
    inner += `<span class="me-chip-name">${escapeHtml(name)}</span>`
    return `<span class="me-chip ${typeClass}" data-mm-token="${encodeURIComponent(match)}" data-preview-url="${escapeHtml(imgUrl)}" contenteditable="false">${inner}</span>`
  }).replace(/\n/g, '<br>')
}

// ============ DOM → plainText ============

function readPlainTextFromDom() {
  const el = editorRef.value
  if (!el) return ''
  return domToPlainText(el)
}

function domToPlainText(el) {
  const lines = []
  const children = el.childNodes
  let cumulative = 0
  // 缓冲连续的内联内容（裸文本节点、chip、BR、span 等），合并为同一行
  let inlineBuffer = []

  function flushInline() {
    if (inlineBuffer.length === 0) return
    const text = inlineBuffer.join('')
    if (text.trim()) lines.push(text)
    inlineBuffer = []
  }

  for (const child of children) {
    if (child.nodeType === Node.TEXT_NODE) {
      inlineBuffer.push(child.textContent)
      continue
    }

    if (child.nodeType !== Node.ELEMENT_NODE) continue
    const ce = child

    if (ce.classList.contains('me-shot-line')) {
      flushInline()
      const header = ce.querySelector('.me-shot-head')
      const detail = ce.querySelector('.me-shot-detail')
      const idxText = header?.querySelector('.me-shot-idx')?.textContent || '镜头 1'
      const idxMatch = idxText.match(/(\d+)/)
      const idx = idxMatch ? idxMatch[1] : '1'

      // 优先从用户编辑的显示文本中解析时长
      const rangeMatch = idxText.match(/（\s*([\d.]+)\s*至\s*([\d.]+)\s*秒/)
      let dur
      if (rangeMatch) {
        const parsedDur = parseFloat(rangeMatch[2]) - parseFloat(rangeMatch[1])
        if (parsedDur > 0 && parsedDur <= 15) {
          dur = parsedDur
          if (header) header.setAttribute('data-shot-duration', String(dur))
        } else {
          const durAttr = header?.getAttribute('data-shot-duration')
          dur = durAttr ? parseFloat(durAttr) : 3
        }
      } else {
        const durAttr = header?.getAttribute('data-shot-duration')
        dur = durAttr ? parseFloat(durAttr) : 3
      }

      const start = cumulative
      const end = cumulative + dur
      const desc = detail ? inlineDomToText(detail) : ''
      lines.push(`镜头 ${idx}（${start} 至 ${end} 秒）：${desc}`)
      cumulative = end
    } else if (ce.classList.contains('me-meta-line')) {
      flushInline()
      const metaText = ce.textContent.trim()
      // 片段边界：重置 shot 时间累加器
      if (/^画面风格和类型:/.test(metaText) || /^场景:/.test(metaText) || /^分镜过渡:/.test(metaText)) {
        cumulative = 0
      }
      lines.push(metaText)
    } else if (ce.classList.contains('me-blank')) {
      flushInline()
      lines.push('')
    } else if (ce.classList.contains('me-text-line')) {
      flushInline()
      lines.push(inlineDomToText(ce))
    } else if (ce.tagName === 'DIV' || ce.tagName === 'P' || ce.tagName === 'LI') {
      // 浏览器生成的块级包装：另起一行处理，保留其中的 chip token
      flushInline()
      const t = inlineDomToText(ce)
      if (t.trim()) lines.push(t)
    } else {
      // 其它内联元素（chip、BR、span、img 等）：追加到当前行缓冲
      inlineBuffer.push(rootInlineNodeToText(ce))
    }
  }
  flushInline()

  // 清除残留的 @[[  连接（@ 触发字符未被完全消费时）
  return lines.join('\n').replace(/@\[\[/g, '[[')
}

// 根级内联节点 → 纯文本（保留 chip 的 [[name|TYPE|id]] token）
function rootInlineNodeToText(node) {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent
  if (node.nodeType !== Node.ELEMENT_NODE) return ''
  if (node.tagName === 'BR') return '\n'
  if (node.classList.contains('me-chip')) {
    const raw = node.getAttribute('data-mm-token')
    if (raw) {
      try { return decodeURIComponent(raw) } catch { return node.textContent }
    }
    return node.textContent
  }
  return inlineDomToText(node)
}

function inlineDomToText(el) {
  let result = ''
  for (const child of el.childNodes) {
    if (child.nodeType === Node.TEXT_NODE) {
      result += child.textContent
    } else if (child.nodeType === Node.ELEMENT_NODE) {
      if (child.classList.contains('me-chip')) {
        const raw = child.getAttribute('data-mm-token')
        if (raw) {
          try { result += decodeURIComponent(raw) } catch { result += child.textContent }
        } else {
          result += child.textContent
        }
      } else if (child.tagName === 'BR') {
        result += '\n'
      } else {
        result += inlineDomToText(child)
      }
    }
  }
  return result
}

function parseDurValue(val) {
  const n = parseFloat(String(val).replace(/[^0-9.]/g, ''))
  if (!Number.isFinite(n)) return 3
  return Math.max(0.5, Math.min(15, n))
}

// ============ 事件处理 ============

function onEditorInput() {
  if (hydrating) return

  // 直接从 DOM selection 检测 @ 状态（不依赖 readPlainTextFromDom，兼容所有输入法）
  const sel = window.getSelection()
  const root = editorRef.value
  if (sel && sel.rangeCount > 0 && root && root.contains(sel.anchorNode)) {
    const tail = getAtFilterTailFromDom(sel)
    if (tail !== null) {
      if (!atMenuOpen.value) {
        atMenuOpen.value = true
        atFilter.value = ''
      }
      atFilter.value = tail
      requestAnimationFrame(() => {
        const s = window.getSelection()
        if (root && s && s.rangeCount > 0) {
          const r = s.getRangeAt(0)
          if (root.contains(r.commonAncestorContainer)) {
            atMenuSavedRange = r.cloneRange()
          }
        }
        updateAtMenuPos()
      })
    } else if (atMenuOpen.value) {
      closeAtMenu()
    }
  } else if (atMenuOpen.value) {
    closeAtMenu()
  }

  const plain = readPlainTextFromDom()
  scheduleEmit(plain)
}

function scheduleEmit(plain) {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    if (hydrating) return
    emit('update:plainText', plain)
    emit('parse-error', null)
  }, 650)
}

function onEditorKeyDown(e) {
  // 时长输入框中的按键处理
  if (e.target.classList?.contains('me-shot-dur-input')) {
    e.stopPropagation()
    if (e.key === 'Enter') {
      e.preventDefault()
      commitDuration(e.target)
      e.target.blur()
    }
    return
  }

  // Escape 关闭菜单
  if (e.key === 'Escape') {
    if (chipSwapUi.value) {
      chipSwapAnchor.value = null
      chipSwapUi.value = null
    }
    if (atMenuOpen.value) {
      closeAtMenu()
    }
    return
  }

  // 光标落在 colon/suffix 区域时重定向
  redirectCursorFromSuffix()
}

function onEditorPaste(e) {
  const html = e.clipboardData?.getData('text/html') || ''
  if (html.includes('me-shot-') || html.includes('me-chip')) return

  e.preventDefault()
  const text = e.clipboardData?.getData('text/plain') || ''
  if (!text) return
  document.execCommand('insertText', false, text)
}

function onEditorMouseDown(e) {
  const chip = e.target?.closest?.('.me-chip')
  if (!chip || !editorRef.value?.contains(chip)) return
  const raw = chip.getAttribute('data-mm-token')
  if (!raw) return

  let token = ''
  try { token = decodeURIComponent(raw) } catch { return }

  const m = token.match(/^\[\[([^\]|]*)\|(ROLE|LOC|SCENE|PROP)\|([^\]]+)\]\]$/)
  if (!m) return

  e.preventDefault()
  atMenuOpen.value = false
  chipSwapAnchor.value = chip
  const rect = chip.getBoundingClientRect()
  const slot = m[2] === 'ROLE' ? 'role' : (m[2] === 'SCENE' || m[2] === 'PROP' ? 'scene' : 'scene')
  chipSwapUi.value = { slot, top: rect.bottom + 4, left: rect.left, minW: Math.max(220, rect.width) }
}

function onEditorMouseUp() {
  nextTick(redirectCursorFromSuffix)
}

// ============ 资产大图悬停预览 ============

function onEditorMouseOver(e) {
  const chip = e.target?.closest?.('.me-chip')
  if (!chip) return
  const url = chip.getAttribute('data-preview-url')
  if (!url) return
  hoverPreview.value = url
  nextTick(() => {
    const rect = chip.getBoundingClientRect()
    const pEl = previewRef.value
    const pHeight = pEl?.offsetHeight || 160
    let top = rect.top - pHeight - 8
    let left = rect.left
    // 上方空间不足则放下方
    if (top < 8) {
      top = rect.bottom + 8
    }
    // 右边界约束
    const maxLeft = window.innerWidth - (pEl?.offsetWidth || 200) - 8
    if (left > maxLeft) left = maxLeft
    if (left < 8) left = 8
    previewPos.value = { position: 'fixed', top: `${top}px`, left: `${left}px` }
  })
}

function onEditorMouseOut(e) {
  const chip = e.target?.closest?.('.me-chip')
  const related = e.relatedTarget?.closest?.('.me-chip')
  if (chip && !related) {
    hoverPreview.value = ''
  }
}

// ============ 时长输入处理 ============

function commitDuration(input) {
  if (hydrating) return
  const head = input.closest('.me-shot-head')
  if (!head) return

  let n = parseDurValue(input.value)
  n = Math.max(0.5, Math.min(15, n))
  input.value = formatShotDuration(n)
  head.setAttribute('data-shot-duration', String(n))

  const plain = readPlainTextFromDom()
  scheduleEmit(plain)
}

// 全局 focusin/focusout 处理
function onDocFocusIn(e) {
  if (e.target?.classList?.contains('me-shot-dur-input')) {
    requestAnimationFrame(() => e.target.select())
  }
}

function onDocFocusOut(e) {
  if (e.target?.classList?.contains('me-shot-dur-input')) {
    commitDuration(e.target)
  }
}

// ============ @ 菜单 ============

function updateAtMenuPos() {
  const root = editorRef.value
  const sel = window.getSelection()
  if (!root || !sel || sel.rangeCount === 0) return
  const range = sel.getRangeAt(0)
  if (!root.contains(range.commonAncestorContainer)) return
  const rect = range.getBoundingClientRect()

  let left = rect.left
  let top = rect.bottom + 6

  // 约束在编辑器范围内
  const rootRect = root.getBoundingClientRect()
  left = Math.max(rootRect.left, Math.min(left, rootRect.right - 240))
  left = Math.max(8, Math.min(left, window.innerWidth - 328))

  // 如果超出屏幕底部，尝试在光标上方显示
  if (top + 280 > window.innerHeight) {
    const aboveTop = rect.top - 286
    if (aboveTop > 8) top = aboveTop
  }
  top = Math.max(8, top)

  atMenuPos.value = { position: 'fixed', left: `${left}px`, top: `${top}px` }
}

function pickAsset(asset) {
  const typeToken = asset.type === 'role' ? 'ROLE' : (asset.type === 'scene' ? 'SCENE' : 'PROP')
  const token = `[[${asset.name}|${typeToken}|${asset.id}]]`
  const chipHtml = buildChipHtml(asset.name, asset.imageUrl, token, asset.type, asset.thumbnailUrl)
  insertChipAtSelection(chipHtml)
  closeAtMenu()
}

function buildChipHtml(name, imgUrl, token, assetType, thumbUrl) {
  const typeClass = assetType === 'role' ? 'me-chip-role' : 'me-chip-loc'
  // img src 优先使用缩略图，原图通过 data-original-url 保留供 onerror fallback
  const srcUrl = thumbUrl || imgUrl
  let inner = ''
  if (srcUrl && (srcUrl.startsWith('http://') || srcUrl.startsWith('https://') || srcUrl.startsWith('/'))) {
    inner += `<img src="${escapeHtml(srcUrl)}" class="me-chip-img" loading="lazy" decoding="async" referrerpolicy="no-referrer" data-original-url="${escapeHtml(imgUrl)}" onerror="if(!this.dataset.fallback&&this.dataset.originalUrl){this.dataset.fallback='1';this.src=this.dataset.originalUrl}" />`
  } else {
    inner += `<span class="me-chip-fallback">${escapeHtml(name.slice(0, 2))}</span>`
  }
  inner += `<span class="me-chip-name">${escapeHtml(name)}</span>`
  return `<span class="me-chip ${typeClass}" data-mm-token="${encodeURIComponent(token)}" data-preview-url="${escapeHtml(imgUrl)}" contenteditable="false">${inner}</span>`
}

function insertChipAtSelection(html) {
  const el = editorRef.value
  if (!el) return
  el.focus()

  const sel = window.getSelection()
  if (!sel) return

  // 恢复保存的 range
  const saved = atMenuSavedRange
  atMenuSavedRange = null
  if (saved && el.contains(saved.commonAncestorContainer)) {
    try {
      sel.removeAllRanges()
      sel.addRange(saved)
    } catch { /* range 可能已失效 */ }
  }

  // 没有 selection 则追加到编辑器末尾
  if (sel.rangeCount === 0 || !sel.anchorNode || !el.contains(sel.anchorNode)) {
    const lastLine = el.querySelector(':scope > :last-child') || el
    const tpl = document.createElement('template')
    tpl.innerHTML = html.trim()
    const frag = document.createDocumentFragment()
    while (tpl.content.firstChild) frag.appendChild(tpl.content.firstChild)
    lastLine.appendChild(frag)
  } else {
    const range = sel.getRangeAt(0)

    // 删除 @ 字符及后续 filter 文本
    if (range.collapsed && range.startContainer.nodeType === Node.TEXT_NODE) {
      const tn = range.startContainer
      const off = range.startOffset
      // 回溯找到 @ 并删除从 @ 到当前位置的文本
      const textBefore = tn.data.substring(0, off)
      const atIdx = textBefore.lastIndexOf('@')
      if (atIdx >= 0) {
        range.setStart(tn, atIdx)
      } else if (off >= 1 && tn.data.charCodeAt(off - 1) === 64) {
        range.setStart(tn, off - 1)
      }
    }
    range.deleteContents()

    const tpl = document.createElement('template')
    tpl.innerHTML = html.trim()
    const frag = document.createDocumentFragment()
    while (tpl.content.firstChild) frag.appendChild(tpl.content.firstChild)
    // insertNode 会抽空 DocumentFragment，需提前捕获末节点
    const insertedLast = frag.lastChild
    range.insertNode(frag)

    // 折叠到 chip 之后，避免插入的 chip 处于 selection 范围内被浏览器高亮成"被选中"
    if (insertedLast) {
      range.setStartAfter(insertedLast)
      range.collapse(true)
      sel.removeAllRanges()
      sel.addRange(range)
    }
  }

  const plain = readPlainTextFromDom()
  scheduleEmit(plain)
}

function closeAtMenu() {
  atMenuOpen.value = false
  atFilter.value = ''
  atMenuSavedRange = null
}

async function syncVolc(asset) {
  if (!props.projectId) return
  const st = syncStates.value[asset.id] || {}
  if (st.syncing) return

  syncStates.value[asset.id] = { syncing: true, error: '', volcId: '' }
  try {
    const kind = asset.type === 'role' ? 'character' : (asset.type === 'scene' ? 'scene' : 'prop')
    const { syncAssetToVolc } = await import('@/api/project/asset')
    const res = await syncAssetToVolc(props.projectId, asset.id, kind)
    if (res?.volc_private_asset_id) {
      syncStates.value[asset.id] = { syncing: false, error: '', volcId: res.volc_private_asset_id }
      asset.volcId = res.volc_private_asset_id
    } else {
      syncStates.value[asset.id] = { syncing: false, error: '', volcId: '' }
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '同步失败'
    syncStates.value[asset.id] = { syncing: false, error: msg, volcId: '' }
  }
}

function getAtFilterTail(text, caretIdx) {
  if (caretIdx == null || caretIdx < 0 || caretIdx > text.length) return null
  const lineStart = text.lastIndexOf('\n', Math.max(0, caretIdx - 1)) + 1
  let segment = text.slice(lineStart, caretIdx)
  while (segment.length > 0) {
    const halfPos = segment.lastIndexOf('@')
    const fullPos = segment.lastIndexOf('＠')
    const atPos = Math.max(halfPos, fullPos)
    if (atPos < 0) return null
    const before = segment.slice(0, atPos)
    const after = segment.slice(atPos + 1)
    if (/(?:镜头|分镜)\d+\s*$/.test(before) && /^\s*[\d.,]*(s\s*:?)?$/i.test(after)) {
      segment = segment.slice(0, atPos)
      continue
    }
    if (after.includes('@') || after.includes('＠')) return null
    return after
  }
  return null
}

/**
 * 直接从 DOM Selection 检测 @ 引用的 filter tail。
 * 不依赖 readPlainTextFromDom 的序列化结果，避免 textContent 与序列化不一致的问题。
 */
function getAtFilterTailFromDom(sel) {
  if (!sel || sel.rangeCount === 0) return null
  const range = sel.getRangeAt(0)
  if (!range.collapsed) return null

  const node = range.startContainer
  // 只处理文本节点中的 @
  if (node.nodeType !== Node.TEXT_NODE) return null
  const text = node.textContent || ''
  const off = range.startOffset
  const textBefore = text.substring(0, off)

  // 找最后一个 @
  const halfPos = textBefore.lastIndexOf('@')
  const fullPos = textBefore.lastIndexOf('＠')
  const atPos = Math.max(halfPos, fullPos)
  if (atPos < 0) return null

  const before = textBefore.substring(0, atPos)
  const after = textBefore.substring(atPos + 1)

  // 排除镜头时长行的 @（兼容 镜头/分镜 格式）
  if (/(?:镜头|分镜)\d+\s*$/.test(before) && /^\s*[\d.,]*$/i.test(after)) return null

  // @ 后文本太长或含换行，不视为引用
  if (after.length > 30) return null

  return after
}

function getCaretCharIndex() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return null
  const range = sel.getRangeAt(0)
  const el = editorRef.value
  if (!el || !el.contains(range.commonAncestorContainer)) return null
  const pre = range.cloneRange()
  pre.selectNodeContents(el)
  pre.setEnd(range.endContainer, range.endOffset)
  return pre.toString().length
}

// ============ chip 替换 ============

function applyChipSwap(row) {
  const anchor = chipSwapAnchor.value
  const el = editorRef.value
  if (!anchor || !el) return

  const typeToken = row.type === 'role' ? 'ROLE' : (row.type === 'scene' ? 'SCENE' : 'PROP')
  const token = `[[${row.name}|${typeToken}|${row.id}]]`
  const html = buildChipHtml(row.name, row.imageUrl, token, row.type, row.thumbnailUrl)
  anchor.outerHTML = html
  chipSwapAnchor.value = null
  chipSwapUi.value = null

  const plain = readPlainTextFromDom()
  scheduleEmit(plain)
}

function onDocMouseDownForSwap(e) {
  if (!chipSwapUi.value) return
  if (chipSwapRef.value?.contains(e.target)) return
  if (chipSwapAnchor.value?.contains?.(e.target)) return
  chipSwapAnchor.value = null
  chipSwapUi.value = null
}

function onDocMouseDownForAtMenu(e) {
  if (!atMenuOpen.value) return
  if (atMenuRef.value?.contains(e.target)) return
  closeAtMenu()
}

// ============ 光标重定向 ============

function redirectCursorFromSuffix() {
  const sel = window.getSelection()
  const node = sel?.anchorNode
  if (!node) return
  const el = node instanceof Text ? node.parentElement : (node instanceof Element ? node : null)
  if (!el?.closest?.('.me-shot-colon')) return
  const shotLine = el.closest('.me-shot-line')
  const detail = shotLine?.querySelector('.me-shot-detail')
  if (!detail) return
  if (detail.childNodes.length === 1 && detail.firstChild?.nodeName === 'BR') detail.textContent = ''
  const range = document.createRange()
  range.setStart(detail, 0)
  range.collapse(true)
  sel.removeAllRanges()
  sel.addRange(range)
}

// ============ 工具函数 ============

function escapeHtml(str) {
  const div = document.createElement('div')
  div.textContent = str
  return div.innerHTML
}

/** 缩略图加载失败时回退到原图 */
function onThumbError(e, originalUrl) {
  const img = e.target
  if (img.dataset.fallback || !originalUrl) return
  img.dataset.fallback = '1'
  img.src = originalUrl
}

// ============ 公开方法 (flushSync) ============

function flushSync() {
  if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null }
  const plain = readPlainTextFromDom()
  emit('update:plainText', plain)
  return { plainText: plain }
}

function forceHydrate() {
  hydrating = true
  const text = props.plainText || ''
  const el = editorRef.value
  if (el) {
    if (!text.trim()) {
      el.innerHTML = ''
    } else {
      el.innerHTML = renderPlainTextToHtml(text)
    }
  }
  hydrating = false
}

defineExpose({ flushSync, readPlainText: readPlainTextFromDom, forceHydrate })

// ============ 生命周期 ============

onMounted(() => {
  hydrateFromPlainText()
  document.addEventListener('focusin', onDocFocusIn, true)
  document.addEventListener('focusout', onDocFocusOut, true)
  document.addEventListener('mousedown', onDocMouseDownForSwap, true)
  document.addEventListener('mousedown', onDocMouseDownForAtMenu, true)
  editorRef.value?.addEventListener('mouseover', onEditorMouseOver)
  editorRef.value?.addEventListener('mouseout', onEditorMouseOut)
})

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  document.removeEventListener('focusin', onDocFocusIn, true)
  document.removeEventListener('focusout', onDocFocusOut, true)
  document.removeEventListener('mousedown', onDocMouseDownForSwap, true)
  document.removeEventListener('mousedown', onDocMouseDownForAtMenu, true)
  editorRef.value?.removeEventListener('mouseover', onEditorMouseOver)
  editorRef.value?.removeEventListener('mouseout', onEditorMouseOut)
})
</script>

<style scoped>
.me-wrap { min-width: 0; position: relative; }

.me-editor {
  min-height: 18rem;
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid rgba(111,126,153,0.24);
  background: rgba(255,255,255,0.86);
  padding: 0.75rem;
  font-size: 0.875rem;
  line-height: 1.625;
  color: #0a0a0a;
  outline: none;
  transition: border-color 0.15s;
  white-space: pre-wrap;
  word-break: break-word;
}
.me-editor:focus { border-color: rgba(47,123,255,0.64); }
.me-editor:empty::before {
  content: attr(data-placeholder);
  color: #4b5563;
  pointer-events: none;
}
/* 子元素间距 */
.me-editor :deep(> * + *) { margin-top: 0.625rem; }

/* 镜头行 */
.me-editor :deep(.me-shot-line) { display: flex; flex-direction: column; gap: 0.25rem; padding-top: 0.25rem; }
.me-editor :deep(.me-shot-header) { display: flex; align-items: center; gap: 0.25rem; }
.me-editor :deep(.me-shot-head) { display: inline-flex; align-items: center; gap: 0.25rem; }
.me-editor :deep(.me-shot-idx) { font-weight: 500; color: #0a0a0a; }
.me-editor :deep(.me-shot-at) { display: inline-flex; align-items: center; color: #9ca3af; font-size: 0.75rem; }
.me-editor :deep(.me-shot-dur-field) { display: inline-flex; align-items: baseline; }
.me-editor :deep(.me-shot-dur-input) {
  min-width: 2rem; max-width: 2.65rem; width: 2.65rem;
  border-radius: 0.375rem; border: 1px solid rgba(161,161,170,0.45);
  background: rgba(244,244,245,0.8); padding: 0.125rem;
  text-align: center; font-size: 13px; font-weight: 600;
  font-variant-numeric: tabular-nums; line-height: 1; color: #111827; outline: none;
}
.me-editor :deep(.me-shot-dur-input:focus) { border-color: #71717a; box-shadow: 0 0 0 1px rgba(161,161,170,0.4); }
.me-editor :deep(.me-shot-range) { display: inline-flex; align-items: center; color: #9ca3af; font-size: 0.75rem; }
.me-editor :deep(.me-shot-colon) { font-size: 0.75rem; color: #9ca3af; user-select: none; }
.me-editor :deep(.me-shot-detail) { color: #111827; line-height: 1.625; }

/* 元数据行 */
.me-editor :deep(.me-meta-label) { font-weight: 500; color: #0a0a0a; }
.me-editor :deep(.me-meta-value) { color: #0a0a0a; word-break: break-word; }

/* 普通文本行 */
.me-editor :deep(.me-text-line) { color: #0a0a0a; }
.me-editor :deep(.me-blank) { min-height: 0; }

/* 资产 chip */
.me-editor :deep(.me-chip) {
  display: inline-flex; align-items: center; gap: 0.25rem;
  margin: 0 0.125rem; vertical-align: middle;
  border-radius: 0.25rem; border: 1px solid rgba(212,212,216,0.7);
  background: rgba(244,244,245,0.6); padding: 0.125rem 0.25rem;
  cursor: pointer; transition: background 0.15s;
}
.me-editor :deep(.me-chip:hover) { background: rgba(244,244,245,1); }
.me-editor :deep(.me-chip-img) { width: 1.25rem; height: 1.25rem; border-radius: 0.125rem; object-fit: cover; }
.me-editor :deep(.me-chip-name) { font-size: 0.75rem; color: #111827; max-width: 6em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.me-editor :deep(.me-chip-fallback) { width: 1.25rem; height: 1.25rem; border-radius: 0.125rem; display: inline-flex; align-items: center; justify-content: center; font-size: 9px; color: #71717a; background: rgba(228,228,231,0.6); flex-shrink: 0; }
.me-editor :deep(.me-chip-role) { border-color: rgba(99,102,241,0.3); background: rgba(99,102,241,0.06); }
.me-editor :deep(.me-chip-loc) { border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.06); }

/* 资产大图悬停预览 */
.me-img-preview {
  position: fixed; z-index: 70;
  border-radius: 0.5rem; border: 1px solid rgba(228,228,231,0.9);
  background: #fff; padding: 0.25rem;
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.15), 0 8px 10px -6px rgba(0,0,0,0.1);
  pointer-events: none;
  max-width: 200px; max-height: 200px;
  overflow: hidden;
}
.me-preview-img {
  width: 100%; height: 100%;
  max-width: 192px; max-height: 192px;
  border-radius: 0.375rem;
  object-fit: cover;
  display: block;
}

/* @ 菜单 */
.me-at-menu {
  position: fixed; z-index: 55;
  border-radius: 0.5rem; border: 1px solid rgba(228,228,231,0.9);
  background: #fff; padding: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
  max-height: 280px; width: 320px; overflow: visible;
}
.me-at-hint { font-size: 11px; color: #9ca3af; margin-bottom: 0.25rem; }
.me-at-list { max-height: 220px; overflow-y: auto; }
.me-at-empty { padding: 0.5rem 0.75rem; font-size: 0.75rem; color: #9ca3af; }
.me-at-row {
  display: flex; align-items: center; gap: 0.5rem; width: 100%;
  padding: 0.25rem 0.5rem 0.25rem 0.25rem; border-radius: 0.375rem; border: none;
  background: none; text-align: left; cursor: pointer; transition: background 0.1s;
  font-size: 0.75rem;
}
.me-at-row:hover:not(:disabled) { background: #f3f4f6; }
.me-at-row:disabled { opacity: 0.45; cursor: not-allowed; }
.me-at-row-wrap { display: flex; align-items: center; gap: 0.25rem; }
.me-at-sync {
  flex-shrink: 0; font-size: 10px; padding: 0.125rem 0.375rem; border-radius: 0.25rem;
  border: 1px solid rgba(245,158,11,0.3); background: rgba(245,158,11,0.08);
  color: #d97706; cursor: pointer; white-space: nowrap; transition: background 0.1s;
}
.me-at-sync:hover:not(:disabled) { background: rgba(245,158,11,0.16); }
.me-at-sync:disabled { opacity: 0.5; cursor: not-allowed; }
.me-at-syncing { color: #9ca3af; border-color: rgba(156,163,175,0.3); background: rgba(156,163,175,0.06); }
.me-at-sync-err { font-size: 9px; color: #ef4444; max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 1; }
.me-at-img { width: 2rem; height: 2rem; border-radius: 0.25rem; object-fit: cover; flex-shrink: 0; }
.me-at-noimg { width: 2rem; height: 2rem; border-radius: 0.25rem; background: #e5e7eb; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #9ca3af; flex-shrink: 0; }
.me-at-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #1c1917; }
.me-at-type { font-size: 10px; font-weight: 500; background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 0.25rem; color: #71717a; flex-shrink: 0; }
.me-at-close { width: 100%; padding: 0.25rem; font-size: 11px; color: #9ca3af; background: none; border: none; cursor: pointer; border-radius: 0.25rem; margin-top: 0.25rem; }
.me-at-close:hover { background: #f3f4f6; }

/* chip 替换菜单 */
.me-swap-menu {
  position: fixed; z-index: 60;
  border-radius: 0.5rem; border: 1px solid rgba(228,228,231,0.9);
  background: #fff; padding: 0.5rem;
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1);
  max-height: 224px;
  min-width: min(calc(100vw - 1.5rem), 18rem);
  overflow-y: auto;
}
.me-swap-hint { font-size: 11px; font-weight: 500; color: #6b7280; margin-bottom: 0.25rem; }
.me-swap-empty { padding: 0.5rem; font-size: 0.75rem; color: #9ca3af; }
.me-swap-row {
  display: flex; align-items: center; gap: 0.5rem; width: 100%;
  padding: 0.375rem 0.5rem; border-radius: 0.375rem; border: none;
  background: none; text-align: left; cursor: pointer; transition: background 0.1s;
  font-size: 0.75rem;
}
.me-swap-row:hover { background: #f3f4f6; }
.me-swap-img { width: 1.75rem; height: 1.75rem; border-radius: 0.25rem; object-fit: cover; flex-shrink: 0; }
.me-swap-noimg { width: 1.75rem; height: 1.75rem; border-radius: 0.25rem; background: #e5e7eb; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #9ca3af; flex-shrink: 0; }
.me-swap-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #0a0a0a; }
.me-swap-close { width: 100%; padding: 0.25rem; font-size: 11px; color: #9ca3af; background: none; border: none; cursor: pointer; border-radius: 0.25rem; margin-top: 0.25rem; }
.me-swap-close:hover { background: #f3f4f6; }
</style>
