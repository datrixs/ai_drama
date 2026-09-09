<template>
  <div class="basic-settings">
    <div class="section-title">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
      </svg>
      <span>基础设置</span>
    </div>

    <!-- 项目名称 -->
    <div class="field-group">
      <label class="field-label">项目名称</label>
      <input
        :value="title"
        class="glass-input-base field-input"
        placeholder="请输入项目名称"
        maxlength="128"
        @input="handleTitleInput"
      />
    </div>

    <!-- 画面比例 & 画面风格 -->
    <div class="field-row">
      <div class="field-col">
        <label class="field-label">画面比例</label>
        <div class="selector-wrap" ref="ratioDropdownRef">
          <button type="button" class="glass-input-base selector-trigger" :class="{ active: ratioOpen }" @click="ratioOpen = !ratioOpen; styleOpen = false">
            <div class="selector-trigger-inner">
              <RatioShape :ratio="resolved.video_ratio" :size="16" />
              <span class="selector-text">{{ ratioLabel }}</span>
            </div>
            <svg class="selector-chevron" :class="{ 'rotate-180': ratioOpen }" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"></path></svg>
          </button>
          <Transition name="dropdown">
            <div v-if="ratioOpen" class="glass-surface-modal selector-dropdown">
              <div class="ratio-grid">
                <button
                  v-for="opt in VIDEO_RATIOS" :key="opt.value"
                  type="button"
                  class="ratio-item"
                  :class="{ selected: resolved.video_ratio === opt.value }"
                  @click="handleChange('video_ratio', opt.value); ratioOpen = false"
                >
                  <RatioShape :ratio="opt.value" :size="40" :selected="resolved.video_ratio === opt.value" />
                  <span class="ratio-label">{{ opt.label }}</span>
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>

      <div class="field-col">
        <label class="field-label">画面风格</label>
        <div class="selector-wrap" ref="styleDropdownRef">
          <button type="button" class="glass-input-base selector-trigger" :class="{ active: styleOpen }" @click="styleOpen = !styleOpen; ratioOpen = false">
            <span class="selector-text">{{ styleLabel }}</span>
            <svg class="selector-chevron" :class="{ 'rotate-180': styleOpen }" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"></path></svg>
          </button>
          <Transition name="dropdown">
            <div v-if="styleOpen" class="glass-surface-modal selector-dropdown selector-dropdown-right" style="min-width: 280px">
              <div class="style-grid">
                <button
                  v-for="opt in ART_STYLES" :key="opt.value"
                  type="button"
                  class="style-item"
                  :class="{ selected: resolved.art_style === opt.value }"
                  @click="handleChange('art_style', opt.value); styleOpen = false"
                >
                  <span class="style-label">{{ opt.label }}</span>
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- 分辨率（只读） -->
    <div class="field-row resolution-row">
      <div class="field-col">
        <label class="field-label-readonly">视频分辨率</label>
        <span class="resolution-value">{{ resolved.video_resolution }}</span>
      </div>
      <div class="field-col">
        <label class="field-label-readonly">图片分辨率</label>
        <span class="resolution-value">{{ resolved.image_resolution }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, h } from 'vue'

const VIDEO_RATIOS = [
  { value: '21:9', label: '21:9' },
  { value: '16:9', label: '16:9' },
  { value: '4:3', label: '4:3' },
  { value: '1:1', label: '1:1' },
  { value: '3:4', label: '3:4' },
  { value: '9:16', label: '9:16' },
]

const ART_STYLES = [
  { value: 'american-comic', label: '漫画风' },
  { value: 'chinese-comic', label: '精致国漫' },
  { value: 'japanese-anime', label: '日系动漫风' },
  { value: 'realistic', label: '真人风格' },
]

const RatioShape = {
  props: { ratio: String, size: { type: Number, default: 24 }, selected: Boolean },
  setup(props) {
    const dims = computed(() => {
      const [w, h] = props.ratio.split(':').map(Number)
      const max = Math.max(w, h)
      const scale = (props.size - 4) / max
      return {
        width: Math.round(w * scale) + 'px',
        height: Math.round(h * scale) + 'px',
      }
    })
    return () => h('div', {
      class: `ratio-shape ${props.selected ? 'ratio-shape-selected' : ''}`,
      style: { ...dims.value, borderRadius: '3px' },
    })
  },
}

