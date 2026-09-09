<template>
  <div class="change-password">
    <div class="section-header">
      <h2 class="section-title">修改密码</h2>
    </div>

    <div class="content-area">
      <div class="content-inner">
        <div class="custom-form">
          <div class="form-field">
            <label class="form-label">原密码 <span class="required">*</span></label>
            <div class="input-wrapper">
              <input
                v-model="form.oldPassword"
                :type="showOld ? 'text' : 'password'"
                class="form-input"
                placeholder="请输入当前密码"
                maxlength="64"
                autocomplete="current-password"
              />
              <button type="button" class="toggle-btn" @click="showOld = !showOld">
                <Eye v-if="!showOld" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
          </div>

          <div class="form-field">
            <label class="form-label">新密码 <span class="required">*</span></label>
            <div class="input-wrapper">
              <input
                v-model="form.newPassword"
                :type="showNew ? 'text' : 'password'"
                class="form-input"
                placeholder="6-64 位字符"
                maxlength="64"
                autocomplete="new-password"
              />
              <button type="button" class="toggle-btn" @click="showNew = !showNew">
                <Eye v-if="!showNew" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
          </div>

          <div class="form-field">
            <label class="form-label">确认新密码 <span class="required">*</span></label>
            <div class="input-wrapper">
              <input
                v-model="form.confirmPassword"
                :type="showConfirm ? 'text' : 'password'"
                class="form-input"
                placeholder="请再次输入新密码"
                maxlength="64"
                autocomplete="new-password"
                @keyup.enter="handleSubmit"
              />
              <button type="button" class="toggle-btn" @click="showConfirm = !showConfirm">
                <Eye v-if="!showConfirm" :size="16" />
                <EyeOff v-else :size="16" />
              </button>
            </div>
          </div>

          <div class="form-actions">
            <button
              class="btn-primary"
              :disabled="!isFormValid || submitting"
              @click="handleSubmit"
            >
              {{ submitting ? '修改中...' : '确认修改' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Eye, EyeOff } from '@lucide/vue'
import { changePassword } from '@/api/user'

const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const showOld = ref(false)
const showNew = ref(false)
const showConfirm = ref(false)
const submitting = ref(false)

const isFormValid = computed(() => {
  return (
    form.oldPassword.length > 0 &&
    form.newPassword.length >= 6 &&
    form.newPassword.length <= 64 &&
    form.confirmPassword === form.newPassword
  )
})

const resetForm = () => {
  form.oldPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
}

const handleSubmit = async () => {
  if (!isFormValid.value || submitting.value) return
  submitting.value = true
  try {
    await changePassword({
      old_password: form.oldPassword,
      new_password: form.newPassword
    })
    ElMessage.success('密码修改成功')
    resetForm()
  } catch {
    // 错误由 request 拦截器统一提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.change-password {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.section-header {
  padding: 16px 24px;
  border-bottom: 0.667px solid rgba(111, 126, 153, 0.12);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.98);
  z-index: 1;
  border-radius: 16px 16px 0 0;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #0a0a0a;
  margin: 0;
}

.content-area {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.content-inner {
  padding: 24px;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 480px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 14px;
  color: #111827;
}

.form-label .required {
  color: #f87171;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.form-input {
  width: 100%;
  border-radius: 10px;
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  background: rgba(255, 255, 255, 0.86);
  padding: 8px 36px 8px 12px;
  font-size: 14px;
  color: #0a0a0a;
  outline: none;
  transition: border-color 0.2s;
  line-height: 20px;
  box-sizing: border-box;
  box-shadow: none;
}

.form-input:focus {
  border-color: #2f7bff;
}

.form-input::placeholder {
  color: #9ca3af;
}

.toggle-btn {
  position: absolute;
  right: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
}

.toggle-btn:hover {
  color: #2f7bff;
}

.form-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: opacity 0.2s;
  height: 33px;
  box-shadow: rgba(47, 123, 255, 0.24) 0px 8px 20px 0px;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
