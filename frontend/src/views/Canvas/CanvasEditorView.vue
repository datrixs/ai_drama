<template>
  <AppLayout>
    <div class="canvas-editor-page">
      <!-- 画布主体 -->
      <div
        class="canvas-flow-wrap"
        :class="{ 'is-drag-active': dragActive, 'is-space-pan': spacePressed }"
        @drop.prevent="onCanvasDrop"
        @dragover.prevent="onCanvasDragOver"
        @dragenter.prevent="onCanvasDragOver"
        @dragleave.prevent="onCanvasDragLeave"
        @contextmenu.prevent
      >
        <VueFlow
          :key="flowRemountKey"
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :min-zoom="0.2"
          :max-zoom="2"
          :delete-key-code="null"
          :zoom-on-scroll="false"
          :pan-on-scroll="true"
          :pan-on-scroll-speed="0.6"
          :prevent-scrolling="false"
          :nodes-draggable="!spacePressed"
          :pan-on-drag="spacePressed"
          :selection-key-code="true"
          :multi-selection-key-code="['Control', 'Meta', 'Shift']"
          fit-view-on-init
          :connect-on-click="false"
          :connection-radius="120"
          @connect="onConnect"
          @connect-start="onConnectStart"
          @connect-end="onConnectEnd"
          @node-drag-stop="onNodeDragStop"
          @node-drag-start="onNodeDragStart"
          @node-drag="onNodeDrag"
          @node-click="onNodeClick"
          @node-context-menu="onNodeContextMenu"
          @pane-context-menu="onPaneContextMenu"
          @pane-click="onPaneClick"
          @viewport-change="onViewportChange"
          @selection-end="onSelectionEnd"
        >
          <Background variant="dots" :gap="22" :size="1.6" pattern-color="#b8bec9" />
          <MiniMap
            v-if="minimapVisible"
            class="canvas-minimap"
            pannable
            zoomable
            :node-color="minimapNodeColor"
            :node-stroke-width="0"
            :border-radius="14"
            :mask-color="'rgba(226, 232, 240, 0.65)'"
          />
          <template #node-text="nodeProps">
            <CanvasNode v-bind="nodeProps" :dimmed="isNodeDimmed(nodeProps)" :viewport-zoom="viewport.zoom" @quick-add="handleQuickAdd" />
          </template>
          <template #node-image="nodeProps">
            <CanvasNode
              v-bind="nodeProps"
              :dimmed="isNodeDimmed(nodeProps)"
              :viewport-zoom="viewport.zoom"
              :is-editing="editingNodeId === nodeProps.id"
              :volc-synced="isItemSyncedToVolcano(nodeProps.data)"
              :volc-syncing="syncingNodeIds.has(nodeProps.id)"
              @quick-add="handleQuickAdd"
              @upload-request="onNodeUploadRequest"
              @open-asset-picker="onNodeOpenAssetPicker"
              @sync-volc="onNodeSyncVolc"
            />
          </template>
          <template #node-video="nodeProps">
            <CanvasNode
              v-bind="nodeProps"
              :dimmed="isNodeDimmed(nodeProps)"
              :viewport-zoom="viewport.zoom"
              :is-editing="editingNodeId === nodeProps.id"
              @quick-add="handleQuickAdd"
              @upload-request="onNodeUploadRequest"
              @open-asset-picker="onNodeOpenAssetPicker"
            />
          </template>
          <template #node-audio="nodeProps">
            <CanvasNode
              v-bind="nodeProps"
              :dimmed="isNodeDimmed(nodeProps)"
              :viewport-zoom="viewport.zoom"
              :is-editing="editingNodeId === nodeProps.id"
              @quick-add="handleQuickAdd"
              @upload-request="onNodeUploadRequest"
              @open-asset-picker="onNodeOpenAssetPicker"
            />
          </template>
          <template #node-group="nodeProps">
            <CanvasGroupNode
              v-bind="nodeProps"
              @ungroup="handleUngroup"
            />
          </template>
          <template #edge-default="edgeProps">
            <CanvasEdge v-bind="edgeProps" @delete="handleDeleteEdge" />
          </template>
        </VueFlow>

        <div v-if="loading" class="canvas-loading">
          <LoaderCircle :size="22" class="spin" /> <span>加载画布...</span>
        </div>
      </div>

      <!-- 顶部 chip -->
      <div class="canvas-topbar">
        <button class="topbar-back" type="button" @click="goBack" title="返回画布列表">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="m12 19-7-7 7-7" /><path d="M19 12H5" />
          </svg>
        </button>
        <input
          v-model="titleDraft"
          class="topbar-title"
          placeholder="未命名画布"
          @blur="commitTitle"
          @keyup.enter="commitTitle"
        />
        <!-- 节点内容自动保存状态：编辑节点内容 → 调 updateItem 期间切换显示 -->
        <div
          v-if="nodeSaveStatus !== 'idle'"
          class="topbar-save-status"
          :class="`topbar-save-status-${nodeSaveStatus}`"
        >
          <span v-if="nodeSaveStatus === 'saving'" class="tss-spinner"></span>
          <svg v-else-if="nodeSaveStatus === 'saved'" class="tss-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
          <svg v-else-if="nodeSaveStatus === 'failed'" class="tss-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
          <span class="tss-text">{{ nodeSaveStatus === 'saving' ? '保存中' : nodeSaveStatus === 'saved' ? '已保存' : '保存失败' }}</span>
        </div>
      </div>

      <!-- 左侧浮动工具栏 -->
      <aside class="canvas-toolbar">
        <div class="add-fab" :class="{ 'is-open': addPanelOpen }">
          <button
            class="tb-btn tb-btn-primary add-fab-btn"
            type="button"
            :disabled="creatingItem"
            title="新建节点"
            @click.stop="toggleAddPanel"
            @mouseenter="openAddPanel"
            @mouseleave="keepAddPanelMaybe"
          >
            <svg class="add-fab-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 5v14" /><path d="M5 12h14" />
            </svg>
          </button>

          <div
            v-if="addPanelOpen"
            class="add-fab-panel"
            @mouseenter="cancelAddPanelClose"
            @mouseleave="scheduleAddPanelClose"
          >
            <div class="afp-header">
              <span class="afp-title-icon">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 5v14" /><path d="M5 12h14" />
                </svg>
              </span>
              <span class="afp-title">新建节点</span>
              <button class="afp-close" type="button" title="关闭" @click.stop="closeAddPanel">×</button>
            </div>

            <button class="afp-card" type="button" :disabled="creatingItem" @click.stop="onAddPanelPick('text')">
              <span class="afp-card-icon afp-card-icon-text">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <path d="M14 2v6h6" />
                  <path d="M10 9H8" />
                  <path d="M16 13H8" />
                  <path d="M16 17H8" />
                </svg>
              </span>
              <span class="afp-card-body">
                <span class="afp-card-title">文本节点</span>
                <span class="afp-card-desc">输入文本内容</span>
              </span>
            </button>

            <button class="afp-card" type="button" :disabled="creatingItem" @click.stop="onAddPanelPick('image')">
              <span class="afp-card-icon afp-card-icon-image">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <rect width="18" height="18" x="3" y="3" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                </svg>
              </span>
              <span class="afp-card-body">
                <span class="afp-card-title">图片节点</span>
                <span class="afp-card-desc">生成画面或上传素材</span>
              </span>
            </button>

            <button class="afp-card" type="button" :disabled="creatingItem" @click.stop="onAddPanelPick('video')">
              <span class="afp-card-icon afp-card-icon-video">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="23 7 16 12 23 17 23 7" /><rect width="15" height="14" x="1" y="5" rx="2" />
                </svg>
              </span>
              <span class="afp-card-body">
                <span class="afp-card-title">视频节点</span>
                <span class="afp-card-desc">生成动态视频片段</span>
              </span>
            </button>

            <button class="afp-card" type="button" :disabled="creatingItem" @click.stop="onAddPanelPick('audio')">
              <span class="afp-card-icon afp-card-icon-audio">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" x2="12" y1="19" y2="22" />
                </svg>
              </span>
              <span class="afp-card-body">
                <span class="afp-card-title">音频节点</span>
                <span class="afp-card-desc">上传本地音频文件</span>
              </span>
            </button>
          </div>
        </div>
        <div class="tb-divider"></div>
        <button
          class="tb-btn"
          type="button"
          title="从资产中心导入"
          @click="onOpenAssetPicker"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
          </svg>
        </button>
      </aside>

      <!-- 选中节点后浮现的浮动操作条（打组）- 跟随选中节点包围盒上方 -->
      <Teleport to="body">
        <Transition name="canvas-floating-action">
          <div
            v-if="canGroupSelection && floatingActionStyle.display !== 'none'"
            class="canvas-floating-action"
            :style="floatingActionStyle"
          >
            <button
              class="cfa-btn cfa-btn-primary"
              type="button"
              title="将所选节点打组"
              @click="handleGroup"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="7" height="7" rx="1.5" />
                <rect x="14" y="3" width="7" height="7" rx="1.5" />
                <rect x="3" y="14" width="7" height="7" rx="1.5" />
                <rect x="14" y="14" width="7" height="7" rx="1.5" />
              </svg>
              <span>打组</span>
            </button>
          </div>
        </Transition>
      </Teleport>

      <!-- 左下角 zoom chip -->
      <div class="canvas-zoom-chip">
        <button class="zoom-btn" type="button" @click="zoomOut" title="缩小">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M5 12h14" /></svg>
        </button>
        <span class="zoom-text">{{ zoomText }}</span>
        <button class="zoom-btn" type="button" @click="zoomIn" title="放大">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14" /><path d="M5 12h14" /></svg>
        </button>
        <span class="zoom-sep"></span>
        <button class="zoom-btn" type="button" @click="resetView" title="重置视图">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 3 9 15" /><path d="M12 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" /><path d="M21 3v6h-6" />
          </svg>
        </button>
        <span class="zoom-sep"></span>
        <button class="zoom-btn" type="button" :class="{ 'is-active': minimapVisible }" @click="toggleMinimap" :title="minimapVisible ? '隐藏小地图' : '显示小地图'">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="18" height="18" x="3" y="3" rx="2" /><path d="M3 9h18" /><path d="M9 21V9" />
          </svg>
        </button>
        <button class="zoom-btn" type="button" @click="autoLayout" title="整理画布">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="7" height="7" x="3" y="3" rx="1.5" /><rect width="7" height="7" x="14" y="3" rx="1.5" /><rect width="7" height="7" x="3" y="14" rx="1.5" /><rect width="7" height="7" x="14" y="14" rx="1.5" />
          </svg>
        </button>
        <button class="zoom-btn" type="button" :class="{ 'is-active': assetFilter !== null }" title="筛选资产节点" @click="toggleAssetFilter">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 4h18l-7 8v7l-4 2v-9z" />
            </svg>
          </button>
        <span class="zoom-sep"></span>
        <button class="zoom-btn" type="button" :disabled="!canUndo" :class="{ 'is-disabled': !canUndo }" @click="undo" title="撤销 (Ctrl+Z)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 14 4 9l5-5" />
            <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11" />
          </svg>
        </button>
        <button class="zoom-btn" type="button" :disabled="!canRedo" :class="{ 'is-disabled': !canRedo }" @click="redo" title="重做 (Ctrl+Y)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 14 5-5-5-5" />
            <path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v0A5.5 5.5 0 0 0 9.5 20H13" />
          </svg>
        </button>
        <span class="zoom-sep"></span>
        <button class="zoom-btn" type="button" @click="shortcutsHelpVisible = true" title="快捷键 (?)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="4" width="20" height="16" rx="2" ry="2" />
            <path d="M6 8h.01" /><path d="M10 8h.01" /><path d="M14 8h.01" /><path d="M18 8h.01" />
            <path d="M8 12h.01" /><path d="M12 12h.01" /><path d="M16 12h.01" />
            <path d="M7 16h10" />
          </svg>
        </button>
      </div>

      <!-- 空状态 launcher -->
      <div v-if="!loading && flowNodes.length === 0" class="canvas-launcher">
        <div class="launcher-chip">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
          </svg>
          <span>从这里开始搭建你的画布</span>
        </div>
        <div class="launcher-actions">
          <button class="launcher-action" type="button" :disabled="creatingItem" @click="addNode('text')">文本节点</button>
          <button class="launcher-action" type="button" :disabled="creatingItem" @click="addNode('image')">图片节点</button>
          <button class="launcher-action" type="button" :disabled="creatingItem" @click="addNode('video')">视频节点</button>
          <button class="launcher-action" type="button" :disabled="creatingItem" @click="addNode('audio')">音频节点</button>
        </div>
      </div>

      <!-- 节点编辑浮层（双击节点打开，跟随节点位置） -->
      <Teleport to="body">
        <div
          v-if="editingNode"
          class="editor-popover"
          :style="editorPopoverStyle"
          @click.stop="closePopoversWhenEditing"
          @mousedown.stop="closePopoversWhenEditing"
        >
          <NodeEditorPanel
            :node-data="editingNode"
            :saving="editorSaving"
            :available-nodes="availableReferenceNodes"
            :incoming-upstream-nodes="incomingUpstreamNodes"
            :viewport-tick="viewportTick"
            :voice-upload-handler="voiceUploadHandler"
            @close="closeEditor"
            @save="onEditorSave"
            @side-add="onEditorSideAdd"
            @submit="onEditorSubmit"
            @focus-item="onFocusReferenceItem"
            @open-history="onOpenHistory"
            @open-asset-picker="onOpenAssetPicker"
            @open-voice-picker="onOpenVoicePicker"
            @imported="onAssetImported"
            @delete="onEditorDelete"
            @unlink-reference="onUnlinkReference"
          />
        </div>
      </Teleport>

      <!-- 右键节点操作菜单 -->
      <NodeContextMenu
        :visible="contextMenuVisible"
        :position="contextMenuPosition"
        :item-type="contextMenuItemType"
        :has-output="contextMenuHasOutput"
        :synced="contextMenuSynced"
        :syncing="contextMenuSyncing"
        :current-tag="contextMenuItemAssetTag"
        :saved-to-asset-center="contextMenuSavedToAssetCenter"
        @action="onContextMenuAction"
        @close="contextMenuVisible = false"
      />

      <!-- 右键画布空白处操作菜单 -->
      <PaneContextMenu
        :visible="paneContextMenuVisible"
        :position="paneContextMenuPosition"
        :can-paste="canPaste"
        :can-undo="canUndo"
        :can-redo="canRedo"
        :batch-candidate-count="batchSaveCandidates.length"
        @action="onPaneContextMenuAction"
        @close="paneContextMenuVisible = false"
      />

      <!-- 连接拖拽空抛弹出的"引用该节点生成"新建框 -->
      <ConnectionCreateMenu
        :visible="connCreateMenu.visible"
        :position="connCreateMenu.pos"
        :creating-item="creatingItem"
        @pick="createConnectedNode"
        @close="closeConnCreateMenu"
      />

      <!-- 隐藏文件选择器，"上传文件"菜单触发 -->
      <input
        ref="fileInputRef"
        type="file"
        multiple
        style="display: none"
        @change="onFileInputChange"
      />

      <!-- 节点上方"上传"按钮专用文件选择器（图片/视频/音频资产） -->
      <input
        ref="nodeAssetInputRef"
        type="file"
        style="display: none"
        @change="onNodeAssetInputChange"
      />

      <AssetCenterPicker
        v-if="assetPickerVisible && !voicePickerMode"
        @close="closeAssetPicker"
        @select="onAssetPicked"
      />

      <VoicePickerDialog
        v-if="assetPickerVisible && voicePickerMode"
        @close="closeAssetPicker"
        @select="onVoicePicked"
      />

      <SaveToAssetCenterDialog
        v-model="saveToAssetDialog.visible"
        :item-id="saveToAssetDialog.itemId"
        :item-type="saveToAssetDialog.itemType"
        :default-name="saveToAssetDialog.defaultName"
        @saved="onSingleSavedToAsset"
      />

      <BatchSaveToAssetCenterDialog
        v-model="batchSaveDialog.visible"
        :document-id="currentDocument?.id || ''"
        :candidate-count="batchSaveDialog.candidateCount"
        @saved="onBatchSavedToAsset"
      />

      <GenerationHistoryDrawer
        v-model:visible="historyDrawerVisible"
        :item-id="historyItemId"
        :item-type="historyItemType"
        :current-generation-id="historyCurrentGenId"
        @applied="onHistoryApplied"
      />

      <ConfirmDialog
        v-model="nodeDeleteConfirmVisible"
        title="删除节点"
        :message="nodeDeleteMessage"
        confirm-text="删除"
        type="danger"
        @confirm="doDeleteNode"
      />

      <ConfirmDialog
        v-model="edgeDeleteConfirmVisible"
        title="删除连线"
        :message="edgeDeleteMessage"
        confirm-text="删除"
        type="danger"
        @confirm="doDeleteEdge"
      />

      <!-- 快捷键说明 -->
      <div v-if="shortcutsHelpVisible" class="shortcuts-overlay" @click.self="shortcutsHelpVisible = false">
        <div class="shortcuts-dialog">
          <div class="shortcuts-header">
            <h3>键盘快捷键</h3>
            <button class="shortcuts-close" type="button" @click="shortcutsHelpVisible = false">×</button>
          </div>
          <div class="shortcuts-body">
            <div v-for="g in shortcutGroups" :key="g.title" class="shortcut-group">
              <div class="shortcut-group-title">{{ g.title }}</div>
              <div v-for="row in g.rows" :key="row.label" class="shortcut-row">
                <span class="shortcut-label">{{ row.label }}</span>
                <span class="shortcut-keys">
                  <kbd v-for="(k, i) in row.keys" :key="i">{{ k }}</kbd>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { LoaderCircle } from '@lucide/vue'
import AppLayout from '@/layout/AppLayout.vue'
import CanvasNode from './components/CanvasNode.vue'
import CanvasGroupNode from './components/CanvasGroupNode.vue'
import CanvasEdge from './components/CanvasEdge.vue'
import NodeContextMenu from './components/NodeContextMenu.vue'
import PaneContextMenu from './components/PaneContextMenu.vue'
import ConnectionCreateMenu from './components/ConnectionCreateMenu.vue'
import NodeEditorPanel from './components/NodeEditorPanel.vue'
import GenerationHistoryDrawer from './components/GenerationHistoryDrawer.vue'
import SaveToAssetCenterDialog from './components/SaveToAssetCenterDialog.vue'
import BatchSaveToAssetCenterDialog from './components/BatchSaveToAssetCenterDialog.vue'
import AssetCenterPicker from '@/views/Home/components/AssetCenterPicker.vue'
import VoicePickerDialog from '@/views/AssetsCenter/components/modals/VoicePickerDialog.vue'
import { useCanvasStore } from '@/store/canvas'
import { generateCanvasImage, generateCanvasText, generateCanvasVideo, getCanvasGeneration, registerCanvasAsset } from '@/api/canvas'
import { useCanvasGrouping } from '@/composables/useCanvasGrouping'
import { useWebSocket } from '@/composables/useWebSocket'
import { WSEventType } from '@/constants/ws'
import { pickNodeTypeForFile, isImageFile, isVideoFile, isTextFile } from './utils/fileMime'
import { validateAndUploadAudio } from './utils/audioUpload'
import { uploadCanvasAssetDirect } from './utils/mediaUpload'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { Background } from '@vue-flow/background'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/minimap/dist/style.css'

