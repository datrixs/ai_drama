<template>
  <div class="asset-grid">
    <!-- Header bar -->
    <div class="asset-grid__header">
      <div class="asset-grid__header-left">
        <SegmentedControl
          v-model="store.filter"
          :options="filterOptions"
          layout="compact"
        />
      </div>
      <div class="asset-grid__header-actions">
        <button
          class="glass-btn-base glass-btn-secondary asset-grid__download-btn"
          @click="$emit('batchUpload')"
        >
          <Upload :size="14" />
          <span>批量上传</span>
        </button>
        <button
          class="glass-btn-base glass-btn-secondary asset-grid__download-btn"
          :disabled="store.isBatchSyncing"
          @click="$emit('batchSync')"
        >
          <RefreshCw :size="14" :class="{ 'asset-grid__spin': store.isBatchSyncing }" />
          <span>{{
            store.batchSyncPending
              ? '同步中...'
              : store.batchSyncTotal > 0
                ? `同步中 ${store.batchSyncDone}/${store.batchSyncTotal}`
                : '批量同步'
          }}</span>
        </button>
        <button
          class="glass-btn-base glass-btn-secondary asset-grid__download-btn"
          :disabled="downloading || !hasAnyAssets"
          @click="handleDownloadAll"
        >
          <component :is="downloading ? RefreshCw : Download" :size="14" :class="{ 'asset-grid__spin': downloading }" />
          <span>{{ downloading ? '打包中...' : '打包下载' }}</span>
        </button>
        <AddAssetDropdown
          @add-character="$emit('addCharacter')"
          @add-location="$emit('addLocation')"
          @add-prop="$emit('addProp')"
          @add-voice="$emit('addVoice')"
        />
      </div>
    </div>

    <!-- Empty: no assets at all -->
    <div v-if="!hasAnyAssets" class="asset-grid__empty-root">
      <div class="glass-surface asset-grid__empty-surface">
        <div class="asset-grid__empty-icon">
          <Plus :size="32" />
        </div>
        <p class="asset-grid__empty-title">暂无资产</p>
        <p class="asset-grid__empty-hint">点击上方按钮添加角色或场景</p>
        <div class="asset-grid__empty-actions">
          <AddAssetDropdown
            @add-character="$emit('addCharacter')"
            @add-location="$emit('addLocation')"
            @add-prop="$emit('addProp')"
            @add-voice="$emit('addVoice')"
          />
        </div>
      </div>
    </div>

    <!-- Empty: filtered result is empty -->
    <div v-else-if="!hasFilteredAssets" class="asset-grid__empty-filtered">
      <p class="asset-grid__empty-hint">点击新建资产添加资产</p>
    </div>

    <!-- Content sections -->
    <template v-else>
      <!-- Characters -->
      <template v-if="showSection('character')">
        <div class="asset-grid__section">
          <div class="asset-grid__section-header">
            <h3 class="asset-grid__section-title">角色</h3>
            <span class="glass-chip glass-chip-neutral">{{ store.sectionPagination.character.total_count || store.characters.length }}</span>
          </div>
          <div class="asset-grid__grid asset-grid__grid--5">
            <CharacterCard
              v-for="item in store.characters"
              :key="item.id"
              :character="item"
              @image-click="emit('imageClick', $event)"
              @image-edit="emit('imageEdit', $event)"
              @voice-design="(...args) => emit('voiceDesign', ...args)"
              @voice-select="emit('voiceSelect', $event)"
              @voice-changed="store.fetchCharacters()"
              @edit="(character, index) => emit('characterEdit', { character, appearanceIndex: index })"
            />
          </div>
          <div class="asset-grid__pagination" v-if="store.sectionPagination.character.total_count > store.pageSize">
            <el-pagination
              :current-page="store.sectionPage.character"
              :page-size="store.pageSize"
              :total="store.sectionPagination.character.total_count"
              layout="prev, pager, next"
              @current-change="(p) => handlePageChange('character', p)"
            />
          </div>
        </div>
      </template>

      <!-- Locations -->
      <template v-if="showSection('location')">
        <div class="asset-grid__section">
          <div class="asset-grid__section-header">
            <h3 class="asset-grid__section-title">场景</h3>
            <span class="glass-chip glass-chip-neutral">{{ store.sectionPagination.location.total_count || store.locations.length }}</span>
          </div>
          <div class="asset-grid__grid asset-grid__grid--4">
            <LocationCard
              v-for="item in store.locations"
              :key="item.id"
              :location="item"
              asset-type="location"
              @image-click="emit('imageClick', $event)"
              @image-edit="emit('imageEdit', $event)"
              @edit="(location, imageIndex) => emit('locationEdit', { location, imageIndex })"
            />
          </div>
          <div class="asset-grid__pagination" v-if="store.sectionPagination.location.total_count > store.pageSize">
            <el-pagination
              :current-page="store.sectionPage.location"
              :page-size="store.pageSize"
              :total="store.sectionPagination.location.total_count"
              layout="prev, pager, next"
              @current-change="(p) => handlePageChange('location', p)"
            />
          </div>
        </div>
      </template>

      <!-- Props -->
      <template v-if="showSection('prop')">
        <div class="asset-grid__section">
          <div class="asset-grid__section-header">
            <h3 class="asset-grid__section-title">道具</h3>
            <span class="glass-chip glass-chip-info">{{ store.sectionPagination.prop.total_count || store.props.length }}</span>
          </div>
          <div class="asset-grid__grid asset-grid__grid--4">
            <LocationCard
              v-for="item in store.props"
              :key="item.id"
              :location="item"
              asset-type="prop"
              @image-click="emit('imageClick', $event)"
              @image-edit="emit('imageEdit', $event)"
              @edit="(location, imageIndex) => emit('propEdit', { location, imageIndex })"
            />
          </div>
          <div class="asset-grid__pagination" v-if="store.sectionPagination.prop.total_count > store.pageSize">
            <el-pagination
              :current-page="store.sectionPage.prop"
              :page-size="store.pageSize"
              :total="store.sectionPagination.prop.total_count"
              layout="prev, pager, next"
              @current-change="(p) => handlePageChange('prop', p)"
            />
          </div>
        </div>
      </template>

      <!-- Voices -->
      <template v-if="showSection('voice')">
        <div class="asset-grid__section">
          <div class="asset-grid__section-header">
            <h3 class="asset-grid__section-title">音色</h3>
            <span class="glass-chip glass-chip-neutral">{{ store.sectionPagination.voice.total_count || store.voices.length }}</span>
          </div>
          <div class="asset-grid__grid asset-grid__grid--5">
            <VoiceCard
              v-for="item in store.voices"
              :key="item.id"
              :voice="item"
              @delete="store.deleteVoice($event)"
            />
          </div>
          <div class="asset-grid__pagination" v-if="store.sectionPagination.voice.total_count > store.pageSize">
            <el-pagination
              :current-page="store.sectionPage.voice"
              :page-size="store.pageSize"
              :total="store.sectionPagination.voice.total_count"
              layout="prev, pager, next"
              @current-change="(p) => handlePageChange('voice', p)"
            />
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Plus, Download, RefreshCw, Upload } from '@lucide/vue'
import { useAssetHubStore } from '@/store/assetHub'
import SegmentedControl from './SegmentedControl.vue'
import AddAssetDropdown from './AddAssetDropdown.vue'
import CharacterCard from './CharacterCard.vue'
import LocationCard from './LocationCard.vue'
import VoiceCard from './VoiceCard.vue'

