<template>
  <div class="mpc-card">
    <!-- 标题栏 -->
    <div class="mpc-head">
      <div class="mpc-head-left">
        <span class="mpc-title">{{ segments.length === 0 ? '分镜编辑器' : `片段 ${activeSegmentIndex + 1}` }}</span>
      </div>
      <div class="mpc-head-right">
        <span v-if="segments.length > 1" class="mpc-seg-info">
          {{ activeSegmentIndex + 1 }}/{{ segments.length }}
        </span>
      </div>
    </div>

    <!-- 富文本编辑器 -->
    <MultimodalEditor
      v-if="segments.length > 0"
      ref="editorRef"
      :plain-text="segmentPlainText"
      :assets="editorAssets"
      :hydrate-stamp="hydrateStamp"
      :project-id="projectId"
      @update:plain-text="onSegmentTextUpdate"
    />
    <!-- 空状态兜底：仅全局模式下脚本未生成时会进入此分支（导演模式进入时已自动新建片段） -->
    <div v-else class="mpc-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" opacity="0.35">
        <rect x="2" y="2" width="20" height="20" rx="2"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/>
      </svg>
      <p>暂无分镜片段</p>
    </div>

    <!-- 解析错误 -->
    <p v-if="parseError" class="mpc-parse-error">{{ parseError }}</p>

    <!-- 底部操作栏 -->
    <div class="mpc-toolbar">
      <div class="mpc-toolbar-row">
        <button class="mpc-btn mpc-btn-muted" :disabled="savingScript" @click="$emit('save-script')">
          {{ savingScript ? '保存中...' : '保存脚本' }}
        </button>

        <button v-if="activeSegment?.status === 'video_generating'"
          class="mpc-btn mpc-btn-accent" disabled>
          视频生成中...
        </button>
        <button v-else
          class="mpc-btn mpc-btn-accent"
          @click="$emit('generate-video', activeSegment)">
          {{ activeSegment?.status === 'failed' ? '重试生成' : '生成视频' }}
        </button>

        <div class="mpc-param-group">
          <select :value="videoForm.model" @change="onParamChange('model', $event.target.value)" class="mpc-select">
            <template v-if="region === 'overseas'">
              <option value="dreamina-seedance-2-0-260128">Dreamina Seedance 2.0</option>
            </template>
            <template v-else>
              <option value="doubao-seedance-2-0-260128">Seedance 2.0</option>
              <option value="doubao-seedance-2-0-fast-260128">Seedance 2.0 Fast</option>
            </template>
          </select>
          <select :value="videoForm.resolution" @change="onParamChange('resolution', $event.target.value)" class="mpc-select">
            <option value="480p">480p</option>
            <option value="720p">720p</option>
            <option v-if="!videoForm.model?.includes('fast')" value="1080p">1080p</option>
          </select>
          <select :value="videoForm.ratio" @change="onParamChange('ratio', $event.target.value)" class="mpc-select">
            <option value="16:9">16:9</option>
            <option value="9:16">9:16</option>
            <option value="1:1">1:1</option>
          </select>
          <select :value="effectiveDuration" @change="onParamChange('duration', $event.target.value ? Number($event.target.value) : null)" class="mpc-select">
            <option value="">自动 ({{ autoDurationLabel }})</option>
            <option v-for="d in durationOptions" :key="d" :value="d">{{ d }}s</option>
          </select>
          <label class="mpc-check">
            <span class="mpc-checkbox" :class="{ 'mpc-checkbox-on': videoForm.generate_audio }" @click.prevent="onParamChange('generate_audio', !videoForm.generate_audio)">
              <svg v-if="videoForm.generate_audio" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
            <span>音频</span>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import MultimodalEditor from './MultimodalEditor.vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const region = computed(() => userStore.userInfo.value?.region || 'domestic')

const durationOptions = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

// 从 shots 计算合计时长（每个镜头 0.5-3s，默认 3s）
function sumShotDuration(shots) {
  if (!shots || !shots.length) return 0
  let total = 0
  for (const s of shots) {
    const hint = s.durationHintSec
    if (hint && typeof hint === 'number') {
      total += Math.max(0.5, Math.min(3, hint))
    } else {
      total += 3
    }
  }
  return total
}

// 将秒数映射到最近的 duration 档位
function snapToDuration(totalSec) {
  const rounded = Math.round(totalSec)
  for (const d of durationOptions) {
    if (rounded <= d) return d
  }
  return durationOptions[durationOptions.length - 1]
}

const autoDuration = computed(() => {
  const seg = props.activeSegment
  if (!seg) return 4
  const shots = seg.shots
  if (shots && shots.length > 0) {
    return snapToDuration(sumShotDuration(shots))
  }
  return 4
})