const route = useRoute()
const router = useRouter()
const documentId = route.params.documentId

const {
  currentDocument, loading, openDocument, renameDocument,
  addItem, updateItem, removeItem, addConnection, removeConnection,
  batchUpdateItems, patchItemsLocally,
} = useCanvasStore()

const flowNodes = ref([])
const flowEdges = ref([])
// 强制 VueFlow 重新挂载的 key（递增即整体重建，彻底清空内部 state.nodes / nodesMap）
const flowRemountKey = ref(0)
const titleDraft = ref('')
const creatingItem = ref(false)
const editingNodeId = ref(null)
const spacePressed = ref(false)
const shortcutsHelpVisible = ref(false)
const editorSaving = ref(false)
// 节点内容自动保存状态指示：'idle' | 'saving' | 'saved' | 'failed'
// onEditorSave 触发时切换为 'saving'，API 返回后切到 'saved' / 'failed'，
// 成功/失败状态展示若干秒后自动回退到 idle，避免一直挂在前一次状态上
const nodeSaveStatus = ref('idle')
let nodeSaveStatusTimer = null
const historyDrawerVisible = ref(false)
const historyItemId = ref('')
const historyItemType = ref('text')
const historyCurrentGenId = ref('')
const assetPickerVisible = ref(false)
const nodeDeleteConfirmVisible = ref(false)
const nodeDeleteTargetId = ref(null)
const edgeDeleteConfirmVisible = ref(false)
const edgeDeleteTargetId = ref(null)
const edgeDeleteTargetIds = ref([])
const contextMenuVisible = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const contextMenuItemType = ref('text')
const contextMenuNodeId = ref(null)
const assetFilter = ref(null)
const voicePickerMode = ref(false)
const voicePickerTargetId = ref(null)
const paneContextMenuVisible = ref(false)
const paneContextMenuPosition = ref({ x: 0, y: 0 })
const copiedNodes = ref([])
const undoStack = ref([])
const redoStack = ref([])
const fileInputRef = ref(null)
const nodeAssetInputRef = ref(null)
const nodeAssetTargetId = ref(null)
const nodeAssetItemType = ref(null)
const syncingNodeIds = ref(new Set())
const saveToAssetDialog = reactive({
  visible: false,
  itemId: '',
  itemType: 'image',
  defaultName: '',
})
const batchSaveDialog = reactive({
  visible: false,
  candidateCount: 0,
})

// 批量保存候选：image+asset_tag∈{character/location/prop} 或 audio，未入库且有输出 URL
const batchSaveCandidates = computed(() => {
  const items = currentDocument.value?.items || []
  return items.filter((it) => {
    if (it.saved_to_asset_center) return false
    const t = (it.item_type || '').toLowerCase()
    if (t === 'audio') {
      // audio 节点必须有可保存的输出
    } else if (t === 'image' && ['character', 'location', 'prop'].includes(it.asset_tag)) {
      // image 节点带资产标记
    } else {
      return false
    }
    const out = it.last_output_json || {}
    return !!(out.url || out.image_url || out.video_url || out.audio_url)
  })
})
const nodeDeleteMessage = computed(() => {
  const item = currentDocument.value?.items?.find((i) => i.id === nodeDeleteTargetId.value)
  return `确定要删除节点"${item?.title || '未命名节点'}"吗？此操作无法撤销。`
})
const edgeDeleteMessage = computed(() => {
  if (edgeDeleteTargetIds.value.length > 1) {
    return `确定要删除选中的 ${edgeDeleteTargetIds.value.length} 条连线吗？下游节点输入框中的自动引用也将被移除。`
  }
  return '确定要删除这条连线吗？下游节点输入框中的自动引用也将被移除。'
})

// ── 资产同步状态辅助 ───────────────────────────────────
// 按 region 判断节点是否已在当前 region 同步至火山资产库
function isItemSyncedToVolcano(item) {
  if (!item) return false
  const region = item.region
  if (region === 'overseas') return !!item.byteplus_asset_id
  return !!item.volc_asset_id
}

function itemHasOutput(item) {
  if (!item) return false
  const oj = item.last_output_json || {}
  return !!(oj.url || oj.image_url || oj.video_url || oj.audio_url)
}

const contextMenuItem = computed(() =>
  currentDocument.value?.items?.find((i) => i.id === contextMenuNodeId.value) || null
)
const contextMenuHasOutput = computed(() => itemHasOutput(contextMenuItem.value))
const contextMenuSynced = computed(() => isItemSyncedToVolcano(contextMenuItem.value))
const contextMenuSyncing = computed(() =>
  contextMenuNodeId.value ? syncingNodeIds.value.has(contextMenuNodeId.value) : false
)
const contextMenuItemAssetTag = computed(() => contextMenuItem.value?.asset_tag || null)
const contextMenuSavedToAssetCenter = computed(() => !!contextMenuItem.value?.saved_to_asset_center)

const editingNode = computed(() => {
  if (!editingNodeId.value) return null
  const item = currentDocument.value?.items?.find((i) => i.id === editingNodeId.value)
  if (!item) return null
  return {
    ...item,
    content_json: item.content_json || {},
    last_output_json: item.last_output_json || null,
  }
})

// 当前编辑节点的入连线上游节点（直接上游，BFS 反向遍历）
// 用于：①预览区缩略图（NodeEditorPanel.referencedNodes）；②@ 引用候选列表
// 组节点作为上游时，展开为组内 image/video/audio 子节点
function _buildIncomingUpstreamSet(items, conns, nodeId) {
  const upstream = new Set()
  const queue = [nodeId]
  const visited = new Set([nodeId])
  while (queue.length) {
    const target = queue.shift()
    for (const c of conns) {
      if (c.target_item_id === target && !visited.has(c.source_item_id)) {
        visited.add(c.source_item_id)
        upstream.add(c.source_item_id)
        queue.push(c.source_item_id)
      }
    }
  }
  return upstream
}

function _nodeToRefView(it) {
  const out = it.last_output_json || {}
  const cj = it.content_json || {}
  return {
    id: it.id,
    item_type: it.item_type,
    parent_id: it.parent_id || null,
    title: it.title || '',
    previewUrl: out.url || out.thumbnail_url || cj.url || cj.thumbnail_url || '',
    previewText: cj.body || cj.text || cj.prompt || '',
    videoUrl: it.item_type === 'video' ? (out.url || cj.url || '') : '',
    thumbnailUrl: it.item_type === 'video'
      ? (it.cover_url || out.thumbnail_url || cj.thumbnail_url || '')
      : '',
    has_output: !!(out.url || cj.url),
  }
}

// 预览区/参考池：基于入连线的直接上游，组节点展开为组内 image/video/audio 子节点（按 id 去重）
const incomingUpstreamNodes = computed(() => {
  const all = currentDocument.value?.items || []
  const conns = currentDocument.value?.connections || []
  const cur = editingNodeId.value
  if (!cur) return []
  const upstream = _buildIncomingUpstreamSet(all, conns, cur)
  const result = []
  const seen = new Set()
  for (const id of upstream) {
    const up = all.find((i) => i.id === id)
    if (!up) continue
    if (up.item_type === 'group') {
      // 展开组内 image/video/audio 子节点
      const children = all.filter(
        (i) => i.parent_id === up.id && ['image', 'video', 'audio'].includes((i.item_type || '').toLowerCase()),
      )
      for (const child of children) {
        if (seen.has(child.id)) continue
        seen.add(child.id)
        result.push(_nodeToRefView(child))
      }
    } else {
      if (seen.has(up.id)) continue
      seen.add(up.id)
      result.push(_nodeToRefView(up))
    }
  }
  return result
})

// @ 候选列表：仅展示已连线节点（组展开为子节点），按 id 去重，过滤视频节点不引用文本、未同步视频不引
const availableReferenceNodes = computed(() => {
  const all = currentDocument.value?.items || []
  const cur = editingNodeId.value
  if (!cur) return []
  const currentItem = all.find((i) => i.id === cur)
  const currentType = currentItem?.item_type
  return incomingUpstreamNodes.value.filter((n) => {
    // 视频节点编辑器不引用文本节点
    if (currentType === 'video' && n.item_type === 'text') return false
    // 未同步的视频不出现在 @ 候选
    if (n.item_type === 'video' && n.has_output) {
      const item = all.find((i) => i.id === n.id)
      if (item && !isItemSyncedToVolcano(item)) return false
    }
    return true
  }).map((n) => ({ ...n, is_upstream: true }))
})

// 节点编辑浮层：跟随节点位置（节点下方），用 Teleport 渲染到 body 以逃离 VueFlow 的 transform
// 关键：DOM rect 不在 computed 里读（会跟 VueFlow transform 应用时序打架，滚动时跳动）。
// 改为：watch viewport/position → 调度 rAF → 在 rAF 里读 rect（此时 VueFlow 已写入 transform，
// 浏览器算出的 rect 是真实位置）→ 写入响应式 ref → computed 用 ref 算最终样式。
const {
  viewport, zoomIn, zoomOut, fitView, screenToFlowCoordinate,
  findNode, getNodes, updateNodeData: vfUpdateNodeData,
  getSelectedNodes, addNodes, removeNodes, updateNode,
  setViewport, removeSelectedNodes,
  userSelectionRect,
} = useVueFlow()

const POPOVER_W = 680
const POPOVER_GAP = 16
const editingNodeRect = ref({ left: 0, top: 0, width: 0, height: 0 })
let rectRafId = null
let dimsObserver = null

function readEditingNodeRect() {
  if (!editingNodeId.value || typeof document === 'undefined') return
  const el = document.querySelector(`.vue-flow__node[data-id="${CSS.escape(editingNodeId.value)}"]`)
  if (!el) return
  const r = el.getBoundingClientRect()
  if (r.width <= 0 || r.height <= 0) return
  editingNodeRect.value = { left: r.left, top: r.top, width: r.width, height: r.height }
}

function scheduleRectRead() {
  if (rectRafId != null) return
  rectRafId = requestAnimationFrame(() => {
    rectRafId = null
    readEditingNodeRect()
  })
}

watch(editingNodeId, (id) => {
  if (rectRafId != null) {
    cancelAnimationFrame(rectRafId)
    rectRafId = null
  }
  if (dimsObserver) {
    dimsObserver.disconnect()
    dimsObserver = null
  }
  if (id) {
    // 首帧立刻读一次，避免开弹框时闪一下错位
    readEditingNodeRect()
    // 监听节点尺寸变化（如图片加载完后节点变高），同步更新 rect
    const el = document.querySelector(`.vue-flow__node[data-id="${CSS.escape(id)}"]`)
    if (el && typeof ResizeObserver !== 'undefined') {
      dimsObserver = new ResizeObserver(() => scheduleRectRead())
      dimsObserver.observe(el)
    }
  } else {
    editingNodeRect.value = { left: 0, top: 0, width: 0, height: 0 }
  }
}, { immediate: true })

// viewport 变化（滚动/缩放）→ 下一帧读 rect
watch(viewport, () => {
  if (editingNodeId.value) scheduleRectRead()
}, { deep: true })

// 给 NodeEditorPanel 一个 viewport 变化的信号，让它重定位已展开的下拉浮层
const viewportTick = ref(0)
watch(viewport, () => {
  viewportTick.value += 1
}, { deep: true })

// 节点拖动 → 下一帧读 rect
watch(() => {
  if (!editingNodeId.value) return null
  const node = findNode(editingNodeId.value)
  return node?.position ? { x: node.position.x, y: node.position.y } : null
}, () => {
  if (editingNodeId.value) scheduleRectRead()
}, { deep: true })

const editorPopoverStyle = computed(() => {
  if (!editingNodeId.value) return { display: 'none' }
  const rect = editingNodeRect.value
  if (!rect.width || !rect.height) return { display: 'none' }

  let left = rect.left + rect.width / 2 - POPOVER_W / 2
  const top = rect.top + rect.height + POPOVER_GAP
  if (left + POPOVER_W > window.innerWidth - 8) {
    left = window.innerWidth - 8 - POPOVER_W
  }
  if (left < 8) left = 8
  return {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    width: `${POPOVER_W}px`,
    maxHeight: `${Math.max(80, window.innerHeight - top - 8)}px`,
    zIndex: 30,
  }
})

const zoomText = computed(() => `${Math.round((viewport.value?.zoom ?? 1) * 100)}%`)

// ── 组合节点（group）：打组/解组 ───────────────────────
// 选中节点（非 group、非子节点）≥2 时启用打组按钮
const canGroupSelection = computed(() => {
  const sel = flowNodes.value.filter(
    (n) => n.selected && n.type !== 'group' && !n.parentNode,
  )
  return sel.length >= 2
})

// 强制 VueFlow 从 store 重建所有节点。
// 关键：换 <VueFlow :key> 让 VueFlow 整体卸载重建 —— 彻底清空内部
// state.nodes / nodesMap / parentLookup 与所有 watchPausable 作用域。
// 仅靠 removeNodes 或 flowNodes.value=[] 在某些时序下不能让内部 state 真正清空
// （pauseModel/pauseStore 会丢变更），导致撤销打组后组框残留。
// 重建前保存 viewport，重建后恢复，避免视图位置跳回默认。
async function forceRebuildFlow() {
  const savedViewport = {
    x: viewport.value?.x ?? 0,
    y: viewport.value?.y ?? 0,
    zoom: viewport.value?.zoom ?? 1,
  }
  flowRemountKey.value += 1
  await nextTick()
  await nextTick()
  syncFromStore()
  await nextTick()
  if (typeof setViewport === 'function') {
    try {
      setViewport(savedViewport)
    } catch (_) { /* 忽略：极少数版本无 setViewport */ }
  }
}

const { groupSelected, ungroupNode } = useCanvasGrouping({
  storeRef: currentDocument,
  flowNodes,
  getSelectedNodes: () => getSelectedNodes.value,
  addItem,
  removeItem,
  batchUpdateItems,
  patchItemsLocally,
  findNode,
  removeFlowNodes: removeNodes,
  updateFlowNode: updateNode,
  // 打组/解组已经自行整体替换 flowNodes.value，不再需要 forceRebuildFlow ——
  // 那会卸载整个 VueFlow 导致正在编辑的输入框失焦。
  // 撤销/重做路径仍走 forceRebuildFlow（见 undo/redo）。
})

async function handleGroup() {
  pushHistory()
  await groupSelected()
}

async function handleUngroup(groupId) {
  pushHistory()
  await ungroupNode(groupId)
}

// 框选结束时同步更新一次"已选中节点数"驱动 UI
function onSelectionEnd() {
  scheduleFloatingActionRect()
}

// ── 浮动「打组」按钮位置：跟随选中节点包围盒上方 ───────
// 通过 DOM rect 计算包围盒（选中节点的并集），渲染到 body 的浮层定位在其上方。
// 触发重算时机：选中状态变化、viewport 变化（缩放/平移）、节点拖动。
const floatingActionRect = ref({ left: 0, top: 0, width: 0 })
let floatingActionRaf = null

function readFloatingActionRect() {
  if (typeof document === 'undefined') return
  const sel = flowNodes.value.filter((n) => n.selected && n.type !== 'group' && !n.parentNode)
  if (sel.length < 2) {
    floatingActionRect.value = { left: 0, top: 0, width: 0 }
    return
  }
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const n of sel) {
    const el = document.querySelector(`.vue-flow__node[data-id="${CSS.escape(n.id)}"]`)
    if (!el) continue
    const r = el.getBoundingClientRect()
    if (!r.width) continue
    minX = Math.min(minX, r.left)
    minY = Math.min(minY, r.top)
    maxX = Math.max(maxX, r.right)
    maxY = Math.max(maxY, r.bottom)
  }
  // DOM 找不到时 fallback：用 flowNodes 的 position + viewport 转换
  if (minX === Infinity) {
    const z = viewport.value?.zoom ?? 1
    const cx = viewport.value?.x ?? 0
    const cy = viewport.value?.y ?? 0
    for (const n of sel) {
      const sx = n.position.x * z + cx
      const sy = n.position.y * z + cy
      minX = Math.min(minX, sx)
      minY = Math.min(minY, sy)
      maxX = Math.max(maxX, sx + 240 * z)
      maxY = Math.max(maxY, sy + 120 * z)
    }
  }
  if (minX === Infinity) {
    floatingActionRect.value = { left: 0, top: 0, width: 0 }
    return
  }
  floatingActionRect.value = {
    left: (minX + maxX) / 2,
    top: minY,
    width: maxX - minX,
  }
}

function scheduleFloatingActionRect() {
  if (floatingActionRaf != null) return
  floatingActionRaf = requestAnimationFrame(() => {
    floatingActionRaf = null
    readFloatingActionRect()
  })
}

const floatingActionStyle = computed(() => {
  const r = floatingActionRect.value
  if (!r.width) return { display: 'none' }
  // 估算按钮宽度（图标+文字+padding）≈ 96px，向上偏移 12px
  const estWidth = 96
  let left = r.left - estWidth / 2
  left = Math.max(8, Math.min(left, window.innerWidth - estWidth - 8))
  const btnH = 44 // 按钮 height(~28) + gap(12) + 4
  let top = r.top - btnH
  // 如果按钮超出屏幕顶部，改放到包围盒下方
  if (top < 8) top = r.top + btnH
  top = Math.max(8, Math.min(top, window.innerHeight - 40))
  return {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    zIndex: 30,
  }
})

// 选中状态变化 → 重读 rect
watch(
  () => flowNodes.value.filter((n) => n.selected).map((n) => n.id).join(','),
  () => scheduleFloatingActionRect(),
)

// viewport 变化（缩放/平移）→ 重读 rect
watch(viewport, () => scheduleFloatingActionRect(), { deep: true })

// 节点拖动 → 实时跟随
function onNodeDrag() {
  scheduleFloatingActionRect()
}

function onViewportChange() {
  // viewport 是响应式 ref，editorPopoverStyle 直接依赖它会自动重算
}

function onNodeDragStart() {
  // 拖动开始前推入历史快照，让节点移动可被撤销
  pushHistory()
}

// Ctrl + 滚轮：缩放画布（鼠标在画布或编辑弹框上都生效，避免触发浏览器页面缩放）
function onDocWheelZoom(e) {
  if (!e.ctrlKey) return
  const onCanvas = e.target.closest('.vue-flow')
  const onPopover = e.target.closest('.editor-popover')
  if (!onCanvas && !onPopover) return
  e.preventDefault()
  if (e.deltaY < 0) {
    zoomIn({ duration: 200 })
  } else {
    zoomOut({ duration: 200 })
  }
}

