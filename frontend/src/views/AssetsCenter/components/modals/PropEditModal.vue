<template>
  <LocationEditModal
    :location="location"
    :image-index="imageIndex"
    @close="$emit('close')"
  />
</template>

<script setup>
import LocationEditModal from './LocationEditModal.vue'

defineProps({
  location: { type: Object, required: true },
  imageIndex: { type: Number, default: 0 }
})

defineEmits(['close'])
</script>
