<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <!-- 图片预览浮层（放在 modal-dialog 外层，避免被 overflow:hidden 裁剪） -->
    <div v-if="previewImageUrl" class="preview-overlay" @click.stop="previewImageUrl = null">
      <img :src="previewImageUrl" class="preview-full-img" />
    </div>

    <div class="modal-dialog glass-surface-modal">
      <div class="dialog-header">
        <div class="dialog-title-row">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <h3 class="dialog-title">{{ titleText }}</h3>
        </div>
        <button class="glass-btn-base glass-btn-soft close-btn" @click="$emit('close')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>

      <!-- 多类型切换 tab（multi 模式下显示） -->
      <div v-if="multi" class="dialog-tabs">
        <button
          v-for="t in typeTabs"
          :key="t.value"
          :class="['tab-btn', { 'tab-btn-active': activeType === t.value }]"
          @click="switchType(t.value)"
        >
          {{ t.label }}
          <span v-if="selectedCountByType[t.value]" class="tab-badge">{{ selectedCountByType[t.value] }}</span>
        </button>
      </div>

      <!-- 搜索 + 资产组筛选 + 本页全选（multi 模式下显示） -->
      <div class="dialog-toolbar">
        <div class="dialog-search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input v-model="searchQuery" class="search-input" placeholder="搜索资产名称..." />
        </div>
        <template v-if="multi">
          <el-select
            v-model="activeFolder"
            class="folder-select"
            placeholder="资产组筛选"
            clearable
            size="small"
            :popper-options="{ strategy: 'fixed' }"
            @change="onFolderChange"
          >
            <el-option label="全部资产组" value="" />
            <el-option
              v-for="f in folders"
              :key="f.id"
              :label="f.name"
              :value="f.id"
            />
          </el-select>
          <button
            class="select-page-btn"
            :class="{ 'select-page-btn--active': allOnPageSelected }"
            @click="toggleSelectAllOnPage"
          >
            {{ allOnPageSelected ? '取消本页全选' : '本页全选' }}
          </button>
        </template>
      </div>

      <div
        ref="scrollContainer"
        class="dialog-content"
        @scroll="handleScroll"
      >
        <!-- 加载中 -->
        <div v-if="loadingState && items.length === 0" class="empty-state">
          <div class="empty-spinner" />
          <span>加载中...</span>
        </div>

        <!-- 空状态 -->
        <div v-else-if="filteredItems.length === 0 && !loadingState" class="empty-state">
          <p class="empty-text">{{ items.length === 0 ? '资产中心暂无资产' : '没有匹配的资产' }}</p>
        </div>

        <!-- 资产网格 -->
        <div v-else class="asset-grid">
          <div
            v-for="item in filteredItems"
            :key="item.id"
            :class="['asset-card', 'glass-surface-soft', {
              'asset-card--selected': isItemSelected(item),
              'asset-card--imported': isItemImported(item),
            }]"
            @click="toggleSelect(item)"
          >
            <div class="card-preview">
              <img v-if="item.preview_url" :src="item.thumbnail_url || item.preview_url" :alt="item.name" class="preview-img preview-img--zoomable" @click.stop="previewImageUrl = item.preview_url" @error="onImgError($event, item.preview_url)" />
              <div v-else class="preview-placeholder">
                <span>{{ item.name?.charAt(0) || '?' }}</span>
              </div>
              <span v-if="isItemImported(item)" class="badge badge--imported">已导入</span>
              <span v-if="isItemSelected(item)" class="badge badge--selected">已选</span>
            </div>
            <div class="card-info">
              <span class="card-name">{{ item.name }}</span>
              <span v-if="item.folder_name" class="card-folder">{{ item.folder_name }}</span>
            </div>
          </div>
        </div>

        <!-- 加载更多指示器 -->
        <div v-if="fetchingMore" class="load-more-indicator">
          <div class="empty-spinner" />
          <span>加载更多...</span>
        </div>
      </div>

      <div class="dialog-footer">
        <span v-if="multi && totalSelected > 0" class="footer-summary">已选 {{ totalSelected }} 项</span>
        <span v-else style="flex: 1" />
        <button class="glass-btn-base glass-btn-secondary footer-btn" @click="$emit('close')">
          取消
        </button>
        <button
          class="glass-btn-base glass-btn-primary footer-btn"
          :disabled="(multi ? totalSelected === 0 : !selectedId) || loading"
          @click="onConfirm"
        >
          {{ multi ? `导入 ${totalSelected || ''} 项` : '确认导入' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { getGlobalAssetPickerList, getGlobalAssetFolders, getAssets } from '@/api/project/assets'

const props = defineProps({
  visible: Boolean,
  type: { type: String, default: 'character' },
  loading: Boolean,
  // 多选模式（导演模式批量导入用）：开启后显示类型 tab、支持跨类型多选
  multi: { type: Boolean, default: false },
  // 项目 ID（multi 模式下用于查询已导入资产）
  projectId: { type: String, default: '' },
})

const emit = defineEmits(['close', 'select'])

// 单选模式
const selectedId = ref(null)
// 多选模式：{ [type]: Set<id> }
const selectedMap = ref({ character: new Set(), location: new Set(), prop: new Set() })
// 多选模式下当前查看的类型 tab
const activeType = ref('all')
// 缓存每个类型的资产列表（切 tab 不丢）
const itemsByType = ref({ character: [], location: [], prop: [] })
// 每类独立分页状态
const pageByType = ref({ character: 0, location: 0, prop: 0 })
const hasMoreByType = ref({ character: true, location: true, prop: true })

const searchQuery = ref('')
const items = ref([])
const hasMore = ref(true)
const loadingState = ref(false)
const fetchingMore = ref(false)
const scrollContainer = ref(null)
const previewImageUrl = ref(null)
// 资产组筛选（multi 模式）
const folders = ref([])
const activeFolder = ref('')
// 已导入资产（multi 模式）：{ [type]: Set<global_id> }
const importedIdsByType = ref({
  character: new Set(),
  location: new Set(),
  prop: new Set(),
})

const typeTabs = [
  { value: 'all', label: '全部' },
  { value: 'character', label: '角色' },
  { value: 'location', label: '场景' },
  { value: 'prop', label: '道具' },
]

const titleText = computed(() => {
  if (props.multi) return '从资产中心批量导入'
  const map = { character: '选择角色', location: '选择场景', prop: '选择道具' }
  return map[props.type] || '选择资产'
})

const currentType = computed(() => (props.multi ? activeType.value : props.type))

const selectedCountByType = computed(() => {
  const out = {}
  for (const t of Object.keys(selectedMap.value)) {
    out[t] = selectedMap.value[t].size
  }
  return out
})

const totalSelected = computed(() =>
  Object.values(selectedMap.value).reduce((sum, s) => sum + s.size, 0),
)

const filteredItems = computed(() => {
  if (!searchQuery.value) return items.value
  const q = searchQuery.value.toLowerCase()
  return items.value.filter(item => item.name?.toLowerCase().includes(q))
})

function isItemSelected(item) {
  if (props.multi) {
    const t = item.type || currentType.value
    return selectedMap.value[t]?.has(item.id) || false
  }
  return selectedId.value === item.id
}

function toggleSelect(item) {
  if (props.multi) {
    if (isItemImported(item)) return
    const t = item.type || currentType.value
    const set = selectedMap.value[t]
    if (set.has(item.id)) set.delete(item.id)
    else set.add(item.id)
    // 触发响应式：重新赋值
    selectedMap.value = { ...selectedMap.value, [t]: new Set(set) }
  } else {
    selectedId.value = item.id
  }
}

function switchType(t) {
  activeType.value = t
  searchQuery.value = ''
  previewImageUrl.value = null
  // 切到具体类型时：缓存有就用缓存；否则发起首次加载
  if (t === 'all') {
    // 'all'：合并三类缓存；若三类都没拉过则发起加载
    const types = ['character', 'location', 'prop']
    const allCached = types.every(tt => itemsByType.value[tt].length > 0 || pageByType.value[tt] > 0)
    if (allCached) {
      items.value = [
        ...itemsByType.value.character,
        ...itemsByType.value.location,
        ...itemsByType.value.prop,
      ]
      hasMore.value = types.some(tt => hasMoreByType.value[tt])
    } else {
      items.value = []
      fetchItems()
    }
  } else {
    const cached = itemsByType.value[t]
    if (cached.length > 0 || pageByType.value[t] > 0) {
      items.value = cached
      hasMore.value = hasMoreByType.value[t]
    } else {
      items.value = []
      fetchItems()
    }
  }
}

async function fetchFolders() {
  try {
    const res = await getGlobalAssetFolders({ size: 100 })
    folders.value = res?.data || []
  } catch {
    folders.value = []
  }
}

async function fetchImportedAssets() {
  if (!props.projectId) return
  try {
    const res = await getAssets(props.projectId, 'all')
    const data = res?.data || res || {}
    const lists = {
      character: data.characters || [],
      location: data.locations || [],
      prop: data.props || [],
    }
    const out = { character: new Set(), location: new Set(), prop: new Set() }
    for (const t of Object.keys(lists)) {
      for (const a of lists[t]) {
        if (a.source_global_id) out[t].add(a.source_global_id)
      }
    }
    importedIdsByType.value = out
  } catch {
    // 静默
  }
}

function isItemImported(item) {
  if (!props.multi) return false
  const t = item.type || currentType.value
  return importedIdsByType.value[t]?.has(item.id) || false
}

function onFolderChange() {
  // 切资产组：清三类缓存 + 重置分页 + 重新拉取
  pageByType.value = { character: 0, location: 0, prop: 0 }
  hasMoreByType.value = { character: true, location: true, prop: true }
  itemsByType.value = { character: [], location: [], prop: [] }
  items.value = []
  fetchItems()
}

function toggleSelectAllOnPage() {
  const visible = filteredItems.value.filter(it => !isItemImported(it))
  if (visible.length === 0) return
  const allSelected = visible.every(it => {
    const t = it.type || currentType.value
    return selectedMap.value[t]?.has(it.id)
  })
  if (allSelected) {
    visible.forEach(it => {
      const t = it.type || currentType.value
      selectedMap.value[t].delete(it.id)
    })
  } else {
    visible.forEach(it => {
      const t = it.type || currentType.value
      selectedMap.value[t].add(it.id)
    })
  }
  // 触发响应式
  selectedMap.value = {
    character: new Set(selectedMap.value.character),
    location: new Set(selectedMap.value.location),
    prop: new Set(selectedMap.value.prop),
  }
}

const allOnPageSelected = computed(() => {
  const visible = filteredItems.value.filter(it => !isItemImported(it))
  return visible.length > 0 && visible.every(it => {
    const t = it.type || currentType.value
    return selectedMap.value[t]?.has(it.id)
  })
})

async function fetchItems(isLoadMore = false) {
  const t = currentType.value
  const types = t === 'all' ? ['character', 'location', 'prop'] : [t]

  if (isLoadMore) {
    fetchingMore.value = true
  } else {
    loadingState.value = true
  }

  try {
    await Promise.all(types.map(tt => fetchOneType(tt, isLoadMore)))

    // 合并展示
    if (t === 'all') {
      items.value = [
        ...itemsByType.value.character,
        ...itemsByType.value.location,
        ...itemsByType.value.prop,
      ]
    } else {
      items.value = itemsByType.value[t]
    }
    hasMore.value = types.some(tt => hasMoreByType.value[tt])
  } catch {
    // 静默处理
  } finally {
    loadingState.value = false
    fetchingMore.value = false
  }
}

async function fetchOneType(t, isLoadMore) {
  if (!isLoadMore) {
    pageByType.value[t] = 1
    hasMoreByType.value[t] = true
  } else {
    if (!hasMoreByType.value[t]) return
    pageByType.value[t]++
  }

  try {
    const pickerType = t === 'prop' ? 'location' : t
    const assetKind = pickerType === 'location' ? t : undefined
    const res = await getGlobalAssetPickerList(pickerType, {
      page: pageByType.value[t],
      size: 20,
      asset_kind: assetKind,
      ...(props.multi && activeFolder.value ? { folder_id: activeFolder.value } : {}),
    })

    const listKey = pickerType === 'character' ? 'characters' : 'locations'
    const newItems = (res?.[listKey] || []).map(it => ({ ...it, type: t }))
    const pagination = res?.pagination || {}

    if (isLoadMore) {
      itemsByType.value = {
        ...itemsByType.value,
        [t]: [...itemsByType.value[t], ...newItems],
      }
    } else {
      itemsByType.value = { ...itemsByType.value, [t]: newItems }
    }

    const loaded = itemsByType.value[t].length
    hasMoreByType.value[t] = loaded < (pagination.total_count || 0)
  } catch {
    // 静默
  }
}

function handleScroll() {
  const el = scrollContainer.value
  if (!el || !hasMore.value || fetchingMore.value || loadingState.value) return

  const threshold = 60
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - threshold) {
    fetchItems(true)
  }
}

function onConfirm() {
  if (props.multi) {
    // 输出 [{type, id, name, preview_url}, ...]
    const out = []
    for (const t of Object.keys(selectedMap.value)) {
      const set = selectedMap.value[t]
      if (!set.size) continue
      const list = itemsByType.value[t] || []
      for (const item of list) {
        if (set.has(item.id)) {
          out.push({
            type: t,
            id: item.id,
            name: item.name,
            preview_url: item.preview_url,
            thumbnail_url: item.thumbnail_url,
          })
        }
      }
    }
    if (out.length) emit('select', out)
  } else {
    if (selectedId.value) emit('select', selectedId.value)
  }
}

function onImgError(e, originalUrl) {
  const img = e.target
  if (img.dataset.fallback) return
  img.dataset.fallback = '1'
  img.src = originalUrl
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    if (previewImageUrl.value) {
      previewImageUrl.value = null
    } else {
      emit('close')
    }
  }
}

