<template>
  <div class="asset-library">
    <!-- 标题行 -->
    <div class="asset-header glass-surface">
      <div class="asset-header-left">
        <div class="asset-header-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
        </div>
        <h2 class="asset-header-title">资产管理</h2>
        <span class="asset-header-stats">
          {{ store.stats.total }} 项资产 · {{ store.characters.length }} 角色 · {{ store.locations.length }} 场景 · {{ store.props.length }} 道具
        </span>
      </div>
      <ProjectAssetToolbar
        :stats="store.stats"
        :all-ready="store.allReady"
        :is-batch-generating="store.isBatchGenerating"
        :director-mode="showSectionsWhenEmpty"
        :batch-importing="batchImporting"
        :batch-syncing="store.isBatchSyncing"
        :batch-sync-pending="store.batchSyncPending"
        :batch-sync-total="store.batchSyncTotal"
        :batch-sync-done="store.batchSyncDone"
        @batch-generate="handleBatchGenerate"
        @batch-sync="handleBatchSync"
        @batch-download="handleBatchDownload"
        @batch-upload="handleBatchUpload"
        @batch-import="handleBatchImport"
      />
    </div>

    <!-- 类型筛选栏 -->
    <ProjectAssetFilterBar
      :kind-filter="store.kindFilter"
      :counts="filterCounts"
      @change="store.kindFilter = $event"
    />

    <!-- 加载状态 -->
    <div v-if="store.loading" class="asset-loading">
      <div class="asset-loading-spinner" />
      <span>加载中...</span>
    </div>

    <!-- 空状态（导演模式 showSectionsWhenEmpty=true 时跳过此分支，分区永远展示） -->
    <div v-else-if="store.stats.total === 0 && !showSectionsWhenEmpty" class="asset-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="m9 16 2 2 4-4"/></svg>
      <p>暂无资产数据</p>
    </div>

    <!-- 资产内容区 -->
    <div v-else class="asset-content">
      <ProjectCharacterSection
        v-if="['all', 'character'].includes(store.kindFilter)"
        :characters="store.characters"
        :project-id="projectId"
        :voice-upload-handler="voiceUploadHandler"
        @preview="openImagePreview"
        @edit="openEditCharacter"
        @generate="handleGenerateSingle"
        @upload="handleUpload"
        @modify="openImageEdit"
        @delete="handleDelete"
        @download="store.downloadAssetImage"
        @reference="openReferenceGenerate"
        @import-from-global="openImportFromGlobal"
        @undo="handleUndo"
        @create="openCreateDialog"
        @sync-volc="handleSyncVolc"
        @voice-design="handleVoiceDesign"
        @voice-select="handleVoiceSelect"
        @voice-changed="handleVoiceChanged"
      />

      <ProjectLocationSection
        v-if="['all', 'location'].includes(store.kindFilter)"
        :locations="store.locations"
        :project-id="projectId"
        :asset-type="'location'"
        @preview="openImagePreview"
        @edit="openEditLocation"
        @generate="handleGenerateSingle"
        @upload="handleUpload"
        @modify="openImageEdit"
        @delete="handleDelete"
        @download="store.downloadAssetImage"
        @import-from-global="openImportFromGlobal"
        @undo="handleUndo"
        @create="openCreateDialog"
        @sync-volc="handleSyncVolc"
      />

      <ProjectLocationSection
        v-if="['all', 'prop'].includes(store.kindFilter)"
        :locations="store.props"
        :project-id="projectId"
        :asset-type="'prop'"
        @preview="openImagePreview"
        @edit="openEditProp"
        @generate="handleGenerateSingle"
        @upload="handleUpload"
        @modify="openImageEdit"
        @delete="handleDelete"
        @download="store.downloadAssetImage"
        @import-from-global="openImportFromGlobal"
        @undo="handleUndo"
        @create="openCreateDialog"
        @sync-volc="handleSyncVolc"
      />
    </div>

    <!-- 图片预览弹窗 -->
    <ProjectImagePreviewDialog
      v-if="previewVisible"
      :image-url="previewImageUrl"
      @close="previewVisible = false"
    />

    <!-- 角色编辑弹窗 -->
    <ProjectEditCharacterDialog
      v-if="editCharacterVisible"
      :visible="editCharacterVisible"
      :character="editTarget"
      :project-id="projectId"
      @close="editCharacterVisible = false"
      @saved="handleEditSaved"
    />

    <!-- 场景编辑弹窗 -->
    <ProjectEditLocationDialog
      v-if="editLocationVisible"
      :visible="editLocationVisible"
      :location="editTarget"
      :project-id="projectId"
      :asset-type="editAssetType"
      @close="editLocationVisible = false"
      @saved="handleEditSaved"
    />

    <!-- 道具编辑弹窗 -->
    <ProjectEditPropDialog
      v-if="editPropVisible"
      :visible="editPropVisible"
      :prop="editTarget"
      :project-id="projectId"
      @close="editPropVisible = false"
      @saved="handleEditSaved"
    />

    <!-- AI 修图弹窗 -->
    <ProjectImageEditDialog
      v-if="imageEditVisible"
      :asset="imageEditTarget"
      :asset-type="imageEditAssetType"
      :project-id="projectId"
      @close="imageEditVisible = false"
      @submit="handleModifyImage"
    />

    <!-- 参考图生图弹窗 -->
    <ProjectReferenceGenerateDialog
      v-if="refGenerateVisible"
      :visible="refGenerateVisible"
      :character="refGenerateTarget"
      :project-id="projectId"
      @close="refGenerateVisible = false"
      @submit="handleReferenceGenerate"
    />

    <!-- 从资产中心导入弹窗 -->
    <GlobalAssetPicker
      v-if="pickerVisible"
      :visible="pickerVisible"
      :type="pickerType"
      :loading="pickerLoading"
      @close="pickerVisible = false"
      @select="handlePickerSelect"
    />

    <!-- 批量从资产中心导入弹窗（多选 + 跨类型） -->
    <GlobalAssetPicker
      v-if="batchPickerVisible"
      :visible="batchPickerVisible"
      :project-id="projectId"
      multi
      @close="batchPickerVisible = false"
      @select="handleBatchPickerSelect"
    />

    <!-- 批量上传弹框（拖拽 / 点击 + 类型切换） -->
    <BatchUploadDialog
      v-if="batchUploadVisible"
      :visible="batchUploadVisible"
      :project-id="projectId"
      @close="batchUploadVisible = false"
      @done="handleBatchUploadDone"
    />

    <!-- 创建资产弹窗 -->
    <ProjectCreateAssetDialog
      v-if="createDialogVisible"
      :visible="createDialogVisible"
      :asset-type="createAssetType"
      @close="createDialogVisible = false"
      @created="handleCreateAsset"
    />

    <!-- 音色库选择弹窗 -->
    <VoicePickerDialog
      v-if="voicePickerVisible"
      :voices="globalVoices"
      @close="voicePickerVisible = false"
      @select="handleVoicePickerSelect"
    />

    <!-- AI 音色设计弹窗 -->
    <VoiceDesignDialog
      v-if="voiceDesignVisible"
      :speaker="voiceDesignTarget?.name || ''"
      :has-existing-voice="!!voiceDesignTarget?.custom_voice_url"
      @close="voiceDesignVisible = false; voiceDesignTarget = null"
      @save="handleVoiceDesignSave"
    />

    <!-- 删除确认弹框（统一 glass 风格） -->
    <ConfirmDialog
      :model-value="!!deleteTarget"
      type="danger"
      title="删除资产"
      :message="deleteTarget ? `确定删除「${deleteTarget.name}」吗？删除后不可恢复。` : ''"
      confirm-text="删除"
      cancel-text="取消"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />

    <!-- 批量同步确认弹框（对齐资产中心交互） -->
    <ConfirmDialog
      v-model="batchSyncConfirmVisible"
      title="批量同步确认"
      :message="batchSyncConfirmMessage"
      confirm-text="开始同步"
      type="warning"
      size="large"
      @confirm="executeBatchSync"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectAssetStore } from '@/store/project_asset'