// 框选/拖节点（mouseDown）时，pan-on-scroll 会被 VueFlow 屏蔽
// 这里手动接管：mouseDown 期间用滚轮平移视口，让用户能边框选边移动页面
const isCanvasMouseDown = ref(false)
function onCanvasMouseDown(e) {
  if (e.target.closest('.vue-flow')) isCanvasMouseDown.value = true
}
function onCanvasMouseUp() {
  isCanvasMouseDown.value = false
}
function onDocWheelPanDuringDrag(e) {
  if (e.ctrlKey) return
  if (!isCanvasMouseDown.value) return
  if (!e.target.closest('.vue-flow')) return
  e.preventDefault()
  e.stopPropagation()
  const speed = 0.6
  const dx = e.deltaX * speed
  const dy = e.deltaY * speed
  viewport.value = {
    ...viewport.value,
    x: viewport.value.x - dx,
    y: viewport.value.y - dy,
  }
  // 让 selection rect 在画布上"锁定"：屏幕起点跟着 viewport 一起平移
  // VueFlow 的 rect 屏幕位置不受 viewport transform 影响，需要手动同步 startX/startY/x/y
  // 这样 rect 在画布上的实际范围会随视口扩大（用户拖动鼠标可继续扩展）
  const r = userSelectionRect.value
  if (r) {
    userSelectionRect.value = {
      ...r,
      startX: r.startX - dx,
      startY: r.startY - dy,
      x: r.x - dx,
      y: r.y - dy,
    }
    // dispatch mousemove 让 VueFlow 立即重算哪些节点在 rect 内（用当前鼠标位置）
    document.dispatchEvent(new MouseEvent('mousemove', {
      bubbles: true,
      cancelable: true,
      clientX: e.clientX,
      clientY: e.clientY,
    }))
  }
}

onMounted(async () => {
  try {
    await openDocument(documentId)
    titleDraft.value = currentDocument.value?.title || ''
    syncFromStore()
  } catch (e) {
    // request 拦截器已弹错误提示
  }
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('keyup', handleKeyup)
  window.addEventListener('blur', resetSpacePan)
  document.addEventListener('visibilitychange', resetSpacePan)
  document.addEventListener('mousedown', onDocClickCloseEditor)
  document.addEventListener('mousedown', onCanvasMouseDown)
  document.addEventListener('mouseup', onCanvasMouseUp)
  document.addEventListener('wheel', onDocWheelZoom, { passive: false, capture: true })
  document.addEventListener('wheel', onDocWheelPanDuringDrag, { passive: false, capture: true })
  unsubscribeWsGeneration = onEvent(applyGenerationFromWsEvent)
})

function onDocClickCloseEditor(e) {
  if (!editingNodeId.value) return
  // 弹框内部：不处理（弹框自身有 mousedown.stop，正常不会进到这里）
  if (e.target.closest('.editor-popover')) return
  // 弹出的下拉菜单 / 节点 handle 菜单：不处理
  if (e.target.closest('.ne-model-menu')) return
  if (e.target.closest('.cn-handle-menu')) return
  // 资产中心 picker / 各种弹窗：不处理
  if (e.target.closest('.asset-center-picker')) return
  if (e.target.closest('.el-overlay')) return
  if (e.target.closest('.el-message-box')) return
  if (e.target.closest('.el-popover')) return
  // 节点上的浮动操作条按钮：交给节点自身的事件处理
  if (e.target.closest('.cn-top-actions')) return
  closeEditor()
}

// 点击编辑弹框时，收起其他弹层（右键节点菜单 / 右键画布菜单）
function closePopoversWhenEditing() {
  contextMenuVisible.value = false
  paneContextMenuVisible.value = false
}

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('keyup', handleKeyup)
  window.removeEventListener('blur', resetSpacePan)
  document.removeEventListener('visibilitychange', resetSpacePan)
  document.removeEventListener('mousedown', onDocClickCloseEditor)
  document.removeEventListener('mousedown', onCanvasMouseDown)
  document.removeEventListener('mouseup', onCanvasMouseUp)
  document.removeEventListener('wheel', onDocWheelZoom, { capture: true })
  document.removeEventListener('wheel', onDocWheelPanDuringDrag, { capture: true })
  if (unsubscribeWsGeneration) {
    unsubscribeWsGeneration()
    unsubscribeWsGeneration = null
  }
  dragStopTimers.forEach((t) => clearTimeout(t))
  dragStopTimers.clear()
  generationPollTimers.forEach((t) => clearTimeout(t))
  generationPollTimers.clear()
  if (floatingActionRaf != null) {
    cancelAnimationFrame(floatingActionRaf)
    floatingActionRaf = null
  }
  if (dimsObserver) {
    dimsObserver.disconnect()
    dimsObserver = null
  }
  if (rectRafId != null) {
    cancelAnimationFrame(rectRafId)
    rectRafId = null
  }
  if (addPanelCloseTimer != null) {
    clearTimeout(addPanelCloseTimer)
    addPanelCloseTimer = null
  }
})

function syncFromStore() {
  const doc = currentDocument.value
  if (!doc) return
  // 计算每个 group 的子节点数量（用于组标题展示）
  const childCountMap = {}
  for (const it of doc.items || []) {
    if (it.parent_id) {
      childCountMap[it.parent_id] = (childCountMap[it.parent_id] || 0) + 1
    }
  }
  flowNodes.value = (doc.items || []).map((item) => {
    const node = {
      id: item.id,
      type: item.item_type,
      position: { x: item.position_x || 0, y: item.position_y || 0 },
      data: {
        ...item,
        child_count: item.item_type === 'group' ? (childCountMap[item.id] || 0) : undefined,
      },
    }
    if (item.item_type === 'group') {
      node.width = item.width || 240
      node.height = item.height || 120
    }
    if (item.parent_id) {
      node.parentNode = item.parent_id
      node.extent = 'parent'
    }
    return node
  })
  flowEdges.value = (doc.connections || []).map((conn) => ({
    id: conn.id,
    source: conn.source_item_id,
    target: conn.target_item_id,
    sourceHandle: conn.source_handle || 'right',
    targetHandle: conn.target_handle || 'left',
    animated: false,
  }))
}

function goBack() {
  router.push('/canvas')
}

async function commitTitle() {
  const newTitle = titleDraft.value.trim()
  if (!currentDocument.value || newTitle === (currentDocument.value.title || '')) return
  try {
    await renameDocument(documentId, newTitle)
    ElMessage.success('画布名称已更新')
  } catch (e) {}
}

// ── 左侧 "+" 浮动按钮：hover 旋转 + 右侧展开节点类型面板 ──
const addPanelOpen = ref(false)
let addPanelCloseTimer = null

function openAddPanel() {
  if (addPanelCloseTimer != null) { clearTimeout(addPanelCloseTimer); addPanelCloseTimer = null }
  addPanelOpen.value = true
}

function cancelAddPanelClose() {
  if (addPanelCloseTimer != null) { clearTimeout(addPanelCloseTimer); addPanelCloseTimer = null }
}

function scheduleAddPanelClose() {
  if (addPanelCloseTimer != null) clearTimeout(addPanelCloseTimer)
  addPanelCloseTimer = setTimeout(() => { addPanelOpen.value = false }, 120)
}

function keepAddPanelMaybe() {
  // 鼠标离开按钮时延迟关闭，给光标移动到面板留出时间
  scheduleAddPanelClose()
}

function closeAddPanel() {
  if (addPanelCloseTimer != null) { clearTimeout(addPanelCloseTimer); addPanelCloseTimer = null }
  addPanelOpen.value = false
}

function toggleAddPanel() {
  if (addPanelOpen.value) closeAddPanel()
  else openAddPanel()
}

async function onAddPanelPick(itemType) {
  closeAddPanel()
  await addNode(itemType)
}

/**
 * 添加节点到 VueFlow：用 addNodes API 而非直接改 flowNodes.value
 * 原因：v-model:nodes 双向绑定下，Vue Flow 内部维护 nodesMap/parentLookup，
 * 直接整体替换数组在打组后可能不同步内部状态，导致后续新增节点无法渲染。
 * addNodes 会同步更新 Vue Flow 内部状态并回写 flowNodes。
 */
function appendFlowNode(node) {
  try {
    addNodes([node])
  } catch (_) {
    // 兜底：直接 push 到 flowNodes
    flowNodes.value = [...flowNodes.value, node]
  }
}

async function addNode(itemType) {
  if (creatingItem.value) return
  pushHistory()
  creatingItem.value = true
  const pos = computeSpawnPosition()
  try {
    const created = await addItem({
      item_type: itemType,
      title: '',
      position_x: Math.round(pos.x),
      position_y: Math.round(pos.y),
      width: 240,
      height: 120,
    })
    appendFlowNode({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      data: { ...created },
    })
  } catch (e) {
    // request 拦截器已弹错误提示
  } finally {
    creatingItem.value = false
  }
}

function computeSpawnPosition() {
  const offset = (flowNodes.value.length % 6) * 30
  const zoom = viewport.value?.zoom ?? 1
  const cx = viewport.value?.x ?? 0
  const cy = viewport.value?.y ?? 0
  return {
    x: (200 + offset - cx) / Math.max(zoom, 0.0001),
    y: (140 + offset - cy) / Math.max(zoom, 0.0001),
  }
}

async function handleQuickAdd({ id, direction, itemType }) {
  if (creatingItem.value) return
  const currentNode = flowNodes.value.find((n) => n.id === id)
  if (!currentNode) return
  pushHistory()

  // 计算新节点位置：当前节点左/右偏移 320px，垂直方向根据已有相邻节点错开
  const offsetX = direction === 'after' ? 320 : -320
  const newY = findClearY(currentNode.position.x + offsetX, currentNode.position.y)
  const newX = currentNode.position.x + offsetX

  creatingItem.value = true
  try {
    const created = await addItem({
      item_type: itemType,
      title: '',
      position_x: Math.round(newX),
      position_y: Math.round(newY),
      width: 240,
      height: 120,
    })
    appendFlowNode({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      data: { ...created },
    })

    // 自动连线：前插 -> 新 -> 当前；后插 -> 当前 -> 新
    const sourceId = direction === 'after' ? id : created.id
    const targetId = direction === 'after' ? created.id : id
    const conn = await addConnection({
      source_item_id: sourceId,
      target_item_id: targetId,
      source_handle: 'right',
      target_handle: 'left',
    })
    flowEdges.value = [...flowEdges.value, {
      id: conn.id,
      source: sourceId,
      target: targetId,
      sourceHandle: 'right',
      targetHandle: 'left',
      animated: false,
    }]

    // 自动引用：后一个节点引用前一个节点
    try {
      await addUpstreamReference(sourceId, targetId)
    } catch (e) {
      // 不影响节点创建与连线
    }
  } catch (e) {
    // request 拦截器已弹错误提示
  } finally {
    creatingItem.value = false
  }
}

function findClearY(targetX, baseY) {
  // 在目标 X 列附近（±240px 宽度重叠），找到第一个不与现有节点重叠的 Y
  const nodeWidth = 240
  const nodeHeight = 120
  const gap = 60
  let candidateY = baseY
  const overlaps = (y) =>
    flowNodes.value.some((n) => {
      const xOverlap = Math.abs(n.position.x - targetX) < nodeWidth
      const yOverlap = Math.abs(n.position.y - candidateY) < nodeHeight
      return xOverlap && yOverlap
    })
  let attempts = 0
  while (overlaps(candidateY) && attempts < 20) {
    candidateY += nodeHeight + gap
    attempts++
  }
  return candidateY
}

// 把源节点加入目标节点的 prompt_tokens，实现“连线后自动引用”
// 仅文本源节点会拼接：text→text 拼接到 body 末尾；text→image/video 拼接到 prompt_tokens 文本片段。
// 图片/视频/音频/组源节点连线后不再自动拼 @ 引用——资产展示改由「连线驱动的预览区」承载，
// prompt 中的 @ 仅作 prompt 文字标注，由用户在编辑器手动输入。
async function addUpstreamReference(sourceId, targetId) {
  if (!sourceId || !targetId || sourceId === targetId) return
  const sourceItem = currentDocument.value?.items?.find((i) => i.id === sourceId)
  const targetItem = currentDocument.value?.items?.find((i) => i.id === targetId)
  if (!sourceItem || !targetItem) return

  // 非文本上游：不再修改目标 prompt；连线本身已让资产进入下游预览区
  if (sourceItem.item_type !== 'text') return

  // 文本 → 文本：把源节点正文追加到目标节点 body 末尾（与图片/视频 mention 行为对齐）
  if (
    sourceItem.item_type === 'text' && targetItem.item_type === 'text'
  ) {
    const sourceBody = String(sourceItem.content_json?.body || sourceItem.content_json?.text || '').trim()
    if (!sourceBody) return
    const targetContent = targetItem.content_json || {}
    const targetBody = String(targetContent.body || targetContent.text || '')
    // 用纯文本比较做幂等，避免重复连线导致内容反复追加
    const sourcePlain = sourceBody.replace(/<[^>]+>/g, '').trim()
    const targetPlain = targetBody.replace(/<[^>]+>/g, '').trim()
    if (!sourcePlain || targetPlain.includes(sourcePlain)) return
    const newBody = targetBody ? `${targetBody}<div>${sourceBody}</div>` : sourceBody
    try {
      const updated = await updateItem(targetId, {
        content_json: { ...targetContent, body: newBody },
      })
      if (updated?.content_json) updateNodeData(targetId, { content_json: updated.content_json })
    } catch (e) {
      // 引用写入失败不影响连线本身
    }
    return
  }

  // 文本 → 视频/图片：把源节点正文作为文本片段追加到目标 prompt_tokens 末尾，
  // 让视频/图片 prompt 编辑器立刻显示该文本，并参与后续生成的 prompt 拼装
  if (
    sourceItem.item_type === 'text'
    && (targetItem.item_type === 'video' || targetItem.item_type === 'image')
  ) {
    const sourcePlain = String(sourceItem.content_json?.body || sourceItem.content_json?.text || '')
      .replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim()
    if (!sourcePlain) return
    const contentJson = targetItem.content_json || {}
    const tokens = Array.isArray(contentJson.prompt_tokens) ? contentJson.prompt_tokens : []
    // 幂等：已有相同文本片段则不再追加
    if (tokens.some((t) => t.type === 'text' && (t.value || '').trim() === sourcePlain)) return
    const lastTextIdx = tokens.reduce((acc, t, i) => (t.type === 'text' ? i : acc), -1)
    let nextTokens
    if (lastTextIdx >= 0) {
      // 已有文本片段：合并到末尾，避免出现多个连续 text token
      const merged = tokens.slice()
      merged[lastTextIdx] = { type: 'text', value: `${merged[lastTextIdx].value || ''} ${sourcePlain}`.trim() }
      nextTokens = merged
    } else {
      nextTokens = [...tokens, { type: 'text', value: sourcePlain }]
    }
    const plainText = nextTokens.map((t) => {
      if (t.type === 'mention') {
        const role = t.node_type === 'image' && t.role ? `#${t.role}` : ''
        return `[${t.node_title || t.node_id || '节点'}${role}]`
      }
      return t.value || ''
    }).join('')
    try {
      const updated = await updateItem(targetId, {
        content_json: {
          ...contentJson,
          prompt_tokens: nextTokens,
          prompt_plain_text: plainText,
          prompt: plainText,
        },
      })
      if (updated?.content_json) updateNodeData(targetId, { content_json: updated.content_json })
    } catch (e) {
      // 引用写入失败不影响连线本身
    }
    return
  }

  // source 不是 text：上方已 return；这里不再处理
}

// 视频参考资产数量限制（对齐短视频页面 INPUT_LIMITS）
const VIDEO_REF_LIMITS = { maxImages: 9, maxVideos: 3, maxAudios: 3, maxTotal: 12, maxAudioDuration: 15, maxVideoDuration: 15 }

/**
 * 统计视频节点已有连线中各类型资产的数量
 */
function countVideoRefAssets(videoItemId) {
  const items = currentDocument.value?.items || []
  const conns = currentDocument.value?.connections || []
  const upstreamConnIds = conns.filter((c) => c.target_item_id === videoItemId)
  const upstreamItems = upstreamConnIds
    .map((c) => items.find((i) => i.id === c.source_item_id))
    .filter(Boolean)
  let images = 0, videos = 0, audios = 0, audioDuration = 0, videoDuration = 0
  for (const item of upstreamItems) {
    const t = (item.item_type || '').toLowerCase()
    if (t === 'image') images++
    else if (t === 'video') {
      videos++
      const dur = item.last_output_json?.duration || item.content_json?.duration || 0
      videoDuration += (typeof dur === 'number' ? dur : 0)
    } else if (t === 'audio') {
      audios++
      const dur = item.last_output_json?.duration || item.content_json?.duration || 0
      audioDuration += (typeof dur === 'number' ? dur : 0)
    }
  }
  return { images, videos, audios, total: images + videos + audios, audioDuration, videoDuration }
}

/**
 * 校验视频参考资产是否超限
 */
function checkVideoRefLimit(current, addType, addCount = 1, addDuration = 0) {
  if (current.total + addCount > VIDEO_REF_LIMITS.maxTotal) {
    return `视频参考资产总数不能超过 ${VIDEO_REF_LIMITS.maxTotal} 个`
  }
  if (addType === 'image' && current.images + addCount > VIDEO_REF_LIMITS.maxImages) {
    return `图片参考不能超过 ${VIDEO_REF_LIMITS.maxImages} 张`
  }
  if (addType === 'video' && current.videos + addCount > VIDEO_REF_LIMITS.maxVideos) {
    return `视频参考不能超过 ${VIDEO_REF_LIMITS.maxVideos} 个`
  }
  if (addType === 'video' && current.videoDuration + addDuration > VIDEO_REF_LIMITS.maxVideoDuration) {
    return `视频总时长不能超过 ${VIDEO_REF_LIMITS.maxVideoDuration}s`
  }
  if (addType === 'audio' && current.audios + addCount > VIDEO_REF_LIMITS.maxAudios) {
    return `音频参考不能超过 ${VIDEO_REF_LIMITS.maxAudios} 个`
  }
  if (addType === 'audio' && current.audioDuration + addDuration > VIDEO_REF_LIMITS.maxAudioDuration) {
    return `音频总时长不能超过 ${VIDEO_REF_LIMITS.maxAudioDuration}s`
  }
  return null
}

// ── 连接拖拽空抛 → 弹出"引用该节点生成"新建框 ──────────────
// dragConnected：本次拖拽是否已成功建立连线（onConnect 置 true）
// pendingConn：记录拖拽起点 nodeId 与松开位置的 flow 坐标
const dragConnected = ref(false)
const pendingConn = ref({ sourceId: null, flowPos: null })
const connCreateMenu = ref({ visible: false, pos: { x: 0, y: 0 } })

// 拖拽连线开始：记录源节点 id，重置标志
function onConnectStart({ nodeId }) {
  pendingConn.value.sourceId = nodeId || null
  dragConnected.value = false
}

