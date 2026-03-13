<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const password = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

async function handleLogin() {
  if (!password.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.login(password.value)
    router.push('/')
  } catch {
    errorMessage.value = '비밀번호가 올바르지 않습니다.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="login-title">Redmine Helper</h1>
      <p class="login-subtitle">대시보드 로그인</p>
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="password">비밀번호</label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="대시보드 비밀번호 입력"
            :disabled="isLoading"
            autofocus
          />
        </div>
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <button type="submit" :disabled="isLoading || !password" class="login-button">
          {{ isLoading ? '로그인 중...' : '로그인' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}
.login-card {
  background: white;
  border-radius: 8px;
  padding: 40px;
  width: 360px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}
.login-title { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.login-subtitle { color: #666; margin-bottom: 32px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 8px; font-weight: 500; }
.form-group input {
  width: 100%; padding: 10px 14px;
  border: 1px solid #ddd; border-radius: 6px;
  font-size: 14px; box-sizing: border-box;
}
.error-message { color: #e53e3e; font-size: 14px; margin-bottom: 12px; }
.login-button {
  width: 100%; padding: 12px;
  background: #3b82f6; color: white;
  border: none; border-radius: 6px;
  font-size: 15px; font-weight: 600; cursor: pointer;
}
.login-button:disabled { background: #93c5fd; cursor: not-allowed; }
</style>
