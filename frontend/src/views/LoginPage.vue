<template>
  <div class="login-root">
    <div class="login-card">

      <!-- Logo / 品牌 -->
      <div class="login-brand">
        <span class="login-logo">⚕</span>
        <div>
          <div class="login-title">企业运营分析与投研辅助系统</div>
          <div class="login-subtitle">Enterprise Operations Analysis & Investment Research</div>
        </div>
      </div>

      <!-- 表单 -->
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="login-field">
          <label class="login-label">账号</label>
          <input
            v-model="username"
            class="login-input"
            type="text"
            placeholder="请输入账号"
            autocomplete="username"
          />
        </div>
        <div class="login-field">
          <label class="login-label">密码</label>
          <input
            v-model="password"
            class="login-input"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </div>

        <div v-if="error" class="login-error">{{ error }}</div>

        <button class="login-btn" type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>

    </div>

    <!-- 背景装饰 -->
    <div class="login-bg-circle login-bg-circle--1"></div>
    <div class="login-bg-circle login-bg-circle--2"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import usersRaw from '../data/users.csv?raw'

const router = useRouter()
const username = ref('')
const password = ref('')
const error    = ref('')
const loading  = ref(false)

// 解析 CSV
function parseUsers(csv) {
  const lines = csv.trim().split('\n').slice(1) // 跳过 header
  return lines.map(line => {
    const [u, p] = line.split(',')
    return { username: u?.trim(), password: p?.trim() }
  })
}

function handleLogin() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  setTimeout(() => {
    const users = parseUsers(usersRaw)
    const match = users.find(
      u => u.username === username.value && u.password === password.value
    )
    if (match) {
      sessionStorage.setItem('user', username.value)
      router.push('/')
    } else {
      error.value = '账号或密码错误'
    }
    loading.value = false
  }, 400)
}
</script>

<style scoped>
.login-root {
  position: fixed; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-deep);
  overflow: hidden;
}

/* 纹样背景层 */
.login-root::before {
  content: '';
  position: absolute; inset: 0;
  background-image: url('../assets/pattern.webp');
  background-size: 420px auto;
  background-repeat: repeat;
  opacity: 0.07;
  mix-blend-mode: multiply;
  pointer-events: none;
  filter: hue-rotate(140deg) saturate(0.6);
}

/* 渐变遮罩，让纹样边缘柔和 */
.login-root::after {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 70% 70% at 50% 50%, transparent 40%, var(--bg-deep) 100%);
  pointer-events: none;
}

/* 背景装饰圆 */
.login-bg-circle {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}
.login-bg-circle--1 {
  width: 480px; height: 480px;
  top: -120px; right: -100px;
  background: radial-gradient(circle, rgba(75,169,154,0.1) 0%, transparent 70%);
}
.login-bg-circle--2 {
  width: 360px; height: 360px;
  bottom: -80px; left: -80px;
  background: radial-gradient(circle, rgba(75,169,154,0.07) 0%, transparent 70%);
}

/* 卡片 */
.login-card {
  position: relative; z-index: 1;
  width: 380px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 40px 36px 36px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.08), 0 2px 8px rgba(75,169,154,0.08);
  animation: cardRise .5s ease both;
}

/* 品牌区 */
.login-brand {
  display: flex; align-items: center; gap: 14px;
  margin-bottom: 32px;
}
.login-logo {
  font-size: 36px; line-height: 1;
  background: rgba(75,169,154,0.12);
  border: 1px solid rgba(75,169,154,0.25);
  border-radius: 12px;
  width: 52px; height: 52px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.login-title {
  font-size: 17px; font-weight: 700;
  color: var(--text-primary);
}
.login-subtitle {
  font-size: 11px; color: var(--text-muted);
  margin-top: 3px;
}

/* 表单 */
.login-form { display: flex; flex-direction: column; gap: 18px; }

.login-field { display: flex; flex-direction: column; gap: 6px; }
.login-label {
  font-size: 12px; font-weight: 600;
  color: var(--text-secondary);
}
.login-input {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
  transition: border-color .2s, box-shadow .2s;
}
.login-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}
.login-input::placeholder { color: var(--text-muted); }

.login-error {
  font-size: 12px; color: var(--red);
  background: rgba(224,82,82,0.08);
  border: 1px solid rgba(224,82,82,0.2);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
}

.login-btn {
  margin-top: 4px;
  background: var(--accent2);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  padding: 12px;
  font-size: 15px; font-weight: 600;
  cursor: pointer;
  transition: background .2s, box-shadow .2s;
}
.login-btn:hover:not(:disabled) {
  background: var(--accent);
  box-shadow: 0 4px 16px var(--accent-glow);
}
.login-btn:disabled {
  background: #cbd5e1; color: #94a3b8; cursor: not-allowed;
}
</style>