// 拖拽连线结束：若未成功连接（空抛）且源不是组节点，在松开位置弹出新建框
function onConnectEnd(event) {
  // 成功连接时 connect 事件已把 dragConnected 置 true；组节点 source 不弹此菜单
  if (dragConnected.value) return
  const sourceId = pendingConn.value.sourceId
  if (!sourceId) return
  // Vue Flow 的 connect-end 事件可能是 { event } 包裹，也可能是原生 event
  const native = event?.event || event
  const sx = native?.clientX ?? 0
  const sy = native?.clientY ?? 0
  // 把屏幕坐标转换为画布坐标，用于稍后创建节点定位
  pendingConn.value.flowPos = screenToFlowCoordinate({ x: sx, y: sy })
  connCreateMenu.value = { visible: true, pos: { x: sx, y: sy } }
}

// 关闭新建框
function closeConnCreateMenu() {
  connCreateMenu.value.visible = false
}

// 选中某类型 → 建节点 + 连线 + 引用源节点内容 + 自动进入编辑态
async function createConnectedNode(itemType) {
  closeConnCreateMenu()
  const sourceId = pendingConn.value.sourceId
  const pos = pendingConn.value.flowPos
  if (!sourceId || !pos) return
  if (creatingItem.value) return
  pushHistory()
  creatingItem.value = true
  try {
    // 1. 在松开位置创建新节点
    const created = await addItem({
      item_type: itemType,
      title: '',
      position_x: Math.round(pos.x),
      position_y: Math.round(pos.y),
      width: 240,
      height: 120,
    })
    appendFlowNode({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      data: { ...created },
    })

    // 2. 连线 源节点 → 新节点
    //    - 组合节点 source：后端不允许 group 直连，展开组内每个合法子节点逐个连到新节点
    //    - 其余 source：直接连一条线（createSingleConnection 内部已调用 addUpstreamReference 引用源内容）
    const sourceItem = currentDocument.value?.items?.find((i) => i.id === sourceId)
    if (sourceItem?.item_type === 'group') {
      await connectGroupToTarget(sourceItem, created.id, created.item_type, 'right', 'left')
    } else {
      await createSingleConnection(sourceId, created.id, 'right', 'left')
    }

    // 3. 自动进入新节点的编辑态
    await nextTick()
    editingNodeId.value = created.id
  } catch (e) {
    // request 拦截器已弹错误提示
  } finally {
    creatingItem.value = false
    pendingConn.value = { sourceId: null, flowPos: null }
  }
}

async function onConnect(conn) {
  // 标记本次拖拽已成功建立连线，供 onConnectEnd 判断是否为"空抛"
  dragConnected.value = true
  pushHistory()

  const sourceItem = currentDocument.value?.items?.find((i) => i.id === conn.source)
  const targetItem = currentDocument.value?.items?.find((i) => i.id === conn.target)

  // 组节点作为 source：后端不允许 group 直连，展开组内每个合法子节点 → 目标节点的单独连线
  if (sourceItem?.item_type === 'group') {
    await connectGroupToTarget(sourceItem, conn.target, targetItem?.item_type, conn.sourceHandle || 'right', conn.targetHandle || 'left')
    return
  }

  // 普通连线→视频：校验资产数量与同步状态
  if (targetItem?.item_type === 'video' && (sourceItem?.item_type === 'image' || sourceItem?.item_type === 'video' || sourceItem?.item_type === 'audio')) {
    // 已创建资产但未同步的图片/视频节点不允许连线到视频
    if (sourceItem.item_type === 'image' || sourceItem.item_type === 'video') {
      const out = sourceItem.last_output_json || {}
      const hasOutput = !!(out.url || out.image_url || out.video_url)
      if (hasOutput && !isItemSyncedToVolcano(sourceItem)) {
        ElMessage.error('请先同步至火山再使用')
        return
      }
    }
    // 资产数量校验
    const current = countVideoRefAssets(conn.target)
    const dur = sourceItem.last_output_json?.duration || sourceItem.content_json?.duration || 0
    const err = checkVideoRefLimit(current, sourceItem.item_type, 1, typeof dur === 'number' ? dur : 0)
    if (err) {
      ElMessage.error(err)
      return
    }
  }

  await createSingleConnection(conn.source, conn.target, conn.sourceHandle || 'right', conn.targetHandle || 'left')
}

async function createSingleConnection(sourceId, targetId, sourceHandle = 'right', targetHandle = 'left') {
  const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
  flowEdges.value = [...flowEdges.value, {
    id: tempId,
    source: sourceId,
    target: targetId,
    sourceHandle,
    targetHandle,
    animated: true,
  }]
  try {
    const created = await addConnection({
      source_item_id: sourceId,
      target_item_id: targetId,
      source_handle: sourceHandle,
      target_handle: targetHandle,
    })
    const realId = created?.id
    if (!realId) throw new Error('后端未返回连线 ID')
    flowEdges.value = flowEdges.value.map((e) =>
      e.id === tempId ? { ...e, id: realId, animated: false } : e
    )
    try {
      await addUpstreamReference(sourceId, targetId)
    } catch (e) {
      // 不影响连线本身
    }
  } catch (e) {
    flowEdges.value = flowEdges.value.filter((e) => e.id !== tempId)
  }
}

// 组合节点连线：后端不允许 group 直接作为连线源，故展开组内每个合法子节点 → target 的单独连线。
// 复用于：① 拖拽连线 group→目标节点；② group 空抛建新节点后 group→新节点。
// 类型白名单与视频参考资产数量校验均与后端 ALLOWED_CONNECTION_TARGETS / VIDEO_REF_LIMITS 保持一致。
async function connectGroupToTarget(groupItem, targetId, targetItemType, sourceHandle = 'right', targetHandle = 'left') {
  const items = currentDocument.value?.items || []
  const children = items.filter((i) => i.parent_id === groupItem.id && i.item_type !== 'group')
  if (!children.length) {
    ElMessage.warning('组内没有可连线的子节点')
    return { success: 0, fail: 0 }
  }
  // 与后端 ALLOWED_CONNECTION_TARGETS 保持一致
  const ALLOWED = { text: ['text', 'image', 'video'], image: ['image', 'video'], audio: ['video'], video: ['video'] }
  // 视频目标：先预检资产数量，一次性告知超限
  if (targetItemType === 'video') {
    const current = countVideoRefAssets(targetId)
    let addImages = 0, addVideos = 0, addAudios = 0, addAudioDur = 0, addVideoDur = 0
    for (const child of children) {
      const allowed = ALLOWED[child.item_type] || []
      if (!allowed.includes('video')) continue
      if (flowEdges.value.some((e) => e.source === child.id && e.target === targetId)) continue
      // 已创建资产但未同步的跳过（不计入新增）
      if ((child.item_type === 'image' || child.item_type === 'video')) {
        const out = child.last_output_json || {}
        const hasOutput = !!(out.url || out.image_url || out.video_url)
        if (hasOutput && !isItemSyncedToVolcano(child)) continue
      }
      if (child.item_type === 'image') addImages++
      else if (child.item_type === 'video') {
        addVideos++
        const dur = child.last_output_json?.duration || child.content_json?.duration || 0
        addVideoDur += (typeof dur === 'number' ? dur : 0)
      } else if (child.item_type === 'audio') {
        addAudios++
        const dur = child.last_output_json?.duration || child.content_json?.duration || 0
        addAudioDur += (typeof dur === 'number' ? dur : 0)
      }
    }
    // 逐类型校验
    const err = checkVideoRefLimit(current, 'image', addImages) || checkVideoRefLimit(current, 'video', addVideos, addVideoDur) || checkVideoRefLimit(current, 'audio', addAudios, addAudioDur)
      || (current.total + addImages + addVideos + addAudios > VIDEO_REF_LIMITS.maxTotal ? `视频参考资产总数不能超过 ${VIDEO_REF_LIMITS.maxTotal} 个` : null)
    if (err) {
      ElMessage.error(err)
      return { success: 0, fail: children.length }
    }
  }
  let success = 0
  let fail = 0
  for (const child of children) {
    const allowed = ALLOWED[child.item_type] || []
    if (targetItemType && !allowed.includes(targetItemType)) { fail++; continue }
    if (targetItemType === 'video' && (child.item_type === 'image' || child.item_type === 'video')) {
      const out = child.last_output_json || {}
      const hasOutput = !!(out.url || out.image_url || out.video_url)
      if (hasOutput && !isItemSyncedToVolcano(child)) { fail++; continue }
    }
    if (flowEdges.value.some((e) => e.source === child.id && e.target === targetId)) { fail++; continue }
    try {
      await createSingleConnection(child.id, targetId, sourceHandle, targetHandle)
      success++
    } catch (_) { fail++ }
  }
  if (success > 0) {
    ElMessage.success(`已为组内 ${success} 个节点创建连线` + (fail > 0 ? `，${fail} 个跳过` : ''))
  } else {
    ElMessage.warning('组内没有可连线的子节点（类型不匹配、未同步或连线已存在）')
  }
  return { success, fail }
}

const dragStopTimers = new Map()

function onNodeDragStop(event) {
  const node = event?.node
  if (!node) return
  if (dragStopTimers.has(node.id)) clearTimeout(dragStopTimers.get(node.id))
  dragStopTimers.set(
    node.id,
    setTimeout(async () => {
      dragStopTimers.delete(node.id)
      try {
        await updateItem(node.id, {
          position_x: Math.round(node.position.x),
          position_y: Math.round(node.position.y),
        })
        const item = currentDocument.value?.items?.find((i) => i.id === node.id)
        if (item) {
          item.position_x = Math.round(node.position.x)
          item.position_y = Math.round(node.position.y)
        }
      } catch (e) {}
    }, 300)
  )
}

async function deleteSelection() {
  const selectedNodeIds = flowNodes.value.filter((n) => n.selected).map((n) => n.id)
  const selectedEdgeIds = flowEdges.value.filter((e) => e.selected).map((e) => e.id)
  if (selectedNodeIds.length === 0 && selectedEdgeIds.length === 0) return

  // 删除连线需要二次确认
  if (selectedEdgeIds.length > 0) {
    edgeDeleteTargetId.value = selectedEdgeIds[0]
    edgeDeleteTargetIds.value = selectedEdgeIds
    edgeDeleteConfirmVisible.value = true
    return
  }

  for (const id of selectedNodeIds) {
    const node = flowNodes.value.find((n) => n.id === id)
    const isGroup = node?.type === 'group'
    try {
      await removeItem(id)
      // 删除 group 时：前端子节点的 parentNode 需清空（避免 UI 残留），并保留位置
      if (isGroup) {
        flowNodes.value = flowNodes.value
          .filter((n) => n.id !== id)
          .map((n) => {
            if (n.parentNode === id) {
              const absX = Math.round(n.computedPosition?.x ?? n.position?.x ?? 0)
              const absY = Math.round(n.computedPosition?.y ?? n.position?.y ?? 0)
              return {
                ...n,
                parentNode: undefined,
                extent: undefined,
                position: { x: absX, y: absY },
              }
            }
            return n
          })
      } else {
        flowNodes.value = flowNodes.value.filter((n) => n.id !== id)
      }
      flowEdges.value = flowEdges.value.filter(
        (e) => e.source !== id && e.target !== id
      )
    } catch (e) {}
  }
}

// 把源节点从目标节点的 prompt_tokens 中移除，实现"断开连线后自动取消引用"
async function removeUpstreamReference(sourceId, targetId) {
  if (!sourceId || !targetId) return
  const targetItem = currentDocument.value?.items?.find((i) => i.id === targetId)
  if (!targetItem) return
  const contentJson = targetItem.content_json || {}
  const tokens = Array.isArray(contentJson.prompt_tokens) ? contentJson.prompt_tokens : []
  const nextTokens = tokens.filter((t) => !(t.type === 'mention' && t.node_id === sourceId))
  if (nextTokens.length === tokens.length) return
  const plainText = nextTokens.map((t) => {
    if (t.type === 'mention') {
      const role = t.node_type === 'image' && t.role ? `#${t.role}` : ''
      return `[${t.node_title || t.node_id || '节点'}${role}]`
    }
    return t.value || ''
  }).join('')
  try {
    const updated = await updateItem(targetId, {
      content_json: {
        ...contentJson,
        prompt_tokens: nextTokens,
        prompt_plain_text: plainText,
        prompt: plainText,
      },
    })
    if (updated?.content_json) {
      updateNodeData(targetId, { content_json: updated.content_json })
    }
  } catch (e) {
    // 取消引用失败不影响连线删除
  }
}

async function handleDeleteEdge(edgeId) {
  const edge = flowEdges.value.find((e) => e.id === edgeId)
  if (!edge) return
  edgeDeleteTargetId.value = edgeId
  edgeDeleteTargetIds.value = [edgeId]
  edgeDeleteConfirmVisible.value = true
}

async function doDeleteEdge() {
  const edgeIds = edgeDeleteTargetIds.value
  if (!edgeIds || edgeIds.length === 0) {
    edgeDeleteConfirmVisible.value = false
    edgeDeleteTargetId.value = null
    edgeDeleteTargetIds.value = []
    return
  }
  pushHistory()
  for (const edgeId of edgeIds) {
    const edge = flowEdges.value.find((e) => e.id === edgeId)
    if (!edge) continue
    try {
      await removeConnection(edgeId)
      flowEdges.value = flowEdges.value.filter((e) => e.id !== edgeId)
      try {
        await removeUpstreamReference(edge.source, edge.target)
      } catch (e) {
        // 引用移除失败不阻止连线删除
      }
    } catch (e) {}
  }
  edgeDeleteConfirmVisible.value = false
  edgeDeleteTargetId.value = null
  edgeDeleteTargetIds.value = []
}

// 点击节点编辑面板引用缩略图上的"移除引用"按钮：
// 断开"被引用节点(source) → 当前编辑节点(target)"的连线，并同步清理 prompt_tokens 中的 mention。
// 与 doDeleteEdge 互为反向链路（删连线 → 取消引用），此处不弹删除确认框，因为 × 按钮已是明确意图。
async function onUnlinkReference(sourceId) {
  const targetId = editingNodeId.value
  if (!sourceId || !targetId) return
  // 优先精确匹配 source=被引用节点；当被引用节点是 group 的展开子节点时，
  // 连线的 source 实际是其 parent_id，兜底再按 parent_id 匹配一次。
  let edge = flowEdges.value.find((e) => e.source === sourceId && e.target === targetId)
  if (!edge) {
    const refItem = (currentDocument.value?.items || []).find((i) => i.id === sourceId)
    const parentId = refItem?.parent_id
    if (parentId) {
      edge = flowEdges.value.find((e) => e.source === parentId && e.target === targetId)
    }
  }
  if (!edge) return
  pushHistory()
  try {
    await removeConnection(edge.id)
  } catch (e) {
    // 连线可能已被删除，忽略
  }
  flowEdges.value = flowEdges.value.filter((e) => e.id !== edge.id)
  try {
    await removeUpstreamReference(sourceId, targetId)
  } catch (e) {
    // prompt_tokens 清理失败不阻塞连线删除
  }
}

function onNodeClick(event) {
  const node = event?.node
  if (!node) return
  // group 节点不弹内容编辑面板
  if (node.type === 'group') {
    editingNodeId.value = null
    return
  }
  editingNodeId.value = node.id
}

function onNodeContextMenu(event) {
  const node = event?.node
  if (!node) return
  const native = event?.event
  const x = native?.clientX ?? 0
  const y = native?.clientY ?? 0
  contextMenuNodeId.value = node.id
  contextMenuItemType.value = node.type || node.data?.item_type || 'text'
  contextMenuPosition.value = { x, y }
  contextMenuVisible.value = true
  // 同时打开节点编辑弹框（按需求：右键时两个弹框都弹出，操作菜单在顶层）
  editingNodeId.value = node.id
}

function onPaneClick() {
  // 点击画布空白处：收起编辑浮层和右键菜单
  contextMenuVisible.value = false
  paneContextMenuVisible.value = false
  if (editingNodeId.value) closeEditor()
}

function onPaneContextMenu(event) {
  // VueFlow 1.x 直接传原生 MouseEvent；兼容 { event } 包装结构
  const native = event?.event || event
  const x = native?.clientX ?? 0
  const y = native?.clientY ?? 0
  paneContextMenuPosition.value = { x, y }
  paneContextMenuVisible.value = true
}

async function onPaneContextMenuAction(action) {
  paneContextMenuVisible.value = false
  switch (action) {
    case 'upload':
      fileInputRef.value?.click()
      break
    case 'batch-save-asset':
      if (batchSaveCandidates.value.length === 0) {
        ElMessage.info('暂无可保存到资产中心的资产')
        break
      }
      batchSaveDialog.candidateCount = batchSaveCandidates.value.length
      batchSaveDialog.visible = true
      break
    case 'create-text':
      await addNodeAt('text', paneContextMenuPosition.value)
      break
    case 'create-image':
      await addNodeAt('image', paneContextMenuPosition.value)
      break
    case 'create-video':
      await addNodeAt('video', paneContextMenuPosition.value)
      break
    case 'create-audio':
      await addNodeAt('audio', paneContextMenuPosition.value)
      break
    case 'paste':
      await pasteNode(paneContextMenuPosition.value)
      break
    case 'undo':
      undo()
      break
    case 'redo':
      redo()
      break
    default:
      break
  }
}

function onFileInputChange(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (files.length === 0) return
  // 在视口中心创建节点并上传
  const cx = window.innerWidth / 2
  const cy = window.innerHeight / 2
  const dropPos = screenToFlowCoordinate({ x: cx, y: cy })
  pushHistory()
  ;(async () => {
    for (let i = 0; i < files.length; i += 1) {
      const file = files[i]
      const nodeType = pickNodeTypeForFile(file)
      if (!nodeType) {
        ElMessage.warning(`不支持的文件类型：${file.name}`)
        continue
      }
      const offsetPos = { x: dropPos.x + i * 30, y: dropPos.y + i * 30 }
      // 空白处上传：不命中现有节点
      // eslint-disable-next-line no-await-in-loop
      await processDroppedFile(file, nodeType, null, offsetPos)
    }
  })()
}

const canPaste = computed(() => copiedNodes.value.length > 0)
const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

function snapshotCanvas() {
  return {
    nodes: flowNodes.value.map((n) => ({
      id: n.id,
      type: n.type,
      position: { ...n.position },
      data: { ...n.data },
      parentNode: n.parentNode || undefined,
      extent: n.extent || undefined,
      width: n.width || undefined,
      height: n.height || undefined,
      selectable: n.selectable ?? undefined,
    })),
    edges: flowEdges.value.map((e) => ({ ...e })),
    items: (currentDocument.value?.items || []).map((it) => ({
      ...it,
      content_json: it.content_json ? JSON.parse(JSON.stringify(it.content_json)) : null,
      last_output_json: it.last_output_json ? JSON.parse(JSON.stringify(it.last_output_json)) : null,
    })),
    connections: (currentDocument.value?.connections || []).map((c) => ({ ...c })),
  }
}

function pushHistory() {
  undoStack.value.push(snapshotCanvas())
  if (undoStack.value.length > 50) undoStack.value.shift()
  redoStack.value = []
}

