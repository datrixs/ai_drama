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

    <main class="hero-section">
      <div class="hero-container">
        <div class="hero-content">
          <h1 class="hero-title">
            <span class="hero-title-primary">AI影视Studio</span>
<!--            <span class="hero-title-accent">AI影视Studio</span>-->
          </h1>
          <div class="hero-cta">
            <router-link to="/auth/signup" class="cta-btn">立即体验</router-link>
          </div>
        </div>

        <div class="hero-visual">
          <div class="visual-wrapper">
            <div class="visual-glow"></div>
            <div class="visual-card visual-card-1"></div>
            <div class="visual-card visual-card-2"></div>
            <div class="visual-card visual-card-main">
              <div class="card-preview">
                <div class="preview-img">
                  <div class="preview-dot"></div>
                  <div class="preview-shape"></div>
                </div>
                <div class="preview-lines">
                  <div class="preview-line line-long"></div>
                  <div class="preview-line line-short"></div>
                  <div class="preview-actions">
                    <div class="action-circle"></div>
                    <div class="action-btn-mock"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <SiteFooter />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SiteFooter from '@/components/SiteFooter.vue'

const router = useRouter()

onMounted(() => {
  const token = localStorage.getItem('token')
  if (token) {
    router.replace('/home')
  }
})
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

.hero-section {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: -4rem;
  padding: 0 1rem;
}

.hero-container {
  max-width: 80rem;
  margin: 0 auto;
  display: grid;
  gap: 4rem;
  align-items: center;
}

@media (min-width: 1024px) {
  .hero-container {
    grid-template-columns: repeat(2, 1fr);
  }
}

.hero-content {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.hero-title {
  font-size: 3rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.1;
}

@media (min-width: 768px) {
  .hero-title {
    font-size: 4.5rem;
  }
}

.hero-title-primary {
  display: block;
  color: #0a0a0a;
}

.hero-title-accent {
  display: block;
  color: #1d63e8;
}

.hero-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding-top: 1rem;
}

.cta-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(140deg, #2f7bff 0%, #5ca8ff 100%);
  border: none;
  border-radius: 0.75rem;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.3s;
}

.cta-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.hero-visual {
  position: relative;
  height: 600px;
  display: none;
  align-items: center;
  justify-content: center;
}

@media (min-width: 1024px) {
  .hero-visual {
    display: flex;
  }
}

.visual-wrapper {
  position: relative;
  width: 100%;
  max-width: 28rem;
  aspect-ratio: 1;
}

.visual-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 120%;
  height: 120%;
  background: radial-gradient(circle, rgba(148, 163, 184, 0.2), transparent 65%);
  border-radius: 50%;
  filter: blur(48px);
  opacity: 0.7;
}

.visual-card {
  position: absolute;
  border-radius: 1.5rem;
}

.visual-card-1 {
  top: 0;
  right: 2.5rem;
  width: 16rem;
  height: 20rem;
  background: rgba(255, 255, 255, 0.88);
  border: 0.667px solid rgba(255, 255, 255, 0.22);
  box-shadow: 0 6px 18px rgba(19, 35, 66, 0.08);
  transform: rotate(6deg);
  animation: float-delayed 6s ease-in-out infinite;
}

.visual-card-2 {
  bottom: 2.5rem;
  left: 2.5rem;
  width: 18rem;
  height: 20rem;
  background: rgba(255, 255, 255, 0.78);
  border: 0.667px solid rgba(111, 126, 153, 0.24);
  box-shadow: 0 6px 18px rgba(19, 35, 66, 0.08);
  transform: rotate(-3deg);
  animation: float-slow 7s ease-in-out infinite;
}

.visual-card-main {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20rem;
  height: 24rem;
  background: rgba(255, 255, 255, 0.97);
  border: 0.667px solid rgba(255, 255, 255, 0.22);
  box-shadow: 0 14px 34px rgba(15, 32, 66, 0.14);
  overflow: hidden;
  animation: float 5s ease-in-out infinite;
}

.card-preview {
  padding: 1.5rem;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.preview-img {
  width: 100%;
  height: 12rem;
  background: rgba(255, 255, 255, 0.86);
  border-radius: 1rem;
  margin-bottom: 1.5rem;
  position: relative;
  overflow: hidden;
  background: rgba(47, 123, 255, 0.06);
}

.preview-dot {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.88);
}

.preview-shape {
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  width: 3rem;
  height: 3rem;
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.94);
  transform: rotate(12deg);
}

.preview-lines {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.preview-line {
  height: 0.75rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.86);
}

.preview-line.line-long {
  width: 75%;
}

.preview-line.line-short {
  width: 50%;
}

.preview-actions {
  padding-top: 1rem;
  display: flex;
  gap: 0.5rem;
}

.action-circle {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.88);
  border: 0.667px solid rgba(255, 255, 255, 0.22);
}

.action-btn-mock {
  height: 2.5rem;
  flex: 1;
  border-radius: 9999px;
  background: rgba(47, 123, 255, 0.16);
  border: 0.667px solid rgba(111, 126, 153, 0.24);
}

@keyframes float {
  0%, 100% { transform: translate(-50%, -50%) translateY(0); }
  50% { transform: translate(-50%, -50%) translateY(-10px); }
}

@keyframes float-delayed {
  0%, 100% { transform: rotate(6deg) translateY(0); }
  50% { transform: rotate(6deg) translateY(-15px); }
}

@keyframes float-slow {
  0%, 100% { transform: rotate(-3deg) translateY(0); }
  50% { transform: rotate(-3deg) translateY(-12px); }
}
</style>