const props = defineProps({
  title: { type: String, default: '' },
  resolved: { type: Object, required: true },
})

const emit = defineEmits(['change'])

const ratioOpen = ref(false)
const styleOpen = ref(false)
const ratioDropdownRef = ref(null)
const styleDropdownRef = ref(null)

let debounceTimer = null

const ratioLabel = computed(() => {
  const opt = VIDEO_RATIOS.find(o => o.value === props.resolved.video_ratio)
  return opt ? opt.label : props.resolved.video_ratio
})

const styleLabel = computed(() => {
  const opt = ART_STYLES.find(o => o.value === props.resolved.art_style)
  return opt ? opt.label : props.resolved.art_style
})

function handleChange(field, value) {
  emit('change', field, value)
}

function handleTitleInput(e) {
  const val = e.target.value
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('change', 'title', val)
  }, 600)
}

function handleClickOutside(e) {
  if (ratioDropdownRef.value && !ratioDropdownRef.value.contains(e.target)) {
    ratioOpen.value = false
  }
  if (styleDropdownRef.value && !styleDropdownRef.value.contains(e.target)) {
    styleOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.basic-settings {
  padding: 20px;
  background: var(--glass-bg-muted);
  border-radius: 16px;
  border: 1px solid var(--glass-stroke-soft);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--glass-text-primary);
  margin-bottom: 16px;
}

.section-title svg {
  color: var(--glass-accent-from);
}

.field-group {
  margin-bottom: 14px;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--glass-text-secondary);
  margin-bottom: 6px;
}

.field-label-readonly {
  font-size: 13px;
  font-weight: 600;
  color: var(--glass-text-secondary);
  margin-bottom: 6px;
  display: block;
}

.field-input {
  height: 38px;
  padding: 0 12px;
  font-size: 13px;
}

.field-row {
  display: flex;
  gap: 16px;
  margin-bottom: 14px;
}

.field-col {
  flex: 1;
}

.resolution-row {
  gap: 24px;
  margin-bottom: 0;
}

.resolution-value {
  font-size: 13px;
  color: var(--glass-text-tertiary);
}

/* 选择器 */
.selector-wrap {
  position: relative;
}

.selector-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 14px;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
  height: 38px;
}

.selector-trigger.active {
  border-color: var(--glass-accent-from) !important;
  box-shadow: 0 0 0 3px rgba(47, 123, 255, 0.08) !important;
}

.selector-trigger-inner {
  display: flex;
  align-items: center;
  gap: 6px;
}

.selector-text {
  font-weight: 600;
  color: var(--glass-text-primary);
}

.selector-chevron {
  flex-shrink: 0;
  color: var(--glass-text-tertiary);
  transition: transform 0.3s;
}

.selector-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 50;
  padding: 10px;
  min-width: 260px;
}

.selector-dropdown-right {
  left: auto;
  right: 0;
}

/* 比例网格 */
.ratio-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.ratio-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 6px;
  border-radius: 12px;
  border: 1.5px solid var(--glass-stroke-soft);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.ratio-item:hover {
  border-color: var(--glass-stroke-strong);
}

.ratio-item.selected {
  border-color: var(--glass-accent-from);
  background: rgba(47, 123, 255, 0.05);
}

.ratio-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--glass-text-secondary);
}

.ratio-item.selected .ratio-label {
  color: var(--glass-accent-from);
}

/* 线框比例预览 */
.ratio-shape {
  border: 2px solid var(--glass-stroke-strong);
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.ratio-shape-selected {
  border-color: var(--glass-accent-from);
}

/* 风格网格 */
.style-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.style-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1.5px solid var(--glass-stroke-soft);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
}

.style-item:hover {
  border-color: var(--glass-stroke-strong);
}

.style-item.selected {
  border-color: var(--glass-accent-from);
  background: rgba(47, 123, 255, 0.05);
}

.style-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--glass-text-secondary);
  white-space: nowrap;
}

.style-item.selected .style-label {
  color: var(--glass-accent-from);
  font-weight: 600;
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