import { useAssetHubStore } from '@/store/assetHub'
import { getProjectUnsyncedSummary } from '@/api/project/assets'
import ProjectAssetToolbar from './ProjectAssetToolbar.vue'
import ProjectAssetFilterBar from './ProjectAssetFilterBar.vue'
import ProjectCharacterSection from './ProjectCharacterSection.vue'
import ProjectLocationSection from './ProjectLocationSection.vue'
import ProjectEditCharacterDialog from './ProjectEditCharacterDialog.vue'
import ProjectEditLocationDialog from './ProjectEditLocationDialog.vue'
import ProjectEditPropDialog from './ProjectEditPropDialog.vue'
import ProjectImagePreviewDialog from './ProjectImagePreviewDialog.vue'
import ProjectImageEditDialog from './ProjectImageEditDialog.vue'
import ProjectReferenceGenerateDialog from './ProjectReferenceGenerateDialog.vue'
import GlobalAssetPicker from './GlobalAssetPicker.vue'
import ProjectCreateAssetDialog from './ProjectCreateAssetDialog.vue'
import BatchUploadDialog from './BatchUploadDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import VoicePickerDialog from '@/views/AssetsCenter/components/modals/VoicePickerDialog.vue'
import VoiceDesignDialog from '@/views/AssetsCenter/components/modals/VoiceDesignDialog.vue'

