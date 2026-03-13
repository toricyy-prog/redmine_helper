<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import SimilarityBar from '@/components/SimilarityBar.vue'
import { analysisApi } from '@/api/analysis'
import type { DuplicateDetectionItem } from '@/types'

const redmineUrl = ref('')
const duplicates = ref<DuplicateDetectionItem[]>([])
const isLoading = ref(false)

async function loadData() {
  isLoading.value = true
  try {
    const dupResp = await analysisApi.duplicates()
    duplicates.value = dupResp.data
  } finally {
    isLoading.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR')
}

function redmineIssueUrl(issueId: number): string {
  if (!redmineUrl.value) return '#'
  return `${redmineUrl.value}/issues/${issueId}`
}

onMounted(loadData)
</script>

<template>
  <AppLayout>
    <h2 class="page-title">중복 감지 이력</h2>

    <div class="table-container">
      <div class="table-header">
        <span class="total-count">총 {{ duplicates.length }}건</span>
      </div>
      <table v-if="!isLoading && duplicates.length > 0" class="data-table">
        <thead>
          <tr>
            <th>원본 이슈</th>
            <th>중복 의심 이슈</th>
            <th>유사도</th>
            <th>감지 일시</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in duplicates" :key="item.id">
            <td>
              <a :href="redmineIssueUrl(item.source_issue_id)" target="_blank" class="issue-link">
                #{{ item.source_issue_id }}
              </a>
            </td>
            <td>
              <a :href="redmineIssueUrl(item.target_issue_id)" target="_blank" class="issue-link">
                #{{ item.target_issue_id }}
              </a>
            </td>
            <td>
              <SimilarityBar :score="item.similarity_score" :is-duplicate="true" />
            </td>
            <td>{{ formatDate(item.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="!isLoading" class="empty-state">중복 감지 이력이 없습니다.</div>
      <div v-else class="loading-state">로딩 중...</div>
    </div>
  </AppLayout>
</template>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 24px; }
.table-container { background: white; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.table-header { padding: 20px 24px 16px; }
.total-count { font-size: 13px; color: #64748b; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { padding: 12px 24px; text-align: left; font-size: 13px; color: #64748b; border-bottom: 1px solid #f1f5f9; }
.data-table td { padding: 14px 24px; border-bottom: 1px solid #f8fafc; }
.issue-link { color: #3b82f6; font-weight: 600; text-decoration: none; }
.issue-link:hover { text-decoration: underline; }
.empty-state, .loading-state { padding: 40px; text-align: center; color: #94a3b8; }
</style>
