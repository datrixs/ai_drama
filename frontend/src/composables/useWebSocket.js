import { ref } from 'vue'

export const STEP_TEXT = {
  preprocess: '正在预处理小说文本...',
  extraction: '正在提取故事核心要素...',
  layer2_start: '正在生成人物、场景、道具...',
  character: '正在润色人物特征...',
  scene: '正在润色场景描写...',
  prop: '正在润色道具描写...',
  outline: '正在生成每集大纲...',
  storyboard: '正在生成分镜剧本...',
  adjustment_start: '正在调整分析结果...',
  adjustment_done: '调整完成，正在保存...',
}

// ============ 全局单例状态（模块级别） ============
const connected = ref(false)
const lastEventId = ref('')
const reconnectAttempts = ref(0)

let ws = null
let callbacks = new Set()
let reconnectTimer = null
let aliveTimer = null
let pingTimer = null
let lastMsgTime = 0
let stopped = false
let currentUserId = null

const MAX_RECONNECT = 20
const BASE_DELAY = 1000
const MAX_DELAY = 30000
const ALIVE_TIMEOUT = 120000    // 120 秒无消息视为断连
const PING_INTERVAL = 30000     // 30 秒发一次客户端 ping 保活

function buildWsUrl(userId) {
  const token = localStorage.getItem('token')
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}/api/v1/ws/${userId}/ws?token=${encodeURIComponent(token)}`
}

function emitEvent(event) {
  if (event.event_id) {
    lastEventId.value = event.event_id
  }
  for (const cb of callbacks) {
    try { cb(event) } catch (e) { console.error('[WS] callback error:', e) }
  }
}

function getReconnectDelay() {
  const delay = Math.min(BASE_DELAY * Math.pow(2, reconnectAttempts.value), MAX_DELAY)
  return delay + Math.random() * 500
}

function scheduleReconnect() {
  if (stopped) return
  if (reconnectAttempts.value >= MAX_RECONNECT) {
    console.warn('[WS] 达到最大重连次数，重置计数后继续')
    reconnectAttempts.value = 0
  }
  reconnectAttempts.value++
  const delay = getReconnectDelay()
  console.log(`[WS] ${delay}ms 后重连 (第${reconnectAttempts.value}次)`)
  reconnectTimer = setTimeout(() => doConnect(currentUserId), delay)
}

function startPing() {
  stopPing()
  pingTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify({ type: 'ping' })) } catch {}
    }
  }, PING_INTERVAL)
}

function stopPing() {
  if (pingTimer) {
    clearInterval(pingTimer)
    pingTimer = null
  }
}

function startAliveCheck() {
  stopAliveCheck()
  aliveTimer = setInterval(() => {
    if (Date.now() - lastMsgTime > ALIVE_TIMEOUT) {
      console.warn('[WS] 存活超时，主动断开')
      if (ws) ws.close()
    }
  }, 30000)
}

function stopAliveCheck() {
  if (aliveTimer) {
    clearInterval(aliveTimer)
    aliveTimer = null
  }
}

function doConnect(userId) {
  if (!userId) return
  currentUserId = userId

  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    return
  }

  stopped = false
  let url = buildWsUrl(userId)
  if (lastEventId.value) {
    url += `&last_event_id=${encodeURIComponent(lastEventId.value)}`
  }

  ws = new WebSocket(url)

  ws.onopen = () => {
    connected.value = true
    reconnectAttempts.value = 0
    lastMsgTime = Date.now()
    startAliveCheck()
    startPing()
    console.log('[WS] 已连接')
  }

  ws.onmessage = (e) => {
    lastMsgTime = Date.now()
    try {
      const event = JSON.parse(e.data)
      if (event.type === 'ping') return
      emitEvent(event)
    } catch (err) {
      console.error('[WS] 消息解析失败:', err)
    }
  }

  ws.onclose = (e) => {
    connected.value = false
    stopAliveCheck()
    stopPing()
    console.log(`[WS] 连接关闭 code=${e.code}`)
    if (!stopped) {
      scheduleReconnect()
    }
  }

  ws.onerror = (err) => {
    console.error('[WS] 连接错误:', err)
  }
}

// ============ composable 接口 ============

export function useWebSocket() {
  function connect(userId) {
    doConnect(userId)
  }

  function disconnect() {
    stopped = true
    stopAliveCheck()
    stopPing()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
  }

  function onEvent(callback) {
    callbacks.add(callback)
    return () => callbacks.delete(callback)
  }

  function offEvent(callback) {
    callbacks.delete(callback)
  }

  return {
    connected,
    lastEventId,
    connect,
    disconnect,
    onEvent,
    offEvent,
    STEP_TEXT,
  }
}