const props = defineProps({
  projectId: String,
  // 导演模式专属：永远渲染角色/场景/道具分区，即使全部为空也显示分区占位 + 添加按钮
  // 全局模式默认 false，保持「总空态」覆盖行为
  showSectionsWhenEmpty: { type: Boolean, default: false },
})
const store = useProjectAssetStore()
const assetHubStore = useAssetHubStore()

const globalVoices = computed(() => assetHubStore.voices)

const filterCounts = computed(() => ({
  total: store.stats.total,
  character: store.characters.length,
  location: store.locations.length,
  prop: store.props.length,
}))

// 弹窗状态
const previewVisible = ref(false)
const previewImageUrl = ref('')
const editCharacterVisible = ref(false)
const editLocationVisible = ref(false)
const editPropVisible = ref(false)
const editTarget = ref(null)
const editAssetType = ref('location')
const imageEditVisible = ref(false)
const imageEditTarget = ref(null)
const imageEditAssetType = ref('')
const refGenerateVisible = ref(false)
const refGenerateTarget = ref(null)
const pickerVisible = ref(false)
const pickerType = ref('character')
const pickerTargetAssetId = ref(null)
const pickerAssetType = ref('character')
const pickerLoading = ref(false)
const createDialogVisible = ref(false)
const createAssetType = ref('character')
const downloading = ref(false)
// 批量上传 / 批量资产中心导入（导演模式专属）
const batchUploadVisible = ref(false)
const batchPickerVisible = ref(false)
const batchImporting = ref(false)
// 批量同步火山/BytePlus（导演模式专属，后端异步任务，状态由 WebSocket 推送）
const batchSyncing = ref(false)
// 批量同步确认弹窗（对齐资产中心交互）
const batchSyncConfirmVisible = ref(false)
const batchSyncConfirmMessage = ref('')
// 待同步资产 ID 列表（来自 summary 接口，确认同步时立即标记卡片为"同步中"）
const batchSyncPendingAssetIds = ref([])
const batchSyncPendingTotal = ref(0)
// 删除确认弹框
const deleteTarget = ref(null)
const voicePickerVisible = ref(false)
const voicePickerTargetCharacter = ref(null)
const voiceDesignVisible = ref(false)
const voiceDesignTarget = ref(null)

const voiceUploadHandler = (characterId, file) => {
  return store.uploadCharacterVoice(props.projectId, characterId, file)
}

onMounted(() => {
  store.fetchAssets(props.projectId)
})

