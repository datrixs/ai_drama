<template>
  <AppLayout>
    <div class="asset-hub-page">
      <div class="page-container">
        <!-- Title section -->
        <div class="title-section">
          <h1 class="page-title">资产中心</h1>
          <p class="page-desc">管理您的角色、场景、道具和音色资产</p>
          <p class="page-hint">
            <Info :size="14" />
            图片生成使用账户默认模型，可在设置中心配置
          </p>
        </div>

        <!-- Main content -->
        <div class="content-layout">
          <FolderSidebar
            @create="handleCreateFolder"
            @edit="handleEditFolder"
            @delete="handleDeleteFolder"
          />
          <AssetGrid
            @add-character="showAddCharacter = true"
            @add-location="showAddLocation = true"
            @add-prop="showAddProp = true"
            @add-voice="showAddVoice = true"
            @image-click="handleImageClick"
            @image-edit="handleImageEdit"
            @voice-design="handleVoiceDesign"
            @voice-select="handleVoiceSelect"
            @character-edit="handleCharacterEdit"
            @location-edit="handleLocationEdit"
            @prop-edit="handlePropEdit"
            @batch-sync="handleBatchSync"
            @batch-upload="handleBatchUpload"
          />
        </div>
      </div>

      <!-- Creation Modals -->
      <CharacterCreationModal
        v-if="showAddCharacter"
        :folder-id="createFolderId"
        @close="showAddCharacter = false"
        @success="showAddCharacter = false"
      />
      <LocationCreationModal
        v-if="showAddLocation"
        :folder-id="createFolderId"
        @close="showAddLocation = false"
        @success="showAddLocation = false"
      />
      <PropCreationModal
        v-if="showAddProp"
        :folder-id="createFolderId"
        @close="showAddProp = false"
        @success="showAddProp = false"
      />
      <VoiceCreationModal
        v-if="showAddVoice"
        :folder-id="createFolderId"
        @close="showAddVoice = false"
        @success="showAddVoice = false"
      />

      <!-- 批量上传本地图片 -->
      <GlobalBatchUploadDialog
        v-if="batchUploadVisible"
        :visible="batchUploadVisible"
        :folder-id="createFolderId"
        @close="batchUploadVisible = false"
        @done="batchUploadVisible = false"
      />

      <!-- Folder Modal -->
      <FolderModal
        v-if="showFolderModal"
        :folder="editingFolder"
        @close="showFolderModal = false"
        @save="handleSaveFolder"
      />

      <!-- Image Preview -->
      <ImagePreviewModal
        v-if="previewImageUrl"
        :image-url="previewImageUrl"
        @close="previewImageUrl = null"
      />

      <!-- Image Edit Modal -->
      <ImageEditModal
        v-if="imageEditData"
        :asset-type="imageEditData.type"
        :asset-id="imageEditData.id"
        :asset-name="imageEditData.name"
        :image-url="imageEditData.imageUrl"
        :image-index="imageEditData.imageIndex || 0"
        @close="imageEditData = null"
        @confirm="imageEditData = null"
      />

      <!-- Voice Design Dialog -->
      <VoiceDesignDialog
        v-if="voiceDesignData"
        :speaker="voiceDesignData.name"
        :has-existing-voice="voiceDesignData.hasExistingVoice"
        @close="voiceDesignData = null"
        @save="handleVoiceDesignSave"
      />

      <!-- Voice Picker Dialog -->
      <VoicePickerDialog
        v-if="voicePickerCharacterId"
        @close="voicePickerCharacterId = null"
        @select="handleVoicePickerSelect"
      />

      <!-- Edit Modals -->
      <CharacterEditModal
        v-if="characterEditData"
        :character="characterEditData.character"
        :appearance-index="characterEditData.appearanceIndex"
        @close="characterEditData = null"
      />
      <LocationEditModal
        v-if="locationEditData"
        :location="locationEditData.location"
        :image-index="locationEditData.imageIndex"
        @close="locationEditData = null"
      />
      <PropEditModal
        v-if="propEditData"
        :location="propEditData.location"
        :image-index="propEditData.imageIndex"
        @close="propEditData = null"
      />
    </div>
    <ConfirmDialog
      v-model="deleteFolderConfirmVisible"
      title="提示"
      message="确认删除该资产组？其中的资产将移至根目录。"
      confirm-text="删除"
      type="danger"
      @confirm="doDeleteFolder"
    />
    <ConfirmDialog
      v-model="batchSyncConfirmVisible"
      title="批量同步确认"
      :message="batchSyncConfirmMessage"
      confirm-text="开始同步"
      type="warning"
      size="large"
      @confirm="executeBatchSync"
    />
  </AppLayout>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NoPermissionAlert from '@/components/NoPermissionAlert.vue'

