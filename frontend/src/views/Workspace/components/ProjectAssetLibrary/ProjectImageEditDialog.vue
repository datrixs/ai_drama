<template>
  <div class="modal-overlay glass-overlay" @click.self="$emit('close')" @paste="handlePaste">
    <div class="modal-card glass-surface-modal">
      <!-- Header -->
      <div class="modal-header">
        <div>
          <h3 class="modal-title">{{ titleText }}</h3>
          <p class="modal-subtitle">{{ typeLabel }}: {{ asset?.name }} · 输入修改指令，可选择上传参考图片</p>
        </div>
        <button class="glass-btn-base glass-btn-soft modal-close-btn" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="modal-body">
        <!-- Image preview -->
        <div v-if="asset?.image_url" class="image-preview">
          <img :src="asset.image_url" class="preview-img" />
        </div>

        <!-- Instruction -->
        <div class="form-field">
          <label class="glass-field-label">修改指令</label>
          <textarea
            v-model="modifyPrompt"
            class="glass-textarea-base"
            style="height: 96px; resize: none; padding: 8px 12px"
            :placeholder="placeholderText"
          ></textarea>
        </div>

        <!-- Reference images -->
        <div class="form-field">
          <label class="glass-field-label">参考图片 <span class="field-hint">(可选，支持粘贴)</span></label>
          <div class="ref-images-grid">
            <div v-for="(img, idx) in refImageUrls" :key="idx" class="ref-thumb">
              <img :src="img" class="ref-thumb-img" />
              <button class="ref-thumb-remove" @click="removeImage(idx)">
                <X :size="10" />
              </button>
            </div>
            <button class="ref-add-btn" @click="fileInputRef?.click()">
              <Plus :size="20" />
            </button>
          </div>
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            multiple
            style="display: none"
            @change="handleImageUpload"
          />
        </div>
      </div>

      <!-- Footer -->
      <div class="modal-footer">
        <button class="cancel-btn" @click="$emit('close')">
          取消
        </button>
        <button
          class="submit-btn"
          :disabled="!modifyPrompt.trim()"
          @click="handleSubmit"
        >
          开始编辑
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { X, Plus } from '@lucide/vue'

const props = defineProps({
  visible: Boolean,
  asset: Object,
  assetType: { type: String, required: true },
  projectId: String,
})

const emit = defineEmits(['close', 'submit'])

const modifyPrompt = ref('')
const refImageUrls = ref([])
const fileInputRef = ref(null)

const typeLabel = computed(() => {
  const map = { character: '人物', location: '场景', prop: '道具' }
  return map[props.assetType] || ''
})

const titleText = computed(() => {
  const map = { character: '编辑人物图片', location: '编辑场景图片', prop: '编辑道具图片' }
  return map[props.assetType] || '编辑图片'
})

const placeholderText = computed(() => {
  const map = {
    character: '描述你想要修改的内容，例如：把头发改成金色、添加眼镜、换成休闲装...',
    location: '描述你想要修改的内容，例如：添加更多树木、改成夜晚场景...',
    prop: '描述你想要修改的内容，例如：改成银色金属材质、刀柄增加雕纹、去掉宝石装饰...',
  }
  return map[props.assetType] || '描述你想要的修改效果...'
})

function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function handleImageUpload(event) {
  const files = event.target.files
  if (!files || files.length === 0) return
  Array.from(files).forEach((file) => {
    readFileAsDataURL(file).then((dataUrl) => {
      refImageUrls.value.push(dataUrl)
    })
  })
  event.target.value = ''
}

function handlePaste(event) {
  const items = event.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        readFileAsDataURL(file).then((dataUrl) => {
          refImageUrls.value.push(dataUrl)
        })
      }
    }
  }
}

function removeImage(index) {
  refImageUrls.value.splice(index, 1)
}

function handleSubmit() {
  if (!modifyPrompt.value.trim()) return
  emit('submit', {
    assetType: props.assetType,
    assetId: props.asset.id,
    data: {
      modify_prompt: modifyPrompt.value,
      extra_image_urls: refImageUrls.value.length > 0 ? refImageUrls.value : undefined,
    },
  })
  modifyPrompt.value = ''
  refImageUrls.value = []
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
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  align-items: flex-start;
  padding: 16px 20px;
}

.modal-subtitle {
  font-size: 13px;
  color: var(--glass-text-tertiary);
  margin: 4px 0 0;
}

.modal-body {
  gap: 12px;
}

.modal-footer {
  border-top: 1px solid var(--glass-stroke-strong);
  padding: 16px 20px;
}

.cancel-btn {
  padding: 8px 16px;
  color: var(--glass-text-secondary);
  border-radius: 8px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
}

.cancel-btn:hover {
  background: var(--glass-bg-muted);
}

.submit-btn {
  padding: 8px 16px;
  background: var(--glass-accent-from);
  color: #fff;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 14px;
}

.submit-btn:hover {
  background: var(--glass-accent-to);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Image preview */
.image-preview {
  display: flex;
  justify-content: center;
}

.preview-img {
  max-height: 200px;
  object-fit: contain;
  border-radius: 8px;
  background: var(--glass-bg-muted);
}

/* Form fields */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-hint {
  font-size: 12px;
  color: var(--glass-text-tertiary);
  font-weight: normal;
}

/* Reference images grid */
.ref-images-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ref-thumb {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: 6px;
  overflow: hidden;
}

.ref-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ref-thumb-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.ref-thumb-remove:hover {
  background: var(--glass-tone-danger-fg);
}

.ref-add-btn {
  width: 64px;
  height: 64px;
  border-radius: 6px;
  border: 2px dashed var(--glass-stroke-strong);
  background: transparent;
  color: var(--glass-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ref-add-btn:hover {
  border-color: var(--glass-tone-info-fg);
  color: var(--glass-tone-info-fg);
}
</style>
