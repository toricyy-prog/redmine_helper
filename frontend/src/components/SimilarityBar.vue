<script setup lang="ts">
const props = defineProps<{ score: number; isDuplicate: boolean }>()
const percentage = Math.round(props.score * 100)
const color = props.isDuplicate ? '#ef4444' : props.score >= 0.6 ? '#f59e0b' : '#22c55e'
</script>

<template>
  <div class="similarity-bar">
    <div class="bar-track">
      <div class="bar-fill" :style="{ width: `${percentage}%`, backgroundColor: color }" />
    </div>
    <span class="percentage">{{ percentage }}%</span>
    <span v-if="isDuplicate" class="duplicate-badge">중복 의심</span>
  </div>
</template>

<style scoped>
.similarity-bar { display: flex; align-items: center; gap: 8px; }
.bar-track { width: 120px; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.percentage { font-size: 13px; font-weight: 600; width: 40px; }
.duplicate-badge { font-size: 11px; background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; padding: 2px 8px; border-radius: 4px; }
</style>
