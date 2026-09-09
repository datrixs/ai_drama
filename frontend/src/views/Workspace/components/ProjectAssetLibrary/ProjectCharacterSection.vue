<template>
  <div class="character-section glass-surface">
    <!-- 标题行 -->
    <div class="section-header">
      <div class="section-header-left">
        <div class="section-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </div>
        <h3 class="section-title">角色资产</h3>
        <span class="section-count">{{ characters.length }} 个角色</span>
      </div>
      <button class="glass-btn-base glass-btn-primary section-add-btn" @click="$emit('create', 'character')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
        <span>添加角色</span>
      </button>
    </div>

    <!-- 角色网格 -->
    <div v-if="characters.length > 0" class="character-grid">
      <div v-for="char in characters" :key="char.id" class="character-item">
        <ProjectCharacterCard
          :character="char"
          :project-id="projectId"
          :voice-upload-handler="voiceUploadHandler"
          @preview="$emit('preview', $event)"
          @edit="$emit('edit', $event)"
          @generate="$emit('generate', $event)"
          @upload="$emit('upload', $event)"
          @modify="$emit('modify', $event)"
          @delete="$emit('delete', $event)"
          @download="$emit('download', $event)"
          @reference="$emit('reference', $event)"
          @import-from-global="$emit('import-from-global', $event)"
          @undo="$emit('undo', $event)"
          @sync-volc="$emit('sync-volc', $event)"
          @voice-design="$emit('voiceDesign', $event)"
          @voice-select="$emit('voiceSelect', $event)"
          @voice-changed="$emit('voiceChanged', $event)"
        />
      </div>
    </div>
    <!-- 空占位 -->
    <div v-else class="section-empty">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"><circle cx="9" cy="7" r="4"/><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/></svg>
      <span>暂无角色，点上方按钮添加</span>
    </div>
  </div>
</template>

<script setup>
import ProjectCharacterCard from './ProjectCharacterCard.vue'

defineProps({
  characters: { type: Array, default: () => [] },
  projectId: String,
  voiceUploadHandler: { type: Function, default: null },
})

defineEmits(['preview', 'edit', 'generate', 'upload', 'modify', 'delete', 'download', 'reference', 'import-from-global', 'undo', 'create', 'sync-volc', 'voiceDesign', 'voiceSelect', 'voiceChanged'])
</script>

<style scoped>
.character-section {
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
  background: var(--glass-bg-muted);
  color: var(--glass-text-secondary);
  flex-shrink: 0;
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

/* === 角色网格 === */
.character-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

@media (min-width: 640px) {
  .character-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.section-add-btn {
  height: 2rem;
  padding: 0 0.75rem;
  font-size: 0.75rem;
  gap: 0.25rem;
  border-radius: var(--glass-radius-md);
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
