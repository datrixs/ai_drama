<template>
  <Teleport to="body">
    <Transition name="cf-fade">
      <div v-if="visible" class="glass-overlay pay-overlay">
        <div class="glass-surface-modal pay-qrcode-modal" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">扫码支付</h3>
            <button class="modal-close-btn" @click="handleClose">
              <X :size="16" />
            </button>
          </div>

          <div class="modal-body pay-dialog-body">
            <!-- 购买描述 -->
            <div class="pay-desc">{{ description }}</div>

            <!-- 金额 -->
            <div class="pay-amount-row">
              <span v-if="originalAmount && originalAmount !== amount" class="pay-original">¥{{ originalAmount }}</span>
              <span class="pay-amount">¥{{ amount }}</span>
            </div>

            <!-- 二维码 -->
            <div class="qr-wrapper">
              <div v-if="qrLoading" class="qr-loading">
                <LoaderCircle :size="32" class="spin-icon" />
              </div>
              <img v-else :src="qrImageData" alt="支付二维码" class="qr-image" />
            </div>

            <p class="qr-tip">请使用手机扫码完成支付</p>

            <!-- 订单号 -->
            <div class="pay-order-no">
              订单号：{{ orderNo }}
            </div>

            <!-- 倒计时 -->
            <div class="pay-countdown">
              <template v-if="expired">订单已超时</template>
              <template v-else>剩余时间：{{ countdownText }}</template>
            </div>

            <!-- 状态提示 -->
            <div v-if="status === 'success'" class="pay-status pay-status-success">
              <CircleCheckBig :size="16" />
              支付成功
            </div>
            <div v-else-if="status === 'failed'" class="pay-status pay-status-failed">
              <XCircle :size="16" />
              支付失败，请重新下单
            </div>

            <!-- 已完成支付？手动查询按钮 -->
            <button
              v-if="status === 'pending'"
              class="glass-btn-soft check-btn"
              @click="checkOrderStatus"
            >
              已完成支付？
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { LoaderCircle, CircleCheckBig, XCircle, X } from '@lucide/vue'
import QRCode from 'qrcode'
import { useWebSocket } from '@/composables/useWebSocket'
import { WSEventType } from '@/constants/ws'
import { getPayOrderDetail } from '@/api/payOrder'
import { useMembershipStore } from '@/store/membership'

const props = defineProps({
  visible: { type: Boolean, default: false },
  orderNo: { type: String, default: '' },
  qrCodeUrl: { type: String, default: '' },
  amount: { type: String, default: '0.00' },
  originalAmount: { type: String, default: '' },
  description: { type: String, default: '' },
  expireTime: { type: String, default: '' },
})

const emit = defineEmits(['update:visible', 'payment-success'])

const membershipStore = useMembershipStore()
const { onEvent, offEvent } = useWebSocket()

const qrImageData = ref('')
const qrLoading = ref(true)
const status = ref('pending') // pending | success | failed
const expired = ref(false)
const remainSeconds = ref(0)
let countdownTimer = null

