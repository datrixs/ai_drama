<template>
  <AppLayout>
    <div class="conv-page glass-page">

      <!-- 顶部栏 -->
      <div class="conv-header">
        <button class="glass-btn-base glass-btn-secondary conv-back-btn" @click="goBack">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          <span>返回</span>
        </button>
        <h2 class="conv-header-title">AI 对话</h2>
        <button class="glass-btn-base glass-btn-primary conv-new-btn" @click="handleCreate">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
          新对话
        </button>
      </div>

      <div class="conv-body">
        <!-- 左侧对话列表 -->
        <aside class="conv-sidebar glass-surface">
          <div v-if="listLoading" class="conv-sidebar-loading">
            <div class="loading-breathe" />
          </div>
          <div v-else-if="conversations.length === 0" class="conv-sidebar-empty">
            <p>暂无对话</p>
            <p class="conv-sidebar-hint">点击右上角开始新对话</p>
          </div>
          <div v-else class="conv-list">
            <div
              v-for="item in conversations"
              :key="item.id"
              class="conv-list-item"
              :class="{ 'conv-list-item--active': activeId === item.id }"
              @click="handleSelect(item)"
            >
              <div class="conv-list-item-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <div class="conv-list-item-text">
                <span class="conv-list-item-title">{{ item.title || '新对话' }}</span>
                <span class="conv-list-item-time">{{ formatTime(item.created_at) }}</span>
              </div>
            </div>
          </div>
        </aside>

        <!-- 右侧聊天区域 -->
        <main class="conv-chat">
          <!-- 未选中对话 -->
          <div v-if="!activeId" class="conv-chat-empty animate-fadeIn">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="1"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <p>选择或创建一个对话开始</p>
          </div>

          <!-- 消息列表 -->
          <template v-else>
            <div class="conv-messages" ref="messagesRef">
              <div v-if="detailLoading" class="conv-msg-loading">
                <div class="loading-breathe" />
              </div>
              <template v-else>
                <div
                  v-for="(msg, idx) in messages"
                  :key="idx"
                  class="conv-msg"
                  :class="`conv-msg--${msg.role}`"
                >
                  <div class="conv-msg-avatar">
                    <template v-if="msg.role === 'user'">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    </template>
                    <template v-else>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/></svg>
                    </template>
                  </div>
                  <div class="conv-msg-body">
                    <div class="conv-msg-content" v-html="renderContent(msg.content)" />
                    <div v-if="msg.attachments && msg.attachments.length > 0" class="conv-msg-attachments">
                      <div v-for="(att, ai) in msg.attachments" :key="ai" class="conv-attachment">
                        <img v-if="att.type === 'image'" :src="att.url" alt="" class="conv-attachment-img" @error="handleImgError" />
                        <video v-else-if="att.type === 'video'" :src="att.url" controls class="conv-attachment-video" />
                        <a v-else :href="att.url" target="_blank" class="conv-attachment-link">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                          {{ att.label || '下载附件' }}
                        </a>
                      </div>
                    </div>
                    <span class="conv-msg-time">{{ formatTime(msg.timestamp) }}</span>
                  </div>
                </div>

                <!-- 生成中提示 -->
                <div v-if="generating" class="conv-msg conv-msg--assistant conv-msg--generating">
                  <div class="conv-msg-avatar">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/></svg>
                  </div>
                  <div class="conv-msg-body">
                    <div class="conv-generating-dots">
                      <span /><span /><span />
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <!-- 输入区域 -->
            <div class="conv-input-area">
              <div class="conv-input-wrapper glass-surface-elevated">
                <textarea
                  ref="inputRef"
                  v-model="inputText"
                  class="conv-input"
                  rows="1"
                  placeholder="输入消息，与 AI 对话..."
                  :disabled="generating"
                  @keydown.enter.exact="handleSend"
                  @input="autoResize"
                />
                <button
                  class="glass-btn-base glass-btn-primary conv-send-btn"
                  :disabled="!inputText.trim() || generating"
                  @click="handleSend"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
              </div>
            </div>
          </template>
        </main>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '@/layout/AppLayout.vue'
