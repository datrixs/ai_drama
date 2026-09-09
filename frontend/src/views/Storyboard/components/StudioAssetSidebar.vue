<template>
  <aside class="sas-wrap">
    <div class="sas-head">
      <span class="sas-title">资产库</span>
      <button class="sas-plus" @click="$emit('open-project-assets')" title="项目资产库">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
      </button>
    </div>

    <!-- 角色 -->
    <div class="sas-label">角色</div>
    <div class="sas-grid">
      <button v-for="c in characters" :key="c.id" class="sas-card" :disabled="!getImg(c)" :title="c.name"
        @click="$emit('asset-click', { name: c.name, imageUrl: getImg(c), description: getDesc(c) })">
        <img v-if="getImg(c)" :src="getThumb(c)" class="sas-circle" @error="onImgError($event, getImg(c))" />
        <div v-else class="sas-circle sas-empty" />
        <span class="sas-text">{{ c.name }}</span>
      </button>
    </div>

    <!-- 场景 -->
    <div class="sas-label sas-mt">场景</div>
    <div class="sas-grid">
      <button v-for="loc in locations" :key="loc.id" class="sas-card" :disabled="!getImg(loc)" :title="loc.name"
        @click="$emit('asset-click', { name: loc.name, imageUrl: getImg(loc), description: getDesc(loc) })">
        <img v-if="getImg(loc)" :src="getThumb(loc)" class="sas-rect" @error="onImgError($event, getImg(loc))" />
        <div v-else class="sas-rect sas-empty" />
        <span class="sas-text">{{ loc.name }}</span>
      </button>
    </div>

    <!-- 道具 -->
    <div class="sas-label sas-mt">道具</div>
    <div class="sas-grid">
      <button v-for="p in props" :key="p.id" class="sas-card" :disabled="!getImg(p)" :title="p.name"
        @click="$emit('asset-click', { name: p.name, imageUrl: getImg(p), description: getDesc(p) })">
        <img v-if="getImg(p)" :src="getThumb(p)" class="sas-rect" @error="onImgError($event, getImg(p))" />
        <div v-else class="sas-rect sas-empty" />
        <span class="sas-text">{{ p.name }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  characters: { type: Array, default: () => [] },
  locations: { type: Array, default: () => [] },
  props: { type: Array, default: () => [] },
})
defineEmits(['asset-click', 'open-project-assets'])

function getImg(item) { return item.image_url || null }
function getThumb(item) { return item.thumbnail_url || item.image_url || null }
function getDesc(item) { return item.description || item.summary || '' }

function onImgError(e, originalUrl) {
  const img = e.target
  if (img.dataset.fallback || !originalUrl) return
  img.dataset.fallback = '1'
  img.src = originalUrl
}
</script>

<style scoped>
.sas-wrap {
  width: 15.5rem;
  flex-shrink: 0;
  min-height: 0;
  border-radius: 0.75rem;
  border: 1px solid rgba(111,126,153,0.24);
  background: rgba(255,255,255,0.344);
  padding: 0.75rem;
  padding-right: 0.5rem;
  overflow-y: auto;
}
.sas-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;
}
.sas-title { font-size: 0.875rem; font-weight: 700; color: #0a0a0a; }
.sas-plus {
  display: flex; align-items: center; justify-content: center;
  width: 1.5rem; height: 1.5rem; border-radius: 0.375rem;
  border: 1px solid rgba(111,126,153,0.24); background: none;
  color: #111827; cursor: pointer; transition: all 0.15s;
}
.sas-plus:hover { background: rgba(255,255,255,0.86); color: #1d63e8; }
.sas-label { font-size: 11px; font-weight: 600; color: #4b5563; margin-bottom: 0.5rem; }
.sas-mt { margin-top: 1rem; }
.sas-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.sas-card {
  width: 4.5rem; text-align: center; background: none; border: none;
  cursor: pointer; padding: 0; border-radius: 0.5rem; transition: background 0.15s;
}
.sas-card:hover:not(:disabled) { background: rgba(255,255,255,0.688); }
.sas-card:disabled { opacity: 0.4; cursor: not-allowed; }
.sas-circle {
  width: 3.5rem; height: 3.5rem; border-radius: 50%; object-fit: cover;
  margin: 0 auto; border: 1px solid rgba(111,126,153,0.24);
}
.sas-rect {
  width: 3.5rem; height: 2.5rem; border-radius: 0.375rem; object-fit: cover;
  margin: 0 auto; border: 1px solid rgba(111,126,153,0.24);
}
.sas-empty { background: #e5e7eb; }
.sas-text {
  display: block; font-size: 10px; color: #111827;
  margin-top: 0.125rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
</style>