const countdownText = computed(() => {
  const m = Math.floor(remainSeconds.value / 60)
  const s = remainSeconds.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

async function generateQrCode() {
  if (!props.qrCodeUrl) return
  qrLoading.value = true
  try {
    qrImageData.value = await QRCode.toDataURL(props.qrCodeUrl, {
      width: 200,
      margin: 2,
      color: { dark: '#000000', light: '#ffffff' },
    })
  } catch {
    qrImageData.value = ''
  } finally {
    qrLoading.value = false
  }
}

function startCountdown() {
  if (!props.expireTime) return
  const expire = new Date(props.expireTime).getTime()
  const update = () => {
    const diff = Math.max(0, Math.floor((expire - Date.now()) / 1000))
    remainSeconds.value = diff
    if (diff <= 0) {
      expired.value = true
      stopCountdown()
    }
  }
  update()
  countdownTimer = setInterval(update, 1000)
}

function stopCountdown() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

// WebSocket 监听支付结果
function handleWsEvent(event) {
  if (event.event_type !== WSEventType.PAY_ORDER_STATUS) return
  if (event.data?.order_no !== props.orderNo) return

  if (event.data.status === 3) {
    onPaymentSuccess()
  } else if (event.data.status === 4) {
    status.value = 'failed'
    stopCountdown()
  }
}

async function onPaymentSuccess() {
  status.value = 'success'
  stopCountdown()
  ElMessage.success('支付成功')
  // 刷新会员状态和积分余额
  await Promise.all([
    membershipStore.clearCache(),
    membershipStore.fetchCurrent(),
  ])
  emit('payment-success')
  setTimeout(() => handleClose(), 1500)
}

// 兜底：手动查询订单状态
async function checkOrderStatus() {
  if (!props.orderNo) return
  try {
    const order = await getPayOrderDetail(props.orderNo)
    if (order?.status === 3) {
      onPaymentSuccess()
    } else if (order?.status === 4) {
      status.value = 'failed'
      stopCountdown()
      ElMessage.error('支付失败')
    } else {
      ElMessage.info('暂未查询到支付结果，请稍后再试')
    }
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

function handleClose() {
  stopCountdown()
  offEvent(handleWsEvent)
  status.value = 'pending'
  expired.value = false
  emit('update:visible', false)
}

// 弹窗打开时初始化
watch(() => props.visible, (val) => {
  if (val) {
    status.value = 'pending'
    expired.value = false
    generateQrCode()
    startCountdown()
    onEvent(handleWsEvent)
  } else {
    stopCountdown()
    offEvent(handleWsEvent)
  }
})

onUnmounted(() => {
  stopCountdown()
  offEvent(handleWsEvent)
})
</script>

<style scoped>
.pay-overlay {
  z-index: 70;
  align-items: flex-start;
  justify-content: center;
  padding-top: 4.5rem;
}

.pay-qrcode-modal {
  max-width: 420px;
  width: 90%;
  display: flex;
  flex-direction: column;
}

.pay-dialog-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
  gap: 12px;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.pay-desc {
  font-size: 14px;
  font-weight: 500;
  color: var(--glass-text-secondary, #111827);
}

.pay-amount-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.pay-original {
  font-size: 14px;
  color: #9ca3af;
  text-decoration: line-through;
}

.pay-amount {
  font-size: 28px;
  font-weight: 700;
  color: var(--glass-text-primary, #0a0a0a);
}

.qr-wrapper {
  width: 200px;
  height: 200px;
  border: 1px solid var(--glass-stroke-base, rgba(111, 126, 153, 0.24));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.qr-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--glass-accent-from, #2f7bff);
}

.qr-image {
  width: 200px;
  height: 200px;
}

.qr-tip {
  font-size: 13px;
  color: var(--glass-text-tertiary, #4b5563);
  margin: 0;
}

.pay-order-no {
  font-size: 12px;
  color: #9ca3af;
}

.pay-countdown {
  font-size: 13px;
  color: var(--glass-text-tertiary, #4b5563);
}

.pay-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  padding: 8px 20px;
  border-radius: 8px;
}

.pay-status-success {
  color: var(--glass-tone-success-fg, #0f9f62);
  background: var(--glass-tone-success-bg, rgba(16, 185, 129, 0.2));
}

.pay-status-failed {
  color: var(--glass-tone-danger-fg, #cb3a3a);
  background: var(--glass-tone-danger-bg, rgba(239, 68, 68, 0.2));
}

.check-btn {
  font-size: 13px;
  font-weight: 600;
  padding: 6px 16px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

/* 过渡动画 */
.cf-fade-enter-active,
.cf-fade-leave-active {
  transition: opacity 0.2s ease;
}

.cf-fade-enter-from,
.cf-fade-leave-to {
  opacity: 0;
}
</style>