// 用于比较两个 item 是否在可持久化字段上相等
const ITEM_PERSIST_FIELDS = [
  'title', 'position_x', 'position_y', 'width', 'height', 'z_index',
  'content_json', 'generation_config_json', 'last_output_json',
  'last_run_status', 'last_run_error', 'parent_id', 'asset_tag',
  'voice_url', 'voice_cos_key',
]
function jsonSame(a, b) {
  if (a === b) return true
  try {
    return JSON.stringify(a) === JSON.stringify(b)
  } catch (_) {
    return false
  }
}
function itemPersistEqual(a, b) {
  for (const k of ITEM_PERSIST_FIELDS) {
    if (!jsonSame(a?.[k], b?.[k])) return false
  }
  return true
}
function buildItemUpdatePayload(it) {
  const p = {
    title: it.title ?? '',
    position_x: it.position_x ?? 0,
    position_y: it.position_y ?? 0,
    width: it.width ?? 240,
    height: it.height ?? 120,
    z_index: it.z_index ?? 0,
    content_json: it.content_json ?? null,
    generation_config_json: it.generation_config_json ?? null,
    last_output_json: it.last_output_json ?? null,
    last_run_status: it.last_run_status ?? 'idle',
    last_run_error: it.last_run_error ?? null,
    parent_id: it.parent_id || '',
    asset_tag: it.asset_tag || '',
    voice_url: it.voice_url || '',
    voice_cos_key: it.voice_cos_key || '',
  }
  return p
}
function buildItemCreatePayload(it, idRemap) {
  const parentId = it.parent_id ? (idRemap[it.parent_id] || it.parent_id) : null
  return {
    item_type: it.item_type,
    title: it.title ?? '',
    position_x: it.position_x ?? 0,
    position_y: it.position_y ?? 0,
    width: it.width ?? 240,
    height: it.height ?? 120,
    z_index: it.z_index ?? 0,
    content_json: it.content_json ?? null,
    generation_config_json: it.generation_config_json ?? null,
    parent_id: parentId || undefined,
    asset_tag: it.asset_tag || undefined,
    voice_url: it.voice_url || undefined,
    voice_cos_key: it.voice_cos_key || undefined,
  }
}

// 计算两个快照之间的差异并持久化到后端
// from = 当前后端状态（编辑后），to = 目标后端状态（撤销/重做后的样子）
// 顺序：删 → 建 → 改
//   删在前：把 from 多余的节点先干掉（连带 cascade connection / 子节点 parent_id）
//   建在中：撤销"解组"等场景需要先重建 group 才能拿到新 id，用于后续 update 的 parent_id 重映射
//   改在后：此时 idRemap 已就绪，可以正确处理"子节点 parent_id 指向新建的 group"
async function persistCanvasDiff(from, to) {
  const fromItems = new Map(from.items.map((it) => [it.id, it]))
  const toItems = new Map(to.items.map((it) => [it.id, it]))

  const idsToDelete = from.items.filter((it) => !toItems.has(it.id)).map((it) => it.id)
  const itemsToUpdate = to.items.filter((it) => {
    const b = fromItems.get(it.id)
    return b && !itemPersistEqual(b, it)
  })
  const itemsToCreate = to.items.filter((it) => !fromItems.has(it.id))

  // 1. 删（连带的 connection 由后端 cascade）
  for (const id of idsToDelete) {
    try { await removeItem(id) } catch (e) { console.warn('undo/redo: delete item failed', e) }
  }

  // 2. 建（按依赖顺序：父节点先于子节点；idRemap 记录 oldId → newId）
  const idRemap = {}
  let remaining = [...itemsToCreate]
  let safety = 0
  while (remaining.length > 0 && safety < 20) {
    safety += 1
    const still = []
    for (const it of remaining) {
      const parentPending = it.parent_id
        && itemsToCreate.some((x) => x.id === it.parent_id)
        && !idRemap[it.parent_id]
      if (parentPending) { still.push(it); continue }
      try {
        const created = await addItem(buildItemCreatePayload(it, idRemap))
        idRemap[it.id] = created.id
      } catch (e) {
        console.warn('undo/redo: create item failed', e)
      }
    }
    if (still.length === remaining.length) {
      // 一轮下来无进展（可能是父节点创建失败）：直接按当前顺序创建，避免死循环
      for (const it of still) {
        try {
          const created = await addItem(buildItemCreatePayload(it, idRemap))
          idRemap[it.id] = created.id
        } catch (e) { console.warn('undo/redo: create item failed', e) }
      }
      break
    }
    remaining = still
  }

  // 3. 改（应用 idRemap：parent_id 若指向新建的 group，用新 id）
  for (const it of itemsToUpdate) {
    const payload = buildItemUpdatePayload(it)
    if (it.parent_id && idRemap[it.parent_id]) {
      payload.parent_id = idRemap[it.parent_id]
    }
    try { await updateItem(it.id, payload) } catch (e) { console.warn('undo/redo: update item failed', e) }
  }

  // 连线：删除 + 新建（id 是后端生成，无法原 id 还原）
  const fromConns = new Map(from.connections.map((c) => [c.id, c]))
  const toConns = new Map(to.connections.map((c) => [c.id, c]))
  const connsToDelete = from.connections.filter((c) => !toConns.has(c.id))
  const connsToCreate = to.connections.filter((c) => !fromConns.has(c.id))

  for (const c of connsToDelete) {
    try { await removeConnection(c.id) } catch (e) { /* 可能已被 item 级联删除，忽略 */ }
  }
  for (const c of connsToCreate) {
    const sourceId = idRemap[c.source_item_id] || c.source_item_id
    const targetId = idRemap[c.target_item_id] || c.target_item_id
    try {
      await addConnection({
        source_item_id: sourceId,
        target_item_id: targetId,
        source_handle: c.source_handle || 'right',
        target_handle: c.target_handle || 'left',
      })
    } catch (e) { console.warn('undo/redo: create connection failed', e) }
  }
}

const undoPersisting = ref(false)
async function undo() {
  if (undoStack.value.length === 0) return
  if (undoPersisting.value) return
  const current = snapshotCanvas()
  const prev = undoStack.value.pop()
  undoPersisting.value = true
  try {
    await persistCanvasDiff(current, prev)
    await openDocument(documentId)
    await forceRebuildFlow()
    // 撤销/重做后清空选中状态：原 snapshot 里可能含 selected:true，
    // 重建后 flowNodes 默认未选中，但保险起见显式清一次，避免浮动按钮/选中高亮残留。
    try { removeSelectedNodes?.() } catch (_) {}
    redoStack.value.push(current)
    ElMessage.success('已撤销')
  } catch (e) {
    ElMessage.error('撤销失败，请刷新页面')
    console.error('undo failed', e)
  } finally {
    undoPersisting.value = false
  }
}

async function redo() {
  if (redoStack.value.length === 0) return
  if (undoPersisting.value) return
  const current = snapshotCanvas()
  const next = redoStack.value.pop()
  undoPersisting.value = true
  try {
    await persistCanvasDiff(current, next)
    await openDocument(documentId)
    await forceRebuildFlow()
    try { removeSelectedNodes?.() } catch (_) {}
    undoStack.value.push(current)
    ElMessage.success('已重做')
  } catch (e) {
    ElMessage.error('重做失败，请刷新页面')
    console.error('redo failed', e)
  } finally {
    undoPersisting.value = false
  }
}

async function addNodeAt(itemType, screenPos) {
  if (creatingItem.value) return
  const pos = screenPos
    ? screenToFlowCoordinate({ x: screenPos.x, y: screenPos.y })
    : computeSpawnPosition()
  pushHistory()
  creatingItem.value = true
  try {
    const created = await addItem({
      item_type: itemType,
      title: '',
      position_x: Math.round(pos.x),
      position_y: Math.round(pos.y),
      width: 240,
      height: 120,
    })
    appendFlowNode({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      data: { ...created },
    })
  } catch (e) {
    // request 拦截器已弹错误提示
  } finally {
    creatingItem.value = false
  }
}

async function pasteNode(screenPos) {
  // 优先用内存中的 copiedNodes；没有则尝试从剪贴板读取
  if (copiedNodes.value.length === 0) {
    try {
      const text = await navigator.clipboard?.readText?.()
      if (text) {
        const parsed = JSON.parse(text)
        if (parsed?.type === 'canvas-nodes' && parsed.nodes?.length) {
          copiedNodes.value = parsed.nodes
        } else if (parsed?.type === 'canvas-node') {
          copiedNodes.value = [parsed]
        }
      }
    } catch (e) {}
  }
  if (copiedNodes.value.length === 0) {
    ElMessage.warning('暂无可粘贴的节点')
    return
  }
  const basePos = screenPos
    ? screenToFlowCoordinate({ x: screenPos.x, y: screenPos.y })
    : computeSpawnPosition()
  pushHistory()
  creatingItem.value = true
  try {
    for (let i = 0; i < copiedNodes.value.length; i++) {
      const clip = copiedNodes.value[i]
      const pos = { x: basePos.x + i * 30, y: basePos.y + i * 30 }
      if (clip.item_type === 'group') {
        await pasteGroupNode(clip, pos)
      } else {
        const created = await addItem({
          item_type: clip.item_type,
          title: clip.title || '',
          content_json: clip.content_json || null,
          last_output_json: clip.last_output_json || null,
          last_run_status: clip.last_run_status || 'idle',
          position_x: Math.round(pos.x),
          position_y: Math.round(pos.y),
          width: 240,
          height: 120,
        })
        appendFlowNode({
          id: created.id,
          type: created.item_type,
          position: { x: created.position_x, y: created.position_y },
          data: { ...created },
        })
      }
    }
    const count = copiedNodes.value.length
    const hasGroup = copiedNodes.value.some((c) => c.item_type === 'group')
    ElMessage.success(count > 1 ? `已粘贴 ${count} 个节点` : (hasGroup ? '已粘贴组合（含子节点）' : '已粘贴节点'))
  } catch (e) {
    // request 拦截器已弹错误提示
  } finally {
    creatingItem.value = false
  }
}

// 粘贴组合节点：与 duplicateGroupNode 行为一致，但不复制外部入边（剪贴板里没存）
async function pasteGroupNode(clip, groupPos) {
  // 1) 建 group
  const newGroup = await addItem({
    item_type: 'group',
    title: clip.title || '',
    position_x: Math.round(groupPos.x),
    position_y: Math.round(groupPos.y),
    width: clip.width || 240,
    height: clip.height || 120,
    parent_id: null,
  })
  const newGroupId = newGroup.id

  // 2) 建子节点副本（保留相对位置）
  const children = Array.isArray(clip.children) ? clip.children : []
  const createdIds = []  // 与 children 同序，用于 internal_connections 的 idx 映射
  const newChildNodes = []
  for (const child of children) {
    const created = await addItem({
      item_type: child.item_type,
      title: child.title || '',
      content_json: child.content_json || null,
      last_output_json: child.last_output_json || null,
      last_run_status: child.last_run_status || 'idle',
      position_x: Math.round(child.rel_x ?? 0),
      position_y: Math.round(child.rel_y ?? 0),
      width: child.width || 240,
      height: child.height || 120,
      parent_id: newGroupId,
      asset_tag: child.asset_tag || null,
      voice_url: child.voice_url || null,
      voice_cos_key: child.voice_cos_key || null,
    })
    createdIds.push(created.id)
    newChildNodes.push({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      parentNode: newGroupId,
      extent: 'parent',
      data: { ...created },
    })
  }

  // 3) 整体替换 flowNodes：group 在前
  const groupFlowNode = {
    id: newGroupId,
    type: 'group',
    position: { x: newGroup.position_x, y: newGroup.position_y },
    width: newGroup.width || 240,
    height: newGroup.height || 120,
    data: { ...newGroup, child_count: children.length },
    selectable: true,
  }
  flowNodes.value = [...flowNodes.value, groupFlowNode, ...newChildNodes]

  // 4) 复刻组内连线
  const internalConns = Array.isArray(clip.internal_connections) ? clip.internal_connections : []
  for (const ic of internalConns) {
    const srcId = createdIds[ic.source_idx]
    const tgtId = createdIds[ic.target_idx]
    if (!srcId || !tgtId) continue
    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    flowEdges.value = [...flowEdges.value, {
      id: tempId,
      source: srcId,
      target: tgtId,
      sourceHandle: ic.source_handle || 'right',
      targetHandle: ic.target_handle || 'left',
      animated: true,
    }]
    try {
      const newConn = await addConnection({
        source_item_id: srcId,
        target_item_id: tgtId,
        source_handle: ic.source_handle || 'right',
        target_handle: ic.target_handle || 'left',
      })
      const realId = newConn?.id
      if (!realId) throw new Error('后端未返回连线 ID')
      flowEdges.value = flowEdges.value.map((e) =>
        e.id === tempId ? { ...e, id: realId, animated: false } : e
      )
    } catch (e) {
      flowEdges.value = flowEdges.value.filter((e) => e.id !== tempId)
    }
  }
}

async function onContextMenuAction(action, payload) {
  const nodeId = contextMenuNodeId.value
  contextMenuVisible.value = false
  if (!nodeId) return
  const item = currentDocument.value?.items?.find((i) => i.id === nodeId)
  if (!item) return
  switch (action) {
    case 'copy-node':
      await copyNodeToClipboard(item)
      break
    case 'copy-content':
      await copyNodeContentToClipboard(item)
      break
    case 'duplicate':
      await duplicateNode(nodeId)
      break
    case 'delete':
      nodeDeleteTargetId.value = nodeId
      nodeDeleteConfirmVisible.value = true
      break
    case 'save-asset':
      openSaveToAssetDialog(item)
      break
    case 'sync-volcano':
      await syncItemVolcano(nodeId)
      break
    case 'mark-asset':
      await markNodeAsset(nodeId, payload)
      break
    default:
      break
  }
}

async function markNodeAsset(nodeId, tag) {
  try {
    await updateItem(nodeId, { asset_tag: tag })
    const it = currentDocument.value?.items?.find((i) => i.id === nodeId)
    if (it) it.asset_tag = tag ?? null
    flowNodes.value = flowNodes.value.map((n) =>
      n.id === nodeId ? { ...n, data: { ...n.data, asset_tag: tag ?? null } } : n
    )
  } catch (e) {
    ElMessage.error('标记失败')
  }
}

function toggleAssetFilter() {
  assetFilter.value = assetFilter.value === null ? true : null
}

function isNodeDimmed(node) {
  if (assetFilter.value === null) return false
  return !node?.data?.asset_tag
}

function openSaveToAssetDialog(item) {
  if (!itemHasOutput(item)) {
    ElMessage.warning('节点尚无可保存的资产')
    return
  }
  saveToAssetDialog.itemId = item.id
  saveToAssetDialog.itemType = item.item_type
  saveToAssetDialog.defaultName = item.title || ''
  saveToAssetDialog.visible = true
}

// 单节点保存到资产中心成功：本地同步状态，让角标立刻显示
function onSingleSavedToAsset() {
  const id = saveToAssetDialog.itemId
  if (!id) return
  patchItemSavedToAssetCenter(id, true)
}

// 批量保存到资产中心成功：批量更新本地状态
function onBatchSavedToAsset(data) {
  const savedIds = (data?.saved || []).map((s) => s.id)
  for (const id of savedIds) patchItemSavedToAssetCenter(id, true)
}

function patchItemSavedToAssetCenter(itemId, value) {
  const it = currentDocument.value?.items?.find((i) => i.id === itemId)
  if (it) it.saved_to_asset_center = !!value
  flowNodes.value = flowNodes.value.map((n) =>
    n.id === itemId ? { ...n, data: { ...n.data, saved_to_asset_center: !!value } } : n
  )
}

async function syncItemVolcano(nodeId) {
  if (!nodeId || syncingNodeIds.value.has(nodeId)) return
  syncingNodeIds.value = new Set(syncingNodeIds.value).add(nodeId)
  try {
    const { syncItemVolcano: storeSync } = useCanvasStore()
    await storeSync(nodeId)
    ElMessage.success('已同步至火山')
  } catch (e) {
    ElMessage.error(e?.message || '同步失败')
  } finally {
    const next = new Set(syncingNodeIds.value)
    next.delete(nodeId)
    syncingNodeIds.value = next
  }
}

async function onNodeSyncVolc(payload) {
  const nodeId = payload?.id
  if (nodeId) await syncItemVolcano(nodeId)
}

async function copySelectedNodes(selectedNodes) {
  copiedNodes.value = []
  for (const n of selectedNodes) {
    const item = currentDocument.value?.items?.find((i) => i.id === n.id)
    if (item) await buildClipboardNode(item)
  }
  const count = copiedNodes.value.length
  const hasGroup = copiedNodes.value.some((c) => c.item_type === 'group')
  ElMessage.success(count > 1 ? `已复制 ${count} 个节点` : (hasGroup ? '已复制组合（含子节点）' : '已复制节点'))
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(JSON.stringify({ type: 'canvas-nodes', nodes: copiedNodes.value }))
    }
  } catch (e) {}
}

// 构建单个节点的剪贴板数据并推入 copiedNodes
async function buildClipboardNode(item) {
  // 存到内存，作为粘贴时的数据源，同时 canPaste 立即为 true
  const base = {
    type: 'canvas-node',
    item_type: item.item_type,
    title: item.title || '',
    content_json: item.content_json ? JSON.parse(JSON.stringify(item.content_json)) : null,
    last_output_json: item.last_output_json ? JSON.parse(JSON.stringify(item.last_output_json)) : null,
    last_run_status: item.last_run_status || 'idle',
  }
  // 组合节点：把组内子节点 + 组内连线一起存入剪贴板，粘贴时整体复刻
  if (item.item_type === 'group') {
    const allItems = currentDocument.value?.items || []
    const conns = currentDocument.value?.connections || []
    const flowMap = new Map(flowNodes.value.map((n) => [n.id, n]))
    const children = allItems.filter((i) => i.parent_id === item.id)
    base.width = item.width || 240
    base.height = item.height || 120
    base.children = children.map((c) => {
      const fn = flowMap.get(c.id)
      const groupNode = flowMap.get(item.id)
      // 子节点在 flow 中的相对坐标（已经是相对 group 的）
      const relX = Math.round(fn?.position?.x ?? c.position_x ?? 0)
      const relY = Math.round(fn?.position?.y ?? c.position_y ?? 0)
      return {
        item_type: c.item_type,
        title: c.title || '',
        content_json: c.content_json ? JSON.parse(JSON.stringify(c.content_json)) : null,
        last_output_json: c.last_output_json ? JSON.parse(JSON.stringify(c.last_output_json)) : null,
        last_run_status: c.last_run_status || 'idle',
        width: c.width || 240,
        height: c.height || 120,
        asset_tag: c.asset_tag || null,
        voice_url: c.voice_url || null,
        voice_cos_key: c.voice_cos_key || null,
        rel_x: relX,
        rel_y: relY,
      }
    })
    const childIds = new Set(children.map((c) => c.id))
    base.internal_connections = conns
      .filter((c) => childIds.has(c.source_item_id) && childIds.has(c.target_item_id))
      .map((c) => ({
        source_idx: children.findIndex((x) => x.id === c.source_item_id),
        target_idx: children.findIndex((x) => x.id === c.target_item_id),
        source_handle: c.source_handle || 'right',
        target_handle: c.target_handle || 'left',
      }))
  }
  copiedNodes.value.push(base)
}

