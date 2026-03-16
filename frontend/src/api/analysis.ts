import apiClient from './client'
import type {
  AnalysisListResponse,
  AnalysisHistoryItem,
  DuplicateDetectionItem,
  StatsResponse,
  SettingsResponse,
  SettingsUpdateRequest,
} from '@/types'

export const analysisApi = {
  // 분석 이력 목록
  list: (page = 1, pageSize = 20) =>
    apiClient.get<AnalysisListResponse>('/analysis', { params: { page, page_size: pageSize } }),

  // 분석 상세
  get: (id: number) => apiClient.get<AnalysisHistoryItem>(`/analysis/${id}`),

  // 수동 재분석
  rerun: (issueId: number, projectId: number) =>
    apiClient.post('/analysis/rerun', { issue_id: issueId, project_id: projectId }),

  // 중복 감지 목록
  duplicates: () => apiClient.get<DuplicateDetectionItem[]>('/duplicates'),

  // 통계
  stats: () => apiClient.get<StatsResponse>('/stats'),

  // 설정 조회
  getSettings: () => apiClient.get<SettingsResponse>('/settings'),

  // 설정 수정
  updateSettings: (data: SettingsUpdateRequest) =>
    apiClient.put<SettingsResponse>('/settings', data),
}
