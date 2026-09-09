<template>
  <Teleport to="body">
    <Transition name="bsa-fade">
      <div v-if="visible" class="glass-overlay" @click.self="onCancel">
        <div class="glass-surface-modal batch-save-dialog animate-fadeIn" @click.stop>
          <div class="dialog-header">
            <h3>批量保存到资产中心</h3>
            <button class="glass-btn-base glass-btn-soft close-btn" @click="onCancel">
              <X :size="16" />
            </button>
          </div>

          <div class="dialog-body">
            <div class="info-banner">
              <Info :size="14" />
              <span>
                将按节点自身标记自动归类入库：
                image 节点按"角色/场景/道具"标记保存；audio 节点保存为音色。
                共 <b>{{ candidateCount }}</b> 个候选资产。
              </span>
            </div>

            <label class="edit-field">
              <span class="field-label">资产组（可选）</span>
              <div class="select-wrap">
                <select v-model="form.folder_id" class="glass-input-base select-el">
                  <option value="">不分组</option>
                  <option v-for="f in folders" :key="f.id" :value="f.id">{{ f.name }}</option>
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
              :disabled="submitting || candidateCount === 0"
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

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  documentId: { type: String, default: '' },
  candidateCount: { type: Number, default: 0 },
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
  folder_id: '',
  new_folder_name: '',
})

watch(
  () => props.modelValue,
  async (v) => {
    if (!v) return
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
  const payload = {}
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
  if (!props.documentId) {
    ElMessage.error('缺少画布 id')
    return
  }
  if (props.candidateCount === 0) {
    ElMessage.info('暂无可批量保存的资产')
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
    const resp = await canvasStore.batchSaveToAssetCenter(props.documentId, payload)
    const data = resp?.data || resp || {}
    const saved = data.saved || []
    const skipped = data.skipped || []
    const msg = skipped.length
      ? `已保存 ${saved.length} 个资产，跳过 ${skipped.length} 个`
      : `已保存 ${saved.length} 个资产`
    ElMessage.success(msg)
    emit('saved', data)
    visible.value = false
  } catch (e) {
    ElMessage.error(e?.message || '批量保存失败')
  } finally {
    submitting.value = false
  }
}

function onCancel() {
  visible.value = false
}
</script>

<style scoped>
.batch-save-dialog {
  max-width: 30rem;
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

.info-banner {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--glass-text-secondary);
  background: var(--glass-bg-muted);
  border-radius: var(--glass-radius-xs);
}

.info-banner b {
  color: var(--glass-text-primary);
  font-weight: 700;
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

.bsa-fade-enter-active,
.bsa-fade-leave-active {
  transition: opacity 0.2s ease;
}

.bsa-fade-enter-from,
.bsa-fade-leave-to {
  opacity: 0;
}
</style>
