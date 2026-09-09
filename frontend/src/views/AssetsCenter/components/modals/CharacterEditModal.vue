<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')">
    <div class="modal-card glass-surface-modal">
      <!-- 标题 -->
      <div class="modal-header">
        <h3 class="modal-title">编辑角色 - {{ character.name }}</h3>
        <button class="glass-btn-base glass-btn-soft modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>

      <!-- 可滚动主体 -->
      <div class="modal-body">
        <!-- 角色名称 + 资产组 -->
        <div class="form-field">
          <div class="name-row">
            <div class="name-col">
              <label class="glass-field-label">角色名</label>
              <div class="name-input-row">
                <input
                  v-model="editingName"
                  class="glass-input-base"
                  placeholder="输入角色名称..."
                />
                <button
                  v-if="editingName !== character.name"
                  class="glass-btn-base glass-btn-tone-success name-save-btn"
                  :disabled="isSavingName"
                  @click="saveName"
                >
                  {{ isSavingName ? '保存中...' : '保存名字' }}
                </button>
              </div>
            </div>
            <div class="folder-col">
              <label class="glass-field-label">资产组</label>
              <el-select
                v-model="editingFolderId"
                placeholder="选择资产组"
                popper-class="folder-select-popper"
                class="folder-select"
              >
                <el-option label="所有资产" value="" />
                <el-option v-for="f in store.folders" :key="f.id" :label="f.name" :value="f.id" />
              </el-select>
            </div>
          </div>
        </div>

        <!-- 形象切换 -->
        <div v-if="character.appearances.length > 1" class="form-field">
          <label class="glass-field-label">形象切换</label>
          <div class="appearance-tabs">
            <button
              v-for="(app, idx) in character.appearances"
              :key="app.id"
              class="glass-btn-base appearance-tab"
              :class="idx === activeAppearance ? 'glass-btn-primary' : 'glass-btn-soft'"
              @click="switchAppearance(idx)"
            >
              形象 {{ idx + 1 }}
            </button>
          </div>
        </div>

        <!-- 形象标识 -->
        <div v-if="currentAppearance?.change_reason" class="appearance-label">
          形象: <span class="appearance-label-value">{{ currentAppearance.change_reason }}</span>
        </div>

        <!-- 形象描述提示词（含叠加 AI 修改按钮） -->
        <div class="form-field">
          <label class="glass-field-label">形象描述提示词</label>
          <div class="desc-textarea-wrap">
            <textarea
              v-model="editingDescription"
              class="desc-textarea"
              placeholder="输入角色形象描述..."
            ></textarea>
            <div class="ai-modify-overlay">
              <button
                class="glass-btn-base ai-modify-float-btn"
                @click="showAiModifyModal = true"
              >
                <Sparkles :size="16" class="ai-modify-float-icon" />
                <span class="ai-modify-float-text">AI修改描述</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 模型提示词 -->
        <div class="form-field">
          <label class="glass-field-label">模型提示词</label>
          <textarea
            v-model="editingModelPrompt"
            class="glass-textarea-base model-prompt-textarea"
            rows="3"
            placeholder="对生图模型的统一要求（如画风、画幅、禁止项等），将与上方形象描述一起发送。"
          ></textarea>
          <span class="glass-field-hint">保存后生效；触发生成或「生成图片」时，会与形象描述一起发给当前项目配置的生图模型。</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="modal-footer">
        <button
          class="glass-btn-base glass-btn-secondary"
          :disabled="isSaving"
          @click="$emit('close')"
        >
          取消
        </button>
        <button
          class="glass-btn-base glass-btn-tone-info"
          :disabled="isSaving || !editingDescription.trim()"
          @click="saveOnly"
        >
          仅保存
        </button>
        <button
          class="glass-btn-base glass-btn-primary"
          :disabled="isSaving || !editingDescription.trim()"
          @click="saveAndGenerate"
        >
          保存并生成
        </button>
      </div>
    </div>

    <!-- AI 修改描述嵌套弹窗 -->
    <div v-if="showAiModifyModal" class="modal-overlay glass-overlay" style="z-index: 10001" @click.self="showAiModifyModal = false">
      <div class="ai-modal glass-surface-modal">
        <div class="ai-modal-header">
          <h3 class="ai-modal-title">AI修改描述</h3>
          <button class="glass-btn-base glass-btn-ghost ai-modal-close-btn" @click="showAiModifyModal = false">
            <X :size="20" />
          </button>
        </div>
        <div class="glass-divider"></div>
        <div class="ai-modal-body">
          <textarea
            v-model="aiModifyInstruction"
            class="glass-textarea-base"
            placeholder="例如：把头发改成金色、身高改为180cm、穿黑色西装..."
            autofocus
          ></textarea>
        </div>
        <div class="glass-divider"></div>
        <div class="ai-modal-footer">
          <button class="glass-btn-base glass-btn-secondary" @click="showAiModifyModal = false">
            取消
          </button>
          <button
            class="glass-btn-base glass-btn-primary"
            :disabled="!aiModifyInstruction.trim() || isAiModifying"
            @click="handleAiModify"
          >
            <LoaderCircle v-if="isAiModifying" :size="14" class="is-loading" />
            {{ isAiModifying ? '修改中...' : 'AI修改描述' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { X, Sparkles, LoaderCircle } from '@lucide/vue'
import { useAssetHubStore } from '@/store/assetHub'
import { submitAsyncTask } from '@/utils/asyncTask'

const props = defineProps({
  character: { type: Object, required: true },
  appearanceIndex: { type: Number, default: 0 }
})

const emit = defineEmits(['close'])

const store = useAssetHubStore()

const editingName = ref(props.character.name)
const editingFolderId = ref(props.character.folder_id || '')
const editingDescription = ref('')
const editingModelPrompt = ref('')
const aiModifyInstruction = ref('')
const isSaving = ref(false)
const isSavingName = ref(false)
const activeAppearance = ref(props.appearanceIndex)
const showAiModifyModal = ref(false)
const isAiModifying = ref(false)

const currentAppearance = computed(() =>
  props.character.appearances?.[activeAppearance.value]
)

function syncDescription() {
  editingDescription.value = currentAppearance.value?.description || ''
  editingModelPrompt.value = currentAppearance.value?.image_model_system_prompt || ''
}

syncDescription()

watch(activeAppearance, syncDescription)

function switchAppearance(idx) {
  activeAppearance.value = idx
}

async function saveName() {
  if (!editingName.value.trim() || editingName.value === props.character.name) return
  isSavingName.value = true
  try {
    await store.updateCharacter(props.character.id, { name: editingName.value })
    ElMessage.success('名称已保存')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    isSavingName.value = false
  }
}

async function handleAiModify() {
  const instruction = aiModifyInstruction.value.trim()
  if (!instruction || isAiModifying.value) return
  isAiModifying.value = true
  try {
    const result = await submitAsyncTask(
      '/asset-hub/ai-modify-character',
      {
        character_id: props.character.id,
        appearance_index: activeAppearance.value,
        current_description: editingDescription.value,
        modify_instruction: instruction
      },
      { successMsg: 'AI 修改描述完成' }
    )
    if (result?.prompt) {
      editingDescription.value = result.prompt
    }
    showAiModifyModal.value = false
    aiModifyInstruction.value = ''
  } catch {
    // submitAsyncTask already shows error message
  } finally {
    isAiModifying.value = false
  }
}

async function saveOnly() {
  isSaving.value = true
  try {
    if (editingName.value.trim() !== props.character.name) {
      await store.updateCharacter(props.character.id, { name: editingName.value })
    }
    if (editingFolderId.value !== (props.character.folder_id || '')) {
      await store.updateCharacter(props.character.id, { folder_id: editingFolderId.value || null })
    }
    if (currentAppearance.value) {
      await store.updateAppearance({
        character_id: props.character.id,
        appearance_index: currentAppearance.value.appearance_index,
        description: editingDescription.value,
        image_model_system_prompt: editingModelPrompt.value.trim() || null
      })
    }
    emit('close')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    isSaving.value = false
  }
}

async function saveAndGenerate() {
  isSaving.value = true
  try {
    if (editingName.value.trim() !== props.character.name) {
      await store.updateCharacter(props.character.id, { name: editingName.value })
    }
    if (editingFolderId.value !== (props.character.folder_id || '')) {
      await store.updateCharacter(props.character.id, { folder_id: editingFolderId.value || null })
    }
    if (currentAppearance.value) {
      await store.updateAppearance({
        character_id: props.character.id,
        appearance_index: currentAppearance.value.appearance_index,
        description: editingDescription.value,
        image_model_system_prompt: editingModelPrompt.value.trim() || null
      })
    }

    await submitAsyncTask(
      '/asset-hub/generate-image',
      {
        type: 'character',
        id: props.character.id,
        appearance_index: activeAppearance.value,
        count: 1,
        art_style: currentAppearance.value?.art_style || '',
      },
      { successMsg: '图片生成完成' }
    )
    await store.fetchCharacters()
    emit('close')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    isSaving.value = false
  }
}

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 672px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-close-btn:hover {
  color: var(--glass-text-secondary);
}

/* Form fields */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.name-row {
  display: flex;
  gap: 8px;
}

.name-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.folder-col {
  width: 160px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.name-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.name-input-row .glass-input-base {
  flex: 1;
  min-width: 0;
  padding: 8px 12px;
}

.folder-select :deep(.el-select__wrapper) {
  border-radius: var(--glass-radius-md);
}

.name-save-btn {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  white-space: nowrap;
}

/* Appearance tabs */
.appearance-tabs {
  display: flex;
  gap: 4px;
  overflow-x: auto;
}

.appearance-tab {
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 999px;
  white-space: nowrap;
}

/* Appearance label */
.appearance-label {
  font-size: 14px;
  color: var(--glass-text-secondary);
}

.appearance-label-value {
  font-weight: 500;
  color: var(--glass-text-primary);
}

/* 描述 textarea 容器（含叠加 AI 修改按钮） */
.desc-textarea-wrap {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-surface);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.desc-textarea-wrap:hover {
  border-color: var(--glass-stroke-strong);
}

.desc-textarea-wrap:focus-within {
  border-color: var(--glass-stroke-focus);
  background: var(--glass-bg-surface-strong);
  box-shadow: 0 0 0 3px var(--glass-focus-ring);
}

.desc-textarea {
  width: 100%;
  height: 256px;
  resize: none;
  border: 0;
  background: transparent;
  padding: 12px 16px;
  padding-bottom: 64px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--glass-text-primary);
  outline: none;
}

.desc-textarea::placeholder {
  color: var(--glass-text-tertiary);
}

/* AI 修改叠加按钮 */
.ai-modify-overlay {
  position: absolute;
  bottom: 16px;
  right: 16px;
  pointer-events: none;
}

.ai-modify-float-btn {
  pointer-events: auto;
  height: 40px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--glass-stroke-strong);
  background: var(--glass-bg-surface);
  font-size: 14px;
  transition: border-color 0.15s;
}

.ai-modify-float-btn:hover {
  border-color: var(--glass-tone-info-fg);
}

.ai-modify-float-icon {
  color: #7c3aed;
  flex-shrink: 0;
}

.ai-modify-float-text {
  font-weight: 500;
  background: linear-gradient(135deg, #3b82f6, #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* AI 修改嵌套弹窗 */
.ai-modal {
  max-width: 448px;
  width: 100%;
  overflow: hidden;
}

.ai-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
}

.ai-modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0;
}

.ai-modal-close-btn {
  height: 36px;
  width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--glass-text-tertiary);
}

.ai-modal-close-btn:hover {
  color: var(--glass-text-secondary);
}

.ai-modal-body {
  padding: 16px 20px;
}

.ai-modal-body .glass-textarea-base {
  width: 100%;
  height: 128px;
  padding: 12px 16px;
  font-size: 14px;
  resize: none;
}

.ai-modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 20px;
}

.ai-modal-footer .glass-btn-base {
  padding: 8px 16px;
  border-radius: 8px;
}

/* 模型提示词 textarea */
.model-prompt-textarea {
  width: 100%;
  min-height: 80px;
  resize: none;
  padding: 8px 12px;
}

/* Footer */
.modal-footer {
  padding: 16px;
}

.modal-footer .glass-btn-base {
  padding: 8px 16px;
  border-radius: 8px;
}
</style>

<style>
.folder-select-popper {
  z-index: 10000 !important;
}
</style>
