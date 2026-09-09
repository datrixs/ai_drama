<template>
  <div class="vt-wrap">
    <div class="vt-inner">
      <div class="vt-left">
        <span class="vt-title">成片</span>
        <span class="vt-pill">{{ totalSegments }} 片段</span>
        <span v-if="runningCount > 0" class="vt-tag vt-tag-running">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.2-8.6"/></svg>
          {{ runningCount }}
        </span>
        <span v-if="completedCount > 0" class="vt-tag vt-tag-done">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          {{ completedCount }}
        </span>
        <span v-if="failedCount > 0" class="vt-tag vt-tag-fail">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          {{ failedCount }}
        </span>
      </div>
      <div class="vt-right">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  totalSegments: { type: Number, default: 0 },
  runningCount: { type: Number, default: 0 },
  completedCount: { type: Number, default: 0 },
  failedCount: { type: Number, default: 0 },
})
</script>

<style scoped>
.vt-wrap {
  border-radius: 0.75rem;
  border: 1px solid rgba(111,126,153,0.216);
  background: rgba(255,255,255,0.387);
  padding: 0.5rem 0.75rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.vt-inner {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.5rem;
}
.vt-left { display: flex; align-items: center; gap: 0.375rem; }
.vt-title { font-size: 0.8125rem; font-weight: 700; color: #0a0a0a; letter-spacing: -0.01em; }

/* 片段总数 */
.vt-pill {
  font-size: 0.6875rem; font-weight: 600; color: #4b5563;
  background: rgba(111,126,153,0.1);
  padding: 0.125rem 0.45rem; border-radius: 999px;
  font-variant-numeric: tabular-nums;
}

/* 状态标签 */
.vt-tag {
  display: inline-flex; align-items: center; gap: 0.25rem;
  font-size: 0.6875rem; font-weight: 700;
  font-variant-numeric: tabular-nums;
  padding: 0.125rem 0.5rem 0.125rem 0.375rem;
  border-radius: 999px;
}
.vt-tag svg { flex-shrink: 0; }

.vt-tag-running {
  color: #1d63e8;
  background: rgba(47,123,255,0.12);
}
.vt-tag-running svg { animation: vt-spin 1.2s linear infinite; }

.vt-tag-done {
  color: #0f9f62;
  background: rgba(16,185,129,0.12);
}

.vt-tag-fail {
  color: #cb3a3a;
  background: rgba(239,68,68,0.1);
}

.vt-right { display: flex; flex-wrap: wrap; align-items: center; gap: 0.375rem; }

@keyframes vt-spin {
  to { transform: rotate(360deg); }
}
</style>
