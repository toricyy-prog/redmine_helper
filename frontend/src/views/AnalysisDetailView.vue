<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import AppLayout from '@/components/AppLayout.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import SimilarityBar from '@/components/SimilarityBar.vue'
import { analysisApi } from '@/api/analysis'
import type { AnalysisHistoryItem } from '@/types'

const route = useRoute()
const router = useRouter()
const md = new MarkdownIt()

const analysis = ref<AnalysisHistoryItem | null>(null)
const isLoading = ref(false)
const isRerunning = ref(false)
const errorMsg = ref('')

async function loadAnalysis() {
  isLoading.value = true
  try {
    const { data } = await analysisApi.get(Number(route.params.id))
    analysis.value = data
  } catch {
    errorMsg.value = '분석 이력을 불러올 수 없습니다.'
  } finally {
    isLoading.value = false
  }
}

async function rerun() {
  if (!analysis.value) return
  isRerunning.value = true
  try {
    await analysisApi.rerun(analysis.value.issue_id, analysis.value.project_id)
    alert('재분석이 시작되었습니다. 잠시 후 결과를 확인해 주세요.')
    await loadAnalysis()
  } catch {
    alert('재분석 요청 중 오류가 발생했습니다.')
  } finally {
    isRerunning.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR')
}

onMounted(loadAnalysis)
</script>

<template>
  <AppLayout>
    <div class="detail-header">
      <button @click="router.push('/')" class="back-btn">← 목록으로</button>
      <h2 class="page-title">분석 상세</h2>
    </div>

    <div v-if="isLoading" class="loading-state">로딩 중...</div>
    <div v-else-if="errorMsg" class="error-state">{{ errorMsg }}</div>

    <template v-else-if="analysis">
      <!-- 원본 이슈 정보 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">원본 이슈 정보</span>
          <StatusBadge :status="analysis.status" />
        </div>
        <div class="info-row">
          <span class="info-label">이슈 번호</span>
          <span>#{{ analysis.issue_id }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">프로젝트 ID</span>
          <span>{{ analysis.project_id }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">처리 시각</span>
          <span>{{ formatDate(analysis.created_at) }}</span>
        </div>
        <div v-if="analysis.error_message" class="error-message">
          오류: {{ analysis.error_message }}
        </div>
      </div>

      <!-- 유사 이슈 목록 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">유사 이슈 목록</span>
          <span class="badge">{{ analysis.similar_issues?.length ?? 0 }}건</span>
        </div>
        <div v-if="analysis.similar_issues?.length">
          <div v-for="item in analysis.similar_issues" :key="item.id" class="similar-issue-row">
            <span class="issue-id">#{{ item.id }}</span>
            <span class="issue-subject">{{ item.subject }}</span>
            <SimilarityBar :score="item.score" :is-duplicate="item.is_duplicate" />
          </div>
        </div>
        <div v-else class="empty-state">유사 이슈가 없습니다.</div>
      </div>

      <!-- AI 요약 -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">AI 요약</span>
        </div>
        <div v-if="analysis.ai_summary" class="markdown-content" v-html="md.render(analysis.ai_summary)" />
        <div v-else class="empty-state">AI 요약이 없습니다.</div>
      </div>

      <!-- 수동 재분석 -->
      <div class="action-area">
        <button @click="rerun" :disabled="isRerunning" class="rerun-btn">
          {{ isRerunning ? '재분석 중...' : '수동 재분석 실행' }}
        </button>
      </div>
    </template>
  </AppLayout>
</template>

<style scoped>
.detail-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.back-btn { background: none; border: 1px solid #e2e8f0; padding: 8px 14px; border-radius: 6px; cursor: pointer; }
.page-title { font-size: 22px; font-weight: 700; }
.card { background: white; border-radius: 8px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card-title { font-size: 16px; font-weight: 600; }
.badge { background: #f1f5f9; padding: 2px 10px; border-radius: 12px; font-size: 13px; }
.info-row { display: flex; gap: 16px; margin-bottom: 10px; }
.info-label { width: 100px; color: #64748b; font-size: 14px; }
.similar-issue-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
.issue-id { width: 60px; font-weight: 600; color: #3b82f6; }
.issue-subject { flex: 1; font-size: 14px; }
.markdown-content { line-height: 1.7; font-size: 14px; }
.empty-state { color: #94a3b8; padding: 16px 0; }
.loading-state, .error-state { padding: 40px; text-align: center; color: #94a3b8; }
.action-area { text-align: right; margin-top: 8px; }
.rerun-btn { padding: 10px 24px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
.rerun-btn:disabled { background: #93c5fd; cursor: not-allowed; }
</style>
