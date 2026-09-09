<template>
  <Teleport to="body">
    <Transition name="sa-fade">
      <div v-if="visible" class="glass-overlay" @click.self="onCancel">
        <div class="glass-surface-modal save-asset-dialog animate-fadeIn" @click.stop>
          <div class="dialog-header">
            <h3>保存到资产中心</h3>
            <button class="glass-btn-base glass-btn-soft close-btn" @click="onCancel">
              <X :size="16" />
            </button>
          </div>

          <div class="dialog-body">
            <label class="edit-field">
              <span class="field-label">资产名称</span>
              <input
                v-model="form.name"
                class="glass-input-base"
                placeholder="默认取节点标题"
                maxlength="64"
              />
            </label>

            <div v-if="itemType === 'image'" class="edit-field">
              <span class="field-label">保存类型</span>
              <div class="radio-row">
                <button
                  v-for="opt in ASSET_KIND_OPTIONS"
                  :key="opt.value"
                  type="button"
                  class="radio-item"
                  :data-active="form.asset_kind === opt.value"
                  @click="form.asset_kind = opt.value"
                >
                  <span class="radio-dot" :data-active="form.asset_kind === opt.value" />
                  <span>{{ opt.label }}</span>
                </button>
              </div>
            </div>
            <div v-else class="info-banner">
              <Info :size="14" />
              <span>音频节点将保存为音色资产</span>
            </div>

            <label class="edit-field">
              <span class="field-label">资产组（可选）</span>
              <div class="select-wrap">
                <select
                  v-model="form.folder_id"
                  class="glass-input-base select-el"
                >
                  <option value="">不分组</option>
                  <option
                    v-for="f in folders"
                    :key="f.id"
                    :value="f.id"
                  >{{ f.name }}</option>
                  <option value="__new__">+ 新建资产组…</option>
                </select>
                <ChevronDown :size="14" class="select-caret" />
              </div>
            </label>

            <label v-if="form.folder_id === '__new__'" class="edit-field">
              <span class="field-label">新资产组名称</span>
              <input
                v-model="form.new_folder_name"
                class="glass-input-base"
                placeholder="输入资产组名称"
                maxlength="64"
              />
            </label>
          </div>

          <div class="dialog-footer">
            <button class="glass-btn-base glass-btn-secondary footer-btn" @click="onCancel">取消</button>
            <button
              class="glass-btn-base glass-btn-primary footer-btn"
              :disabled="submitting"
              @click="onSubmit"
            >保存</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { X, ChevronDown, Info } from '@lucide/vue'
import { getFolderList } from '@/api/asset/folder'
import { useCanvasStore } from '@/store/canvas'

const ASSET_KIND_OPTIONS = [
  { value: 'character', label: '角色' },
  { value: 'location', label: '场景' },
  { value: 'prop', label: '道具' },
]

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  itemId: { type: String, default: '' },
  itemType: { type: String, default: 'image' }, // image / audio
  defaultName: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const canvasStore = useCanvasStore()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const folders = ref([])
const submitting = ref(false)
const form = reactive({
  name: '',
  asset_kind: 'character',
  folder_id: '',
  new_folder_name: '',
})

watch(
  () => props.modelValue,
  async (v) => {
    if (!v) return
    form.name = props.defaultName || ''
    form.asset_kind = props.itemType === 'audio' ? 'voice' : 'character'
    form.folder_id = ''
    form.new_folder_name = ''
    await loadFolders()
  },
)

async function loadFolders() {
  try {
    const list = await getFolderList({ page: 1, size: 100 })
    folders.value = Array.isArray(list) ? list : (list?.data || [])
  } catch (e) {
    folders.value = []
  }
}

function buildPayload() {
  const payload = {
    asset_kind: props.itemType === 'audio' ? 'voice' : form.asset_kind,
    name: (form.name || '').trim() || undefined,
  }
  if (form.folder_id === '__new__') {
    if (!form.new_folder_name.trim()) {
      throw new Error('请输入新资产组名称')
    }
    payload.new_folder_name = form.new_folder_name.trim()
  } else if (form.folder_id) {
    payload.folder_id = form.folder_id
  }
  return payload
}

async function onSubmit() {
  if (!props.itemId) {
    ElMessage.error('缺少节点 id')
    return
  }
  let payload
  try {
    payload = buildPayload()
  } catch (e) {
    ElMessage.error(e.message)
    return
  }
  submitting.value = true
  try {
    const resp = await canvasStore.saveItemToAssetCenter(props.itemId, payload)
    ElMessage.success('已保存到资产中心')
    emit('saved', resp)
    visible.value = false
  } catch (e) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    submitting.value = false
  }
}

function onCancel() {
  visible.value = false
}
</script>

<style scoped>
.save-asset-dialog {
  max-width: 28rem;
  width: 90%;
  border-radius: var(--glass-radius-xl);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--glass-stroke-base);
}

.dialog-header h3 {
  font-weight: 700;
  font-size: 1rem;
  color: var(--glass-text-primary);
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--glass-text-tertiary);
}
.close-btn:hover {
  color: var(--glass-text-secondary);
}

.dialog-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-text-primary);
}

.dialog-body .glass-input-base {
  padding: 8px 12px;
  font-size: 13px;
}

.radio-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.radio-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-secondary);
  background: var(--glass-bg-muted);
  border: 1px solid var(--glass-stroke-base);
  border-radius: var(--glass-radius-xs);
  cursor: pointer;
  transition: all 0.2s ease;
}
.radio-item:hover {
  color: var(--glass-text-primary);
  border-color: var(--glass-stroke-strong);
}
.radio-item[data-active='true'] {
  color: var(--glass-text-on-accent);
  background: var(--glass-accent-from);
  border-color: var(--glass-accent-from);
}
.radio-item[data-active='true'] .radio-dot {
  background: var(--glass-text-on-accent);
  border-color: var(--glass-text-on-accent);
}

.radio-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid var(--glass-stroke-strong);
  background: var(--glass-bg-surface);
  transition: all 0.2s ease;
  position: relative;
  flex-shrink: 0;
}
.radio-dot[data-active='true']::after {
  content: '';
  position: absolute;
  inset: 3px;
  border-radius: 50%;
  background: var(--glass-text-on-accent);
}

.info-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--glass-text-secondary);
  background: var(--glass-bg-muted);
  border-radius: var(--glass-radius-xs);
}

.select-wrap {
  position: relative;
}

.select-el {
  width: 100%;
  appearance: none;
  -webkit-appearance: none;
  padding-right: 32px;
  cursor: pointer;
}

.select-caret {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--glass-text-tertiary);
  pointer-events: none;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem;
  border-top: 1px solid var(--glass-stroke-base);
}

.footer-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
}

.sa-fade-enter-active,
.sa-fade-leave-active {
  transition: opacity 0.2s ease;
}

.sa-fade-enter-from,
.sa-fade-leave-to {
  opacity: 0;
}
</style>
