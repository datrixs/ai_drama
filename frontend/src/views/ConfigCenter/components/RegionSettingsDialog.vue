<template>
  <Teleport to="body">
    <div v-if="modelValue" class="glass-overlay member-overlay" @click.self="handleClose">
      <div class="glass-surface-modal member-dialog member-dialog-enter region-dialog" @click.stop @keydown.esc="handleClose">
        <div class="modal-header">
          <h3 class="modal-title">区域切换</h3>
          <button class="modal-close-btn" @click="handleClose">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>

        <div class="modal-body member-body">
          <div class="region-tip">
            <Info :size="14" />
            <span>切换区域后，已有资产保留；新区域上传的资产将同步到对应平台（火山引擎 / BytePlus）。</span>
          </div>

          <div class="region-options">
            <div
              class="region-card region-card-domestic"
              :class="{ active: selectedRegion === 'domestic' }"
              @click="selectedRegion = 'domestic'"
            >
              <div class="region-card-header">
                <div class="region-icon region-icon-domestic">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                </div>
                <div class="region-card-name">国内版</div>
                <div v-if="selectedRegion === 'domestic'" class="region-check">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                </div>
              </div>
              <div class="region-card-desc">使用火山引擎（Volc Engine）进行资产同步与视频生成</div>
              <div
                v-if="regionStatus.domestic"
                class="region-card-status"
                :class="`status-${regionStatus.domestic}`"
              >
                <template v-if="regionStatus.domestic === 'ready'">已配置 seedance 模型</template>
                <template v-else-if="regionStatus.domestic === 'unready'">未配置 seedance 模型，切换后将无法生成视频</template>
                <template v-else>检测中...</template>
              </div>
            </div>

            <div
              class="region-card region-card-overseas"
              :class="{ active: selectedRegion === 'overseas' }"
              @click="selectedRegion = 'overseas'"
            >
              <div class="region-card-header">
                <div class="region-icon region-icon-overseas">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                </div>
                <div class="region-card-name">国际版</div>
                <div v-if="selectedRegion === 'overseas'" class="region-check">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                </div>
              </div>
              <div class="region-card-desc">使用 BytePlus（火山引擎国际版）进行资产同步与视频生成</div>
              <div
                v-if="regionStatus.overseas"
                class="region-card-status"
                :class="`status-${regionStatus.overseas}`"
              >
                <template v-if="regionStatus.overseas === 'ready'">已配置 bytedance 模型</template>
                <template v-else-if="regionStatus.overseas === 'unready'">未配置 bytedance 模型，切换后将无法生成视频</template>
                <template v-else>检测中...</template>
              </div>
            </div>
          </div>
        </div>

        <div class="upgrade-footer">
          <button class="glass-btn-base glass-btn-secondary" @click="handleClose">取消</button>
          <button
            class="glass-btn-base"
            :class="selectedRegion === 'overseas' ? 'glass-btn-primary-overseas' : 'glass-btn-primary'"
            :disabled="submitting || selectedRegion === currentRegion"
            @click="handleConfirm"
          >
            <LoaderCircle v-if="submitting" :size="14" class="spin-icon" />
            <template v-else>确认切换</template>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Info, LoaderCircle } from '@lucide/vue'
import { updateUserRegion } from '@/api/user'
import { getUserApiConfig } from '@/api/userApiConfig'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  currentRegion: { type: String, default: 'domestic' },
  // 打开弹窗时默认选中的区域（通常是用户从下拉框点击的目标区域）
  defaultRegion: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'updated', 'switched'])

const selectedRegion = ref(props.defaultRegion || props.currentRegion)
const submitting = ref(false)
const configData = ref(null)
const configLoading = ref(false)

// 目标区域对应的默认视频模型（与原 AppLayout 中的映射保持一致）
const REGION_DEFAULT_VIDEO_MODEL = {
  domestic: 'doubao-seedance-2-0-260128',
  overseas: 'dreamina-seedance-2-0-260128',
}