onUnmounted(() => {
  store.reset()
})

// ============ 操作处理 ============

function handleBatchGenerate() {
  store.batchGenerate(props.projectId)
}

async function handleBatchSync() {
  if (store.isBatchSyncing) return  // 任务进行中或等待开始期间重复触发
  let summary
  try {
    summary = await getProjectUnsyncedSummary(props.projectId)
  } catch {
    return
  }
  const { region, character = 0, scene = 0, prop = 0, total = 0, asset_ids = [] } = summary || {}
  if (!total) {
    ElMessage.info('当前项目无待同步资产')
    return
  }
  const regionLabel = region === 'overseas' ? '国际版（BytePlus）' : '国内版（火山引擎）'
  batchSyncConfirmMessage.value =
    `当前区域：${regionLabel}\n角色 ${character} 条 / 场景 ${scene} 条 / 道具 ${prop} 条\n共 ${total} 条`
  // 暂存待同步资产 ID，确认时立即在卡片上标记"同步中"，无需等待 WS started 事件
  batchSyncPendingAssetIds.value = asset_ids
  batchSyncPendingTotal.value = total
  batchSyncConfirmVisible.value = true
}

async function executeBatchSync() {
  // 立即标记按钮"同步中"并预置已知待同步资产 ID，让卡片角标实时显示
  store.markBatchSyncPending(batchSyncPendingTotal.value, batchSyncPendingAssetIds.value)
  try {
    await store.batchSyncVolc(props.projectId)
  } catch {
    // 失败时回滚 pending 状态，让按钮可重新点击
    store.resetBatchSync()
  }
}

async function handleBatchDownload() {
  downloading.value = true
  try {
    await store.batchDownload(props.projectId)
  } finally {
    downloading.value = false
  }
}

function handleGenerateSingle({ assetType, assetId }) {
  store.generateSingle(props.projectId, assetType, assetId)
}

function handleUpload({ assetType, assetId, file }) {
  store.uploadImage(props.projectId, assetType, assetId, file)
}

function handleDelete({ assetType, assetId, name }) {
  deleteTarget.value = { assetType, assetId, name }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  const { assetType, assetId } = deleteTarget.value
  deleteTarget.value = null
  await store.deleteAsset(props.projectId, assetType, assetId)
}

function openImagePreview({ imageUrl }) {
  previewImageUrl.value = imageUrl
  previewVisible.value = true
}

function openEditCharacter(asset) {
  editTarget.value = asset
  editCharacterVisible.value = true
}

function openEditLocation(asset) {
  editTarget.value = asset
  editAssetType.value = 'location'
  editLocationVisible.value = true
}

function openEditProp(asset) {
  editTarget.value = asset
  editPropVisible.value = true
}

async function handleEditSaved({ assetType, assetId, data, generateImage }) {
  await store.updateAsset(props.projectId, assetType, assetId, data)
  if (generateImage) {
    store.generateSingle(props.projectId, assetType, assetId)
  }
}

function openImageEdit({ asset, assetType }) {
  imageEditTarget.value = asset
  imageEditAssetType.value = assetType
  imageEditVisible.value = true
}

function handleModifyImage({ assetType, assetId, data }) {
  store.modifyImage(props.projectId, assetType, assetId, data)
  imageEditVisible.value = false
}

function openReferenceGenerate(asset) {
  refGenerateTarget.value = asset
  refGenerateVisible.value = true
}

function handleReferenceGenerate({ assetId, data }) {
  store.referenceGenerate(props.projectId, assetId, data)
  refGenerateVisible.value = false
}

function openImportFromGlobal({ assetType, assetId }) {
  pickerType.value = assetType
  pickerTargetAssetId.value = assetId
  pickerAssetType.value = assetType
  pickerVisible.value = true
}

async function handlePickerSelect(globalAssetId) {
  pickerLoading.value = true
  try {
    await store.copyFromGlobal(
      props.projectId,
      pickerAssetType.value,
      pickerTargetAssetId.value,
      globalAssetId,
    )
    pickerVisible.value = false
  } finally {
    pickerLoading.value = false
  }
}

