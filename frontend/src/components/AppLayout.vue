<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="logo">Redmine Helper</div>
      <ul class="nav-menu">
        <li><RouterLink to="/">대시보드</RouterLink></li>
        <li><RouterLink to="/duplicates">중복 감지</RouterLink></li>
        <li><RouterLink to="/settings">설정</RouterLink></li>
      </ul>
      <button @click="logout" class="logout-btn">로그아웃</button>
    </nav>
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; min-height: 100vh; min-width: 1280px; }
.sidebar {
  width: 220px; background: #1e293b; color: white;
  padding: 24px 0; display: flex; flex-direction: column;
}
.logo { padding: 0 20px 24px; font-size: 18px; font-weight: 700; }
.nav-menu { list-style: none; padding: 0; margin: 0; flex: 1; }
.nav-menu li a {
  display: block; padding: 12px 20px; color: #cbd5e1;
  text-decoration: none; transition: background 0.2s;
}
.nav-menu li a:hover, .nav-menu li a.router-link-active {
  background: #334155; color: white;
}
.logout-btn {
  margin: 0 20px; padding: 10px; background: #ef4444;
  color: white; border: none; border-radius: 6px; cursor: pointer;
}
.main-content { flex: 1; padding: 32px; background: #f8fafc; overflow-y: auto; }
</style>
