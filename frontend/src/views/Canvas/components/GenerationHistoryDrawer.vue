<template>
  <el-drawer
    :model-value="visible"
    direction="rtl"
    size="640"
    :title="drawerTitle"
    :destroy-on-close="true"
    @update:model-value="$emit('update:visible', $event)"
    @open="loadList"
  >
    <div v-loading="loading" class="ghd-body">
      <div v-if="!loading && rows.length === 0" class="ghd-empty">
        <div class="ghd-empty-title">暂无历史版本</div>
        <div class="ghd-empty-hint">提交一次生成后会在这里显示</div>
      </div>

      <div v-for="g in rows" :key="g.id" class="ghd-card" :class="{ 'is-current': g.id === currentGenerationId }">
        <div class="ghd-card-preview">
          <template v-if="g.generation_type === 'text'">
            <div class="ghd-preview-text">{{ textPreview(g) || '（空文本）' }}</div>
          </template>
          <template v-else-if="g.generation_type === 'image'">
            <img v-if="previewUrl(g)" :src="previewUrl(g)" alt="缩略图" class="ghd-preview-img" />
            <div v-else class="ghd-preview-placeholder">IMG</div>
          </template>
          <template v-else-if="g.generation_type === 'audio'">
            <audio v-if="previewUrl(g)" :src="previewUrl(g)" class="ghd-preview-audio" controls preload="metadata"></audio>
            <div v-else class="ghd-preview-placeholder">AUDIO</div>
          </template>
          <template v-else>
            <video v-if="previewUrl(g)" :src="previewUrl(g)" class="ghd-preview-video" muted controls></video>
            <div v-else class="ghd-preview-placeholder">VIDEO</div>
          </template>
        </div>

        <div class="ghd-card-meta">
          <div class="ghd-card-meta-row">
            <span class="ghd-status-tag" :class="`is-${g.status}`">{{ statusLabel(g.status) }}</span>
            <span class="ghd-card-time">{{ formatTime(g.create_time) }}</span>
          </div>
          <div class="ghd-card-prompt">{{ promptPreview(g) }}</div>
          <div class="ghd-card-actions">
            <button
              v-if="g.status === 'completed'"
              class="ghd-apply-btn"
              type="button"
              @click="onApply(g)"
            >应用此版本</button>
            <button
              class="ghd-link-btn"
              type="button"
              :disabled="modelCallLoadingId === g.id"
              @click="onViewModelCall(g)"
            >{{ modelCallOpenId === g.id ? '收起模型调用' : '查看模型调用' }}</button>
          </div>
          <!-- 模型调用详情：内嵌展开 -->
          <div v-if="modelCallOpenId === g.id" class="ghd-modelcall">
            <div v-if="modelCallLoadingId === g.id" class="ghd-modelcall-loading">加载中…</div>
            <div v-else-if="modelCallError" class="ghd-modelcall-error">{{ modelCallError }}</div>
            <div v-else-if="!modelCallDetail" class="ghd-modelcall-empty">该版本未关联模型调用记录</div>
            <template v-else>
              <div class="ghd-modelcall-grid">
                <div class="ghd-mc-item"><span class="ghd-mc-label">供应商</span><span class="ghd-mc-value">{{ modelCallDetail.model_provider_name || modelCallDetail.model_provider || '—' }}</span></div>
                <div class="ghd-mc-item"><span class="ghd-mc-label">模型</span><span class="ghd-mc-value">{{ modelCallDetail.model_name || '—' }}</span></div>
                <div class="ghd-mc-item"><span class="ghd-mc-label">耗时</span><span class="ghd-mc-value">{{ formatLatency(modelCallDetail.latency_ms) }}</span></div>
                <div class="ghd-mc-item"><span class="ghd-mc-label">积分</span><span class="ghd-mc-value">{{ formatPoint(modelCallDetail.point) }}</span></div>
                <div class="ghd-mc-item"><span class="ghd-mc-label">输入 token</span><span class="ghd-mc-value">{{ modelCallDetail.input_tokens ?? 0 }}</span></div>
                <div class="ghd-mc-item"><span class="ghd-mc-label">输出 token</span><span class="ghd-mc-value">{{ modelCallDetail.output_tokens ?? 0 }}</span></div>
                <div class="ghd-mc-item"><span class="ghd-mc-label">调用时间</span><span class="ghd-mc-value">{{ formatTime(modelCallDetail.call_time) }}</span></div>
                <div class="ghd-mc-item"><span class="ghd-mc-label">请求 ID</span><span class="ghd-mc-value ghd-mc-mono">{{ modelCallDetail.request_id || '—' }}</span></div>
              </div>
              <div v-if="modelCallDetail.error_message" class="ghd-modelcall-errormsg">
                错误：{{ modelCallDetail.error_message }}
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { listCanvasGenerations, applyCanvasGeneration, getCanvasGenerationModelCall } from '@/api/canvas'

