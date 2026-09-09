import { ref, computed } from 'vue'
import { getUserInfo } from '@/api/user'

const userInfo = ref(null)
const loaded = ref(false)

const isMainAccount = computed(() => {
  return userInfo.value?.parent_user_id === null || userInfo.value?.parent_user_id === undefined
})

const isSubAccount = computed(() => {
  return userInfo.value?.parent_user_id !== null && userInfo.value?.parent_user_id !== undefined
})

const permissions = computed(() => {
  if (isMainAccount.value) return null
  return userInfo.value?.permissions || {}
})

export function useUserStore() {
  async function fetchUser() {
    try {
      const data = await getUserInfo()
      userInfo.value = data
      loaded.value = true
      return data
    } catch (e) {
      loaded.value = false
      throw e
    }
  }

  function hasPermission(code) {
    if (isMainAccount.value) return true
    return !!permissions.value?.[code]
  }

  function reset() {
    userInfo.value = null
    loaded.value = false
  }

  return {
    userInfo,
    loaded,
    isMainAccount,
    isSubAccount,
    permissions,
    fetchUser,
    hasPermission,
    reset,
  }
}