const emit = defineEmits([
  'addCharacter', 'addLocation', 'addProp', 'addVoice',
  'imageClick', 'imageEdit', 'voiceDesign', 'voiceSelect',
  'characterEdit', 'locationEdit', 'propEdit', 'batchSync', 'batchUpload'
])

const store = useAssetHubStore()
const downloading = ref(false)

const filterOptions = [
  { value: 'all', label: '全部' },
  { value: 'character', label: '角色' },
  { value: 'location', label: '场景' },
  { value: 'prop', label: '道具' },
  { value: 'voice', label: '音色' }
]

const hasAnyAssets = computed(() =>
  store.characters.length > 0 ||
  store.locations.length > 0 ||
  store.props.length > 0 ||
  store.voices.length > 0
)

const hasFilteredAssets = computed(() => {
  if (store.filter === 'all') return hasAnyAssets.value
  if (store.filter === 'character') return store.characters.length > 0
  if (store.filter === 'location') return store.locations.length > 0
  if (store.filter === 'prop') return store.props.length > 0
  if (store.filter === 'voice') return store.voices.length > 0
  return false
})

function showSection(type) {
  return store.filter === 'all' || store.filter === type
}

async function handleDownloadAll() {
  downloading.value = true
  try {
    await store.batchDownload()
  } finally {
    downloading.value = false
  }
}