watch(() => [props.visible, props.type], ([visible]) => {
  if (visible) {
    selectedId.value = null
    selectedMap.value = { character: new Set(), location: new Set(), prop: new Set() }
    itemsByType.value = { character: [], location: [], prop: [] }
    pageByType.value = { character: 0, location: 0, prop: 0 }
    hasMoreByType.value = { character: true, location: true, prop: true }
    activeType.value = props.multi ? 'all' : props.type
    searchQuery.value = ''
    previewImageUrl.value = null
    activeFolder.value = ''
    items.value = []
    if (props.multi) {
      if (folders.value.length === 0) fetchFolders()
      fetchImportedAssets()
    }
    fetchItems()
  }
}, { immediate: true })

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-dialog {
  max-width: 640px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
}

.dialog-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--glass-text-tertiary);
}

.close-btn:hover {
  color: var(--glass-text-secondary);
}

/* 类型 tab（multi 模式） */
.dialog-tabs {
  display: flex;
  gap: 4px;
  margin: 0 20px;
  padding-top: 8px;
}

.tab-btn {
  position: relative;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-tertiary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover { color: var(--glass-text-primary); }

.tab-btn-active {
  color: var(--glass-tone-info-fg);
  background: var(--glass-tone-info-bg);
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: var(--glass-accent-from);
  border-radius: 9px;
}

.footer-summary {
  flex: 1;
  font-size: 13px;
  color: var(--glass-text-secondary);
}

/* 搜索 */
.dialog-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 20px;
  padding-top: 8px;
}

