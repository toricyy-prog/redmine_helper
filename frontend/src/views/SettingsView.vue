<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { analysisApi } from '@/api/analysis'

const similarityThreshold = ref(0.3)
const duplicateThreshold = ref(0.9)
const maxSimilarIssues = ref(5)
const categoryList = ref<string[]>([])
const newCategory = ref('')
const isSaving = ref(false)
const saveMessage = ref('')

async function loadSettings() {
  const { data } = await analysisApi.getSettings()
  similarityThreshold.value = data.similarity_threshold
  duplicateThreshold.value = data.duplicate_threshold
  maxSimilarIssues.value = data.max_similar_issues
  categoryList.value = [...data.category_list]
}

function addCategory() {
  const cat = newCategory.value.trim()
  if (cat && !categoryList.value.includes(cat)) {
    categoryList.value.push(cat)
    newCategory.value = ''
  }
}

function removeCategory(index: number) {
  categoryList.value.splice(index, 1)
}

async function saveSettings() {
  isSaving.value = true
  saveMessage.value = ''
  try {
    await analysisApi.updateSettings({
      similarity_threshold: similarityThreshold.value,
      duplicate_threshold: duplicateThreshold.value,
      max_similar_issues: maxSimilarIssues.value,
      category_list: categoryList.value,
    })
    saveMessage.value = '설정이 저장되었습니다.'
    setTimeout(() => { saveMessage.value = '' }, 3000)
  } catch {
    saveMessage.value = '저장 중 오류가 발생했습니다.'
  } finally {
    isSaving.value = false
  }
}

onMounted(loadSettings)
</script>

<template>
  <AppLayout>
    <h2 class="page-title">설정</h2>

    <div class="settings-card">
      <h3 class="section-title">유사도 임계값</h3>

      <div class="setting-row">
        <div class="setting-info">
          <label>유사 이슈 탐지 임계값</label>
          <p class="setting-desc">이 값 이상인 이슈만 유사 이슈로 표시합니다.</p>
        </div>
        <div class="slider-group">
          <input
            v-model.number="similarityThreshold"
            type="range" min="0.1" max="1.0" step="0.05"
            class="slider"
          />
          <span class="slider-value">{{ (similarityThreshold * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <div class="setting-row">
        <div class="setting-info">
          <label>중복 감지 임계값</label>
          <p class="setting-desc">이 값 이상이면 중복 이슈로 플래그 처리됩니다.</p>
        </div>
        <div class="slider-group">
          <input
            v-model.number="duplicateThreshold"
            type="range" min="0.1" max="1.0" step="0.05"
            class="slider"
          />
          <span class="slider-value">{{ (duplicateThreshold * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <div class="setting-row">
        <div class="setting-info">
          <label>최대 유사 이슈 수</label>
          <p class="setting-desc">분석 결과에 표시할 최대 유사 이슈 건수입니다.</p>
        </div>
        <div class="slider-group">
          <input
            v-model.number="maxSimilarIssues"
            type="range" min="1" max="20" step="1"
            class="slider"
          />
          <span class="slider-value">{{ maxSimilarIssues }}건</span>
        </div>
      </div>
    </div>

    <div class="settings-card">
      <h3 class="section-title">카테고리 목록</h3>
      <div class="category-list">
        <div v-for="(cat, index) in categoryList" :key="cat" class="category-tag">
          {{ cat }}
          <button @click="removeCategory(index)" class="remove-btn">×</button>
        </div>
      </div>
      <div class="add-category">
        <input
          v-model="newCategory"
          placeholder="새 카테고리 입력"
          @keyup.enter="addCategory"
          class="category-input"
        />
        <button @click="addCategory" class="add-btn">추가</button>
      </div>
    </div>

    <div class="action-area">
      <span v-if="saveMessage" class="save-message">{{ saveMessage }}</span>
      <button @click="saveSettings" :disabled="isSaving" class="save-btn">
        {{ isSaving ? '저장 중...' : '설정 저장' }}
      </button>
    </div>
  </AppLayout>
</template>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 24px; }
.settings-card { background: white; border-radius: 8px; padding: 28px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid #f1f5f9; }
.setting-row { display: flex; justify-content: space-between; align-items: flex-start; padding: 14px 0; border-bottom: 1px solid #f8fafc; }
.setting-info label { font-weight: 500; display: block; margin-bottom: 4px; }
.setting-desc { font-size: 13px; color: #64748b; margin: 0; }
.slider-group { display: flex; align-items: center; gap: 12px; }
.slider { width: 200px; }
.slider-value { width: 50px; text-align: right; font-weight: 600; }
.category-list { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; min-height: 36px; }
.category-tag { display: flex; align-items: center; gap: 6px; background: #eff6ff; color: #3b82f6; border: 1px solid #bfdbfe; border-radius: 16px; padding: 4px 12px; font-size: 13px; }
.remove-btn { background: none; border: none; cursor: pointer; color: #93c5fd; font-size: 16px; line-height: 1; padding: 0; }
.remove-btn:hover { color: #ef4444; }
.add-category { display: flex; gap: 8px; }
.category-input { flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 14px; }
.add-btn { padding: 8px 16px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer; font-size: 14px; }
.action-area { display: flex; justify-content: flex-end; align-items: center; gap: 16px; }
.save-message { font-size: 14px; color: #22c55e; }
.save-btn { padding: 12px 28px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: 600; }
.save-btn:disabled { background: #93c5fd; cursor: not-allowed; }
</style>