const autoDurationLabel = computed(() => `${autoDuration.value}s`)

const effectiveDuration = computed(() => {
  return props.videoForm.duration ?? ''
})

const props = defineProps({
  projectId: { type: String, required: true },
  episodeId: { type: String, required: true },
  segments: { type: Array, default: () => [] },
  activeSegmentIndex: { type: Number, default: 0 },
  segmentPlainText: { type: String, default: '' },
  activeSegment: { type: Object, default: null },
  videoForm: { type: Object, default: () => ({}) },
  savingScript: { type: Boolean, default: false },
  assets: { type: Object, default: () => ({}) },
  parseError: { type: String, default: null },
})

const emit = defineEmits([
  'save-script', 'generate-video', 'cancel-task',
  'select-segment', 'update:segmentPlainText', 'update:videoForm',
])

const editorRef = ref(null)
const hydrateStamp = computed(() => `${props.episodeId}:${props.activeSegmentIndex}`)

const editorAssets = computed(() => {
  const a = props.assets
  return [{
    characters: a.characters || [],
    locations: a.locations || [],
    props: a.props || [],
  }]
})

function onSegmentTextUpdate(text) {
  emit('update:segmentPlainText', text)
}

function onParamChange(field, value) {
  const form = { ...props.videoForm, [field]: value }
  if (field === 'model' && value.includes('fast') && form.resolution === '1080p') {
    form.resolution = '720p'
  }
  emit('update:videoForm', form)
}

function flushEditor() {
  return editorRef.value?.flushSync?.() || { plainText: '' }
}

function forceHydrate() {
  editorRef.value?.forceHydrate?.()
}

defineExpose({ flushEditor, forceHydrate })
</script>

<style scoped>
.mpc-card {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: rgba(255,255,255,0.94);
  border-radius: 1rem;
  border: 1px solid rgba(111,126,153,0.24);
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  overflow: hidden;
}

.mpc-card > .mpc-head,
.mpc-card > .mpc-parse-error {
  flex-shrink: 0;
  padding-left: 1rem;
  padding-right: 1rem;
}
.mpc-card > .mpc-head { padding-top: 1rem; }

.mpc-card > :deep(.me-wrap) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 1rem;
}

.mpc-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.5rem;
}
.mpc-head-left { display: flex; align-items: baseline; gap: 0.25rem; }
.mpc-title { font-size: 0.875rem; font-weight: 500; color: #0a0a0a; }
.mpc-head-right { font-size: 0.75rem; color: #4b5563; }
.mpc-seg-info { font-size: 0.75rem; color: #4b5563; }

.mpc-parse-error { margin: 0.5rem 0 0; font-size: 0.75rem; color: #d97706; }

/* 空状态兜底（导演模式自动新建后不会触发，仅作防御） */
.mpc-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem;
  color: #9ca3af;
}
.mpc-empty p { margin: 0; font-size: 0.875rem; color: #4b5563; }

/* 底部工具栏 */
.mpc-toolbar {
  flex-shrink: 0;
  border-top: 1px solid rgba(111,126,153,0.144);
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.mpc-toolbar-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-wrap: wrap;
}

/* 按钮 */
.mpc-btn {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.375rem 0.75rem; border-radius: 1rem;
  font-size: 0.75rem; font-weight: 600; cursor: pointer;
  border: 1px solid transparent; transition: all 0.2s; white-space: nowrap;
}
.mpc-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.mpc-btn-muted { background: rgba(255,255,255,0.94); border-color: rgba(111,126,153,0.24); color: #0a0a0a; box-shadow: 0 2px 10px rgba(22,35,64,0.05); }
.mpc-btn-muted:hover:not(:disabled) { background: #f3f4f6; }
.mpc-btn-accent { background: rgba(47,123,255,0.2); color: #1d63e8; box-shadow: inset 0 0 0 1px rgba(29,99,232,0.24); border: none; }
.mpc-btn-accent:hover:not(:disabled) { filter: brightness(1.1); }

/* 参数选择 */
.mpc-param-group {
  display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; margin-left: auto;
}
.mpc-select {
  padding: 0.25rem 0.4rem; border: 1px solid rgba(111,126,153,0.24);
  border-radius: 0.375rem; font-size: 0.75rem; background: #fff; color: #0a0a0a; outline: none;
}
.mpc-check {
  display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.75rem; font-weight: 500; color: #4b5563; cursor: pointer;
  user-select: none;
}
.mpc-checkbox {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px;
  border: 1.5px solid rgba(111,126,153,0.36);
  border-radius: 4px;
  background: #fff;
  transition: all 0.15s;
}
.mpc-checkbox-on {
  background: #2f7bff;
  border-color: #2f7bff;
  color: #fff;
}
.mpc-checkbox svg {
  display: block;
}
</style>
