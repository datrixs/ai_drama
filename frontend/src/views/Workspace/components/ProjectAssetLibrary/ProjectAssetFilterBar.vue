<template>
  <div class="filter-wrapper glass-surface">
    <SegmentedControl
      :options="filterItems"
      :model-value="kindFilter"
      layout="compact"
      @update:model-value="$emit('change', $event)"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SegmentedControl from '@/views/AssetsCenter/components/SegmentedControl.vue'

const props = defineProps({
  kindFilter: { type: String, default: 'all' },
  counts: { type: Object, required: true },
})

defineEmits(['change'])

const filterItems = computed(() => [
  { value: 'all', label: `全部${props.counts.total ? ` (${props.counts.total})` : ''}` },
  { value: 'character', label: `角色${props.counts.character ? ` (${props.counts.character})` : ''}` },
  { value: 'location', label: `场景${props.counts.location ? ` (${props.counts.location})` : ''}` },
  { value: 'prop', label: `道具${props.counts.prop ? ` (${props.counts.prop})` : ''}` },
])
</script>

<style scoped>
.filter-wrapper {
  padding: 0.75rem 1rem;
  overflow-x: auto;
}
</style>