async function handlePageChange(type, page) {
  store.setPage(type, page)
  if (type === 'character') await store.fetchCharacters()
  else if (type === 'location') await store.fetchLocations()
  else if (type === 'prop') await store.fetchProps()
  else if (type === 'voice') await store.fetchVoices()
}
</script>

<style scoped>
.asset-grid {
  flex: 1;
  min-width: 0;
}

/* Header */
.asset-grid__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.asset-grid__header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.asset-grid__header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.asset-grid__download-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  border-radius: 8px;
}

.asset-grid__download-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.asset-grid__spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Empty states */
.asset-grid__empty-root {
  display: block;
}

.asset-grid__empty-surface {
  border-radius: 12px;
  padding: 48px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.asset-grid__empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--glass-bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--glass-text-tertiary);
  margin-bottom: 16px;
}

.asset-grid__empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0 0 8px 0;
}

.asset-grid__empty-actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.asset-grid__empty-hint {
  font-size: 14px;
  color: var(--glass-text-tertiary);
  margin: 0;
}

.asset-grid__empty-filtered {
  display: flex;
  min-height: 320px;
  align-items: center;
  justify-content: center;
}

/* Sections */
.asset-grid__section {
  margin-bottom: 32px;
}

.asset-grid__pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding: 8px 0;
}

/* Glass-style pagination overrides */
.asset-grid__pagination :deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-button-bg-color: transparent;
  gap: 4px;
}

.asset-grid__pagination :deep(.el-pagination .btn-prev),
.asset-grid__pagination :deep(.el-pagination .btn-next),
.asset-grid__pagination :deep(.el-pagination .el-pager li) {
  border-radius: var(--glass-radius-xs);
  background: transparent;
  border: none;
  color: var(--glass-text-tertiary);
  font-size: 13px;
  font-weight: 600;
  min-width: 32px;
  height: 32px;
  line-height: 32px;
  transition: all 0.2s ease;
}

.asset-grid__pagination :deep(.el-pagination .btn-prev:hover),
.asset-grid__pagination :deep(.el-pagination .btn-next:hover),
.asset-grid__pagination :deep(.el-pagination .el-pager li:hover) {
  background: var(--glass-bg-muted);
  color: var(--glass-text-primary);
}

.asset-grid__pagination :deep(.el-pagination .el-pager li.is-active) {
  background: linear-gradient(140deg, var(--glass-accent-from), var(--glass-accent-to));
  color: var(--glass-text-on-accent);
  box-shadow: 0 4px 12px var(--glass-accent-shadow-soft);
}

.asset-grid__pagination :deep(.el-pagination .btn-prev:disabled),
.asset-grid__pagination :deep(.el-pagination .btn-next:disabled) {
  opacity: 0.35;
  background: transparent;
}

.asset-grid__section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.asset-grid__section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0;
}

/* Grids */
.asset-grid__grid {
  display: grid;
  gap: 16px;
  grid-auto-flow: dense;
}

.asset-grid__grid--4 {
  grid-template-columns: repeat(4, 1fr);
}

.asset-grid__grid--5 {
  grid-template-columns: repeat(5, 1fr);
}

/* Responsive */
@media (max-width: 1280px) {
  .asset-grid__grid--5 {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 1024px) {
  .asset-grid__grid--4 {
    grid-template-columns: repeat(3, 1fr);
  }
  .asset-grid__grid--5 {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .asset-grid__grid--4 {
    grid-template-columns: repeat(2, 1fr);
  }
  .asset-grid__grid--5 {
    grid-template-columns: repeat(2, 1fr);
  }
  .card-span-3 {
    grid-column: span 2;
  }
}

</style>
