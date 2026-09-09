<template>
  <div class="user-section">
    <div class="account-name-area">
      <span class="account-name">{{ userInfo.name || '未登录' }}</span>
      <span class="account-badge">{{ isMainAccount ? '主账号' : '子账号' }}</span>
    </div>
    <div class="account-card">
      <div class="card-tier">
        <span class="card-tier-icon" :class="`card-tier-icon-${currentTierIndex}`" v-html="currentLevelIcon" />
        <div class="card-tier-info">
          <span class="card-tier-name">{{ displayLevelName }}</span>
          <span v-if="expireDateText" class="card-tier-expire">{{ expireDateText }}</span>
        </div>
      </div>
      <div class="card-balance">可用积分：{{ formatBalance(userInfo.balance) }}</div>
      <div class="card-actions">
        <button class="btn-action btn-upgrade" @click="showMemberDialog = true">{{ isMainAccount ? '升级' : '查看会员' }}</button>
        <button v-if="membershipStore.canBuyPoints && isMainAccount" class="btn-action btn-buy" @click="showPointsDialog = true">购买积分包</button>
      </div>
      <div v-if="membershipStore.nextLevel" class="downgrade-hint">
        <Info :size="14" />
        <span>已预约降级至「{{ membershipStore.nextLevel.name }}」，当前周期到期后生效</span>
      </div>
    </div>

    <!-- 新版会员权益弹框 -->
    <MembershipDialog v-model="showMemberDialog" :readonly="!isMainAccount" @payment-success="onMembershipPaymentSuccess" />

    <!-- 购买积分包弹框 -->
    <Teleport to="body">
      <div v-if="showPointsDialog" class="glass-overlay member-overlay" @click.self="showPointsDialog = false">
        <div class="glass-surface-modal member-dialog member-dialog-enter points-dialog" @click.stop @keydown.esc="showPointsDialog = false">
          <div class="modal-header">
            <h3 class="modal-title">购买积分包</h3>
            <button class="modal-close-btn" @click="showPointsDialog = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div class="modal-body member-body">
            <div class="points-form">
              <div class="points-current">
                <span class="points-current-label">当前可用积分</span>
                <span class="points-current-value">{{ formatBalance(userInfo.balance) }}</span>
              </div>
              <div class="points-input-group">
                <label class="points-label">购买积分数量</label>
                <input
                  v-model.number="pointsAmount"
                  type="number"
                  class="points-input"
                  placeholder="请输入积分数量"
                  min="10000"
                  step="1000"
                />
                <div class="points-hint">1 元 = 100 积分，10,000 积分起购</div>
                <div v-if="pointsError" class="points-error">{{ pointsError }}</div>
              </div>

              <div class="points-quick-select">
                <button
                  v-for="opt in quickOptions"
                  :key="opt"
                  class="quick-btn"
                  :class="{ active: pointsAmount === opt }"
                  @click="pointsAmount = opt"
                >{{ (opt / 10000).toFixed(opt % 10000 === 0 ? 0 : 1) }}万</button>
              </div>

              <div class="points-summary">
                <div class="points-summary-row">
                  <span class="points-summary-label">购买积分</span>
                  <span class="points-summary-value">{{ formatBalance(pointsAmount || 0) }} 积分</span>
                </div>
                <div class="points-summary-divider" />
                <div class="points-summary-row points-summary-total">
                  <span class="points-summary-label">需支付</span>
                  <span class="points-summary-price">¥{{ pointsCost }}</span>
                </div>
              </div>

              <button
                class="points-submit"
                :disabled="!!pointsError || !pointsAmount || buying"
                @click="handleBuyPoints"
              >
                <LoaderCircle v-if="buying" :size="16" class="spin-icon" />
                <template v-else>确认购买</template>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 支付二维码弹窗 -->
    <PayQrcodeDialog
      v-model:visible="payDialogVisible"
      :order-no="payOrder.orderNo"
      :qr-code-url="payOrder.qrCodeUrl"
      :amount="payOrder.amount"
      :original-amount="payOrder.originalAmount"
      :description="payOrder.description"
      :expire-time="payOrder.expireTime"
      @payment-success="onPaymentSuccess"
    />

  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Info, LoaderCircle } from '@lucide/vue'
