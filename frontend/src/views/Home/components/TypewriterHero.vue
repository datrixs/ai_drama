<template>
  <div class="typewriter-hero">
    <!-- 标题 — 带对焦动画 -->
    <h1 class="hero-title" style="animation: twh-focus-pull 8s ease-in-out infinite">
      {{ title }}
    </h1>

    <!-- 终端打字机副标题 -->
    <p class="hero-subtitle">
      <span class="terminal-prefix">&gt;_</span>
      <span
        v-for="(char, i) in displayText"
        :key="i"
        class="type-char"
        :style="charStyle(i)"
      >{{ char === ' ' ? ' ' : char }}</span>
      <span class="type-cursor" />
    </p>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})

const TYPE_SPEED = 55
const DELETE_SPEED = 20
const PAUSE_AFTER_TYPE = 3200
const PAUSE_AFTER_DELETE = 500

const displayText = ref('')
const isDeleting = ref(false)
let timeout = null
let prevLen = 0

function tick() {
  const sub = props.subtitle
  if (!isDeleting.value && displayText.value.length === sub.length) {
    timeout = setTimeout(() => { isDeleting.value = true; tick() }, PAUSE_AFTER_TYPE)
    return
  }
  if (isDeleting.value && displayText.value.length === 0) {
    timeout = setTimeout(() => { isDeleting.value = false; tick() }, PAUSE_AFTER_DELETE)
    return
  }
  prevLen = displayText.value.length
  const nextLen = displayText.value.length + (isDeleting.value ? -1 : 1)
  displayText.value = sub.slice(0, nextLen)
  timeout = setTimeout(tick, isDeleting.value ? DELETE_SPEED : TYPE_SPEED)
}

function isNewChar(i) {
  return !isDeleting.value && i === displayText.value.length - 1 && displayText.value.length > prevLen
}

function charStyle(i) {
  if (isNewChar(i)) {
    return {
      animationName: 'twh-charIn',
      animationDuration: '0.25s',
      animationTimingFunction: 'ease-out',
      animationIterationCount: 1,
      animationFillMode: 'forwards',
    }
  }
  return {
    animationName: 'twh-hover',
    animationDuration: '3s',
    animationTimingFunction: 'ease-in-out',
    animationIterationCount: 'infinite',
    animationDelay: `${i * 0.08}s`,
  }
}

onMounted(() => { tick() })
onUnmounted(() => { if (timeout) clearTimeout(timeout) })
</script>

<style scoped>
.typewriter-hero {
  text-align: center;
  margin-bottom: 1rem;
}

.hero-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  letter-spacing: 0.08em;
  margin-bottom: 0.5rem;
}

.hero-subtitle {
  font-family: monospace;
  font-size: 0.875rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--glass-text-tertiary);
}

.terminal-prefix {
  margin-right: 0.375rem;
  opacity: 0.5;
}

.type-char {
  display: inline-block;
}

.type-cursor {
  display: inline-block;
  width: 0.5rem;
  height: 1rem;
  margin-left: 0.125rem;
  background: var(--glass-text-tertiary);
  vertical-align: middle;
  border-radius: 1px;
  animation: twh-blink 1s step-end infinite;
}
</style>
