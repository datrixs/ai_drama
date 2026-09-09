<template>
  <el-dialog
    v-model="visible"
    width="520px"
    align-center
    :show-close="true"
    class="director-dialog"
    @close="handleClose"
  >
    <template #header>
      <div class="director-dialog-title">导演模式 · 新建项目</div>
    </template>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      class="director-form"
      @submit.prevent
    >
      <el-form-item label="项目名称" prop="title">
        <el-input
          v-model="form.title"
          placeholder="给项目起个名字"
          maxlength="100"
          show-word-limit
        />
      </el-form-item>

      <div class="form-row">
        <el-form-item label="画面比例" prop="video_ratio">
          <el-select v-model="form.video_ratio" placeholder="选择画面比例">
            <el-option label="21:9" value="21:9" />
            <el-option label="16:9" value="16:9" />
            <el-option label="4:3" value="4:3" />
            <el-option label="1:1" value="1:1" />
            <el-option label="3:4" value="3:4" />
            <el-option label="9:16" value="9:16" />
          </el-select>
        </el-form-item>

        <el-form-item label="画面风格" prop="art_style">
          <el-select v-model="form.art_style" placeholder="选择画面风格">
            <el-option label="漫画风" value="american-comic" />
            <el-option label="精致国漫" value="chinese-comic" />
            <el-option label="日系动漫风" value="japanese-anime" />
            <el-option label="真人风格" value="realistic" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="预计集数" prop="expected_episodes">
        <el-input-number
          v-model="form.expected_episodes"
          :min="0"
          :max="50"
          :step="1"
          controls-position="right"
          class="ep-counter"
        />
        <div class="ep-hint">后续可随时新增或删除剧集</div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <button class="glass-btn-base glass-btn-secondary" @click="handleClose">
          取消
        </button>
        <button
          class="glass-btn-base glass-btn-primary"
          :disabled="submitting"
          @click="submit"
        >
          {{ submitting ? '创建中...' : '创建项目' }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createProject } from '@/api/project'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'created'])

const router = useRouter()
const visible = ref(props.modelValue)
const formRef = ref(null)
const submitting = ref(false)

watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

const form = reactive({
  title: '',
  video_ratio: '9:16',
  art_style: 'realistic',
  expected_episodes: 5,
})

const rules = {
  title: [
    { required: true, message: '请填写项目名称', trigger: 'blur' },
    { max: 100, message: '不超过 100 字', trigger: 'blur' },
  ],
  video_ratio: [{ required: true, message: '请选择画面比例', trigger: 'change' }],
  art_style: [{ required: true, message: '请选择画面风格', trigger: 'change' }],
  expected_episodes: [
    { required: true, message: '请填写预计集数', trigger: 'change' },
    { type: 'number', min: 0, max: 50, message: '集数范围 0-50', trigger: 'change' },
  ],
}

function resetForm() {
  form.title = ''
  form.video_ratio = '9:16'
  form.art_style = 'realistic'
  form.expected_episodes = 5
  formRef.value?.clearValidate?.()
}

function handleClose() {
  visible.value = false
}

