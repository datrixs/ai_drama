<template>
  <AppLayout>
    <div class="config-page">
      <div class="config-layout">
        <aside class="config-sidebar">
          <div class="sidebar-inner">
            <LoginUserInfo :user-info="userInfo" @balance-changed="loadUserInfo" @switch-tab="activeTab = $event" />
            <ConfigCenterMenu v-model="activeTab" :menu-items="sidebarTabs" />
            <button class="logout-btn" @click="handleLogout">退出登录</button>
          </div>
        </aside>

        <div class="config-content">
          <div v-if="activeTab === 'api'" class="content-inner">
            <ApiConfig />
          </div>

          <div v-else-if="activeTab === 'billing'" class="content-inner">
            <UserBilling />
          </div>

          <div v-else-if="activeTab === 'subAccounts'" class="content-inner">
            <SubUserManage @balance-changed="loadUserInfo" />
          </div>

          <div v-else-if="activeTab === 'transferPoint'" class="content-inner">
            <TransferPoint @balance-changed="loadUserInfo" />
          </div>

          <div v-else-if="activeTab === 'payOrders'" class="content-inner">
            <PayOrderList />
          </div>

          <div v-else-if="activeTab === 'changePassword'" class="content-inner">
            <ChangePassword />
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Settings, Coins, Users, ArrowRightLeft, HandCoins, Lock
} from '@lucide/vue'
import { logoutApi } from '@/api/auth'
import { getUserInfo } from '@/api/user'
import { useUserStore } from '@/store/user'
import { useMembershipStore } from '@/store/membership'
import { useWebSocket } from '@/composables/useWebSocket'
import AppLayout from '@/layout/AppLayout.vue'
import LoginUserInfo from './components/LoginUserInfo.vue'
import ConfigCenterMenu from './components/ConfigCenterMenu.vue'
import ApiConfig from './ApiConfig.vue'
import UserBilling from './UserBilling.vue'
import SubUserManage from './SubUserManage.vue'
import TransferPoint from './TransferPoint.vue'
import PayOrderList from './PayOrderList.vue'
import ChangePassword from './ChangePassword.vue'

const router = useRouter()

const userStore = useUserStore()
const membershipStore = useMembershipStore()
const ws = useWebSocket()

const activeTab = ref('api')

const userInfo = reactive({
  name: '',
  role: '',
  email: '',
  type: '',
  balance: '0.00',
  parent_user_id: undefined,
  region: 'domestic'
})

const isPrimaryAccount = computed(() => userInfo.parent_user_id === null)

// 付费会员判断：以会员等级(level)为准。
// membership/current 对免费用户也会返回带 granted_balance/purchased_balance 的对象（非 null），
// 故不能判断 currentMembership 整体，必须看 level 字段（与 LoginUserInfo 的「免费版」口径一致）。
const isPaidMember = computed(() => !!membershipStore.currentLevel)

const sidebarTabs = computed(() => {
  const tabs = [
    { key: 'api', label: 'API 配置', icon: Settings },
    { key: 'billing', label: '积分使用记录', icon: Coins },
    { key: 'payOrders', label: '积分获取记录', icon: HandCoins },
  ]
  if (isPrimaryAccount.value) {
    tabs.push({ key: 'subAccounts', label: '子账号管理', icon: Users })
    // 积分转账仅对付费会员开放，免费用户不显示
    if (isPaidMember.value) {
      tabs.push({ key: 'transferPoint', label: '积分转账', icon: ArrowRightLeft })
    }
  }
  tabs.push({ key: 'changePassword', label: '修改密码', icon: Lock })
  return tabs
})

const loadUserInfo = async () => {
  try {
    const user = await getUserInfo()
    userInfo.name = user.username || ''
    userInfo.role = user.parent_user_id ? '子账号' : '主账号'
    userInfo.email = user.email || ''
    userInfo.type = user.type || ''
    userInfo.balance = user.balance || '0.00'
    userInfo.parent_user_id = user.parent_user_id || null
    userInfo.region = user.region || 'domestic'
  } catch {
    // 获取用户信息失败时使用默认值
  }
}

const handleLogout = async () => {
  try {
    await logoutApi()
  } catch {
    // 忽略登出接口错误
  }
  localStorage.removeItem('token')
  router.push('/auth/signin')
}

onMounted(async () => {
  await loadUserInfo()
  // 拉取当前会员信息，供 sidebarTabs 判断是否显示「积分转账」
  await membershipStore.fetchCurrent()
  // 设置中心涉及积分充值，需建立 WS 以接收支付结果推送
  if (!userStore.loaded.value) {
    await userStore.fetchUser()
  }
  const userId = userStore.userInfo.value?.id
  if (userId) ws.connect(userId)
})
</script>

<style scoped>
.config-page {
  padding: 20px 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.config-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 140px);
}

.config-sidebar {
  width: 256px;
  flex-shrink: 0;
}

.sidebar-inner {
  background: rgba(255, 255, 255, 0.96);
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  border-radius: 16px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.logout-btn {
  margin-top: auto;
  width: 100%;
  padding: 12px 16px;
  border-radius: 12px;
  border: none;
  background: rgba(239, 68, 68, 0.15);
  color: #cb3a3a;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.25);
}

.config-content {
  flex: 1;
  min-width: 0;
}

.content-inner {
  background: rgba(255, 255, 255, 0.96);
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  border-radius: 16px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
</style>
