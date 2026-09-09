<template>
  <div class="glass-page">
    <nav class="glass-nav">
      <div class="nav-inner">
        <div class="nav-left">
          <router-link to="/" class="nav-logo" title="返回首页">
            <img src="/pipixia-logo2.png" alt="皮皮虾短剧" class="logo-img" />
          </router-link>
          <div
            v-if="showSwitcher"
            class="region-switcher"
            @click.stop="openRegionDialog"
          >
            <div class="region-current">
              <svg class="region-current-icon" :class="{ 'region-current-icon-overseas': currentRegion === 'overseas' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" /><path d="M2 12h20" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              <span class="region-current-text">{{ currentRegionLabel }}</span>
              <svg class="region-current-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </div>
          </div>
        </div>
        <div class="nav-right">
          <router-link to="/home" class="nav-link" :class="{ active: $route.path === '/home' }">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m12.296 3.464 3.02 3.956" /><path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3z" /><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="m6.18 5.276 3.1 3.899" />
            </svg>
            视频制作
          </router-link>
          <router-link to="/canvas" class="nav-link" :class="{ active: $route.path.startsWith('/canvas') }">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect width="8" height="8" x="3" y="3" rx="2" /><path d="M7 11v4a2 2 0 0 0 2 2h4" /><rect width="8" height="8" x="13" y="13" rx="2" />
            </svg>
            无限画布
          </router-link>
          <router-link to="/workspace" class="nav-link" :class="{ active: $route.path.startsWith('/workspace') }">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
            </svg>
            工作区
          </router-link>
          <router-link to="/assets-center" class="nav-link" :class="{ active: $route.path === '/assets-center' }">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
            资产中心
          </router-link>
          <router-link to="/config-center" class="nav-link" :class="{ active: $route.path === '/config-center' }">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            设置中心
          </router-link>
        </div>
      </div>
    </nav>

    <main class="page-main">
      <slot />
    </main>

    <NoPermissionAlert
      :visible="noPermVisible"
      :message="noPermMessage"
      @close="handleNoPermClose"
    />

    <RegionSettingsDialog
      v-model="showRegionDialog"
      :current-region="currentRegion"
      :default-region="pendingRegion"
      @switched="onRegionSwitched"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { logoutApi } from '@/api/auth'
import { useUserStore } from '@/store/user'
import { useWebSocket } from '@/composables/useWebSocket'
import NoPermissionAlert from '@/components/NoPermissionAlert.vue'
import RegionSettingsDialog from '@/views/ConfigCenter/components/RegionSettingsDialog.vue'

const router = useRouter()
const route = useRoute()

const userStore = useUserStore()

const noPermVisible = ref(false)
const noPermMessage = ref('')

const PERM_MESSAGES = {
  'project:read': '你当前没有「查看项目」的权限，无法进入工作区，请联系主账号管理员开通。',
  'asset:read': '你当前没有「查看资产」的权限，无法访问资产中心，请联系主账号管理员开通。',
}

function showNoPermission(permissionCode) {
  noPermMessage.value = PERM_MESSAGES[permissionCode] || '你当前没有该功能的访问权限，请联系主账号管理员开通。'
  noPermVisible.value = true
}

function handleNoPermClose() {
  noPermVisible.value = false
}

router.beforeEach(async (to, from, next) => {
  noPermVisible.value = false
  // 防御性清理：确保页面切换时 body overflow 不被残留锁定
  document.body.style.overflow = ''

  if (!to.meta.permission) {
    return next()
  }

  if (!userStore.loaded.value) {
    try {
      await userStore.fetchUser()
    } catch {
      return next()
    }
  }

  if (userStore.isSubAccount.value && !userStore.hasPermission(to.meta.permission)) {
    showNoPermission(to.meta.permission)
    return next(false)
  }

  next()
})

const handleLogout = async () => {
  try {
    await logoutApi()
  } catch {
    // 忽略登出接口错误，仍然清除本地状态
  }
  localStorage.removeItem('token')
  router.push('/auth/signin')
}

// ── 区域切换（国内版 / 国际版） ──
const showRegionDialog = ref(false)
const pendingRegion = ref('')

const showSwitcher = computed(() => !!userStore.userInfo.value)
const currentRegion = computed(() => userStore.userInfo.value?.region || 'domestic')
const currentRegionLabel = computed(() => (currentRegion.value === 'overseas' ? '国际版' : '国内版'))

function openRegionDialog() {
  // 弹窗内自带区域选择 + 配置状态展示 + 二次确认
  pendingRegion.value = currentRegion.value
  showRegionDialog.value = true
}

