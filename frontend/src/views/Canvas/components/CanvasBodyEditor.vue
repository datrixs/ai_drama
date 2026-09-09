<template>
  <div class="cbe-wrap">
    <div
      ref="editableRef"
      class="cbe-editor"
      :class="{ 'is-disabled': disabled }"
      contenteditable="true"
      :data-placeholder="placeholder"
      @input="onInput"
      @blur="onBlur"
      @paste="onPaste"
      @focus="onFocus"
    ></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  html: { type: String, default: '' },
  placeholder: { type: String, default: '编辑正文（Ctrl+B 加粗，Ctrl+I 斜体）' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:html', 'blur', 'focus'])

const editableRef = ref(null)
const isSyncing = ref(false)

function readHtml() {
  return editableRef.value ? editableRef.value.innerHTML : ''
}

function onInput() {
  if (isSyncing.value) return
  emit('update:html', readHtml())
}
function onBlur() { emit('blur', readHtml()) }
function onFocus() { emit('focus') }

function onPaste(e) {
  // 仅粘贴纯文本，避免外部样式污染
  e.preventDefault()
  const txt = e.clipboardData?.getData('text/plain') || ''
  document.execCommand('insertText', false, txt)
}

watch(
  () => props.html,
  (val) => {
    if (!editableRef.value) return
    const next = val || ''
    if (next === readHtml()) return
    isSyncing.value = true
    editableRef.value.innerHTML = next
    nextTick(() => { isSyncing.value = false })
  }
)

onMounted(async () => {
  await nextTick()
  if (!editableRef.value) return
  isSyncing.value = true
  editableRef.value.innerHTML = props.html || ''
  await nextTick()
  isSyncing.value = false
})

defineExpose({
  getHtml: readHtml,
  setHtml: (v) => {
    if (!editableRef.value) return
    isSyncing.value = true
    editableRef.value.innerHTML = v || ''
    nextTick(() => { isSyncing.value = false })
  },
})
</script>

<style scoped>
.cbe-wrap { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.cbe-editor {
  flex: 1;
  min-height: 80px;
  overflow-y: auto;
  padding: 12px 14px;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 12px;
  background: #fff;
  color: #1f2a44;
  font-size: 13.5px;
  line-height: 1.75;
  outline: none;
  white-space: pre-wrap;
  word-break: break-word;
}
.cbe-editor:focus { box-shadow: 0 0 0 3px rgba(75, 120, 255, 0.12); border-color: rgba(75, 120, 255, 0.28); }
.cbe-editor.is-disabled { opacity: 0.55; pointer-events: none; }
.cbe-editor:empty::before { content: attr(data-placeholder); color: #98a2b3; }
.cbe-editor :deep(h1) { font-size: 1.4em; font-weight: 700; margin: 0.4em 0 0.2em; }
.cbe-editor :deep(h2) { font-size: 1.2em; font-weight: 700; margin: 0.4em 0 0.2em; }
.cbe-editor :deep(p) { margin: 0.2em 0; }
.cbe-editor :deep(ul), .cbe-editor :deep(ol) { padding-left: 1.4em; margin: 0.2em 0; }
</style>