async function submit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const res = await createProject({
      mode: 'director',
      title: form.title.trim(),
      video_ratio: form.video_ratio,
      art_style: form.art_style,
      expected_episodes: form.expected_episodes,
    })
    ElMessage.success('项目已创建')
    visible.value = false
    const projectId = res?.id || res?.data?.id
    emit('created', res)
    if (projectId) {
      router.push(`/workspace/${projectId}`)
    }
  } catch (e) {
    ElMessage.error(e?.message || '创建失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

watch(visible, (v) => {
  if (v) resetForm()
})
</script>

<style scoped>
.director-dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--glass-text-primary);
}
.director-form {
  padding: 4px 0;
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.ep-counter {
  width: 100%;
}
.ep-hint {
  font-size: 12px;
  color: var(--glass-text-tertiary, #6b7280);
  margin-top: 6px;
  line-height: 1.5;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.dialog-footer .glass-btn-base {
  min-width: 96px;
  padding: 9px 18px;
  font-size: 14px;
  border-radius: 12px;
}
.dialog-footer .glass-btn-primary {
  background: linear-gradient(135deg, var(--glass-accent-from, #2f7bff), var(--glass-accent-to, #5ca8ff));
  box-shadow: 0 4px 14px var(--glass-accent-shadow-soft, rgba(47, 123, 255, 0.24));
}
.dialog-footer .glass-btn-primary:hover:not(:disabled) {
  filter: brightness(1.08);
  box-shadow: 0 6px 20px var(--glass-accent-shadow-strong, rgba(47, 123, 255, 0.32));
  transform: translateY(-1px);
}
.dialog-footer .glass-btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  filter: grayscale(0.2);
}

/* ===== Element Plus 控件玻璃化 ===== */
.director-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 700;
  color: var(--glass-text-primary, #0a0a0a);
  letter-spacing: 0.01em;
  padding-bottom: 6px;
  line-height: 1.4;
}
.director-form :deep(.el-input__wrapper),
.director-form :deep(.el-select__wrapper),
.director-form :deep(.el-input-number) {
  background: var(--glass-bg-muted, rgba(244, 247, 252, 0.6));
  border-radius: var(--glass-radius-md, 10px);
  box-shadow: inset 0 0 0 1px var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  transition: box-shadow 0.2s ease, background-color 0.2s ease;
}
.director-form :deep(.el-input__wrapper:hover),
.director-form :deep(.el-select__wrapper:hover),
.director-form :deep(.el-input-number:hover) {
  box-shadow: inset 0 0 0 1px var(--glass-stroke-strong, rgba(111, 126, 153, 0.45));
}
.director-form :deep(.el-input__wrapper.is-focus),
.director-form :deep(.el-select__wrapper.is-focused),
.director-form :deep(.el-input-number .el-input__wrapper.is-focus) {
  box-shadow:
    inset 0 0 0 1px var(--glass-stroke-focus, #2f7bff),
    0 0 0 3px var(--glass-focus-ring, rgba(47, 123, 255, 0.16));
  background: var(--glass-bg-surface-strong, #fff);
}
.director-form :deep(.el-input__inner),
.director-form :deep(.el-select__placeholder),
.director-form :deep(.el-select__selected-item) {
  color: var(--glass-text-primary, #0a0a0a);
}
.director-form :deep(.el-input__inner::placeholder) {
  color: var(--glass-text-tertiary, #9ca3af);
  opacity: 0.85;
}
/* el-input-number 整体边框（默认 input__wrapper 不撑满） */
.director-form :deep(.el-input-number .el-input-number__decrease),
.director-form :deep(.el-input-number .el-input-number__increase) {
  background: transparent;
  border-color: var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  color: var(--glass-text-secondary, #4b5563);
}
.director-form :deep(.el-input-number .el-input-number__decrease:hover),
.director-form :deep(.el-input-number .el-input-number__increase:hover) {
  color: var(--glass-stroke-focus, #2f7bff);
}
/* 错误态：用 glass 危险色 */
.director-form :deep(.el-form-item.is-error .el-input__wrapper),
.director-form :deep(.el-form-item.is-error .el-select__wrapper),
.director-form :deep(.el-form-item.is-error .el-input-number .el-input__wrapper) {
  box-shadow:
    inset 0 0 0 1px var(--glass-stroke-danger, #ef4444),
    0 0 0 2px var(--glass-danger-ring, rgba(239, 68, 68, 0.16));
}
.director-form :deep(.el-form-item__error) {
  font-size: 12px;
  padding-top: 4px;
}
</style>

<style>
.director-dialog {
  border-radius: 22px !important;
  overflow: hidden;
}
.director-dialog .el-dialog__header {
  margin: 0;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(111, 126, 153, 0.18);
}
.director-dialog .el-dialog__body {
  padding: 20px 24px 8px;
}
.director-dialog .el-dialog__footer {
  padding: 12px 24px 20px;
  border-top: 1px solid rgba(111, 126, 153, 0.12);
}
</style>
