<template>
  <Teleport to="body">
    <div v-if="modelValue" class="glass-overlay member-overlay" @click.self="handleClose">
      <div class="glass-surface-modal member-dialog member-dialog-enter" @click.stop @keydown.esc="handleClose">
        <div class="modal-header">
          <h3 class="modal-title">会员权益</h3>
          <button class="modal-close-btn" @click="handleClose">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>

        <div class="modal-body member-body">
          <div v-if="store.loading" class="loading-wrapper">
            <LoaderCircle :size="24" class="spin-icon" />
          </div>

          <template v-else>
            <!-- 计费周期切换（暂时隐藏月度/年度切换，仅展示月度会员） -->
            <div v-if="showPeriodSwitch" class="billing-period-switch">
              <span class="period-option" :class="{ active: subscribeType === 'monthly' }" @click="subscribeType = 'monthly'">月付</span>
              <span class="period-option" :class="{ active: subscribeType === 'yearly' }" @click="subscribeType = 'yearly'">年付<span v-if="maxYearlySaved" class="save-tag">{{ maxYearlySaved }}</span></span>
            </div>

            <!-- 套餐对比卡片 -->
            <div class="plan-cards">
              <div
                v-for="level in store.levels"
                :key="level.id"
                class="plan-card"
                :class="[
                  `plan-tier-${getTierIndex(level)}`,
                  { 'plan-current': isCurrentActiveLevel(level) },
                ]"
              >
                <div class="plan-card-accent" />
                <div class="plan-current-ribbon" v-if="isCurrentActiveLevel(level)"><span>当前</span></div>

                <!-- 顶部：左图标容器 + 右文字价格 -->
                <div class="plan-header">
                  <div class="plan-icon-box" :class="`plan-icon-box-${getTierIndex(level)}`" v-html="getLevelIcon(level)" />
                  <div class="plan-header-text">
                    <h4 class="plan-name">{{ level.name }}</h4>
                    <div class="plan-price">
                      <span class="plan-price-val" :class="`plan-price-tier-${getTierIndex(level)}`">
                        <template v-if="isFreeTier(level)">免费使用</template>
                        <template v-else>{{ subscribeType === 'monthly' ? `¥${Math.round(level.monthly_discount_price)}` : `¥${Math.round(level.yearly_discount_price)}` }}</template>
                      </span>
                      <span v-if="!isFreeTier(level)" class="plan-price-unit">
                        {{ subscribeType === 'monthly' ? '/ 月' : '/ 年' }}
                      </span>
                    </div>
                    <!-- 月付：年化价格 -->
                    <div v-if="subscribeType === 'monthly' && !isFreeTier(level)" class="plan-price-note">
                      相当于 ¥{{ Math.round(Number(level.monthly_discount_price) * 12) }}/年
                    </div>
                    <!-- 年付：月均价格 -->
                    <div v-if="subscribeType === 'yearly' && !isFreeTier(level)" class="plan-price-note">
                      相当于 ¥{{ Math.round(Number(level.yearly_discount_price) / 12) }}/月
                    </div>
                  </div>
                </div>

                <ul class="plan-features">
                  <li v-for="(feature, idx) in getLevelFeatures(level)" :key="idx">
                    <Check :size="13" />
                    <span>{{ feature }}</span>
                  </li>
                </ul>

                <!-- 按钮区域：免费版、当前版本、只读模式不显示按钮 -->
                <template v-if="!isFreeTier(level) && !isCurrentActiveLevel(level) && !readonly">
                  <button
                    class="plan-action"
                    :class="[`plan-action-tier-${getTierIndex(level)}`]"
                    :disabled="payingLevelId === level.id"
                    @click="handlePay(level)"
                  >
                    <LoaderCircle v-if="payingLevelId === level.id" :size="14" class="spin-icon" />
                    <template v-else>升级</template>
                  </button>
                </template>
              </div>
            </div>

            <!-- 积分扣费规则 -->
            <div class="billing-rules">
              <h5 class="billing-rules-title">积分扣费规则</h5>
              <div class="billing-rules-grid">
                <div v-for="rule in billingRules" :key="rule.label" class="rule-card">
                  <div class="rule-icon" :class="`rule-icon-${rule.color}`" v-html="rule.icon" />
                  <div class="rule-text">
                    <span class="rule-label">{{ rule.label }}</span>
                    <span class="rule-desc">{{ rule.desc }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

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
    </div>
  </Teleport>

  <!-- 确认变更弹窗 -->
  <Teleport to="body">
    <div v-if="showConfirmDialog" class="glass-overlay member-overlay" @click.self="showConfirmDialog = false">
      <div class="glass-surface-modal member-dialog member-dialog-enter upgrade-dialog" @click.stop @keydown.esc="showConfirmDialog = false">
        <div class="modal-header">
          <h3 class="modal-title">{{ confirmTitle }}</h3>
          <button class="modal-close-btn" @click="showConfirmDialog = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>

        <div class="modal-body member-body">
          <!-- 套餐信息 -->
          <div class="upgrade-plan-info">
            <div class="upgrade-plan-header">
              <div class="upgrade-plan-icon" :class="`upgrade-plan-icon-${getTierIndex(confirmTarget)}`" v-html="confirmTarget ? getLevelIcon(confirmTarget) : ''" />
              <div class="upgrade-plan-text">
                <h4 class="upgrade-plan-name">{{ confirmTarget?.name }}</h4>
                <div class="upgrade-plan-price-row">
                  <span class="upgrade-price-current" :class="`upgrade-price-tier-${getTierIndex(confirmTarget)}`">¥{{ previewData.pay_amount }}</span>
                </div>
              </div>
              <!-- 计费周期显示 -->
              <div class="upgrade-period-tag">
                {{ subscribeType === 'monthly' ? '月付' : '年付' }}
              </div>
            </div>
          </div>

          <!-- 积分到账提示 -->
          <div v-if="Number(previewData.point_adjust) > 0" class="upgrade-points-notice">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2f7bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            <span><strong>{{ previewData.point_adjust }}</strong> 积分将立即添加到您的每月积分</span>
          </div>

          <!-- 费用说明 -->
          <div class="upgrade-fee-items">
            <div class="upgrade-fee-item">
              <div class="upgrade-fee-main">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2f7bff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                <span>您将在今天支付本账单周期剩余部分的费用：<strong>¥{{ previewData.pay_amount }}</strong></span>
              </div>
              <div class="upgrade-fee-hint">根据您当前计划的剩余时间计算升级金额，并补发两个计划之间的积分差额</div>
            </div>
          </div>

          <!-- 下一个计费周期 -->
          <div v-if="previewData.effective_time" class="upgrade-next-cycle">
            <span class="upgrade-next-cycle-label">下一个计费周期</span>
            <span class="upgrade-next-cycle-date">{{ previewData.effective_time }}</span>
          </div>
        </div>

        <div class="modal-footer upgrade-footer">
          <button class="glass-btn-secondary glass-btn-base" @click="showConfirmDialog = false">取消</button>
          <button class="glass-btn-primary glass-btn-base" @click="confirmAndPay">确认</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { LoaderCircle, Check } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { useMembershipStore } from '@/store/membership'
import { createMembershipOrder } from '@/api/payOrder'
import { getChangePreview } from '@/api/membership'
import PayQrcodeDialog from './PayQrcodeDialog.vue'

const props = defineProps({
  modelValue: Boolean,
  // 只读模式（子账号）：隐藏购买/升级按钮，仅展示套餐权益对比
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'payment-success'])

const store = useMembershipStore()

// 暂时隐藏月度/年度切换，仅展示月度会员；恢复时将 showPeriodSwitch 置为 true 即可
const showPeriodSwitch = false
const subscribeType = ref('monthly')

const payingLevelId = ref('')
const payDialogVisible = ref(false)
const payOrder = reactive({
  orderNo: '',
  qrCodeUrl: '',
  amount: '',
  originalAmount: '',
  description: '',
  expireTime: '',
})

// ── 确认弹窗状态 ──

const showConfirmDialog = ref(false)
const confirmTarget = ref(null)
const previewData = reactive({
  change_type: 0,
  pay_amount: '',
  point_adjust: '',
  effective_time: '',
  expire_time: '',
  message: '',
})

const confirmTitle = computed(() => {
  if (!confirmTarget.value || !store.currentLevel) return '确认变更'
  return confirmTarget.value.level_order > (store.currentLevel.level_order || 0)
    ? '升级并获得积分'
    : '降级确认'
})

// ── 视觉层级辅助函数 ──

function getTierIndex(level) {
  return store.levels.findIndex(l => l.id === level.id)
}

function isFreeTier(level) {
  return getTierIndex(level) === 0
}

// ── 图标映射（按 tier 索引：0=免费 1=专业 2=企业） ──

const LEVEL_ICONS = {
  0: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
  1: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
  2: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v3"/><path d="M12 12v4"/><path d="M10 14h4"/></svg>',
}

function getLevelIcon(level) {
  const tier = getTierIndex(level)
  return LEVEL_ICONS[tier] || LEVEL_ICONS[0]
}

// ── 权益文案 ──

function getLevelFeatures(level) {
  const mp = level.privileges.find(p => p.key === 'monthly_points')
  const mpVal = mp ? Number(mp.value).toLocaleString() : '0'
  const tier = getTierIndex(level)

  const POINTS_TEMPLATES = {
    0: `注册即赠 ${mpVal} 积分`,
    1: `每月赠送 ${mpVal} 积分`,
    2: `${mpVal} 积分/月起，可按需定制`,
  }

  const FIXED_FEATURES = {
    0: [
      '每日登录赠送 60 积分',
      '支持 480P / 720P 分辨率体验',
      '最多可管理 3 个项目',
      '支持 1 个并发任务',
      '使用普通任务队列',
      '生成内容带平台水印',
    ],
    1: [
      '支持最高 1080P 分辨率',
      '最多可管理 100 个项目',
      '支持 5 个并发任务',
      '享受高速任务队列',
      '支持去除平台水印',
      '支持个人或小团队商用',
    ],
    2: [
      '最高 1080P，可申请更高规格',
      '项目级可视化数据配置',
      '20 个并发任务起，可扩展专属队列',
      '专属任务队列与优先处理',
      '定制品牌水印',
      '企业商用及扩展授权',
      '子账号与团队权限配置',
    ],
  }

  const pointsText = POINTS_TEMPLATES[tier] || `每月赠送 ${mpVal} 积分`
  const fixed = FIXED_FEATURES[tier] || []
  return [pointsText, ...fixed]
}

// ── 价格辅助 ──


const maxYearlySaved = computed(() => {
  const percents = store.levels
    .filter(l => Number(l.monthly_discount_price) > 0)
    .map(l => {
      const monthlyYearTotal = Number(l.monthly_discount_price) * 12
      const yearlyTotal = Number(l.yearly_discount_price)
      const saved = Math.round((1 - yearlyTotal / monthlyYearTotal) * 100)
      return saved > 0 ? saved : 0
    })
    .filter(p => p > 0)
  if (percents.length === 0) return ''
  return `省${Math.max(...percents)}%`
})

// ── 积分扣费规则 ──

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

// ── 场景识别 ──

function isCurrentActiveLevel(level) {
  return store.isCurrentLevel(level.id) && store.currentSubscribeType === subscribeType.value
}

// ── 购买流程 ──

function handleClose() {
  payDialogVisible.value = false
  emit('update:modelValue', false)
}

async function handlePay(level) {
  // 降级拦截
  if (store.currentLevel && level.level_order < store.currentLevel.level_order) {
    ElMessage.warning('暂不支持降级')
    return
  }
  // 跨类型拦截
  if (store.currentSubscribeType && subscribeType.value !== store.currentSubscribeType) {
    ElMessage.warning('暂不支持直接切换月付/年付方式，请在当前周期结束后再次进行购买')
    return
  }

  let preview
  try {
    preview = await getChangePreview({
      target_level_id: level.id,
      subscribe_type: subscribeType.value,
    })
  } catch {
    return
  }

  if (!preview || preview.change_type === 0) {
    ElMessage.warning(preview?.message || '不支持的操作')
    return
  }

  // 升级/降级需打开自定义确认弹窗
  if (preview.change_type === 2 || preview.change_type === 3) {
    confirmTarget.value = level
    Object.assign(previewData, preview)
    showConfirmDialog.value = true
    return
  }

  // 首次购买直接下单
  await placeOrder(level)
}

async function confirmAndPay() {
  if (!confirmTarget.value) return
  showConfirmDialog.value = false
  await placeOrder(confirmTarget.value)
  confirmTarget.value = null
}

async function placeOrder(level) {
  payingLevelId.value = level.id
  try {
    const data = await createMembershipOrder({
      level_id: level.id,
      subscribe_type: subscribeType.value,
      pay_channel: 'unionpay',
    })
    const suffix = subscribeType.value === 'monthly' ? '月付' : '年付'
    payOrder.orderNo = data.order_no
    payOrder.qrCodeUrl = data.qr_code_url
    payOrder.amount = data.pay_amount
    payOrder.originalAmount = data.original_amount
    payOrder.description = `${level.name} ${suffix}`
    payOrder.expireTime = data.expire_time
    payDialogVisible.value = true
  } catch {
    // ElMessage 已由 request 拦截器处理
  } finally {
    payingLevelId.value = ''
  }
}

function onPaymentSuccess() {
  emit('payment-success')
}

watch(() => props.modelValue, (val) => {
  if (val) {
    store.fetchLevels()
    store.fetchCurrent()
  } else {
    payDialogVisible.value = false
    showConfirmDialog.value = false
  }
})
</script>

<style scoped>
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
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
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

.loading-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #2f7bff;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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

/* ===== 套餐卡片 grid ===== */
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

/* --- 免费版 --- */
.plan-tier-0 {
  background: linear-gradient(165deg, #fafafa 0%, #f4f4f5 100%);
}
.plan-tier-0 .plan-card-accent { background: linear-gradient(90deg, #9ca3af, #d1d5db); }
.plan-tier-0 .plan-features li svg { color: #9ca3af; }
.plan-tier-0:hover { background: linear-gradient(165deg, #f3f3f4 0%, #e8e8ea 100%); border-color: rgba(156, 163, 175, 0.35); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06); }
.plan-tier-0:hover .plan-icon-box { background: #e8ecf1; }

/* --- 专业版 --- */
.plan-tier-1 {
  background: linear-gradient(165deg, #eff6ff 0%, #dbeafe 100%);
  border-color: rgba(59, 130, 246, 0.22);
}
.plan-tier-1 .plan-card-accent { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.plan-tier-1 .plan-features li svg { color: #3b82f6; }
.plan-tier-1:hover { background: linear-gradient(165deg, #dbeafe 0%, #bfdbfe 100%); border-color: rgba(59, 130, 246, 0.45); box-shadow: 0 6px 24px rgba(59, 130, 246, 0.12); }
.plan-tier-1:hover .plan-icon-box { background: rgba(59, 130, 246, 0.16); }

/* --- 企业版 --- */
.plan-tier-2 {
  background: linear-gradient(165deg, #faf5ff 0%, #f3e8ff 100%);
}
.plan-tier-2 .plan-card-accent { background: linear-gradient(90deg, #7c3aed, #a78bfa); }
.plan-tier-2 .plan-features li svg { color: #8b5cf6; }
.plan-tier-2:hover { background: linear-gradient(165deg, #f3e8ff 0%, #e9d5ff 100%); border-color: rgba(124, 58, 237, 0.35); box-shadow: 0 6px 24px rgba(124, 58, 237, 0.1); }
.plan-tier-2:hover .plan-icon-box { background: rgba(124, 58, 237, 0.16); }

/* 当前套餐高亮 */
.plan-current {
  border-color: rgba(59, 130, 246, 0.4) !important;
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

.plan-icon-box-0 {
  background: #f1f5f9;
  color: #64748b;
}

.plan-icon-box-1 {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

.plan-icon-box-2 {
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

.plan-price-tier-0 {
  font-size: 18px;
  color: #0a0a0a;
  margin-top: 6px;
}

.plan-price-tier-1 {
  font-size: 26px;
  color: #2563eb;
}

.plan-price-tier-2 {
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

/* ===== 权益列表 ===== */
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

.plan-tier-0 .plan-features {
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

.plan-features li.privilege-disabled {
  opacity: 0.45;
}

.plan-features li.privilege-disabled .cross-icon {
  color: #9ca3af;
}

/* ===== 按钮区域 ===== */
.plan-action {
  width: 100%;
  padding: 8px 0;
  border-radius: 8px;
  border: 1px solid rgba(111, 126, 153, 0.2);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s ease-out, background 0.18s ease-out, color 0.18s ease-out, border-color 0.18s ease-out;
  text-align: center;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.plan-action:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.plan-action-locked {
  opacity: 0.5;
  cursor: not-allowed;
}

.plan-action-locked:hover {
  opacity: 0.5;
}

.plan-action-current-label {
  background: #f4f4f5;
  color: #9ca3af;
  border-color: transparent;
  cursor: default;
  text-align: center;
}

/* 专业版按钮 */
.plan-action-tier-1 {
  background: rgba(59, 130, 246, 0.08);
  color: #93b4f8;
  border-color: rgba(59, 130, 246, 0.15);
}

.plan-tier-1:hover .plan-action-tier-1 {
  color: #2563eb;
  background: rgba(59, 130, 246, 0.14);
  border-color: rgba(59, 130, 246, 0.3);
}

/* 企业版按钮 */
.plan-action-tier-2 {
  background: rgba(124, 58, 237, 0.06);
  color: #b794f6;
  border-color: rgba(124, 58, 237, 0.15);
}

.plan-action-tier-2:hover,
.plan-tier-2:hover .plan-action-tier-2 {
  border-color: #7c3aed;
  background: rgba(124, 58, 237, 0.14);
  color: #7c3aed;
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

/* ===== 确认变更弹窗 ===== */
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

.upgrade-plan-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.upgrade-plan-icon-1 { background: rgba(59, 130, 246, 0.1); color: #2563eb; }
.upgrade-plan-icon-2 { background: rgba(124, 58, 237, 0.1); color: #7c3aed; }
.upgrade-plan-icon-0 { background: #f1f5f9; color: #64748b; }

.upgrade-plan-text {
  min-width: 0;
  flex: 1;
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

.upgrade-price-current {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.upgrade-price-tier-1 { color: #2563eb; }
.upgrade-price-tier-2 { color: #7c3aed; }
.upgrade-price-tier-0 { color: #0a0a0a; }

.upgrade-period-tag {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  background: rgba(111, 126, 153, 0.08);
  padding: 4px 10px;
  border-radius: 6px;
  flex-shrink: 0;
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