const route = useRoute()
const noPermission = computed(() => route.query._no_perm === '1')
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { Info } from '@lucide/vue'
import AppLayout from '@/layout/AppLayout.vue'
import FolderSidebar from './components/FolderSidebar.vue'
import AssetGrid from './components/AssetGrid.vue'
import FolderModal from './components/modals/FolderModal.vue'
import CharacterCreationModal from './components/modals/CharacterCreationModal.vue'
import LocationCreationModal from './components/modals/LocationCreationModal.vue'
import PropCreationModal from './components/modals/PropCreationModal.vue'
import VoiceCreationModal from './components/modals/VoiceCreationModal.vue'
import VoicePickerDialog from './components/modals/VoicePickerDialog.vue'
import GlobalBatchUploadDialog from './components/modals/GlobalBatchUploadDialog.vue'
import VoiceDesignDialog from './components/modals/VoiceDesignDialog.vue'
import ImagePreviewModal from './components/ImagePreviewModal.vue'
import ImageEditModal from './components/modals/ImageEditModal.vue'
import CharacterEditModal from './components/modals/CharacterEditModal.vue'
import LocationEditModal from './components/modals/LocationEditModal.vue'
import PropEditModal from './components/modals/PropEditModal.vue'
import { useAssetHubStore, UNGROUPED_FOLDER_ID, PLATFORM_FOLDER_ID } from '@/store/assetHub'
import { useWebSocket } from '@/composables/useWebSocket'
import { useUserStore } from '@/store/user'
import { getUserUnsyncedSummary, syncAllUserAssets } from '@/api/shortVideo'

const store = useAssetHubStore()
const ws = useWebSocket()
const userStore = useUserStore()
// 哨兵 id（'ungrouped' / 'platform'）不是真实 folder_id，新建资产时降级为 null
const createFolderId = computed(() => {
  const id = store.selectedFolderId
  return (id === UNGROUPED_FOLDER_ID || id === PLATFORM_FOLDER_ID) ? null : id
})
let removeWsListener = null

const showAddCharacter = ref(false)
const showAddLocation = ref(false)
const showAddProp = ref(false)
const showAddVoice = ref(false)
const showFolderModal = ref(false)
const editingFolder = ref(null)
const previewImageUrl = ref(null)
const batchUploadVisible = ref(false)
const imageEditData = ref(null)
const voiceDesignData = ref(null)
const voicePickerCharacterId = ref(null)
const characterEditData = ref(null)
const locationEditData = ref(null)
const propEditData = ref(null)

function handleCreateFolder() {
  editingFolder.value = null
  showFolderModal.value = true
}

function handleEditFolder(folder) {
  editingFolder.value = folder
  showFolderModal.value = true
}

async function handleSaveFolder(name) {
  if (editingFolder.value) {
    await store.updateFolder(editingFolder.value.id, name)
  } else {
    await store.createFolder(name)
  }
  showFolderModal.value = false
}

const deleteFolderConfirmVisible = ref(false)
const deleteFolderTarget = ref(null)

// 批量同步确认弹窗状态
const batchSyncConfirmVisible = ref(false)
const batchSyncConfirmMessage = ref('')
const batchSyncPendingFolderId = ref(null)

async function handleDeleteFolder(folderId) {
  deleteFolderTarget.value = folderId
  deleteFolderConfirmVisible.value = true
}

async function doDeleteFolder() {
  try {
    await store.deleteFolder(deleteFolderTarget.value)
  } catch {
    // cancelled
  }
}

function handleImageClick(url) {
  previewImageUrl.value = url
}

function handleImageEdit(payload) {
  imageEditData.value = payload
}

function handleVoiceDesign(characterId, characterName) {
  const character = store.characters.find(c => c.id === characterId)
  voiceDesignData.value = {
    id: characterId,
    name: characterName,
    hasExistingVoice: !!character?.custom_voice_url
  }
}

function handleVoiceDesignSave(voiceData) {
  if (voiceDesignData.value?.id) {
    store.bindVoiceToCharacter(voiceDesignData.value.id, {
      voice_type: voiceData.voice_type || 'ai_designed',
      voice_id: voiceData.voice_id,
      custom_voice_url: voiceData.custom_voice_url,
    })
  }
  voiceDesignData.value = null
}

function handleVoiceSelect(characterId) {
  voicePickerCharacterId.value = characterId
}

async function handleVoicePickerSelect(voice) {
  if (voicePickerCharacterId.value) {
    await store.bindVoiceToCharacter(voicePickerCharacterId.value, {
      global_voice_id: voice.id,
      voice_id: voice.voice_id || null,
      voice_type: voice.voice_type || null,
      custom_voice_url: voice.custom_voice_url
    })
  }
  voicePickerCharacterId.value = null
}

function handleCharacterEdit(payload) {
  characterEditData.value = payload
}

function handleLocationEdit(payload) {
  locationEditData.value = payload
}

function handlePropEdit(payload) {
  propEditData.value = payload
}

onMounted(async () => {
  if (!userStore.loaded.value) {
    await userStore.fetchUser()
  }
  const userId = userStore.userInfo.value?.id
  if (userId) {
    removeWsListener = ws.onEvent(handleWsEvent)
    ws.connect(userId)
  }
  store.fetchAll()
})