import { useDict } from '@/utils/useDict'
import { formatBalance } from '@/utils/format'
import { useMembershipStore } from '@/store/membership'
import { createPointOrder } from '@/api/payOrder'
import MembershipDialog from './MembershipDialog.vue'
import PayQrcodeDialog from './PayQrcodeDialog.vue'

const props = defineProps({
  userInfo: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['balance-changed', 'switch-tab'])

const { user_type } = useDict('user_type')
const membershipStore = useMembershipStore()

// 主账号/子账号判断：子账号展示主账号会员等级，但无升级/购买积分入口
const isMainAccount = computed(() => !props.userInfo.parent_user_id)

const typeLabel = computed(() => {
  const item = user_type.value.find(d => d.key === props.userInfo.type)
  return item?.remark || props.userInfo.type
})

// ── 等级图标映射（侧边栏用户卡片，按 tier 索引） ──

const displayLevelName = computed(() => {
  if (membershipStore.currentLevel) return membershipStore.currentLevel.name
  // 无会员记录 → 免费版（优先取排序最小的等级名；levels 为空时固定显示"免费版"）
  return membershipStore.levels[0]?.name || '免费版'
})

// 非免费用户的有效期文案（免费用户无会员记录，expire_time 为空 → 不显示）
const expireDateText = computed(() => {
  const t = membershipStore.currentMembership?.expire_time
  if (!t) return ''
  return `有效期至 ${String(t).slice(0, 10)}`
})

const currentTierIndex = computed(() => {
  const level = membershipStore.currentLevel
  if (!level) return 0
  const idx = membershipStore.levels.findIndex(l => l.id === level.id)
  return idx >= 0 ? idx : 0
})

const LEVEL_ICONS = {
  0: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
  1: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
  2: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v3"/><path d="M12 12v4"/><path d="M10 14h4"/></svg>',
}

const currentLevelIcon = computed(() => {
  return LEVEL_ICONS[currentTierIndex.value] || LEVEL_ICONS[0]
})

// ── 弹框控制 ──

const showMemberDialog = ref(false)
const showPointsDialog = ref(false)

// ── 购买积分包 ──

const pointsAmount = ref(10000)
const quickOptions = [10000, 50000, 100000, 500000]

const pointsError = computed(() => {
  if (!pointsAmount.value || pointsAmount.value < 10000) return '最少购买 10,000 积分'
  if (!Number.isInteger(pointsAmount.value)) return '积分数量必须为整数'
  return ''
})

const pointsCost = computed(() => formatBalance(((pointsAmount.value || 0) / 100).toFixed(2)))

const handleBuyPoints = async () => {
  if (pointsError.value || !pointsAmount.value) return
  buying.value = true
  try {
    const data = await createPointOrder({
      point_amount: pointsAmount.value,
      pay_channel: 'unionpay',
    })
    payOrder.orderNo = data.order_no
    payOrder.qrCodeUrl = data.qr_code_url
    payOrder.amount = data.pay_amount
    payOrder.originalAmount = data.original_amount
    payOrder.description = `${formatBalance(pointsAmount.value)} 积分`
    payOrder.expireTime = data.expire_time
    showPointsDialog.value = false
    payDialogVisible.value = true
  } catch {
    // ElMessage 已由 request 拦截器处理
  } finally {
    buying.value = false
  }
}

// ── 支付二维码弹窗 ──

const payDialogVisible = ref(false)
const payOrder = reactive({
  orderNo: '',
  qrCodeUrl: '',
  amount: '',
  originalAmount: '',
  description: '',
  expireTime: '',
})
const buying = ref(false)

function onPaymentSuccess() {
  emit('balance-changed')
}

// ── 旧版会员权益弹框数据 ──

const billingPeriod = ref('monthly')

const planOrder = { free: 0, pro: 1, enterprise: 2 }

const currentPlanKey = computed(() => {
  const t = (props.userInfo.type || '').toLowerCase()
  const label = typeLabel.value || ''
  if (t === 'enterprise' || label.includes('企业')) return 'enterprise'
  if (t === 'pro' || t === 'professional' || label.includes('专业')) return 'pro'
  return 'free'
})

const currentBillingPeriod = computed(() => props.userInfo.billing_period || 'monthly')

function getPlanAction(planKey, cardPeriod) {
  const currentPlan = currentPlanKey.value
  const currentPeriod = currentBillingPeriod.value
  const level = planOrder[planKey] ?? 0
  const currentLevel = planOrder[currentPlan] ?? 0

  if (planKey === 'free') {
    if (currentPlan === 'free') return { visible: false, label: '当前版本' }
    return { visible: false }
  }

  if (currentPlan === 'free') {
    return { visible: true, label: '升级', disabled: false, crossPeriod: false }
  }

  if (cardPeriod === currentPeriod) {
    if (planKey === currentPlan) return { visible: false, label: '当前版本' }
    if (level > currentLevel) return { visible: true, label: '升级', disabled: false, crossPeriod: false }
    return { visible: false }
  }

  // 不同周期
  if (currentPeriod === 'monthly') {
    return { visible: true, label: '升级', disabled: true, crossPeriod: true }
  }
  return { visible: false }
}

const plans = computed(() => {
  const isYearly = billingPeriod.value === 'yearly'
  const period = billingPeriod.value
  return [
    {
      key: 'free',
      name: '免费版',
      price: '免费使用',
      priceUnit: '',
      priceNote: '',
      badge: '',
      ...getPlanAction('free', period),
      isCurrent: currentPlanKey.value === 'free',
      icon: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
      features: [
        '注册即赠 1,200 积分',
        '每日登录赠送 60 积分',
        '支持 480P / 720P 分辨率体验',
        '最多可管理 3 个项目',
        '支持 1 个并发任务',
        '使用普通任务队列',
        '生成内容带平台水印',
      ],
    },
    {
      key: 'pro',
      name: '专业版',
      price: isYearly ? '¥950' : '¥99',
      priceUnit: isYearly ? '/ 年' : '/ 月',
      priceNote: isYearly ? '相当于 ¥79/月' : '¥950 / 年',
      badge: '',
      ...getPlanAction('pro', period),
      isCurrent: currentPlanKey.value === 'pro',
      icon: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
      features: [
        '每月赠送 12,000 积分',
        '支持最高 1080P 分辨率',
        '最多可管理 100 个项目',
        '支持 5 个并发任务',
        '享受高速任务队列',
        '支持去除平台水印',
        '支持个人或小团队商用',
      ],
    },
    {
      key: 'enterprise',
      name: '企业版',
      price: isYearly ? '¥28,790' : '¥2,999',
      priceUnit: '起',
      priceNote: isYearly ? '相当于 ¥2,399/月' : '¥28,790 / 年',
      badge: '',
      ...getPlanAction('enterprise', period),
      isCurrent: currentPlanKey.value === 'enterprise',
      icon: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v3"/><path d="M12 12v4"/><path d="M10 14h4"/></svg>',
      features: [
        '400,000 积分/月起，可按需定制',
        '最高 1080P，可申请更高规格',
        '项目级可视化数据配置',
        '20 个并发任务起，可扩展专属队列',
        '专属任务队列与优先处理',
        '定制品牌水印',
        '企业商用及扩展授权',
        '子账号与团队权限配置',
      ],
    },
  ]
})

const billingRules = [
  {
    label: '计费方式',
    desc: '按模型调用消耗积分，不同模型和任务类型的单价不同。',
    icon: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>',
    color: 'blue',
  },
  {
    label: '用量查询',
    desc: '可在「积分使用记录」页面查看每次调用的积分消耗明细。',
    icon: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    color: 'teal',
  },
  {
    label: '积分有效期',
    desc: '充值积分长期有效；每日/月赠送积分仅当日/月有效；\n优先使用赠送积分。',
    icon: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    color: 'amber',
  },
  {
    label: '升级说明',
    desc: '升级后立即生效，积分额度将按照当前等级重新计算。',
    icon: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v10l4.24 4.24"/><circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-4.24 4.24"/></svg>',
    color: 'purple',
  },
]

// ── 升级确认弹框 ──

const showUpgradeDialog = ref(false)
const upgradePeriod = ref('monthly')
const selectedPlanForUpgrade = ref(null)

const openUpgradeDialog = (plan) => {
  showMemberDialog.value = false
  selectedPlanForUpgrade.value = plan
  upgradePeriod.value = billingPeriod.value
  showUpgradeDialog.value = true
}

const handlePlanAction = (plan) => {
  if (plan.crossPeriod) {
    ElMessage.warning('暂不支持直接切换月付/年付方式，请在当前周期结束后再次进行购买')
    return
  }
  openUpgradeDialog(plan)
}

const upgradeTarget = computed(() => {
  const plan = selectedPlanForUpgrade.value
  if (!plan) return {}
  const isYearly = upgradePeriod.value === 'yearly'
  const planData = plans.value.find(p => p.key === plan.key)
  if (!planData) return {}

  const priceConfig = {
    pro: {
      monthly: { price: '¥99', unit: '/月', original: '' },
      yearly: { price: '¥950', unit: '/年', original: '¥1,188' },
      prorated: '32.10',
      nextCycle: '¥99/月',
      points: '12,000',
    },
    enterprise: {
      monthly: { price: '¥2,399', unit: '/月', original: '¥2,999' },
      yearly: { price: '¥28,790', unit: '/年', original: '¥35,988' },
      prorated: '975.60',
      nextCycle: '¥2,399/月',
      points: '400,000',
    },
  }
  const config = priceConfig[plan.key] || priceConfig.pro
  const periodConfig = isYearly ? config.yearly : config.monthly

  return {
    key: plan.key,
    name: plan.name,
    icon: plan.icon,
    price: periodConfig.price,
    priceUnit: periodConfig.unit,
    originalPrice: periodConfig.original,
    pointsAdded: config.points,
    proratedCharge: config.prorated,
    nextCyclePrice: isYearly ? periodConfig.price + periodConfig.unit : config.nextCycle,
    nextBillingDate: '2026年7月12日',
  }
})

const handleUpgrade = () => {
  // TODO: 对接升级接口
  showUpgradeDialog.value = false
}

// ── 支付成功回调 ──

const onMembershipPaymentSuccess = () => {
  emit('balance-changed')
}

onMounted(async () => {
  await membershipStore.fetchLevels()
  membershipStore.fetchCurrent()
})
</script>

<style scoped>
.user-section {
  margin-bottom: 8px;
}

.account-name-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
}

