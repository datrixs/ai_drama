import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMembershipLevels, getCurrentMembership } from '@/api/membership'
import { getPointPlans } from '@/api/point'

export const useMembershipStore = defineStore('membership', () => {
  const levels = ref([])
  const currentMembership = ref(null)
  const pointPlans = ref([])
  const loading = ref(false)

  const currentLevel = computed(() => currentMembership.value?.level || null)

  const currentSubscribeType = computed(() => currentMembership.value?.subscribe_type || null)

  const nextLevel = computed(() => currentMembership.value?.next_level || null)

  const canBuyPoints = computed(() => {
    if (!currentLevel.value) return false
    const level = levels.value.find(l => l.id === currentLevel.value.id)
    return level?.can_buy_points ?? false
  })

  function isCurrentLevel(levelId) {
    return currentLevel.value?.id === levelId
  }

  async function fetchLevels() {
    if (levels.value.length > 0) return levels.value
    loading.value = true
    try {
      const data = await getMembershipLevels()
      levels.value = Array.isArray(data) ? data : []
      return levels.value
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrent() {
    try {
      // 确保 levels 已加载，currentTierIndex 等计算属性依赖 levels
      if (levels.value.length === 0) {
        await fetchLevels()
      }
      const data = await getCurrentMembership()
      currentMembership.value = data || null
      return currentMembership.value
    } catch {
      currentMembership.value = null
    }
  }

  async function fetchPointPlans() {
    if (pointPlans.value.length > 0) return pointPlans.value
    try {
      const data = await getPointPlans()
      pointPlans.value = Array.isArray(data) ? data : []
      return pointPlans.value
    } catch {
      pointPlans.value = []
    }
  }

  function clearCache() {
    levels.value = []
    currentMembership.value = null
    pointPlans.value = []
  }

  return {
    levels,
    currentMembership,
    pointPlans,
    loading,
    currentLevel,
    currentSubscribeType,
    nextLevel,
    canBuyPoints,
    isCurrentLevel,
    fetchLevels,
    fetchCurrent,
    fetchPointPlans,
    clearCache,
  }
})
