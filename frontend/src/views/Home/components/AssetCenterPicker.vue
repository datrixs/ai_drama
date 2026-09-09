<template>
  <div class="picker-overlay" @click.self="$emit('close')">
    <div class="picker-modal">
      <div class="picker-header">
        <h3>资产中心</h3>
        <button class="picker-close" @click="$emit('close')">×</button>
      </div>

      <!-- 筛选 -->
      <div class="picker-filters">
        <select v-model="filterType" class="picker-select">
          <option value="">全部类型</option>
          <option value="image">图片</option>
          <option value="audio">音频</option>
        </select>
        <select v-model="filterFolder" class="picker-select">
          <option value="">资产组筛选</option>
          <option v-for="f in folders" :key="f.id" :value="f.id">{{ f.name }}</option>
        </select>
        <input v-model="searchText" class="picker-search" placeholder="搜索资产..." />
      </div>

      <!-- 资产列表 -->
      <div class="picker-body app-scrollbar">
        <div v-if="loading" class="picker-empty">加载中...</div>
        <div v-else-if="filteredAssets.length === 0" class="picker-empty">暂无资产</div>
        <div v-else class="picker-grid">
          <div
            v-for="asset in filteredAssets"
            :key="asset.id"
            class="picker-card"
            :class="{ 'picker-card-selected': isSelected(asset) }"
            @click="toggleSelect(asset)"
          >
            <img
              v-if="asset.image_url"
              :src="asset.thumbnail_url || asset.image_url"
              class="picker-card-img"
              @error="onImgError($event, asset.image_url)"
            />
            <div v-else class="picker-card-placeholder">
              <svg v-if="asset.asset_type === 'audio'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
            </div>
            <span class="picker-card-name">{{ asset.name }}</span>
            <span class="picker-type-tag" :class="'picker-type-' + asset.asset_type">
              {{ asset.asset_type === 'image' ? '图' : asset.asset_type === 'audio' ? '音' : '视' }}
            </span>
            <span v-if="isSelected(asset)" class="picker-check">✓</span>
            <span
              v-if="(asset.asset_type === 'image' || asset.asset_type === 'audio') && !asset.volc_asset_id && !syncingIds.has(asset.id)"
              class="picker-sync-tag"
              @click.stop="handleSyncAsset(asset)"
            >未同步</span>
            <span
              v-if="(asset.asset_type === 'image' || asset.asset_type === 'audio') && !asset.volc_asset_id && syncingIds.has(asset.id)"
              class="picker-sync-tag picker-sync-tag--syncing"
            >同步中</span>
          </div>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="picker-footer">
        <button class="glass-btn-base glass-btn-secondary picker-footer-btn" @click="$emit('close')">取消</button>
        <button
          class="glass-btn-base glass-btn-primary picker-footer-btn"
          :disabled="selected.length === 0"
          @click="handleConfirm"
        >
          选入({{ selected.length }})
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useShortVideoStore } from '@/store/shortVideo'
import { getAssetCenterFolders, syncUserAssetToVolc } from '@/api/shortVideo'

const emit = defineEmits(['close', 'select'])

const store = useShortVideoStore()
const loading = ref(false)
const searchText = ref('')
const filterType = ref('')
const filterFolder = ref('')
const selected = ref([])
const folders = ref([])
const syncingIds = ref(new Set())

const filteredAssets = computed(() => {
  let assets = store.assetCenterAssets
  if (filterType.value) {
    assets = assets.filter(a => a.asset_type === filterType.value)
  }
  if (filterFolder.value) {
    assets = assets.filter(a => a.folder_id === filterFolder.value)
  }
  if (searchText.value.trim()) {
    const kw = searchText.value.trim().toLowerCase()
    assets = assets.filter(a => a.name.toLowerCase().includes(kw))
  }
  return assets
})

function isSelected(asset) {
  return selected.value.some(s => s.id === asset.id)
}

