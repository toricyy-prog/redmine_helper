<script setup lang="ts">
defineProps<{ status: 'success' | 'failed' | 'no_similar' }>()
const labelMap = { success: '성공', failed: '실패', no_similar: '유사 없음' }
const colorMap = { success: '#22c55e', failed: '#ef4444', no_similar: '#f59e0b' }
</script>

<template>
  <span class="badge" :style="{ backgroundColor: colorMap[status] }">
    {{ labelMap[status] }}
  </span>
</template>

<style scoped>
.badge {
  display: inline-block; padding: 2px 10px;
  border-radius: 12px; color: white; font-size: 12px; font-weight: 600;
}
</style>