import {
  createConversation,
  getConversations,
  sendMessage,
  getConversationDetail,
} from '@/api/conversation'

const props = defineProps({
  projectId: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()

const conversations = ref([])
const activeId = ref(null)
const messages = ref([])
const inputText = ref('')
const generating = ref(false)
const listLoading = ref(false)
const detailLoading = ref(false)

const messagesRef = ref(null)
const inputRef = ref(null)

// ---- 对话列表 ----
async function fetchList() {
  listLoading.value = true
  try {
    const res = await getConversations(props.projectId)
    conversations.value = res.items || res || []
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    listLoading.value = false
  }
}

async function handleCreate() {
  const type = route.query.type || 'general'
  try {
    const res = await createConversation(props.projectId, {
      conversation_type: type,
      title: '新对话',
    })
    conversations.value.unshift(res)
    activeId.value = res.id
    messages.value = []
    await nextTick()
    inputRef.value?.focus()
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

function handleSelect(item) {
  if (activeId.value === item.id) return
  activeId.value = item.id
  fetchDetail(item.id)
}

async function fetchDetail(convId) {
  detailLoading.value = true
  try {
    const res = await getConversationDetail(props.projectId, convId)
    messages.value = res.messages || []
    await nextTick()
    scrollToBottom()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    detailLoading.value = false
  }
}

// ---- 发送消息 ----
async function handleSend(e) {
  if (e && e.type === 'keydown') {
    if (e.shiftKey) return
    e.preventDefault()
  }
  const text = inputText.value.trim()
  if (!text || generating.value) return

  // 如果没有活跃对话，先创建
  if (!activeId.value) {
    await handleCreate()
    if (!activeId.value) return
  }

  // 追加用户消息到界面
  const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() }
  messages.value.push(userMsg)
  inputText.value = ''
  await nextTick()
  scrollToBottom()
  autoResize()

  generating.value = true
  try {
    const res = await sendMessage(props.projectId, activeId.value, {
      content: text,
    })
    // 追加助手回复
    if (res.reply || res.assistant_message) {
      const assistantMsg = res.reply || res.assistant_message
      messages.value.push({
        role: 'assistant',
        content: typeof assistantMsg === 'string' ? assistantMsg : assistantMsg.content || '',
        timestamp: new Date().toISOString(),
        attachments: assistantMsg.attachments
          ? assistantMsg.attachments
          : res.result_video_url
            ? [{ type: 'video', url: res.result_video_url, label: '生成视频' }]
            : [],
      })
    }
    await nextTick()
    scrollToBottom()
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    generating.value = false
  }
}

// ---- 工具函数 ----
function renderContent(content) {
  if (!content) return ''
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const time = d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  if (isToday) return time
  return `${d.getMonth() + 1}/${d.getDate()} ${time}`
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function handleImgError(e) {
  e.target.style.display = 'none'
}

function goBack() {
  router.push(`/workspace/${props.projectId}`)
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.conv-page {
  padding: 1.5rem;
  min-height: calc(100vh - 4rem);
}

.conv-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.conv-back-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.conv-header-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--glass-text-primary);
  margin: 0;
}

.conv-new-btn {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.conv-body {
  display: flex;
  gap: 1rem;
  height: calc(100vh - 9rem);
}

/* ===== 左侧列表 ===== */
.conv-sidebar {
  width: 260px;
  min-width: 260px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  border-radius: var(--glass-radius-lg);
}

.conv-sidebar-loading,
.conv-sidebar-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 0;
  color: var(--glass-text-tertiary);
  font-size: 0.85rem;
  gap: 0.5rem;
}

.conv-sidebar-hint {
  font-size: 0.75rem;
  margin: 0;
}

.conv-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.conv-list-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.65rem 0.75rem;
  border-radius: var(--glass-radius-md);
  cursor: pointer;
  transition: background 0.15s;
}

.conv-list-item:hover {
  background: var(--glass-bg-muted);
}

.conv-list-item--active {
  background: var(--glass-bg-muted);
  border-left: 3px solid var(--glass-accent-from);
}

.conv-list-item-icon {
  flex-shrink: 0;
  color: var(--glass-text-tertiary);
}

.conv-list-item-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.conv-list-item-title {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--glass-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-list-item-time {
  font-size: 0.7rem;
  color: var(--glass-text-tertiary);
  margin-top: 0.15rem;
}

/* ===== 右侧聊天区域 ===== */
.conv-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-radius: var(--glass-radius-lg);
  background: var(--glass-bg-surface);
  border: 1px solid var(--glass-stroke-soft);
}

.conv-chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--glass-text-tertiary);
  font-size: 0.9rem;
}