// 右键菜单单节点复制（兼容）
async function copyNodeToClipboard(item) {
  copiedNodes.value = []
  await buildClipboardNode(item)
  const hasGroup = item.item_type === 'group'
  ElMessage.success(hasGroup ? '已复制组合（含子节点）' : '已复制节点')
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(JSON.stringify({ type: 'canvas-nodes', nodes: copiedNodes.value }))
    }
  } catch (e) {}
}

async function copyNodeContentToClipboard(item) {
  try {
    const cj = item.content_json || {}
    const oj = item.last_output_json || {}
    let text = ''
    if (item.item_type === 'text') {
      text = cj.text || cj.prompt || ''
    } else {
      text = oj.url || cj.url || ''
    }
    if (!text) {
      ElMessage.warning('当前节点暂无可复制内容')
      return
    }
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    }
    ElMessage.success(item.item_type === 'text' ? '已复制文本' : '已复制链接')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

async function duplicateNode(nodeId) {
  const item = currentDocument.value?.items?.find((i) => i.id === nodeId)
  if (!item) return
  const sourceNode = flowNodes.value.find((n) => n.id === nodeId)
  if (creatingItem.value) return
  pushHistory()
  creatingItem.value = true
  try {
    if (item.item_type === 'group') {
      await duplicateGroupNode(item, sourceNode)
      ElMessage.success('已创建副本（含组内资产）')
      return
    }

    const created = await addItem({
      item_type: item.item_type,
      title: item.title ? `${item.title} 副本` : '',
      content_json: item.content_json || null,
      last_output_json: item.last_output_json || null,
      last_run_status: item.last_run_status || 'idle',
      position_x: Math.round((sourceNode?.position?.x ?? 0) + 60),
      position_y: Math.round((sourceNode?.position?.y ?? 0) + 60),
      width: 240,
      height: 120,
    })
    appendFlowNode({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      data: { ...created },
    })

    // 复制原节点的所有相关连线到副本：入边 X→原 → X→副本；出边 原→Y → 副本→Y
    await copyRelatedConnections([nodeId], [created.id])

    ElMessage.success('已创建副本')
  } catch (e) {
    // request 拦截器已弹错误提示
  } finally {
    creatingItem.value = false
  }
}

// 复制一组旧实体（节点或组+子节点）的所有相关连线到新实体：
//   - 入边 X→old → X→new（对端 X 不变）
//   - 出边 old→Y → new→Y（对端 Y 不变）
//   - 组场景：组内子节点之间的连线、子节点对组外的连线一并按 idMap 映射复制
// 自动去重，避免同一条连线被复制多次；跳过自连接。
async function copyRelatedConnections(oldIds, newIds) {
  if (!oldIds.length || oldIds.length !== newIds.length) return
  const oldToNew = new Map()
  for (let i = 0; i < oldIds.length; i++) oldToNew.set(oldIds[i], newIds[i])

  const allConns = currentDocument.value?.connections || []
  const processed = new Set()
  for (const c of allConns) {
    if (!oldToNew.has(c.source_item_id) && !oldToNew.has(c.target_item_id)) continue
    const newSource = oldToNew.get(c.source_item_id) || c.source_item_id
    const newTarget = oldToNew.get(c.target_item_id) || c.target_item_id
    if (newSource === newTarget) continue  // 自连接跳过
    const key = `${newSource}->${newTarget}`
    if (processed.has(key)) continue  // 已复制过跳过
    processed.add(key)

    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    flowEdges.value = [...flowEdges.value, {
      id: tempId,
      source: newSource,
      target: newTarget,
      sourceHandle: c.source_handle || 'right',
      targetHandle: c.target_handle || 'left',
      animated: true,
    }]
    try {
      const newConn = await addConnection({
        source_item_id: newSource,
        target_item_id: newTarget,
        source_handle: c.source_handle || 'right',
        target_handle: c.target_handle || 'left',
      })
      const realId = newConn?.id
      if (!realId) throw new Error('后端未返回连线 ID')
      flowEdges.value = flowEdges.value.map((e) =>
        e.id === tempId ? { ...e, id: realId, animated: false } : e
      )
    } catch (e) {
      flowEdges.value = flowEdges.value.filter((e) => e.id !== tempId)
    }
  }
}

// 组合节点副本：递归复制组内子节点 + 组内子节点之间的连线 + 组的外部入边
async function duplicateGroupNode(groupItem, groupSourceNode) {
  const groupAbsX = groupSourceNode?.position?.x ?? groupItem.position_x ?? 0
  const groupAbsY = groupSourceNode?.position?.y ?? groupItem.position_y ?? 0
  const offsetX = 60
  const offsetY = 60

  // 1) 建新 group 节点
  const newGroup = await addItem({
    item_type: 'group',
    title: groupItem.title ? `${groupItem.title} 副本` : '',
    position_x: Math.round(groupAbsX + offsetX),
    position_y: Math.round(groupAbsY + offsetY),
    width: groupItem.width || 240,
    height: groupItem.height || 120,
    parent_id: null,
  })
  const newGroupId = newGroup.id

  // 2) 拉取组内子节点 + 建副本（保留相对位置）；建立 id 映射
  const children = (currentDocument.value?.items || []).filter((i) => i.parent_id === groupItem.id)
  const idMap = new Map()  // oldId -> newId
  const newChildNodes = []
  for (const child of children) {
    const cNode = flowNodes.value.find((n) => n.id === child.id)
    const cRelX = cNode?.position?.x ?? child.position_x ?? 0
    const cRelY = cNode?.position?.y ?? child.position_y ?? 0
    const created = await addItem({
      item_type: child.item_type,
      title: child.title || '',
      content_json: child.content_json || null,
      last_output_json: child.last_output_json || null,
      last_run_status: child.last_run_status || 'idle',
      position_x: Math.round(cRelX),
      position_y: Math.round(cRelY),
      width: child.width || 240,
      height: child.height || 120,
      parent_id: newGroupId,
      asset_tag: child.asset_tag || null,
      voice_url: child.voice_url || null,
      voice_cos_key: child.voice_cos_key || null,
    })
    idMap.set(child.id, created.id)
    newChildNodes.push({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      parentNode: newGroupId,
      extent: 'parent',
      data: { ...created },
    })
  }

  // 3) 整体替换 flowNodes：group 在前（先注册父节点），子节点挂 parentNode
  const groupFlowNode = {
    id: newGroupId,
    type: 'group',
    position: { x: newGroup.position_x, y: newGroup.position_y },
    width: newGroup.width || 240,
    height: newGroup.height || 120,
    data: { ...newGroup, child_count: children.length },
    selectable: true,
  }
  flowNodes.value = [...flowNodes.value, groupFlowNode, ...newChildNodes]

  // 4) 复制所有相关连线：组内子节点之间 + 组的外部入/出边 + 组内子节点对组外的连线
  //    一次性按 idMap 映射复制（已自动去重 + 跳过自连接）
  const oldIds = [groupItem.id, ...children.map((c) => c.id)]
  const newIds = [newGroupId, ...newChildNodes.map((n) => n.id)]
  await copyRelatedConnections(oldIds, newIds)
}

function closeEditor() {
  // 关闭前确保最后一次改动已落库
  editingNodeId.value = null
}

async function onEditorDelete() {
  const itemId = editingNodeId.value
  if (!itemId) return
  nodeDeleteTargetId.value = itemId
  nodeDeleteConfirmVisible.value = true
}

async function doDeleteNode() {
  const itemId = nodeDeleteTargetId.value
  if (!itemId) return
  pushHistory()
  try {
    await removeItem(itemId)
    flowNodes.value = flowNodes.value.filter((n) => n.id !== itemId)
    flowEdges.value = flowEdges.value.filter((e) => e.source !== itemId && e.target !== itemId)
    editingNodeId.value = null
    nodeDeleteTargetId.value = null
    ElMessage.success('节点已删除')
  } catch (e) {
    // request 拦截器已弹错误提示
  }
}

async function onEditorSave(payload, itemIdFromEditor) {
  // 优先用 editor emit 携带的 itemId：closeEditor 把 editingNodeId 置空后会触发浮层 unmount，
  // unmount 期间 onBeforeUnmount 会再 emit 一次 save，此时 editingNodeId 已经是 null，
  // 必须从 payload 透传的 itemId 才能拿到正确的节点 id
  const itemId = itemIdFromEditor || editingNodeId.value
  if (!itemId) return
  editorSaving.value = true
  setNodeSaveStatus('saving')
  try {
    const updated = await updateItem(itemId, payload)
    // 用 updateNodeData 而不是直接索引赋值——后者不会触发 VueFlow 内部图状态同步，
    // 导致画布上节点的 data prop 不刷新（标题、其它字段都不会重渲染）
    // onSubmit 先 emit('save') 再 emit('submit')，onEditorSubmit 会立即把节点置 pending；
    // 此处 await updateItem 返回晚于该写入，updated.last_run_status 仍是 'idle'，直接整体回写
    // 会把 pending 覆盖回去，导致"生成中"遮罩不显示。这里显式剔除运行时状态字段，
    // 它们只由生成流程（提交/WS/轮询）维护。
    //
    // 同时剔除媒体输出字段（last_output_json / cover_url）：图片/视频是预签名 URL，
    // 后端每次返回的字符串都不同，若整体回写会让 video/img 的 src 变化 → 媒体重新加载
    // → 画面抖动。保存文本只应刷新 title/content_json，媒体输出由生成/上传流程单独维护。
    const {
      last_run_status: _s,
      last_run_error: _e,
      last_output_json: _o,
      cover_url: _c,
      ...safePatch
    } = updated || {}
    updateNodeData(itemId, safePatch)
    setNodeSaveStatus('saved')
  } catch (e) {
    setNodeSaveStatus('failed')
    // request 拦截器已弹错误提示
  } finally {
    editorSaving.value = false
  }
}

function setNodeSaveStatus(status) {
  if (nodeSaveStatusTimer) {
    clearTimeout(nodeSaveStatusTimer)
    nodeSaveStatusTimer = null
  }
  nodeSaveStatus.value = status
  // 终态停留 2.5s 后回到 idle，避免老状态长期挂在标题栏
  if (status === 'saved' || status === 'failed') {
    nodeSaveStatusTimer = setTimeout(() => {
      nodeSaveStatus.value = 'idle'
      nodeSaveStatusTimer = null
    }, 2500)
  }
}

async function onEditorSideAdd({ direction, itemType }) {
  const currentNode = flowNodes.value.find((n) => n.id === editingNodeId.value)
  if (!currentNode) return
  const fakeId = editingNodeId.value
  editingNodeId.value = null
  await handleQuickAdd({ id: fakeId, direction, itemType })
}

// ── 节点生成（阶段 3.1：文本节点） ─────────────────────
const generatingItems = reactive(new Set())  // 正在生成中的节点 id 集合
const generationPollTimers = new Map()       // item_id -> setTimeout handle
// 本组件发起的生成 tracking：itemId -> generation_id（API 返回前用 '__pending__' 占位）
// 用途：避免 WS 推送的历史/陈旧完成事件把刚设的 pending 覆盖；
// 同时保证当前真正在跑的 generation 完成时能立即 apply
const localPendingGen = reactive({})

function updateNodeData(itemId, patch) {
  const idx = flowNodes.value.findIndex((n) => n.id === itemId)
  if (idx < 0) return
  // 用整体数组替换触发 VueFlow 重新渲染（直接改 idx 在 VueFlow 内部 state 不可靠）
  const next = flowNodes.value.slice()
  next[idx] = {
    ...flowNodes.value[idx],
    data: { ...flowNodes.value[idx].data, ...patch },
  }
  flowNodes.value = next
  // 同步 VueFlow 内部图状态（驱使 GraphNode 重新渲染 data prop）
  if (typeof vfUpdateNodeData === 'function') {
    try {
      vfUpdateNodeData(itemId, (node) => ({ ...node.data, ...patch }))
    } catch (_) {
      // noop
    }
  }
}

async function onEditorSubmit({ prompt, prompt_tokens, prompt_plain_text, params }) {
  const itemId = editingNodeId.value
  if (!itemId) return
  const item = flowNodes.value.find((n) => n.id === itemId)
  if (!item) return
  const itemType = item.data?.item_type

  if (itemType !== 'text' && itemType !== 'image' && itemType !== 'video' && itemType !== 'audio') {
    ElMessage.warning('不支持的节点类型')
    return
  }

  if (itemType === 'audio') {
    ElMessage.info('音频节点暂不支持生成，请直接上传音频文件')
    return
  }

  generatingItems.add(itemId)
  // 占位标记：在 await API 返回前，阻止 WS 推送的历史完成事件把刚设的 pending 覆盖
  localPendingGen[itemId] = '__pending__'
  updateNodeData(itemId, { last_run_status: 'pending', last_run_error: null })
  // 提前关闭编辑浮层，让用户立刻看到画布节点上的"生成中"遮罩
  // （编辑浮层会遮挡画布节点，等 API 返回再关会让用户误以为没在生成）
  editingNodeId.value = null

  try {
    let resp
    if (itemType === 'text') {
      resp = await generateCanvasText(itemId, {
        prompt: prompt || prompt_plain_text || null,
        prompt_tokens: prompt_tokens || [],
        prompt_plain_text: prompt_plain_text || '',
        model: params?.model || null,
      })
    } else if (itemType === 'image') {
      resp = await generateCanvasImage(itemId, {
        prompt: prompt || prompt_plain_text || null,
        prompt_tokens: prompt_tokens || [],
        prompt_plain_text: prompt_plain_text || '',
        model: params?.model || null,
        ratio: params?.ratio || null,
        model_key: params?.model_key || null,
        image_style: params?.imageStyle || null,
      })
    } else {
      // video — 提交 prompt_tokens，由后端 collect_image_refs_by_role 解析首尾帧/参考图
      // 视频参数对齐 NodeEditorPanel.params 字段名：videoRatio/videoResolution/videoDuration
      resp = await generateCanvasVideo(itemId, {
        prompt: prompt || prompt_plain_text || null,
        prompt_tokens: prompt_tokens || [],
        prompt_plain_text: prompt_plain_text || '',
        model: params?.model || null,
        ratio: params?.videoRatio || params?.ratio || null,
        resolution: params?.videoResolution || null,
        duration: params?.videoDuration || null,
      })
    }
    const generationId = resp?.generation_id
    if (!generationId) throw new Error('未返回 generation_id')
    // 替换占位为真实 generation_id，WS 回调用它判断完成事件是否本次发起
    localPendingGen[itemId] = generationId
    ElMessage.success('已提交生成任务')
    // 启动轮询
    pollGeneration(itemId, generationId, itemType)
  } catch (e) {
    generatingItems.delete(itemId)
    delete localPendingGen[itemId]
    updateNodeData(itemId, { last_run_status: 'failed', last_run_error: '提交失败' })
  }
}

function onFocusReferenceItem(nodeId) {
  if (!nodeId || nodeId === editingNodeId.value) return
  const node = flowNodes.value.find((n) => n.id === nodeId)
  if (!node) return
  editingNodeId.value = node.id
}

function onOpenHistory() {
  const node = flowNodes.value.find((n) => n.id === editingNodeId.value)
  if (!node) return
  historyItemId.value = node.id
  historyItemType.value = node.data?.item_type || 'text'
  historyCurrentGenId.value = ''
  historyDrawerVisible.value = true
}

function onHistoryApplied({ itemId, item }) {
  // 应用历史版本后：把后端返回的 item 字段 patch 到 flowNodes + store
  if (!itemId || !item) return
  updateNodeData(itemId, {
    content_json: item.content_json,
    last_output_json: item.last_output_json,
    last_run_status: item.last_run_status,
    last_run_error: item.last_run_error,
  })
}

// ── 资产导入（上传 / 资产中心） ───────────────────────
function onOpenAssetPicker() {
  voicePickerMode.value = false
  voicePickerTargetId.value = null
  assetPickerVisible.value = true
}

function onOpenVoicePicker(payload) {
  const nodeId = payload?.id || editingNodeId.value
  if (!nodeId) return
  voicePickerMode.value = true
  voicePickerTargetId.value = nodeId
  assetPickerVisible.value = true
}

async function voiceUploadHandler(characterId, file) {
  if (!characterId || !file) return
  const uploaded = await validateAndUploadAudio(file)
  await updateItem(characterId, { voice_url: uploaded.url, voice_cos_key: uploaded.cos_key })
  const it = currentDocument.value?.items?.find((i) => i.id === characterId)
  if (it) {
    it.voice_url = uploaded.url
    it.voice_cos_key = uploaded.cos_key
  }
  flowNodes.value = flowNodes.value.map((n) =>
    n.id === characterId
      ? { ...n, data: { ...n.data, voice_url: uploaded.url, voice_cos_key: uploaded.cos_key } }
      : n
  )
}

async function onVoicePicked(voice) {
  assetPickerVisible.value = false
  const nodeId = voicePickerTargetId.value || editingNodeId.value
  voicePickerMode.value = false
  voicePickerTargetId.value = null
  if (!nodeId || !voice) return
  const url = voice.custom_voice_url || voice.audio_url || voice.url || null
  if (!url) {
    ElMessage.warning('该音色没有可用的音频 URL')
    return
  }
  try {
    await updateItem(nodeId, { voice_url: url, voice_cos_key: voice.cos_key || null })
    const it = currentDocument.value?.items?.find((i) => i.id === nodeId)
    if (it) {
      it.voice_url = url
      it.voice_cos_key = voice.cos_key || null
    }
    flowNodes.value = flowNodes.value.map((n) =>
      n.id === nodeId
        ? { ...n, data: { ...n.data, voice_url: url, voice_cos_key: voice.cos_key || null } }
        : n
    )
    ElMessage.success('音色已应用')
  } catch (e) {
    ElMessage.error(e?.message || '应用音色失败')
  }
}

function closeAssetPicker() {
  assetPickerVisible.value = false
  voicePickerMode.value = false
  voicePickerTargetId.value = null
}

function onAssetImported(item) {
  if (!item?.id) return
  // 后端 create_completed_generation 内部已同步资产库；这里一并回写，
  // 避免本地上传 / 资产中心导入后节点上仍是"未同步火山"
  const patch = {
    content_json: item.content_json,
    last_output_json: item.last_output_json,
    last_run_status: item.last_run_status,
    last_run_error: item.last_run_error,
    cover_url: item.cover_url,
    volc_asset_id: item.volc_asset_id,
    byteplus_asset_id: item.byteplus_asset_id,
  }
  // 1) 节点卡片数据源（flowNodes.data）
  updateNodeData(item.id, patch, vfUpdateNodeData)
  // 2) 编辑面板数据源（currentDocument.items）——editingNode 从这里取值。
  //    不同步的话，上传后立即打开节点看到的仍是旧数据：无"已生成"角标、无缩略图，需刷新才恢复。
  const it = currentDocument.value?.items?.find((i) => i.id === item.id)
  if (it) Object.assign(it, patch)
}

async function onAssetPicked(assets) {
  assetPickerVisible.value = false
  // 节点上方按钮触发时优先使用 nodeAssetTargetId；否则回退到正在编辑的节点
  const itemId = nodeAssetTargetId.value || editingNodeId.value
  if (!itemId || !Array.isArray(assets) || assets.length === 0) return
  const asset = assets[0]
  if (asset.asset_type !== 'image' && asset.asset_type !== 'audio') {
    ElMessage.warning('画布节点目前仅支持导入图片或音频类资产')
    return
  }
  try {
    const resp = await registerCanvasAsset(itemId, {
      source: 'asset_center',
      url: asset.asset_type === 'audio' ? asset.audio_url : asset.image_url,
      thumbnail_url: asset.thumbnail_url || null,
      filename: asset.name || null,
      asset_id: asset.id,
    })
    const updated = resp?.item
    if (updated) onAssetImported(updated)
    ElMessage.success('已从资产中心导入')
  } catch (err) {
    ElMessage.error(err?.message || '导入失败')
  } finally {
    nodeAssetTargetId.value = null
  }
}

// ── 节点上方浮动按钮：上传 / 资产中心 ──────────────────
function onNodeUploadRequest(payload) {
  const nodeId = payload?.id
  if (!nodeId) return
  const node = findNode(nodeId)
  const itemType = node?.data?.item_type || node?.type
  if (!itemType) return
  nodeAssetTargetId.value = nodeId
  nodeAssetItemType.value = itemType
  if (nodeAssetInputRef.value) {
    nodeAssetInputRef.value.value = ''
    if (itemType === 'video') {
      nodeAssetInputRef.value.accept = 'video/mp4,video/webm,video/quicktime'
    } else if (itemType === 'audio') {
      nodeAssetInputRef.value.accept = 'audio/*,.mp3,.wav,.m4a,.aac,.ogg,.flac'
    } else {
      nodeAssetInputRef.value.accept = 'image/jpeg,image/png,image/webp,image/gif,image/bmp'
    }
    nodeAssetInputRef.value.click()
  }
}

function onNodeOpenAssetPicker(payload) {
  const nodeId = payload?.id
  if (!nodeId) return
  nodeAssetTargetId.value = nodeId
  assetPickerVisible.value = true
}

async function onNodeAssetInputChange(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  const itemId = nodeAssetTargetId.value
  const itemType = nodeAssetItemType.value
  if (!itemId) return
  // 立即把节点切换到"本地上传中"，避免大文件上传期间用户以为卡住
  updateNodeData(itemId, { is_uploading: true })
  try {
    // 统一走前端直传 COS + register-asset（按 itemType 内部分流 image/video/audio）
    const resp = await uploadCanvasAssetDirect(itemId, file, itemType)
    const updatedItem = resp?.item || null
    const okLabelMap = { image: '图片已导入', video: '视频已导入', audio: '音频已导入' }
    ElMessage.success(okLabelMap[itemType] || '文件已导入')
    if (updatedItem) onAssetImported(updatedItem)
  } catch (err) {
    ElMessage.error(err?.message || '上传失败')
  } finally {
    updateNodeData(itemId, { is_uploading: false })
    nodeAssetTargetId.value = null
    nodeAssetItemType.value = null
  }
}

// ── 拖拽本地文件到画布 ───────────────────────────────
const dragActive = ref(false)

function onCanvasDragOver(e) {
  // 仅在拖入文件时高亮（忽略节点内部的拖拽）
  if (e.dataTransfer?.types?.includes('Files')) {
    dragActive.value = true
  }
}

function onCanvasDragLeave(e) {
  // 仅在真正离开容器（不是进入子元素）时取消高亮
  if (e.relatedTarget && e.currentTarget.contains(e.relatedTarget)) return
  dragActive.value = false
}

async function onCanvasDrop(e) {
  dragActive.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length === 0) return

  // 找命中节点（用真实 DOM 检测，VueFlow 节点容器带 data-id）
  let hitNodeId = null
  const hitEl = document.elementFromPoint(e.clientX, e.clientY)
  const hitNodeWrap = hitEl?.closest('[data-id]')
  if (hitNodeWrap) {
    const id = hitNodeWrap.getAttribute('data-id')
    const node = findNode(id)
    if (node) hitNodeId = id
  }

  const dropPos = screenToFlowCoordinate({ x: e.clientX, y: e.clientY })

  // 分类文件，文本走原有逻辑，媒体文件批量创建节点后再并行上传
  const textTasks = []
  const mediaTasks = []

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const nodeType = pickNodeTypeForFile(file)
    if (!nodeType) {
      ElMessage.warning(`不支持的文件类型：${file.name}`)
      continue
    }
    const offsetPos = { x: dropPos.x + i * 30, y: dropPos.y + i * 30 }
    if (nodeType === 'text') {
      textTasks.push({ file, nodeType, hitNodeId, dropPos: offsetPos })
    } else {
      const fileName = file.name.replace(/\.[^.]+$/, '')
      mediaTasks.push({ file, nodeType, hitNodeId, dropPos: offsetPos, fileName })
    }
  }

  // 文本文件：逐个处理（需要读取内容写入节点）
  for (const t of textTasks) {
    await processDroppedFile(t.file, t.nodeType, t.hitNodeId, t.dropPos)
  }

  // 媒体文件：先批量创建所有节点，再并行上传
  const createdItems = []
  for (const t of mediaTasks) {
    const itemId = t.hitNodeId
    if (itemId) {
      const node = findNode(itemId)
      if (node?.data?.item_type !== t.nodeType) {
        const labelMap = { image: '图片', video: '视频', audio: '音频' }
        ElMessage.warning(`${labelMap[t.nodeType] || '该类型'}文件只能拖到同类节点`)
        continue
      }
      createdItems.push({ ...t, targetItemId: itemId })
    } else {
      const created = await createItemWithPosition(t.nodeType, t.dropPos, t.fileName)
      if (!created) continue
      createdItems.push({ ...t, targetItemId: created.id })
    }
  }

  // 所有节点标记为上传中。必须用 is_uploading，不能用 last_run_status='uploading'——
  // 后者会触发 isRunning 显示"生成中…"，且与 is_uploading 的"上传中"文案/遮罩逻辑冲突。
  for (const item of createdItems) {
    updateNodeData(item.targetItemId, { is_uploading: true })
  }

  // 并行上传（统一走前端直传 COS + register-asset，按 nodeType 内部分流）
  const uploadPromises = createdItems.map(async (item) => {
    try {
      const resp = await uploadCanvasAssetDirect(item.targetItemId, item.file, item.nodeType)
      const updated = resp?.item
      if (updated) onAssetImported(updated)
      const okLabelMap = { image: '图片已导入', video: '视频已导入', audio: '音频已导入' }
      ElMessage.success(okLabelMap[item.nodeType] || '文件已导入')
    } catch (err) {
      ElMessage.error(err?.message || '文件导入失败')
    } finally {
      // 无论成功失败都清除上传中状态；成功的 last_run_status 已由 onAssetImported 回写为 completed
      updateNodeData(item.targetItemId, { is_uploading: false })
    }
  })

  await Promise.all(uploadPromises)
}

