import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const isAuthenticated = computed(() => !!token.value)

  async function login(password: string): Promise<void> {
    const { data } = await authApi.login(password)
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
  }

  function logout(): void {
    token.value = null
    localStorage.removeItem('access_token')
  }

  return { token, isAuthenticated, login, logout }
})
