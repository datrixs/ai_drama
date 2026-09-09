<template>
  <Teleport to="body">
    <div v-if="visible" class="glass-overlay" @click.self="$emit('close')">
      <div class="glass-surface-modal edit-dialog animate-fadeIn">
        <div class="edit-header">
          <h3>参考图生图 - {{ character?.name }}</h3>
          <button class="glass-icon-btn-sm" @click="$emit('close')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        <div class="edit-body">
          <!-- 参考图上传 -->
          <label class="edit-field">
            <span class="field-label">参考图（最多 5 张）</span>
            <div class="ref-images">
              <div v-for="(url, idx) in refImageUrls" :key="idx" class="ref-image-item">
                <img :src="url" />
                <button class="ref-remove" @click="refImageUrls.splice(idx, 1)">x</button>
              </div>
              <label v-if="refImageUrls.length < 5" class="ref-add">
                <input type="file" accept="image/jpeg,image/png,image/webp" class="hidden" @change="handleRefImageAdd" />
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
              </label>
            </div>
          </label>

          <!-- 模式选择 -->
          <div class="mode-select">
            <button class="mode-btn" :class="{ active: mode === 'direct' }" @click="mode = 'direct'">直接生成</button>
            <button class="mode-btn" :class="{ active: mode === 'extract' }" @click="mode = 'extract'">提取描述后生成</button>
          </div>

          <!-- 描述 -->
          <label class="edit-field">
            <div class="field-label-row">
              <span class="field-label">角色描述</span>
              <button v-if="mode === 'extract'" class="ai-btn" :disabled="extracting" @click="handleExtract">
                {{ extracting ? '提取中...' : 'AI 提取描述' }}
              </button>
            </div>
            <textarea v-model="description" class="glass-textarea-base" rows="3" placeholder="角色描述" />
          </label>
        </div>
        <div class="edit-footer">
          <button class="glass-btn-base glass-btn-secondary" @click="$emit('close')">取消</button>
          <button class="glass-btn-base glass-btn-primary" :disabled="refImageUrls.length === 0" @click="handleSubmit">
            开始生成
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useProjectAssetStore } from '@/store/project_asset'

const props = defineProps({
  visible: Boolean,
  character: Object,
  projectId: String,
})

const emit = defineEmits(['close', 'submit'])
const store = useProjectAssetStore()
const refImageUrls = ref([])
const mode = ref('direct')
const description = ref('')
const extracting = ref(false)

watch(() => props.character, (val) => {
  if (val) description.value = val.description || ''
}, { immediate: true })

function handleRefImageAdd(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    refImageUrls.value.push(ev.target.result)
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

async function handleExtract() {
  if (refImageUrls.value.length === 0) return
  extracting.value = true
  const result = await store.extractDescription(props.projectId, {
    reference_image_urls: refImageUrls.value,
  })
  if (result) {
    description.value = result
    ElMessage.success('描述提取成功')
  }
  extracting.value = false
}

function handleSubmit() {
  emit('submit', {
    assetId: props.character.id,
    data: {
      reference_image_urls: refImageUrls.value,
      description: description.value || null,
      mode: mode.value,
    },
  })
  refImageUrls.value = []
  mode.value = 'direct'
}
</script>

<style scoped>
.edit-dialog { max-width: 32rem; width: 90%; border-radius: var(--glass-radius-xl); }
.edit-header { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid var(--glass-stroke-base); }
.edit-header h3 { font-weight: 700; font-size: 1rem; color: var(--glass-text-primary); }
.edit-body { padding: 1.25rem; display: flex; flex-direction: column; gap: 0.875rem; }
.edit-field { display: flex; flex-direction: column; gap: 0.375rem; }
.field-label-row { display: flex; align-items: center; justify-content: space-between; }
.field-label { font-size: 0.8125rem; font-weight: 600; color: var(--glass-text-primary); }
.ai-btn { display: flex; align-items: center; gap: 0.25rem; padding: 0.25rem 0.625rem; font-size: 0.6875rem; font-weight: 500; border-radius: 999px; background: var(--glass-tone-info-bg); color: var(--glass-tone-info-fg); }
.ai-btn:hover:not(:disabled) { background: var(--glass-accent-from); color: white; }
.ai-btn:disabled { opacity: 0.6; cursor: wait; }

.mode-select { display: flex; gap: 0.5rem; }
.mode-btn { padding: 0.375rem 0.875rem; border-radius: 999px; font-size: 0.8125rem; color: var(--glass-text-secondary); background: var(--glass-bg-muted); border: 1px solid var(--glass-stroke-base); transition: all 0.15s ease; }
.mode-btn.active { background: var(--glass-accent-from); color: white; border-color: transparent; }

.ref-images { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.ref-image-item { position: relative; width: 4rem; height: 4rem; border-radius: var(--glass-radius-sm); overflow: hidden; }
.ref-image-item img { width: 100%; height: 100%; object-fit: cover; }
.ref-remove { position: absolute; top: 2px; right: 2px; width: 16px; height: 16px; border-radius: 50%; background: rgba(0,0,0,0.6); color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; }
.ref-add { width: 4rem; height: 4rem; border-radius: var(--glass-radius-sm); border: 1px dashed var(--glass-stroke-base); display: flex; align-items: center; justify-content: center; cursor: pointer; }

.edit-footer { display: flex; justify-content: flex-end; gap: 0.5rem; padding: 0.875rem 1.25rem; border-top: 1px solid var(--glass-stroke-base); }
</style>