function toggleSelect(asset) {
  const idx = selected.value.findIndex(s => s.id === asset.id)
  if (idx >= 0) {
    selected.value.splice(idx, 1)
  } else {
    selected.value.push(asset)
  }
}

function handleConfirm() {
  emit('select', selected.value)
  emit('close')
}

function onImgError(e, originalUrl) {
  const img = e.target
  if (img.dataset.fallback || !originalUrl) return
  img.dataset.fallback = '1'
  img.src = originalUrl
}

function inferAssetKind(asset) {
  if (asset.asset_type === 'audio') return 'voice'
  return asset.name?.includes('形象') ? 'character_appearance' : 'location_image'
}

async function handleSyncAsset(asset) {
  if (syncingIds.value.has(asset.id)) return
  syncingIds.value.add(asset.id)
  try {
    const res = await syncUserAssetToVolc(asset.id, inferAssetKind(asset))
    asset.volc_asset_id = res.volc_id
  } catch {
    // error handled by interceptor
  } finally {
    syncingIds.value.delete(asset.id)
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      store.fetchAssetCenter(),
      getAssetCenterFolders().then(res => {
        const data = res?.data ?? res
        folders.value = Array.isArray(data) ? data : []
      }).catch(() => {}),
    ])
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.picker-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}

.picker-modal {
  width: 90%;
  max-width: 640px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 1rem;
  border: 1px solid var(--glass-stroke-base);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--glass-stroke-base);
}

.picker-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--glass-text-primary);
}

.picker-close {
  width: 28px;
  height: 28px;
  border-radius: 0.375rem;
  border: none;
  background: transparent;
  color: var(--glass-text-tertiary);
  font-size: 1.25rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.picker-close:hover {
  background: var(--glass-bg-muted);
  color: var(--glass-text-primary);
}

.picker-filters {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--glass-stroke-soft);
}

.picker-select {
  height: 2rem;
  padding: 0 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-muted);
  color: var(--glass-text-primary);
  font-size: 0.8125rem;
  outline: none;
}

.picker-search {
  flex: 1;
  height: 2rem;
  padding: 0 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-muted);
  color: var(--glass-text-primary);
  font-size: 0.8125rem;
  outline: none;
}

.picker-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
}

.picker-empty {
  text-align: center;
  padding: 2rem;
  color: var(--glass-text-tertiary);
  font-size: 0.875rem;
}

.picker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 0.5rem;
}

.picker-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem;
  border-radius: 0.5rem;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.picker-card:hover {
  background: var(--glass-bg-muted);
}

.picker-card-selected {
  border-color: var(--glass-accent-from, #3b82f6);
  background: rgba(59, 130, 246, 0.06);
}

.picker-card-img {
  width: 56px;
  height: 56px;
  border-radius: 0.375rem;
  object-fit: cover;
}

.picker-card-placeholder {
  width: 56px;
  height: 56px;
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-bg-muted);
  color: var(--glass-text-tertiary);
}

.picker-card-name {
  font-size: 0.625rem;
  color: var(--glass-text-secondary);
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.picker-type-tag {
  position: absolute;
  top: 2px;
  left: 2px;
  padding: 0 3px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 600;
  color: #fff;
}

.picker-type-image { background: #3b82f6; }
.picker-type-video { background: #8b5cf6; }
.picker-type-audio { background: #f59e0b; }

.picker-sync-tag {
  position: absolute;
  top: 2px;
  right: 2px;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 8px;
  font-weight: 500;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  cursor: pointer;
  line-height: 14px;
  z-index: 2;
  transition: all 0.15s;
}
.picker-sync-tag:hover {
  background: rgba(245, 158, 11, 0.25);
}
.picker-sync-tag--syncing {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.3);
  cursor: default;
}

.picker-check {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--glass-accent-from, #3b82f6);
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.picker-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-surface-strong);
  border-radius: 0 0 1rem 1rem;
}

.picker-footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}
</style>