async function processDroppedFile(file, nodeType, hitNodeId, dropPos) {
  // 文本文件 → 写入文本节点 body（不创建 generation 记录）
  if (nodeType === 'text') {
    let targetItemId = hitNodeId
    if (!targetItemId) {
      const created = await createItemWithPosition('text', dropPos)
      if (!created) return
      targetItemId = created.id
    } else {
      const node = findNode(targetItemId)
      if (node?.data?.item_type !== 'text') {
        ElMessage.warning('文本文件只能拖到文本节点')
        return
      }
    }
    try {
      const text = await readFileAsText(file)
      const item = flowNodes.value.find((n) => n.id === targetItemId)
      const contentJson = { ...(item?.data?.content_json || {}), body: text }
      await updateItem(targetItemId, { content_json: contentJson })
      updateNodeData(targetItemId, { content_json: contentJson })
      ElMessage.success(`已导入 ${file.name}`)
    } catch (err) {
      ElMessage.error(err?.message || '文本导入失败')
    }
    return
  }

  // image / video / audio → 先创建节点（显示上传中），再异步上传
  let targetItemId = hitNodeId
  if (targetItemId) {
    const node = findNode(targetItemId)
    if (node?.data?.item_type !== nodeType) {
      const labelMap = { image: '图片', video: '视频', audio: '音频' }
      ElMessage.warning(`${labelMap[nodeType] || '该类型'}文件只能拖到同类节点`)
      return
    }
  } else {
    const fileName = file.name.replace(/\.[^.]+$/, '')
    const created = await createItemWithPosition(nodeType, dropPos, fileName)
    if (!created) return
    targetItemId = created.id
  }

  // 标记节点为上传中状态
  updateNodeData(targetItemId, { last_run_status: 'pending' })

  try {
    // 拖拽上传同样切换"本地上传中"遮罩
    updateNodeData(targetItemId, { is_uploading: true })
    // 统一走前端直传 COS + register-asset（按 nodeType 内部分流 image/video/audio）
    const resp = await uploadCanvasAssetDirect(targetItemId, file, nodeType)
    const updated = resp?.item
    if (updated) onAssetImported(updated)
    const okLabelMap = { image: '图片已导入', video: '视频已导入', audio: '音频已导入' }
    ElMessage.success(okLabelMap[nodeType] || '文件已导入')
  } catch (err) {
    // 上传失败时恢复节点状态
    updateNodeData(targetItemId, { last_run_status: 'idle' })
    ElMessage.error(err?.message || '文件导入失败')
  } finally {
    updateNodeData(targetItemId, { is_uploading: false })
  }
}

async function createItemWithPosition(itemType, pos, title = '') {
  creatingItem.value = true
  try {
    const created = await addItem({
      item_type: itemType,
      title,
      position_x: Math.round(pos.x),
      position_y: Math.round(pos.y),
      width: 240,
      height: 120,
    })
    appendFlowNode({
      id: created.id,
      type: created.item_type,
      position: { x: created.position_x, y: created.position_y },
      data: { ...created },
    })
    return created
  } catch (e) {
    return null
  } finally {
    creatingItem.value = false
  }
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.readAsText(file)
  })
}

async function pollGeneration(itemId, generationId, itemType) {
  // 用指数退避轮询：1.5s → 2s → 3s → 5s，最长 5 分钟
  const intervals = [1500, 2000, 3000, 5000]
  const maxAttempts = 60
  let attempts = 0

  const tick = async () => {
    attempts += 1
    if (attempts > maxAttempts) {
      cleanupPoll(itemId)
      updateNodeData(itemId, { last_run_status: 'failed', last_run_error: '生成超时' })
      generatingItems.delete(itemId)
      delete localPendingGen[itemId]
      return
    }
    try {
      const gen = await getCanvasGeneration(itemId, generationId)
      if (gen?.status === 'completed') {
        applyGenerationResult(itemId, itemType, gen)
        generatingItems.delete(itemId)
        delete localPendingGen[itemId]
        cleanupPoll(itemId)
        return
      }
      if (gen?.status === 'failed') {
        updateNodeData(itemId, {
          last_run_status: 'failed',
          last_run_error: gen?.error_msg || '生成失败',
        })
        generatingItems.delete(itemId)
        delete localPendingGen[itemId]
        cleanupPoll(itemId)
        return
      }
      // pending / processing：继续轮询
      const delay = intervals[Math.min(attempts, intervals.length) - 1]
      generationPollTimers.set(itemId, setTimeout(tick, delay))
    } catch (e) {
      // 网络错误：稍后重试
      generationPollTimers.set(itemId, setTimeout(tick, 3000))
    }
  }

  generationPollTimers.set(itemId, setTimeout(tick, intervals[0]))
}

function applyGenerationResult(itemId, itemType, gen) {
  const output = gen?.output_json || {}
  const node = flowNodes.value.find((n) => n.id === itemId)
  const prevContent = node?.data?.content_json || {}

  if (itemType === 'text') {
    const text = output.text || ''
    updateNodeData(itemId, {
      last_run_status: 'completed',
      last_run_error: null,
      content_json: { ...prevContent, text },
      last_output_json: { text },
    })
    const docItem = currentDocument.value?.items?.find((i) => i.id === itemId)
    if (docItem) {
      docItem.content_json = { ...(docItem.content_json || {}), text }
      docItem.last_output_json = { text }
      docItem.last_run_status = 'completed'
    }
  } else if (itemType === 'image') {
    const url = output.url || ''
    const thumbnailUrl = output.thumbnail_url || url
    updateNodeData(itemId, {
      last_run_status: 'completed',
      last_run_error: null,
      content_json: { ...prevContent, prompt: prevContent.prompt || '' },
      last_output_json: { url, thumbnail_url: thumbnailUrl },
    })
    const docItem = currentDocument.value?.items?.find((i) => i.id === itemId)
    if (docItem) {
      docItem.last_output_json = { url, thumbnail_url: thumbnailUrl }
      docItem.last_run_status = 'completed'
    }
  } else if (itemType === 'video') {
    const url = output.url || ''
    updateNodeData(itemId, {
      last_run_status: 'completed',
      last_run_error: null,
      content_json: { ...prevContent, prompt: prevContent.prompt || '' },
      last_output_json: { url },
    })
    const docItem = currentDocument.value?.items?.find((i) => i.id === itemId)
    if (docItem) {
      docItem.last_output_json = { url }
      docItem.last_run_status = 'completed'
    }
  } else if (itemType === 'audio') {
    const url = output.url || ''
    updateNodeData(itemId, {
      last_run_status: 'completed',
      last_run_error: null,
      content_json: { ...prevContent, prompt: prevContent.prompt || '' },
      last_output_json: { url },
    })
    const docItem = currentDocument.value?.items?.find((i) => i.id === itemId)
    if (docItem) {
      docItem.last_output_json = { url }
      docItem.last_run_status = 'completed'
    }
  }
}

function cleanupPoll(itemId) {
  const t = generationPollTimers.get(itemId)
  if (t) {
    clearTimeout(t)
    generationPollTimers.delete(itemId)
  }
}

// ── WS 实时通知：完成/失败立即 apply，避免只靠轮询 ──
// 终态（completed/failed）一到就更新节点 + store，并停掉该节点的轮询；
// 中间状态（pending/processing）由轮询继续兜底
function applyGenerationFromWsEvent(event) {
  if (event?.event_type !== WSEventType.CANVAS_GENERATION_PROGRESS) return
  const data = event?.data || {}
  const itemId = data.item_id
  const genId = data.generation_id
  if (!itemId) return

  // 本组件 tracking 判定：
  //   - '__pending__'：onEditorSubmit 已发起、API 尚未返回，此时丢弃任何完成事件，
  //     防止 WS 推送的历史/陈旧事件把刚设的 pending 覆盖
  //   - generation_id：API 已返回的真实 id，与事件不一致说明是历史事件，丢弃
  //   - undefined：本组件未发起（如刷新后），允许 apply 实现实时刷新
  const local = localPendingGen[itemId]
  if (local === '__pending__') return
  if (local && genId && local !== genId) return

  const patch = data.item_patch || {}
  if (data.status === 'completed') {
    const nodePatch = {
      last_run_status: 'completed',
      last_run_error: null,
      content_json: patch.content_json || {},
      last_output_json: patch.last_output_json || {},
    }
    if (patch.cover_url !== undefined) nodePatch.cover_url = patch.cover_url
    // 后端在 WS 推送前已完成资产库同步，把 volc_asset_id / byteplus_asset_id 一并落到节点，
    // 让"已同步火山"角标即时正确
    if (patch.volc_asset_id !== undefined) nodePatch.volc_asset_id = patch.volc_asset_id
    if (patch.byteplus_asset_id !== undefined) nodePatch.byteplus_asset_id = patch.byteplus_asset_id
    updateNodeData(itemId, nodePatch)
    const docItem = currentDocument.value?.items?.find((i) => i.id === itemId)
    if (docItem) {
      if (patch.content_json) docItem.content_json = patch.content_json
      if (patch.last_output_json) docItem.last_output_json = patch.last_output_json
      if (patch.cover_url !== undefined) docItem.cover_url = patch.cover_url
      if (patch.volc_asset_id !== undefined) docItem.volc_asset_id = patch.volc_asset_id
      if (patch.byteplus_asset_id !== undefined) docItem.byteplus_asset_id = patch.byteplus_asset_id
      docItem.last_run_status = 'completed'
    }
    cleanupPoll(itemId)
    generatingItems.delete(itemId)
    delete localPendingGen[itemId]
  } else if (data.status === 'failed') {
    const errMsg = data.error_msg || patch.last_run_error || '生成失败'
    updateNodeData(itemId, {
      last_run_status: 'failed',
      last_run_error: errMsg,
    })
    const docItem = currentDocument.value?.items?.find((i) => i.id === itemId)
    if (docItem) {
      docItem.last_run_status = 'failed'
      docItem.last_run_error = errMsg
    }
    cleanupPoll(itemId)
    generatingItems.delete(itemId)
    delete localPendingGen[itemId]
    ElMessage.error(errMsg)
  }
}

const { onEvent } = useWebSocket()
let unsubscribeWsGeneration = null

function handleKeydown(e) {
  const target = e.target
  if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return
  // // Ctrl/Cmd + A：全选"可打组的顶层节点"（排除 group 节点与已打组的子节点，避免与单层约束打架）
  // if ((e.ctrlKey || e.metaKey) && (e.key === 'a' || e.key === 'A')) {
  //   e.preventDefault()
  //   flowNodes.value = flowNodes.value.map((n) => ({
  //     ...n,
  //     selected: n.type !== 'group' && !n.parentNode,
  //   }))
  //   return
  // }
  // if (e.key === 'Delete' || e.key === 'Backspace') {
  const mod = e.ctrlKey || e.metaKey
  if (e.code === 'Space') {
    e.preventDefault()
    spacePressed.value = true
  } else if (mod && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault()
    if (e.shiftKey) redo()
    else undo()
  } else if (mod && (e.key === 'y' || e.key === 'Y')) {
    e.preventDefault()
    redo()
  } else if (mod && (e.key === 'd' || e.key === 'D')) {
    e.preventDefault()
    duplicateSelection()
  } else if (mod && (e.key === 'c' || e.key === 'C')) {
    const selected = flowNodes.value.filter((n) => n.selected && !n.parentNode)
    if (selected.length === 0) return
    e.preventDefault()
    copySelectedNodes(selected)
  } else if (mod && (e.key === 'v' || e.key === 'V')) {
    if (copiedNodes.value.length === 0) return
    e.preventDefault()
    pasteNode()
  } else if (e.key === 'Escape') {
    if (closeTopOverlay()) return
    if (deselectAllNodes()) e.preventDefault()
  } else if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
    const selected = flowNodes.value.filter((n) => n.selected)
    if (selected.length === 0) return
    e.preventDefault()
    const step = e.shiftKey ? 10 : 1
    const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0
    const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0
    const moved = selected.map((n) => ({
      id: n.id,
      position: { x: n.position.x + dx, y: n.position.y + dy },
    }))
    flowNodes.value = flowNodes.value.map((n) => {
      const m = moved.find((mm) => mm.id === n.id)
      return m ? { ...n, position: m.position } : n
    })
    for (const m of moved) {
      onNodeDragStop({ node: { id: m.id, position: m.position } })
    }
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    e.preventDefault()
    deleteSelection()
  } else if (e.key === '?' || (e.shiftKey && e.key === '/')) {
    e.preventDefault()
    shortcutsHelpVisible.value = true
  }
}

