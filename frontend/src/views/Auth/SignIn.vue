<template>
  <div class="glass-page">
    <nav class="glass-nav">
      <div class="nav-inner">
        <div class="nav-left">
          <router-link to="/" class="nav-logo" title="返回首页">
            <img src="/pipixia-logo2.png" alt="皮皮虾短剧" class="logo-img" />
          </router-link>
        </div>
        <div class="nav-right">
          <router-link to="/auth/signin" class="nav-link">登录</router-link>
          <router-link to="/auth/signup" class="nav-btn">注册</router-link>
        </div>
      </div>
    </nav>

    <div class="page-body">
      <div class="form-wrapper">
        <div class="glass-card">
          <div class="card-header">
            <h1 class="card-title">欢迎回来</h1>
            <p class="card-subtitle">登录到平台</p>
          </div>

          <form class="auth-form" @submit.prevent="handleSubmit">
            <div class="form-field">
              <label class="field-label" for="username">用户名</label>
              <input
                id="username"
                v-model="username"
                name="username"
                type="text"
                autocomplete="username"
                required
                class="field-input"
                placeholder="请输入用户名"
              />
            </div>

            <div class="form-field">
              <label class="field-label" for="password">密码</label>
              <input
                id="password"
                v-model="password"
                name="password"
                type="password"
                autocomplete="current-password"
                required
                class="field-input"
                placeholder="请输入密码"
              />
            </div>

            <div v-if="errorMsg" class="error-alert">
              {{ errorMsg }}
            </div>

            <button
              type="submit"
              :disabled="loading"
              class="submit-btn"
            >
              <span v-if="loading" class="btn-loading">
                <span class="spinner"></span>
                登录中...
              </span>
              <span v-else>登录</span>
            </button>
          </form>

          <div class="card-footer">
            <p class="footer-text">
              还没有账户？
              <router-link to="/auth/signup" class="footer-link">立即注册</router-link>
            </p>
          </div>

          <div class="card-bottom">
            <router-link to="/" class="back-home">← 返回首页</router-link>
          </div>
        </div>
      </div>
    </div>

    <SiteFooter />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { loginApi } from '@/api/auth'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

const handleSubmit = async () => {
  if (!username.value.trim() || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    const data = await loginApi(username.value.trim(), password.value)
    localStorage.setItem('token', data.access_token)
    const redirect = route.query.redirect || '/home'
    router.push(redirect)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.glass-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f3f4f6;
}

.glass-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 0.667px solid rgba(255, 255, 255, 0.22);
  box-shadow: 0 8px 18px rgba(15, 32, 66, 0.1);
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
  .nav-inner {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .nav-inner {
    padding: 0 2rem;
  }
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

.nav-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
}

.nav-link {
  font-size: 0.875rem;
  font-weight: 500;
  color: #111827;
  text-decoration: none;
  transition: color 0.15s;
  cursor: pointer;
}

.nav-link:hover {
  color: #0a0a0a;
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 1rem;
  cursor: pointer;
  text-decoration: none;
  transition: opacity 0.15s;
}

.nav-btn:hover {
  opacity: 0.9;
}

.page-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
}

.form-wrapper {
  max-width: 28rem;
  width: 100%;
}

.glass-card {
  background: rgba(255, 255, 255, 0.97);
  border: 0.667px solid rgba(255, 255, 255, 0.22);
  border-radius: 1.75rem;
  padding: 2rem;
  box-shadow: 0 14px 34px rgba(15, 32, 66, 0.14);
}

.card-header {
  text-align: center;
  margin-bottom: 2rem;
}

.card-title {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0a0a0a;
  margin-bottom: 0.5rem;
}

.card-subtitle {
  color: #111827;
  font-size: 1rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.field-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #0a0a0a;
}

.field-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.86);
  border: 0.667px solid transparent;
  border-radius: 1rem;
  color: #0a0a0a;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.field-input::placeholder {
  color: #4b5563;
}

.field-input:focus {
  border-color: rgba(47, 123, 255, 0.64);
  box-shadow: 0 0 0 3px rgba(47, 123, 255, 0.22);
}

.error-alert {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(236, 72, 72, 0.64);
  color: #cb3a3a;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
}

.submit-btn {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 1rem;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
  box-shadow: 0 2px 10px rgba(47, 123, 255, 0.24);
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-loading {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.card-footer {
  margin-top: 1.5rem;
  text-align: center;
}

.footer-text {
  color: #111827;
  font-size: 0.875rem;
}

.footer-link {
  color: #1d63e8;
  font-weight: 600;
  text-decoration: none;
  transition: text-decoration 0.15s;
}

.footer-link:hover {
  text-decoration: underline;
}

.card-bottom {
  margin-top: 1.5rem;
  text-align: center;
}

.back-home {
  color: #4b5563;
  font-size: 0.875rem;
  text-decoration: none;
  transition: color 0.15s;
}

.back-home:hover {
  color: #111827;
}
</style>
