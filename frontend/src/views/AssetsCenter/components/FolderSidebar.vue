<template>
  <div class="folder-sidebar">
    <div class="glass-surface folder-sidebar__surface">
      <!-- Header -->
      <div class="folder-sidebar__header">
        <span class="folder-sidebar__title">资产组</span>
        <button class="glass-btn-base glass-btn-primary folder-sidebar__add-btn" @click="$emit('create')">
          <Plus :size="14" />
        </button>
      </div>

      <!-- All assets -->
      <button
        :class="['folder-sidebar__item', { 'folder-sidebar__item--selected': !store.selectedFolderId }]"
        @click="store.selectFolder(null)"
      >
        <el-icon :size="16"><Folder /></el-icon>
        <span class="folder-sidebar__item-text">所有资产</span>
      </button>

      <!-- Ungrouped assets -->
      <button
        :class="['folder-sidebar__item', { 'folder-sidebar__item--selected': store.selectedFolderId === UNGROUPED_FOLDER_ID }]"
        @click="store.selectFolder(UNGROUPED_FOLDER_ID)"
      >
        <el-icon :size="16"><Folder /></el-icon>
        <span class="folder-sidebar__item-text">未分组</span>
      </button>

      <!-- Folder list -->
      <div v-if="store.folders.length" class="folder-sidebar__list">
        <button
          v-for="folder in store.folders"
          :key="folder.id"
          :class="['folder-sidebar__item', 'folder-sidebar__item--folder', { 'folder-sidebar__item--selected': store.selectedFolderId === folder.id }]"
          @click="store.selectFolder(folder.id)"
        >
          <Folder :size="16" />
          <span class="folder-sidebar__item-text">{{ folder.name }}</span>
          <span v-if="folder.is_shared" class="folder-sidebar__shared-tag">共享</span>
          <span v-if="!folder.is_shared" class="folder-sidebar__item-actions">
            <button
              class="glass-btn-base glass-btn-soft folder-sidebar__action-btn"
              @click.stop="$emit('edit', folder)"
            >
              <Pencil :size="12" />
            </button>
            <button
              class="glass-btn-base glass-btn-tone-danger folder-sidebar__action-btn"
              @click.stop="$emit('delete', folder.id)"
            >
              <Trash2 :size="12" />
            </button>
          </span>
        </button>
      </div>

      <!-- Empty state -->
      <div v-else class="folder-sidebar__empty">
        暂无资产组
      </div>

      <!-- 平台资产（独立区域，跟用户资产组分离） -->
      <div class="folder-sidebar__platform">
        <button
          :class="['folder-sidebar__item', 'folder-sidebar__item--platform', { 'folder-sidebar__item--selected': store.selectedFolderId === PLATFORM_FOLDER_ID }]"
          @click="store.selectFolder(PLATFORM_FOLDER_ID)"
          title="由平台统一提供，不可修改"
        >
          <Landmark :size="16" />
          <span class="folder-sidebar__item-text">平台资产</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Plus, Edit, Trash, Folder, Pencil, Trash2, Landmark } from '@lucide/vue'
import { useAssetHubStore, UNGROUPED_FOLDER_ID, PLATFORM_FOLDER_ID } from '@/store/assetHub'

const store = useAssetHubStore()

defineEmits(['create', 'edit', 'delete'])
</script>

<style scoped>
.folder-sidebar {
  width: 14rem;
  flex-shrink: 0;
}

.folder-sidebar__surface {
  padding: 16px;
}

.folder-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.folder-sidebar__title {
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-secondary);
}

.folder-sidebar__add-btn {
  width: 24px;
  height: 24px;
  border-radius: 9999px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.folder-sidebar__item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  border: none;
  background: none;
  text-align: left;
  font-size: 14px;
  color: var(--glass-text-secondary);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.folder-sidebar__item:hover {
  background: var(--glass-bg-muted);
}

.folder-sidebar__item--selected {
  background: var(--glass-tone-info-bg);
  color: var(--glass-tone-info-fg);
}

.folder-sidebar__item--selected:hover {
  background: var(--glass-tone-info-bg);
}

.folder-sidebar__item-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-sidebar__item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.folder-sidebar__item--folder:hover .folder-sidebar__item-actions {
  opacity: 1;
  pointer-events: auto;
}

.folder-sidebar__action-btn {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.folder-sidebar__list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
}

.folder-sidebar__empty {
  font-size: 12px;
  text-align: center;
  padding: 16px 0;
  color: var(--glass-text-tertiary);
}

.folder-sidebar__shared-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(47, 123, 255, 0.1);
  color: #2f7bff;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 16px;
}

/* 平台资产独立区域 */
.folder-sidebar__platform {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
}

.folder-sidebar__item--platform {
  color: var(--glass-text-secondary);
}

.folder-sidebar__item--platform.folder-sidebar__item--selected {
  color: #0d9488;
  background: rgba(13, 148, 136, 0.12);
}
</style>