.account-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-badge {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
  color: #0f9f62;
  background: rgba(16, 185, 129, 0.15);
  border: none;
  padding: 2px 10px;
  border-radius: 999px;
  flex-shrink: 0;
}

.account-card {
  margin: 16px 0 12px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.card-tier {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.card-tier-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.card-tier-name {
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  color: #333;
}

.card-tier-expire {
  font-size: 11px;
  font-weight: 400;
  line-height: 16px;
  color: #9ca3af;
}

.card-tier-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  flex-shrink: 0;
}

.card-tier-icon-0 {
  background: #f1f5f9;
  color: #64748b;
}

.card-tier-icon-1 {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.card-tier-icon-2 {
  background: rgba(124, 58, 237, 0.1);
  color: #7c3aed;
}

.card-balance {
  margin-top: 12px;
  font-size: 14px;
  line-height: 20px;
  color: #333;
}

.downgrade-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 12px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 12px;
  color: #1d4ed8;
  line-height: 1.5;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.btn-action {
  height: 32px;
  line-height: 32px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  text-align: center;
  white-space: nowrap;
  border: none;
}

.btn-upgrade {
  width: 80px;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  color: #ffffff;
}

.btn-upgrade:hover {
  background: linear-gradient(140deg, #1d63e8 0%, #2f7bff 100%);
}

.btn-buy {
  width: 116px;
  background: #ffffff;
  color: #2f7bff;
  border: 1px solid rgba(47, 123, 255, 0.3);
}

.btn-buy:hover {
  background: rgba(47, 123, 255, 0.06);
  border-color: #2f7bff;
}

/* ===== 弹框遮罩层 ===== */
.member-overlay {
  align-items: flex-start;
  justify-content: center;
  padding-top: 4.5rem;
  z-index: 60;
}

/* ===== 会员弹框 ===== */
.member-dialog {
  max-width: 920px;
  width: calc(100vw - 48px);
  max-height: calc(100vh - 6rem);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

@keyframes memberDialogIn {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.member-dialog-enter {
  animation: memberDialogIn 0.2s ease-out;
}

.member-body {
  padding: 20px 28px 24px;
  gap: 14px;
  overflow-y: auto;
  scrollbar-width: none;
}

.member-body::-webkit-scrollbar {
  display: none;
}

/* ===== 计费周期切换 ===== */
.billing-period-switch {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 4px;
  background: rgba(111, 126, 153, 0.08);
  border-radius: 10px;
  margin: 0 auto 10px;
  width: fit-content;
}

.period-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #6f7e99;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.period-option:hover {
  color: #374151;
}

.period-option.active {
  background: #fff;
  color: #1f2937;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.save-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  background: linear-gradient(135deg, #ff8a3d, #ff6b2c);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  border-radius: 6px;
  line-height: 1.5;
}

/* ===== 套餐卡片 ===== */
.plan-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.plan-card {
  position: relative;
  border-radius: 14px;
  border: 1px solid rgba(111, 126, 153, 0.14);
  padding: 20px 18px 18px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: transform 0.22s ease-out, box-shadow 0.22s ease-out, border-color 0.22s ease-out;
  cursor: default;
}

.plan-card-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 14px 14px 0 0;
}

.plan-card:hover {
  transform: translateY(-2px);
}

.plan-card:hover .plan-icon-box {
  transform: scale(1.05);
}

/* 免费版 */
.plan-free {
  background: linear-gradient(165deg, #fafafa 0%, #f4f4f5 100%);
}
.plan-free .plan-card-accent { background: linear-gradient(90deg, #9ca3af, #d1d5db); }
.plan-free .plan-features li svg { color: #9ca3af; }
.plan-free:hover { background: linear-gradient(165deg, #f3f3f4 0%, #e8e8ea 100%); border-color: rgba(156, 163, 175, 0.35); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06); }
.plan-free:hover .plan-icon-box { background: #e8ecf1; }

/* 专业版 */
.plan-pro {
  background: linear-gradient(165deg, #eff6ff 0%, #dbeafe 100%);
  border-color: rgba(59, 130, 246, 0.22);
}
.plan-pro .plan-card-accent { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.plan-pro .plan-features li svg { color: #3b82f6; }
.plan-pro:hover {
  background: linear-gradient(165deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: rgba(59, 130, 246, 0.45);
  box-shadow: 0 6px 24px rgba(59, 130, 246, 0.12);
}
.plan-pro:hover .plan-icon-box { background: rgba(59, 130, 246, 0.16); }

/* 企业版 */
.plan-enterprise {
  background: linear-gradient(165deg, #faf5ff 0%, #f3e8ff 100%);
}
.plan-enterprise .plan-card-accent { background: linear-gradient(90deg, #7c3aed, #a78bfa); }
.plan-enterprise .plan-features li svg { color: #8b5cf6; }
.plan-enterprise:hover { background: linear-gradient(165deg, #f3e8ff 0%, #e9d5ff 100%); border-color: rgba(124, 58, 237, 0.35); box-shadow: 0 6px 24px rgba(124, 58, 237, 0.1); }
.plan-enterprise:hover .plan-icon-box { background: rgba(124, 58, 237, 0.16); }

/* 推荐角标 */
.plan-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.2px;
  color: #fff;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border-radius: 10px;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.2);
  line-height: 1.5;
  z-index: 1;
}

/* 当前套餐 — 右上角斜三角丝带 */
.plan-current-ribbon {
  position: absolute;
  top: 0;
  right: 0;
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, #2f7bff 0%, #5ca8ff 100%);
  clip-path: polygon(100% 0, 0 0, 100% 100%);
  z-index: 2;
  pointer-events: none;
}

.plan-current-ribbon span {
  position: absolute;
  top: 16px;
  right: 4px;
  transform: rotate(45deg);
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

/* ===== 卡片顶部：左图标 + 右文字 ===== */
.plan-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 18px;
}

.plan-icon-box {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.22s ease-out, background 0.22s ease-out;
}

.plan-icon-box-free {
  background: #f1f5f9;
  color: #64748b;
}

.plan-icon-box-pro {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.plan-icon-box-enterprise {
  background: rgba(124, 58, 237, 0.1);
  color: #7c3aed;
}

.plan-header-text {
  min-width: 0;
}

.plan-name {
  font-size: 16px;
  font-weight: 700;
  color: #0a0a0a;
  margin: 0 0 4px;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.plan-price-val {
  font-size: 22px;
  font-weight: 700;
  color: #0a0a0a;
  line-height: 1.2;
}

.plan-price-free {
  font-size: 18px;
  color: #0a0a0a;
  margin-top: 6px;
}

.plan-price-pro {
  font-size: 26px;
  color: #2563eb;
}

.plan-price-enterprise {
  font-size: 24px;
  color: #7c3aed;
}

.plan-price-unit {
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
}

.plan-price-note {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
}

.plan-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  margin-bottom: 14px;
}

.plan-free .plan-features {
  margin-top: 18px;
}

.plan-features li {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12.5px;
  color: #374151;
  line-height: 1.6;
}

.plan-features li svg {
  flex-shrink: 0;
  margin-top: 2px;
}

/* 卡片底部按钮 */
.plan-action {
  width: 100%;
  padding: 8px 0;
  border-radius: 8px;
  border: 1px solid rgba(111, 126, 153, 0.2);
  font-size: 13px;
  font-weight: 600;
  cursor: default;
  transition: transform 0.15s ease-out, background 0.18s ease-out, color 0.18s ease-out, border-color 0.18s ease-out;
  text-align: center;
  flex-shrink: 0;
}

.plan-action:disabled {
  opacity: 1;
  cursor: default;
}

.plan-action-locked {
  opacity: 0.5;
  cursor: not-allowed;
}

.plan-action-locked:hover {
  opacity: 0.5;
}

.plan-action-free {
  background: #f4f4f5;
  color: #9ca3af;
  border-color: transparent;
}

.plan-action-pro {
  background: rgba(59, 130, 246, 0.08);
  color: #93b4f8;
  border-color: rgba(59, 130, 246, 0.15);
}

.plan-pro:hover .plan-action-pro {
  color: #2563eb;
  background: rgba(59, 130, 246, 0.14);
  border-color: rgba(59, 130, 246, 0.3);
}

.plan-action-enterprise {
  background: rgba(124, 58, 237, 0.06);
  color: #b794f6;
  border-color: rgba(124, 58, 237, 0.15);
  cursor: pointer;
}

.plan-action-enterprise:hover,
.plan-enterprise:hover .plan-action-enterprise {
  border-color: #7c3aed;
  background: rgba(124, 58, 237, 0.14);
  color: #7c3aed;
}

.plan-action-enterprise:active {
  transform: scale(0.98);
}

/* ===== 积分扣费规则 ===== */
.billing-rules {
  border-radius: 10px;
  border: 1px solid rgba(111, 126, 153, 0.1);
  background: #f7f8fa;
  padding: 12px 16px;
}

.billing-rules-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 8px;
}

.billing-rules-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.rule-card {
  background: #fff;
  border: 1px solid rgba(111, 126, 153, 0.12);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  transition: transform 0.18s ease-out, background 0.18s ease-out, box-shadow 0.18s ease-out;
}

.rule-card:hover {
  transform: translateY(-1px);
  background: #f8fafc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.rule-card:hover .rule-icon {
  transform: scale(1.05);
}

.rule-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.18s ease-out;
}

.rule-icon-blue { background: #eff6ff; color: #3b82f6; }
.rule-icon-teal { background: #f0fdfa; color: #14b8a6; }
.rule-icon-amber { background: #fffbeb; color: #d97706; }
.rule-icon-purple { background: #faf5ff; color: #8b5cf6; }

.rule-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.rule-label {
  font-size: 12.5px;
  font-weight: 600;
  color: #374151;
}

.rule-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.45;
  white-space: pre-line;
}

/* ===== 购买积分包弹框 ===== */
.points-dialog {
  max-width: 520px;
}

.points-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 4px 0 8px;
}

.points-current {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.points-current-label {
  font-size: 13px;
  color: #6b7280;
}

.points-current-value {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.points-input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.points-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.points-input {
  height: 40px;
  padding: 0 14px;
  font-size: 14px;
  color: #111827;
  background: #fff;
  border: 1px solid rgba(111, 126, 153, 0.24);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.points-input:focus {
  border-color: #2f7bff;
  box-shadow: 0 0 0 3px rgba(47, 123, 255, 0.12);
}

.points-hint {
  font-size: 12px;
  color: #6b7280;
}

.points-error {
  font-size: 12px;
  color: #dc2626;
}

.points-quick-select {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-btn {
  padding: 6px 14px;
  font-size: 13px;
  color: #4b5563;
  background: rgba(111, 126, 153, 0.08);
  border: 1px solid transparent;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-btn:hover {
  background: rgba(47, 123, 255, 0.08);
  color: #2f7bff;
}

.quick-btn.active {
  background: rgba(47, 123, 255, 0.12);
  color: #2f7bff;
  border-color: rgba(47, 123, 255, 0.3);
}

.points-summary {
  background: #f9fafb;
  border: 1px solid rgba(111, 126, 153, 0.16);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.points-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.points-summary-label {
  font-size: 13px;
  color: #4b5563;
}

.points-summary-value {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.points-summary-divider {
  height: 1px;
  background: rgba(111, 126, 153, 0.16);
}

.points-summary-total .points-summary-label {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.points-summary-price {
  font-size: 22px;
  font-weight: 700;
  color: #2f7bff;
  background: linear-gradient(135deg, #2f7bff 0%, #5ca8ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.points-submit {
  height: 42px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.points-submit:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
}

.points-submit:disabled {
  background: #c8d4e8;
  cursor: not-allowed;
}

.spin-icon {
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== 升级确认弹框 ===== */
.upgrade-dialog {
  max-width: 520px;
}

.upgrade-plan-info {
  background: #f9fafb;
  border: 1px solid rgba(111, 126, 153, 0.12);
  border-radius: 12px;
  padding: 16px;
}

.upgrade-plan-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.upgrade-period-switch {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  background: rgba(111, 126, 153, 0.08);
  border-radius: 8px;
  margin-left: auto;
  flex-shrink: 0;
}

.upgrade-period-opt {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #6f7e99;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
  white-space: nowrap;
}

.upgrade-period-opt:hover {
  color: #374151;
}

.upgrade-period-opt.active {
  background: #fff;
  color: #1f2937;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.upgrade-plan-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.upgrade-plan-icon-pro {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.upgrade-plan-icon-enterprise {
  background: rgba(124, 58, 237, 0.1);
  color: #7c3aed;
}

.upgrade-plan-text {
  min-width: 0;
}

.upgrade-plan-name {
  font-size: 16px;
  font-weight: 700;
  color: #0a0a0a;
  margin: 0 0 4px;
}

.upgrade-plan-price-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.upgrade-price-original {
  font-size: 14px;
  color: #9ca3af;
  text-decoration: line-through;
}

.upgrade-price-current {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.upgrade-price-pro {
  color: #2563eb;
}

.upgrade-price-enterprise {
  color: #7c3aed;
}

.upgrade-price-unit {
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
}

.upgrade-points-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  font-size: 13px;
  color: #1e40af;
  line-height: 1.5;
}

.upgrade-points-notice strong {
  color: #2f7bff;
}

.upgrade-fee-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upgrade-fee-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #374151;
  line-height: 1.5;
}

.upgrade-fee-item svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.upgrade-fee-item strong {
  color: #111827;
}

.upgrade-fee-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.upgrade-fee-hint {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
  padding-left: 22px;
}

.upgrade-next-cycle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f9fafb;
  border: 1px solid rgba(111, 126, 153, 0.12);
  border-radius: 10px;
}

.upgrade-next-cycle-label {
  font-size: 13px;
  color: #6b7280;
}

.upgrade-next-cycle-date {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.upgrade-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 28px;
  border-top: 1px solid rgba(111, 126, 153, 0.1);
  flex-shrink: 0;
}

.glass-btn-base {
  height: 34px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.glass-btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.glass-btn-secondary:hover {
  background: #e5e7eb;
}

.glass-btn-primary {
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(47, 123, 255, 0.24);
}

.glass-btn-primary:hover {
  opacity: 0.92;
}

/* ===== 响应式 ===== */
@media (max-width: 780px) {
  .plan-cards {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .billing-rules-grid {
    grid-template-columns: 1fr;
  }
  .member-dialog {
    max-width: 480px;
    width: calc(100vw - 32px);
    max-height: calc(100vh - 4rem);
  }
  .member-overlay {
    padding-top: 2rem;
  }
  .member-body {
    padding: 16px 18px 20px;
  }
}
</style>