/* ===== 消息列表 ===== */
.conv-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.conv-msg-loading {
  display: flex;
  justify-content: center;
  padding: 3rem 0;
}

.conv-msg {
  display: flex;
  gap: 0.75rem;
  max-width: 80%;
}

.conv-msg--user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.conv-msg--assistant {
  align-self: flex-start;
}

.conv-msg-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--glass-bg-muted);
  color: var(--glass-text-secondary);
}

.conv-msg--user .conv-msg-avatar {
  background: var(--glass-tone-info-bg);
  color: var(--glass-tone-info-fg);
}

.conv-msg-body {
  display: flex;
  flex-direction: column;
}

.conv-msg-content {
  padding: 0.65rem 0.85rem;
  border-radius: var(--glass-radius-lg);
  font-size: 0.85rem;
  line-height: 1.6;
  word-break: break-word;
}

.conv-msg--user .conv-msg-content {
  background: var(--glass-accent-from);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.conv-msg--assistant .conv-msg-content {
  background: var(--glass-bg-muted);
  color: var(--glass-text-primary);
  border-bottom-left-radius: 4px;
}

.conv-msg-time {
  font-size: 0.65rem;
  color: var(--glass-text-tertiary);
  margin-top: 0.25rem;
  padding: 0 0.15rem;
}

.conv-msg--user .conv-msg-time {
  text-align: right;
}

/* 附件 */
.conv-msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.conv-attachment-img {
  max-width: 240px;
  max-height: 180px;
  border-radius: var(--glass-radius-sm);
  object-fit: cover;
}

.conv-attachment-video {
  max-width: 320px;
  max-height: 240px;
  border-radius: var(--glass-radius-sm);
  background: #000;
}

.conv-attachment-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  color: var(--glass-accent-from);
  text-decoration: none;
}

.conv-attachment-link:hover {
  text-decoration: underline;
}

/* 生成中动画 */
.conv-msg--generating {
  opacity: 0.7;
}

.conv-generating-dots {
  display: flex;
  gap: 0.35rem;
  padding: 0.85rem 1rem;
  background: var(--glass-bg-muted);
  border-radius: var(--glass-radius-lg);
  border-bottom-left-radius: 4px;
}

.conv-generating-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--glass-text-tertiary);
  animation: dot-pulse 1.4s ease-in-out infinite;
}

.conv-generating-dots span:nth-child(2) { animation-delay: 0.2s; }
.conv-generating-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

/* ===== 输入区域 ===== */
.conv-input-area {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--glass-stroke-soft);
}

.conv-input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--glass-radius-lg);
}

.conv-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--glass-text-primary);
  resize: none;
  outline: none;
  font-family: inherit;
  max-height: 160px;
}

.conv-input::placeholder {
  color: var(--glass-text-tertiary);
}

.conv-send-btn {
  width: 2rem;
  height: 2rem;
  padding: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.conv-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .conv-body {
    flex-direction: column;
    height: auto;
  }

  .conv-sidebar {
    width: 100%;
    min-width: unset;
    max-height: 180px;
  }

  .conv-chat {
    min-height: 400px;
  }

  .conv-msg {
    max-width: 92%;
  }
}
</style>