.dialog-search {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--glass-bg-muted);
  border-radius: 8px;
  color: var(--glass-text-tertiary);
}

.folder-select {
  width: 160px;
  flex-shrink: 0;
}

.select-page-btn {
  flex-shrink: 0;
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-secondary);
  background: var(--glass-bg-muted);
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.select-page-btn:hover {
  color: var(--glass-text-primary);
  background: var(--glass-bg-surface);
}

.select-page-btn--active {
  color: var(--glass-tone-info-fg);
  background: var(--glass-tone-info-bg);
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--glass-text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--glass-text-tertiary);
}

.dialog-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--glass-text-tertiary);
  font-size: 14px;
}

.empty-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* 资产网格 */
.asset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.asset-card {
  position: relative;
  padding: 8px;
  border-radius: 12px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.2s;
}

.asset-card:hover {
  border-color: var(--glass-stroke-base);
}

.asset-card--selected {
  border-color: var(--glass-stroke-focus);
  background: var(--glass-tone-info-bg);
}

.asset-card--selected:hover {
  border-color: var(--glass-stroke-focus);
}

.asset-card--imported:not(.asset-card--selected) {
  opacity: 0.7;
}

.card-preview {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 8px;
  overflow: hidden;
  background: var(--glass-bg-muted);
}

.badge {
  position: absolute;
  top: 6px;
  left: 6px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 10px;
  line-height: 16px;
  pointer-events: none;
}

.badge--imported {
  color: var(--glass-text-tertiary);
  background: rgba(0, 0, 0, 0.55);
  left: auto;
  right: 6px;
}

.badge--selected {
  color: #fff;
  background: var(--glass-accent-from);
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--glass-accent-from);
  opacity: 0.5;
}

.card-info {
  padding-top: 6px;
}

.card-name {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-folder {
  display: block;
  font-size: 11px;
  color: var(--glass-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 加载更多 */
.load-more-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0;
  color: var(--glass-text-tertiary);
  font-size: 13px;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 12px 20px;
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}

.footer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 图片缩放光标 */
.preview-img--zoomable {
  cursor: zoom-in;
}

/* 图片预览浮层 */
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  cursor: zoom-out;
}

.preview-full-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
}
</style>