onUnmounted(() => {
  if (removeWsListener) {
    removeWsListener()
    removeWsListener = null
  }
})

function handleWsEvent(event) {
  console.log('[AssetHub] WS event:', event.event_type, event.data)
  const { event_type, data } = event
  switch (event_type) {
    case 'asset_hub_generation_started':
      if (data.target_type === 'appearance') {
        store.updateAppearanceStatus(data.target_id, 'generating', data.action_type)
      } else {
        store.updateLocationImageStatus(data.target_id, 'generating', data.action_type)
      }
      break
    case 'asset_hub_generation_completed':
      if (data.target_type === 'appearance') {
        store.updateAppearanceImage(data.target_id, data.image_url, data.thumbnail_url)
        store.fetchCharacters()
      } else {
        store.updateLocationImageState(data.target_id, data.image_url, data.thumbnail_url)
        store.fetchLocations()
      }
      break
    case 'asset_hub_generation_failed':
      if (data.target_type === 'appearance') {
        store.updateAppearanceStatus(data.target_id, 'failed')
      } else {
        store.updateLocationImageStatus(data.target_id, 'failed')
      }
      if (data.error) ElMessage.error(data.error)
      break
    case 'asset_hub_batch_sync_started':
      store.markBatchSyncStarted(data.total, data.asset_ids || [])
      break
    case 'asset_hub_batch_sync_progress':
      if (data.status === 'success') {
        // 即时回写 volc_id 让角标立即变化，再异步刷新拉最新数据
        if (data.kind === 'character_appearance') {
          store.updateAppearanceVolcId(data.asset_id, data.volc_id)
          store.fetchCharacters()
        } else if (data.kind === 'location_image') {
          store.updateLocationImageVolcId(data.asset_id, data.volc_id)
          store.fetchLocations()
          store.fetchProps()
        } else if (data.kind === 'voice') {
          store.updateVoiceVolcId(data.asset_id, data.volc_id)
          store.fetchVoices()
        }
      } else {
        ElMessage.error(`同步失败：${data.error || '未知错误'}`)
      }
      store.setAssetBatchSyncing(data.asset_id, false)
      store.incBatchSyncDone()
      break
    case 'asset_hub_batch_sync_completed':
      ElMessage.success(`批量同步完成：成功 ${data.success_count} 条，失败 ${data.failed_count} 条`)
      store.resetBatchSync()
      store.fetchCharacters()
      store.fetchLocations()
      store.fetchProps()
      store.fetchVoices()
      break
    case 'asset_hub_batch_sync_failed':
      ElMessage.error(`批量同步任务异常：${data.error || '未知错误'}`)
      store.resetBatchSync()
      break
  }
}

function handleBatchUpload() {
  batchUploadVisible.value = true
}

async function handleBatchSync() {
  if (store.isBatchSyncing) return  // 防止任务进行中或等待开始期间重复触发
  // 三态 folder_id：null=全部，'null'=未分组，其他=指定资产组
  const folderId = store.resolveFolderIdParam()
  let summary
  try {
    summary = await getUserUnsyncedSummary(folderId)
  } catch {
    return
  }
  const { region, character = 0, scene = 0, prop = 0, voice = 0, total = 0 } = summary || {}
  if (!total) {
    ElMessage.info('当前资产组无待同步资产')
    return
  }
  const regionLabel = region === 'overseas' ? '国际版（BytePlus）' : '国内版（火山引擎）'
  const folderLabel = folderId === 'null'
    ? '（未分组）'
    : folderId ? '（当前资产组）' : '（所有资产）'
  batchSyncConfirmMessage.value =
    `当前区域：${regionLabel}${folderLabel}\n角色 ${character} 条 / 场景 ${scene} 条 / 道具 ${prop} 条 / 音色 ${voice} 条\n共 ${total} 条`
  batchSyncPendingFolderId.value = folderId
  batchSyncConfirmVisible.value = true
}

async function executeBatchSync() {
  const folderId = batchSyncPendingFolderId.value
  // 立即把按钮置为"同步中"，避免在后端 started 事件到达前被重复点击
  store.markBatchSyncPending()
  try {
    await syncAllUserAssets(folderId)
    ElMessage.success('批量同步任务已开始')
  } catch {
    // 失败时回滚 pending 状态，让按钮可重新点击
    store.resetBatchSync()
  }
}
</script>

<style scoped>
.asset-hub-page {
  min-height: calc(100vh - 4rem);
}

.page-container {
  max-width: 80rem;
  margin: 0 auto;
  padding: 24px 16px;
}

.title-section {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--glass-text-primary);
  margin: 0;
}

.page-desc {
  font-size: 14px;
  color: var(--glass-text-secondary);
  margin: 4px 0 0;
}

.page-hint {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  margin: 8px 0 0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.content-layout {
  display: flex;
  gap: 24px;
}
</style>
