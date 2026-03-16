<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { analysisApi } from '@/api/analysis'
import type { AnalysisHistoryItem, StatsResponse } from '@/types'

const router = useRouter()
const analyses = ref<AnalysisHistoryItem[]>([])
const stats = ref<StatsResponse | null>(null)
const total = ref(0)
const currentPage = ref(1)
const isLoading = ref(false)

async function loadData() {
  isLoading.value = true
  try {
    const [listResp, statsResp] = await Promise.all([
      analysisApi.list(currentPage.value, 20),
      analysisApi.stats(),
    ])
    analyses.value = listResp.data.items
    total.value = listResp.data.total
    stats.value = statsResp.data
  } finally {
    isLoading.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR')
}

onMounted(loadData)
</script>

<template>
  <AppLayout>
    <h2 class="page-title">대시보드</h2>

    <!-- 통계 요약 카드 -->
    <div v-if="stats" class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">오늘 처리 건수</div>
        <div class="stat-value">{{ stats.today_analyzed }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">오늘 중복 감지</div>
        <div class="stat-value warning">{{ stats.today_duplicates }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">성공률</div>
        <div class="stat-value">{{ (stats.success_rate * 100).toFixed(1) }}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">전체 분석</div>
        <div class="stat-value">{{ stats.total_analyzed }}</div>
      </div>
    </div>

    <!-- 분석 이력 테이블 -->
    <div class="table-container">
      <div class="table-header">
        <h3>최근 분석 이력</h3>
        <span class="total-count">총 {{ total }}건</span>
      </div>
      <table v-if="!isLoading && analyses.length > 0" class="data-table">
        <thead>
          <tr>
            <th>이슈 번호</th>
            <th>상태</th>
            <th>유사 이슈 수</th>
            <th>처리 시각</th>
            <th>상세</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in analyses" :key="item.id">
            <td>#{{ item.issue_id }}</td>
            <td><StatusBadge :status="item.status" /></td>
            <td>{{ item.similar_issues?.length ?? 0 }}건</td>
            <td>{{ formatDate(item.created_at) }}</td>
            <td>
              <button @click="router.push(`/analysis/${item.id}`)" class="detail-btn">
                상세 보기
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!isLoading" class="empty-state">분석 이력이 없습니다.</div>
      <div v-else class="loading-state">로딩 중...</div>
    </div>
  </AppLayout>
</template>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 24px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
.stat-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.stat-label { font-size: 13px; color: #64748b; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #1e293b; }
.stat-value.warning { color: #f59e0b; }
.table-container { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.table-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px 16px; }
.table-header h3 { font-size: 16px; font-weight: 600; }
.total-count { font-size: 13px; color: #64748b; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 12px 24px; text-align: left; font-size: 13px; color: #64748b; border-bottom: 1px solid #f1f5f9; }
.data-table td { padding: 14px 24px; border-bottom: 1px solid #f8fafc; }
.detail-btn { padding: 5px 12px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.empty-state, .loading-state { padding: 40px; text-align: center; color: #94a3b8; }
</style>