// 检查目标区域的视频模型是否已开启 + 对应厂商 API Key 是否已配置
function checkRegionModelReady(config, region) {
  if (!config) return false
  const targetModel = REGION_DEFAULT_VIDEO_MODEL[region]
  if (!targetModel) return false

  const hasModel = (config.custom_models || []).some(
    m => m.model === targetModel && m.enabled
  )
  let hasApiKey = false
  if (region === 'overseas') {
    const provider = (config.custom_providers || []).find(
      p => (p.id || '').toLowerCase() === 'byteplus'
    )
    hasApiKey = !!(provider && provider.api_key)
  } else {
    hasApiKey = !!config.ark_api_key
  }
  return hasModel && hasApiKey
}

// 各区域配置状态：'ready' | 'unready' | 'loading'（loading 仅在拉取过程中）
const regionStatus = computed(() => {
  if (configLoading.value) {
    return { domestic: 'loading', overseas: 'loading' }
  }
  if (!configData.value) return { domestic: '', overseas: '' }
  return {
    domestic: checkRegionModelReady(configData.value, 'domestic') ? 'ready' : 'unready',
    overseas: checkRegionModelReady(configData.value, 'overseas') ? 'ready' : 'unready',
  }
})

async function loadConfig() {
  configLoading.value = true
  try {
    configData.value = await getUserApiConfig()
  } catch {
    // 读取失败时不阻断切换流程，状态显示为未配置
    configData.value = null
  } finally {
    configLoading.value = false
  }
}

watch(() => props.modelValue, (v) => {
  if (v) {
    selectedRegion.value = props.defaultRegion || props.currentRegion
    loadConfig()
  } else {
    // 关闭时重置，避免下次打开瞬间残留旧状态
    configData.value = null
  }
})

function handleClose() {
  if (submitting.value) return
  emit('update:modelValue', false)
}

async function handleConfirm() {
  if (submitting.value || selectedRegion.value === props.currentRegion) return
  submitting.value = true
  try {
    await updateUserRegion(selectedRegion.value)
    // 切换后拉取新的 video_model，交给父组件做差异化提示与刷新
    let newVideoModel = null
    try {
      const fresh = await getUserApiConfig()
      newVideoModel = fresh.video_model
    } catch {
      // 读取失败时使用通用提示
    }
    emit('switched', { region: selectedRegion.value, videoModel: newVideoModel })
    emit('updated', selectedRegion.value)
    emit('update:modelValue', false)
  } catch {
    // request 拦截器已弹错误提示
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.region-dialog {
  max-width: 520px;
}

.region-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  font-size: 12px;
  color: #1d4ed8;
  line-height: 1.5;
  margin-bottom: 16px;
}

.region-tip svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.region-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.region-card {
  position: relative;
  border: 1.5px solid rgba(111, 126, 153, 0.18);
  border-radius: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  background: #fff;
}

.region-card:hover {
  border-color: rgba(47, 123, 255, 0.35);
  background: #f8faff;
}

.region-card.active {
  border-color: #2f7bff;
  background: rgba(47, 123, 255, 0.06);
  box-shadow: 0 2px 8px rgba(47, 123, 255, 0.08);
}
.region-card-overseas.active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.06);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.08);
}

.region-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.region-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.region-icon-domestic {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.region-icon-overseas {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
}

.region-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  flex: 1;
}

.region-check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2f7bff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.region-card-desc {
  margin-top: 8px;
  padding-left: 42px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

.region-card-status {
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.region-card-status.status-ready {
  color: #2563eb;
  background: rgba(47, 123, 255, 0.08);
}
.region-card-overseas .region-card-status.status-ready {
  color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
}

.region-card-status.status-unready {
  color: #dc2626;
  background: rgba(220, 38, 38, 0.08);
}

.region-card-status.status-loading {
  color: #6b7280;
  background: rgba(111, 126, 153, 0.08);
}

.upgrade-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 28px;
  border-top: 1px solid rgba(111, 126, 153, 0.1);
  flex-shrink: 0;
}

.glass-btn-base {
  height: 34px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.glass-btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.glass-btn-secondary:hover {
  background: #e5e7eb;
}

.glass-btn-primary {
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(47, 123, 255, 0.24);
}

.glass-btn-primary-overseas {
  background: linear-gradient(140deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.24);
}

.glass-btn-primary:hover:not(:disabled) {
  opacity: 0.92;
}

.glass-btn-primary:disabled,
.glass-btn-primary-overseas:disabled {
  background: #c8d4e8;
  cursor: not-allowed;
  box-shadow: none;
}

.spin-icon {
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