function onRegionSwitched({ videoModel }) {
  // reload 会清掉当前页 JS 状态（含 ElMessage），用 sessionStorage 把消息带到新页面
  // onMounted 检查并展示，移除 setTimeout 等待
  sessionStorage.setItem('region_switched_msg', JSON.stringify({
    type: videoModel ? 'success' : 'warning',
    text: videoModel
      ? `切换成功，当前视频生成模型已切换为：${videoModel}`
      : '切换成功，当前暂无视频生成模型',
  }))
  window.location.reload()
}

onMounted(async () => {
  if (!userStore.loaded.value) {
    try {
      await userStore.fetchUser()
    } catch {
      // 未登录场景由路由守卫处理，这里忽略
    }
  }

  // 启动全局 WS 连接（单例，重复挂载安全）—— 用于画布生成进度等实时事件推送
  const userId = userStore.userInfo.value?.id
  if (userId) {
    useWebSocket().connect(userId)
  }

  // 区域切换后通过 reload 带过来的提示消息（reload 会清掉 ElMessage，所以这里补展示）
  const savedMsg = sessionStorage.getItem('region_switched_msg')
  if (savedMsg) {
    sessionStorage.removeItem('region_switched_msg')
    try {
      const { type, text } = JSON.parse(savedMsg)
      if (type === 'warning') {
        ElMessage.warning(text)
      } else {
        ElMessage.success(text)
      }
    } catch {
      // 消息体损坏时静默丢弃
    }
  }
})
</script>

<style scoped>
.glass-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--glass-bg-canvas);
}

.glass-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: var(--glass-bg-nav);
  border-bottom: 1px solid var(--glass-stroke-soft);
  box-shadow: var(--glass-shadow-nav);
  backdrop-filter: blur(var(--glass-blur-nav));
  -webkit-backdrop-filter: blur(var(--glass-blur-nav));
}

.nav-inner {
  max-width: 80rem;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  height: 4rem;
}

@media (min-width: 640px) {
  .nav-inner { padding: 0 1.5rem; }
}
@media (min-width: 1024px) {
  .nav-inner { padding: 0 2rem; }
}

.nav-left {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.75rem;
}

.nav-logo {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  border-radius: 0.5rem;
  outline: none;
  text-decoration: none;
}

.logo-img {
  width: 173.42px;
  height: 48px;
  object-fit: contain;
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  letter-spacing: -0.02em;
}

/* ── 区域切换下拉框 ── */
.region-switcher {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.region-current {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px 4px 8px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--glass-text-secondary);
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease;
  user-select: none;
  white-space: nowrap;
}

.region-current:hover {
  color: var(--glass-text-primary);
  background: rgba(47, 123, 255, 0.08);
}

.region-current-icon {
  width: 1rem;
  height: 1rem;
  color: #2f7bff;
}
.region-current-icon-overseas {
  color: #6366f1;
}

.region-current-text {
  line-height: 20px;
}

.region-current-arrow {
  width: 12px;
  height: 12px;
  transition: transform 0.18s ease;
  color: var(--glass-text-tertiary);
}

.region-current-arrow.open {
  transform: rotate(180deg);
}

.region-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 148px;
  padding: 4px;
  background: #ffffff;
  border: 1px solid rgba(111, 126, 153, 0.16);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 60;
  animation: regionDropdownIn 0.16s ease-out;
}

@keyframes regionDropdownIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.region-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: #374151;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.region-option:hover {
  background: rgba(47, 123, 255, 0.08);
  color: #2f7bff;
}

.region-option.active {
  color: #2f7bff;
  font-weight: 600;
  background: rgba(47, 123, 255, 0.06);
}

.region-check {
  width: 14px;
  height: 14px;
  color: #2f7bff;
}

.nav-right {
  display: flex;
  min-width: 0;
  flex: 1;
  justify-content: flex-end;
  align-items: center;
  gap: 1.5rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--glass-text-secondary);
  text-decoration: none;
  transition: color 0.15s;
  cursor: pointer;
  white-space: nowrap;
}

.nav-link:hover {
  color: var(--glass-text-primary);
}

.nav-link.active {
  color: var(--glass-accent-from);
}

.nav-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

.logout-btn {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--glass-text-tertiary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.15s;
  padding: 0.25rem 0.5rem;
  white-space: nowrap;
}

.logout-btn:hover {
  color: var(--glass-tone-danger-fg);
}

.page-main {
  flex: 1;
}
</style>