const props = defineProps({
  visible: { type: Boolean, default: false },
  itemId: { type: String, default: '' },
  itemType: { type: String, default: 'text' },
  currentGenerationId: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'applied'])

const rows = ref([])
const loading = ref(false)

const modelCallOpenId = ref('')
const modelCallLoadingId = ref('')
const modelCallDetail = ref(null)
const modelCallError = ref('')

const drawerTitle = computed(() => {
  const map = { text: '文本', image: '图片', video: '视频', audio: '音频' }
  const t = map[props.itemType] || '节点'
  return `生成历史 · ${t}节点`
})

function statusLabel(s) {
  return { completed: '已完成', failed: '失败', pending: '排队中', processing: '生成中', canceled: '已取消' }[s] || s
}
function formatTime(t) {
  if (!t) return ''
  try {
    const d = new Date(t)
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mi = String(d.getMinutes()).padStart(2, '0')
    return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
  } catch { return t }
}
function textPreview(g) {
  const out = g.output_json || {}
  return out.body || out.text || ''
}
function previewUrl(g) {
  const out = g.output_json || {}
  return out.thumbnail_url || out.url || ''
}
function promptPreview(g) {
  const inp = g.input_json || {}
  const txt = inp.prompt_plain_text || inp.prompt || ''
  if (!txt) return ''
  return txt.length > 120 ? txt.slice(0, 120) + '…' : txt
}

async function loadList() {
  if (!props.itemId) return
  loading.value = true
  try {
    const resp = await listCanvasGenerations(props.itemId, { page: 1, size: 30 })
    const data = resp?.data || resp
    rows.value = data?.list || []
  } catch (e) {
    rows.value = []
    ElMessage.error('加载历史失败')
  } finally {
    loading.value = false
  }
}

async function onApply(g) {
  if (!props.itemId || !g?.id) return
  try {
    const updated = await applyCanvasGeneration(props.itemId, g.id)
    ElMessage.success('已应用此版本')
    emit('applied', { itemId: props.itemId, generation: g, item: updated?.data || updated })
    emit('update:visible', false)
  } catch (e) {
    ElMessage.error(e?.message || '应用失败')
  }
}

async function onViewModelCall(g) {
  if (!props.itemId || !g?.id) return
  // 切换展开/收起
  if (modelCallOpenId.value === g.id) {
    modelCallOpenId.value = ''
    return
  }
  modelCallOpenId.value = g.id
  modelCallDetail.value = null
  modelCallError.value = ''
  modelCallLoadingId.value = g.id
  try {
    const resp = await getCanvasGenerationModelCall(props.itemId, g.id)
    const data = resp?.data ?? resp
    modelCallDetail.value = data || null
  } catch (e) {
    modelCallError.value = e?.message || '加载模型调用详情失败'
  } finally {
    modelCallLoadingId.value = ''
  }
}