function handleUndo({ assetType, assetId }) {
  store.undoImage(props.projectId, assetType, assetId)
}

function handleSyncVolc({ assetType, assetId }) {
  store.syncToVolc(props.projectId, assetType, assetId)
}

function openCreateDialog(assetType) {
  createAssetType.value = assetType
  createDialogVisible.value = true
}

async function handleCreateAsset({ assetType, data, generateImage }) {
  const result = await store.createAsset(props.projectId, assetType, data)
  createDialogVisible.value = false
  if (generateImage && result) {
    const assetId = result.id || result[assetType]?.id
    if (assetId) {
      store.generateSingle(props.projectId, assetType, assetId)
    }
  }
}

// ============ 批量上传 / 批量从资产中心导入（导演模式专属） ============

function handleBatchUpload() {
  batchUploadVisible.value = true
}

async function handleBatchUploadDone() {
  batchUploadVisible.value = false
  await store.fetchAssets(props.projectId)
}

function handleBatchImport() {
  batchPickerVisible.value = true
}

async function handleBatchPickerSelect(items) {
  // items: [{type, id, name, preview_url, ...}]
  if (!items || items.length === 0) {
    batchPickerVisible.value = false
    return
  }
  batchPickerVisible.value = false
  batchImporting.value = true
  const total = items.length
  let ok = 0
  let failed = 0
  try {
    for (const item of items) {
      try {
        // 先创建空资产，再从资产中心 copy 图片（silent=true 避免每项都弹 toast）
        const created = await store.createAsset(props.projectId, item.type, { name: item.name }, { silent: true })
        const assetId = created?.id || created?.[item.type]?.id
        if (!assetId) throw new Error('创建失败')
        await store.copyFromGlobal(props.projectId, item.type, assetId, item.id, { silent: true })
        ok++
      } catch {
        failed++
      }
    }
    if (ok > 0) ElMessage.success(`已导入 ${ok}/${total} 项${failed ? `，${failed} 项失败` : ''}`)
    else if (failed > 0) ElMessage.error(`全部 ${total} 项导入失败`)
    await store.fetchAssets(props.projectId)
  } finally {
    batchImporting.value = false
  }
}

// ============ 音色 ============

function handleVoiceDesign(character) {
  voiceDesignTarget.value = character
  voiceDesignVisible.value = true
}

async function handleVoiceDesignSave(voiceData) {
  const char = voiceDesignTarget.value
  if (!char) return
  await store.bindVoice(props.projectId, char.id, voiceData)
  voiceDesignVisible.value = false
  voiceDesignTarget.value = null
}

function handleVoiceSelect(character) {
  voicePickerTargetCharacter.value = character
  voicePickerVisible.value = true
  if (assetHubStore.voices.length === 0) {
    assetHubStore.fetchVoices()
  }
}

async function handleVoicePickerSelect(voice) {
  const char = voicePickerTargetCharacter.value
  if (!char) return
  await store.bindVoice(props.projectId, char.id, {
    voice_id: voice.voice_id || null,
    voice_type: voice.voice_type || null,
    custom_voice_url: voice.custom_voice_url || null,
  })
  voicePickerVisible.value = false
  voicePickerTargetCharacter.value = null
}

function handleVoiceChanged() {
  store.fetchAssets(props.projectId)
}
</script>

<style scoped>
.asset-library {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.asset-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 1rem;
}

.asset-header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.asset-header-icon {
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5625rem;
  background: var(--glass-bg-muted);
  color: var(--glass-text-secondary);
  flex-shrink: 0;
}

.asset-header-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  margin: 0;
}

.asset-header-stats {
  font-size: 0.75rem;
  color: var(--glass-text-tertiary);
}

.asset-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.asset-loading, .asset-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  min-height: 12rem;
  color: var(--glass-text-tertiary);
  font-size: 0.875rem;
}

.asset-loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--glass-stroke-base);
  border-top-color: var(--glass-accent-from);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
