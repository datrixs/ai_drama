<template>
  <div class="location-section glass-surface">
    <!-- 标题行 -->
    <div class="section-header">
      <div class="section-header-left">
        <div class="section-icon" :class="assetType === 'location' ? 'section-icon-info' : 'section-icon-warning'">
          <ImageIcon v-if="assetType === 'location'" :size="18" />
          <Diamond v-else :size="18" />
        </div>
        <h3 class="section-title">{{ assetType === 'location' ? '场景资产' : '道具资产' }}</h3>
        <span class="section-count">{{ locations.length }} 个{{ assetType === 'location' ? '场景' : '道具' }}</span>
      </div>
      <button class="glass-btn-base glass-btn-primary section-add-btn" @click="$emit('create', assetType)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
        <span>添加{{ assetType === 'location' ? '场景' : '道具' }}</span>
      </button>
    </div>

    <!-- 场景/道具网格 -->
    <div v-if="locations.length > 0" class="location-grid">
      <ProjectLocationCard
        v-for="loc in locations"
        :key="loc.id"
        :location="loc"
        :project-id="projectId"
        :asset-type="assetType"
        @preview="$emit('preview', $event)"
        @edit="$emit('edit', $event)"
        @generate="$emit('generate', $event)"
        @upload="$emit('upload', $event)"
        @modify="$emit('modify', $event)"
        @delete="$emit('delete', $event)"
        @download="$emit('download', $event)"
        @import-from-global="$emit('import-from-global', $event)"
        @undo="$emit('undo', $event)"
        @sync-volc="$emit('sync-volc', $event)"
      />
    </div>
    <!-- 空占位 -->
    <div v-else class="section-empty">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
      <span>暂无{{ assetType === 'location' ? '场景' : '道具' }}，点上方按钮添加</span>
    </div>
  </div>
</template>

<script setup>
import ProjectLocationCard from './ProjectLocationCard.vue'
import { Image as ImageIcon, Diamond } from '@lucide/vue'

defineProps({
  locations: { type: Array, default: () => [] },
  projectId: String,
  assetType: { type: String, default: 'location' },
})

defineEmits(['preview', 'edit', 'generate', 'upload', 'modify', 'delete', 'download', 'import-from-global', 'undo', 'create', 'sync-volc'])
</script>

<style scoped>
.location-section {
  padding: 1.5rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.section-header-left {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.section-icon {
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.5625rem;
  flex-shrink: 0;
}

.section-icon-info {
  background: var(--glass-tone-info-bg);
  color: var(--glass-tone-info-fg);
}

.section-icon-warning {
  background: var(--glass-tone-warning-bg, var(--glass-bg-muted));
  color: var(--glass-tone-warning-fg, var(--glass-text-secondary));
}

.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  margin: 0;
}

.section-count {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.125rem 0.5rem;
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--glass-bg-muted) 50%, transparent);
  color: var(--glass-text-tertiary);
}

.section-add-btn {
  height: 2rem;
  padding: 0 0.75rem;
  font-size: 0.75rem;
  gap: 0.25rem;
  border-radius: var(--glass-radius-md);
}

/* === 场景/道具网格 === */
.location-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

@media (min-width: 640px) {
  .location-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* === 空占位 === */
.section-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 7.5rem;
  border-radius: var(--glass-radius-md, 0.75rem);
  background: var(--glass-bg-muted, rgba(244, 247, 252, 0.5));
  border: 1px dashed var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  color: var(--glass-text-tertiary, #6b7280);
  font-size: 0.8125rem;
}
</style>