function handleKeyup(e) {
  if (e.code === 'Space') {
    spacePressed.value = false
  }
}

function resetSpacePan() {
  spacePressed.value = false
}

// 关闭最顶层的浮层，返回 true 表示吃掉了这次 Esc
function closeTopOverlay() {
  if (contextMenuVisible.value) { contextMenuVisible.value = false; return true }
  if (paneContextMenuVisible.value) { paneContextMenuVisible.value = false; return true }
  if (editingNodeId.value) { editingNodeId.value = null; return true }
  return false
}

// 取消所有节点选中状态，返回 true 表示有节点被取消选中
function deselectAllNodes() {
  const hasSelected = flowNodes.value.some((n) => n.selected)
  if (!hasSelected) return false
  flowNodes.value = flowNodes.value.map((n) => (n.selected ? { ...n, selected: false } : n))
  return true
}

// 复制当前选中的节点（按 Ctrl/Cmd+D）
async function duplicateSelection() {
  if (creatingItem.value) return
  const selected = flowNodes.value.filter((n) => n.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先选中节点')
    return
  }
  // 选中多个时按选择顺序依次复制；只复制单个时直接调 duplicateNode 保留入边复制逻辑
  if (selected.length === 1) {
    await duplicateNode(selected[0].id)
    return
  }
  for (const node of selected) {
    await duplicateNode(node.id)
  }
}

// 快捷键说明分组
const shortcutGroups = [
  {
    title: '画布平移与缩放',
    rows: [
      { label: '平移画布（任意位置拖动）', keys: ['Space', '+', '拖动'] },
      { label: '框选节点', keys: ['空白处拖动'] },
      { label: '缩放', keys: ['Ctrl', '+', '滚轮'] },
      { label: '重置视图', keys: ['工具栏按钮'] },
    ],
  },
  {
    title: '编辑',
    rows: [
      { label: '撤销', keys: ['Ctrl/Cmd', '+', 'Z'] },
      { label: '重做', keys: ['Ctrl/Cmd', '+', 'Shift', '+', 'Z'] },
      { label: '重做（备选）', keys: ['Ctrl/Cmd', '+', 'Y'] },
      { label: '复制选中节点', keys: ['Ctrl/Cmd', '+', 'C'] },
      { label: '粘贴节点', keys: ['Ctrl/Cmd', '+', 'V'] },
      { label: '创建节点副本', keys: ['Ctrl/Cmd', '+', 'D'] },
      { label: '删除选中', keys: ['Delete'] },
    ],
  },
  {
    title: '节点位置',
    rows: [
      { label: '微移 1 像素', keys: ['↑', '↓', '←', '→'] },
      { label: '微移 10 像素', keys: ['Shift', '+', '方向键'] },
    ],
  },
  {
    title: '其他',
    rows: [
      { label: '取消选中 / 关闭弹层', keys: ['Esc'] },
      { label: '打开本说明', keys: ['?'] },
    ],
  },
]

function resetView() {
  fitView?.({ padding: 0.2 })
}

// ── 小地图 ──
const minimapVisible = ref(false)
function toggleMinimap() {
  minimapVisible.value = !minimapVisible.value
}
function minimapNodeColor(node) {
  if (node?.selected) return 'rgba(47, 123, 255, 0.85)'
  return 'rgba(100, 116, 139, 0.55)'
}

// ── 整理画布：基于边的拓扑分层布局 ──
const LAYOUT_NODE_W = 240
const LAYOUT_NODE_H = 140
const LAYOUT_GAP_X = 80
const LAYOUT_GAP_Y = 40

async function autoLayout() {
  if (flowNodes.value.length === 0) return
  pushHistory()
  // 子节点不参与独立布局，跟随组移动
  const layoutNodes = flowNodes.value.filter((n) => !n.parentNode)
  // 读每个节点的实际 DOM 高度（文本/图片/视频节点高度差异大，固定值会导致垂直重叠）
  const nodeHeightOf = (id) => {
    if (typeof document === 'undefined') return LAYOUT_NODE_H
    const el = document.querySelector(`.vue-flow__node[data-id="${CSS.escape(id)}"]`)
    return el?.offsetHeight || LAYOUT_NODE_H
  }
  // 永远网格布局：每行 4 个，按当前顺序排；y 用行内最大节点高度累加，避免重叠
  const positions = new Map()
  const cols = Math.min(4, Math.max(1, layoutNodes.length))
  let rowY = 0
  for (let i = 0; i < layoutNodes.length; i += cols) {
    const rowSlice = layoutNodes.slice(i, i + cols)
    const rowMaxH = Math.max(...rowSlice.map((n) => nodeHeightOf(n.id)))
    rowSlice.forEach((n, j) => {
      positions.set(n.id, {
        x: j * (LAYOUT_NODE_W + LAYOUT_GAP_X),
        y: rowY,
      })
    })
    rowY += rowMaxH + LAYOUT_GAP_Y
  }
  // 应用到 flowNodes：只移动非子节点，子节点保持相对组的位置
  const next = flowNodes.value.map((n) => {
    if (n.parentNode) return n
    const p = positions.get(n.id)
    if (!p) return n
    return { ...n, position: { x: Math.round(p.x), y: Math.round(p.y) } }
  })
  flowNodes.value = next
  // 同步 store + 后端
  for (const n of next) {
    if (n.parentNode) continue
    const p = positions.get(n.id)
    if (!p) continue
    const item = currentDocument.value?.items?.find((i) => i.id === n.id)
    if (item) {
      item.position_x = n.position.x
      item.position_y = n.position.y
    }
    try {
      await updateItem(n.id, {
        position_x: n.position.x,
        position_y: n.position.y,
      })
    } catch (e) {}
  }
  // 6. 视图适应
  setTimeout(() => fitView?.({ padding: 0.2 }), 60)
  ElMessage.success('已整理画布')
}
</script>

<style scoped>
.canvas-editor-page {
  position: relative;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 4rem);
  background: #e3e7ed;
  overflow: hidden;
}

.canvas-flow-wrap {
  position: absolute;
  inset: 0;
}

.canvas-flow-wrap.is-drag-active::after {
  content: '拖入将创建节点';
  position: absolute;
  inset: 12px;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #355ce0;
  background: rgba(75, 120, 255, 0.06);
  border: 2px dashed rgba(75, 120, 255, 0.4);
  border-radius: 14px;
  z-index: 1000;
}

.canvas-flow-wrap :deep(.vue-flow) {
  background: #e3e7ed;
}

.canvas-flow-wrap :deep(.vue-flow__edge-path) {
  stroke: #ffffff;
  stroke-width: 2;
}

/* 节点默认光标：移动而非 grab，避免误导成平移 */
.canvas-flow-wrap :deep(.vue-flow__node.draggable),
.canvas-flow-wrap :deep(.vue-flow__node.draggable.dragging) {
  cursor: move;
}

/* 空格按住：节点和连线区光标变成 grab，提示当前拖动是平移画布 */
.canvas-flow-wrap.is-space-pan :deep(.vue-flow__node),
.canvas-flow-wrap.is-space-pan :deep(.vue-flow__pane) {
  cursor: grab;
}
.canvas-flow-wrap.is-space-pan :deep(.vue-flow__node.dragging),
.canvas-flow-wrap.is-space-pan :deep(.vue-flow__pane.dragging) {
  cursor: grabbing;
}

/* ── 小地图：右下角玻璃质感 ── */
.canvas-flow-wrap :deep(.vue-flow__minimap) {
  position: absolute;
  right: 20px;
  bottom: 20px;
  width: 200px;
  height: 140px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 14px;
  box-shadow: 0 10px 24px rgba(34, 57, 98, 0.12);
  z-index: 18;
}

.canvas-flow-wrap :deep(.vue-flow__minimap svg) {
  border-radius: 14px;
}

.canvas-flow-wrap :deep(.vue-flow__minimap-mask) {
  fill: rgba(226, 232, 240, 0.65);
}

/* ── 顶部 chip ── */
.canvas-topbar {
  position: absolute;
  top: 20px;
  left: 24px;
  right: 24px;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 12px;
  pointer-events: none;
}

.topbar-back,
.topbar-title {
  pointer-events: auto;
}

.topbar-back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  color: #52607a;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(34, 57, 98, 0.08);
  transition: all 0.15s ease;
}

.topbar-back:hover {
  color: #1f2a44;
  background: #fff;
  transform: translateY(-1px);
}

.topbar-title {
  flex: 0 1 360px;
  height: 36px;
  padding: 0 14px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2a44;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(34, 57, 98, 0.08);
  transition: all 0.15s ease;
}

.topbar-title:focus {
  background: #fff;
  border-color: rgba(47, 123, 255, 0.4);
  outline: none;
  box-shadow: 0 0 0 3px rgba(47, 123, 255, 0.12), 0 8px 20px rgba(34, 57, 98, 0.08);
}

/* ── 节点内容自动保存状态指示 ── */
.topbar-save-status {
  pointer-events: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(34, 57, 98, 0.08);
  box-shadow: 0 4px 12px rgba(34, 57, 98, 0.06);
  color: #52607a;
  animation: tssFadeIn 0.18s ease-out;
}
.topbar-save-status-saving { color: #2f7bff; }
.topbar-save-status-saved { color: #16a34a; }
.topbar-save-status-failed { color: #ef4444; }

.tss-spinner {
  width: 12px;
  height: 12px;
  border: 1.5px solid rgba(47, 123, 255, 0.25);
  border-top-color: #2f7bff;
  border-radius: 50%;
  animation: tssSpin 0.8s linear infinite;
}
.tss-icon { flex-shrink: 0; }

@keyframes tssSpin { to { transform: rotate(360deg); } }
@keyframes tssFadeIn {
  from { opacity: 0; transform: translateY(-2px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── 左侧浮动工具栏 ── */
.canvas-toolbar {
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 18;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 999px;
  padding: 10px 6px;
  gap: 10px;
  box-shadow: 0 14px 32px rgba(34, 57, 98, 0.1);
}

.tb-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f6fb;
  color: #52607a;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tb-btn:hover:not(:disabled) {
  background: #e7edf8;
  color: #1f2a44;
  transform: translateY(-1px);
}

.tb-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tb-btn-active {
  background: #4f46e5;
  color: #fff;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);
}

.tb-btn-active:hover:not(:disabled) {
  background: #4338ca;
  color: #fff;
}

/* 选中节点后浮现的浮动操作条（打组）- 由 JS 计算 fixed 定位 */
.canvas-floating-action {
  z-index: 30;
  display: flex;
  gap: 8px;
  padding: 6px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(34, 57, 98, 0.12);
  pointer-events: all;
}
.cfa-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: none;
  border-radius: 7px;
  font-size: 12px;
  line-height: 18px;
  cursor: pointer;
  background: #f3f6fb;
  color: #52607a;
  transition: all 0.15s ease;
}
.cfa-btn:hover {
  background: #e7edf8;
  color: #1f2a44;
}
.cfa-btn-primary {
  background: #4f46e5;
  color: #fff;
}
.cfa-btn-primary:hover {
  background: #4338ca;
  color: #fff;
}

.canvas-floating-action-enter-active,
.canvas-floating-action-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.canvas-floating-action-enter-from,
.canvas-floating-action-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.tb-btn-primary {
  width: 44px;
  height: 44px;
  background: linear-gradient(180deg, #4b78ff, #355ce0);
  color: #fff;
  box-shadow: 0 8px 20px rgba(75, 120, 255, 0.32);
}

.tb-btn-primary:hover:not(:disabled) {
  background: linear-gradient(180deg, #5b88ff, #456ce8);
  color: #fff;
}

.tb-divider {
  width: 24px;
  height: 1px;
  background: rgba(34, 57, 98, 0.1);
}

/* ── 左侧 "+" 浮动按钮：hover 旋转 + 右侧展开节点类型面板 ── */
.add-fab {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-fab-btn {
  position: relative;
}

.add-fab-icon {
  transition: transform 0.28s cubic-bezier(0.34, 1.2, 0.5, 1);
  transform-origin: center center;
}

.add-fab:hover .add-fab-icon,
.add-fab.is-open .add-fab-icon {
  transform: rotate(45deg);
}

.add-fab-panel {
  position: absolute;
  left: calc(100% + 14px);
  top: 50%;
  transform: translateY(-50%);
  width: 264px;
  background: #ffffff;
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 14px;
  padding: 10px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.18);
  z-index: 30;
  animation: afpIn 0.18s ease-out;
  transform-origin: left center;
}

@keyframes afpIn {
  from { opacity: 0; transform: translateY(-50%) translateX(-6px) scale(0.96); }
  to   { opacity: 1; transform: translateY(-50%) translateX(0) scale(1); }
}

/* 连接小箭头已移除 */

.add-fab-panel .afp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px 10px;
  margin-bottom: 4px;
  border-bottom: 1px solid rgba(34, 57, 98, 0.06);
}

.add-fab-panel .afp-title-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(47, 123, 255, 0.12);
  color: #2f7bff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.add-fab-panel .afp-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.add-fab-panel .afp-close {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #9ca3af;
  font-size: 18px;
  line-height: 1;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s ease, color 0.12s ease;
}

.add-fab-panel .afp-close:hover {
  background: rgba(34, 57, 98, 0.06);
  color: #1f2937;
}

.add-fab-panel .afp-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 10px;
  border: 1px solid transparent;
  background: #fafbfc;
  border-radius: 10px;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  margin-top: 6px;
  transition: background 0.14s ease, border-color 0.14s ease, transform 0.14s ease, box-shadow 0.14s ease;
}

.add-fab-panel .afp-card:first-of-type {
  margin-top: 0;
}

.add-fab-panel .afp-card:hover:not(:disabled) {
  background: #ffffff;
  border-color: rgba(47, 123, 255, 0.25);
  box-shadow: 0 4px 14px rgba(47, 123, 255, 0.1);
  transform: translateX(2px);
}

.add-fab-panel .afp-card:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-fab-panel .afp-card-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.add-fab-panel .afp-card-icon-text {
  background: rgba(47, 123, 255, 0.12);
  color: #2f7bff;
}

.add-fab-panel .afp-card-icon-image {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.add-fab-panel .afp-card-icon-video {
  background: rgba(147, 51, 234, 0.12);
  color: #9333ea;
}

.add-fab-panel .afp-card-icon-audio {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.add-fab-panel .afp-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.add-fab-panel .afp-card-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.2;
}

.add-fab-panel .afp-card-desc {
  font-size: 11.5px;
  color: #9ca3af;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 左下角 zoom chip ── */
.canvas-zoom-chip {
  position: absolute;
  left: 20px;
  bottom: 20px;
  z-index: 18;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 36px;
  padding: 0 8px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 999px;
  box-shadow: 0 10px 24px rgba(34, 57, 98, 0.1);
}

.zoom-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #52607a;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}

.zoom-btn:hover {
  background: #e7edf8;
  color: #1f2a44;
}

.zoom-btn.is-active {
  background: #e7edf8;
  color: #2f7bff;
}

.zoom-btn.is-disabled,
.zoom-btn:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

.zoom-btn.is-disabled:hover,
.zoom-btn:disabled:hover {
  background: transparent;
  color: #c0c4cc;
}

.zoom-text {
  min-width: 40px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #1f2a44;
  user-select: none;
}

.zoom-sep {
  width: 1px;
  height: 16px;
  background: rgba(34, 57, 98, 0.1);
  margin: 0 2px;
}

/* ── 空状态 launcher ── */
.canvas-launcher {
  position: absolute;
  left: 50%;
  bottom: 80px;
  z-index: 16;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  pointer-events: none;
}

.launcher-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(34, 57, 98, 0.08);
  color: #52607a;
  box-shadow: 0 12px 30px rgba(34, 57, 98, 0.1);
  font-size: 13px;
}

.launcher-chip svg {
  color: #4b78ff;
}

.launcher-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
  pointer-events: auto;
}

.launcher-action {
  height: 38px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid rgba(34, 57, 98, 0.1);
  background: rgba(255, 255, 255, 0.98);
  color: #1f2a44;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(34, 57, 98, 0.08);
  transition: all 0.15s ease;
}

.launcher-action:hover:not(:disabled) {
  background: #f8fbff;
  border-color: rgba(75, 120, 255, 0.3);
  color: #355ce0;
  transform: translateY(-1px);
}

.launcher-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 加载/空状态提示 ── */
.canvas-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  font-size: 13px;
  color: #9ca3af;
  gap: 6px;
}

.spin {
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 960px) {
  .canvas-topbar {
    left: 16px;
    right: 16px;
  }
  .canvas-toolbar {
    left: 12px;
  }
  .canvas-launcher {
    left: 24px;
    right: 24px;
    bottom: 80px;
    transform: none;
  }
}

/* 快捷键说明弹框 */
.shortcuts-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.shortcuts-dialog {
  width: 560px;
  max-width: 92vw;
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  background: var(--glass-bg-surface, #ffffff);
  border-radius: 14px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.18);
  overflow: hidden;
  border: 1px solid rgba(34, 57, 98, 0.08);
}

.shortcuts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(34, 57, 98, 0.06);
}

.shortcuts-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--glass-text-primary, #0f172a);
}

.shortcuts-close {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  color: var(--glass-text-tertiary, #64748b);
  cursor: pointer;
  border-radius: 6px;
}

.shortcuts-close:hover {
  background: rgba(15, 23, 42, 0.06);
  color: var(--glass-text-primary, #0f172a);
}

.shortcuts-body {
  padding: 16px 20px 20px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 28px;
}

.shortcut-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.shortcut-group-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--glass-text-tertiary, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.shortcut-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.shortcut-label {
  color: var(--glass-text-secondary, #475569);
}

.shortcut-keys {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.shortcut-keys kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11px;
  font-weight: 500;
  color: var(--glass-text-primary, #0f172a);
  background: rgba(15, 23, 42, 0.06);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 5px;
  line-height: 1;
}

@media (max-width: 720px) {
  .shortcuts-dialog { width: 92vw; }
  .shortcuts-body { grid-template-columns: 1fr; }
}
</style>

<style>
/* 浮层（teleport 到 body，必须非 scoped） */
.editor-popover {
  background: #fff;
  border-radius: 18px;
  box-shadow:
    0 32px 80px -12px rgba(15, 23, 42, 0.28),
    0 12px 32px -8px rgba(15, 23, 42, 0.12),
    0 0 0 1px rgba(34, 57, 98, 0.06);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: editorPopoverIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes editorPopoverIn {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

</style>
