export interface SimilarIssueItem {
  id: number
  subject: string
  score: number
  is_duplicate: boolean
}

export interface AnalysisHistoryItem {
  id: number
  issue_id: number
  project_id: number
  status: 'success' | 'failed' | 'no_similar'
  similar_issues: SimilarIssueItem[] | null
  ai_summary: string | null
  created_at: string
  error_message: string | null
}

export interface AnalysisListResponse {
  items: AnalysisHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface DuplicateDetectionItem {
  id: number
  source_issue_id: number
  target_issue_id: number
  similarity_score: number
  created_at: string
}

export interface StatsResponse {
  total_analyzed: number
  total_success: number
  total_failed: number
  total_no_similar: number
  total_duplicates: number
  success_rate: number
  today_analyzed: number
  today_duplicates: number
}

export interface SettingsResponse {
  similarity_threshold: number
  duplicate_threshold: number
  max_similar_issues: number
  category_list: string[]
  enable_auto_comment: boolean
}

export interface SettingsUpdateRequest {
  similarity_threshold?: number
  duplicate_threshold?: number
  max_similar_issues?: number
  category_list?: string[]
  enable_auto_comment?: boolean
}