function formatLatency(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} s`
}

function formatPoint(p) {
  if (p == null || p === '') return '—'
  const n = Number(p)
  if (Number.isNaN(n)) return String(p)
  return n.toFixed(2)
}

defineExpose({ reload: loadList })
</script>

<style scoped>
.ghd-body { padding: 12px 16px 24px; display: flex; flex-direction: column; gap: 10px; }
.ghd-empty { padding: 48px 12px; text-align: center; color: #6b7280; }
.ghd-empty-title { font-size: 14px; color: #1f2a44; margin-bottom: 4px; }
.ghd-empty-hint { font-size: 12px; color: #98a2b3; }
.ghd-card { display: flex; gap: 10px; padding: 10px; border: 1px solid rgba(34, 57, 98, 0.08); border-radius: 10px; background: #fff; transition: border-color 0.15s; }
.ghd-card.is-current { border-color: rgba(75, 120, 255, 0.32); background: rgba(75, 120, 255, 0.04); }
.ghd-card-preview { flex: 0 0 120px; width: 120px; height: 90px; border-radius: 8px; background: #f3f6fb; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.ghd-preview-text { width: 100%; height: 100%; padding: 6px; font-size: 11px; line-height: 1.4; color: #1f2a44; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical; }
.ghd-preview-img { width: 100%; height: 100%; object-fit: cover; }
.ghd-preview-video { width: 100%; height: 100%; object-fit: cover; background: #000; }
.ghd-preview-audio { width: 100%; height: 36px; object-fit: contain; }
.ghd-preview-placeholder { color: #98a2b3; font-size: 11px; letter-spacing: 0.4px; }
.ghd-card-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.ghd-card-meta-row { display: flex; align-items: center; gap: 8px; }
.ghd-status-tag { display: inline-flex; align-items: center; padding: 1px 8px; border-radius: 999px; font-size: 10px; line-height: 1.6; background: rgba(34, 57, 98, 0.08); color: #1f2a44; }
.ghd-status-tag.is-completed { background: rgba(46, 193, 192, 0.16); color: #12807f; }
.ghd-status-tag.is-failed { background: rgba(255, 91, 138, 0.16); color: #b3285a; }
.ghd-status-tag.is-processing, .ghd-status-tag.is-pending { background: rgba(75, 120, 255, 0.16); color: #355ce0; }
.ghd-card-time { font-size: 11px; color: #667085; }
.ghd-card-prompt { font-size: 12px; color: #1f2a44; line-height: 1.5; max-height: 48px; overflow: hidden; }
.ghd-card-actions { margin-top: auto; display: flex; justify-content: flex-end; gap: 6px; }
.ghd-apply-btn { padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(75, 120, 255, 0.32); background: rgba(75, 120, 255, 0.08); color: #355ce0; font-size: 11px; cursor: pointer; }
.ghd-apply-btn:hover { background: rgba(75, 120, 255, 0.16); }
.ghd-link-btn { padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(34, 57, 98, 0.12); background: transparent; color: #475467; font-size: 11px; cursor: pointer; }
.ghd-link-btn:hover:not(:disabled) { background: #f3f6fb; color: #1f2a44; }
.ghd-link-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── 模型调用详情 ── */
.ghd-modelcall { margin-top: 6px; padding: 8px 10px; background: #f8fafc; border: 1px solid rgba(34, 57, 98, 0.08); border-radius: 8px; }
.ghd-modelcall-loading, .ghd-modelcall-empty, .ghd-modelcall-error { font-size: 11px; color: #667085; padding: 2px 0; }
.ghd-modelcall-error { color: #b3285a; }
.ghd-modelcall-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; }
.ghd-mc-item { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.ghd-mc-label { font-size: 10px; color: #667085; }
.ghd-mc-value { font-size: 12px; color: #1f2a44; word-break: break-all; }
.ghd-mc-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; }
.ghd-modelcall-errormsg { margin-top: 6px; padding: 4px 6px; font-size: 11px; color: #b3285a; background: rgba(239, 68, 68, 0.08); border-radius: 4px; }
</style>
