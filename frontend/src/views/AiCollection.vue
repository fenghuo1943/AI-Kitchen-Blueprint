<template>
  <div class="ai-collect">
    <h2 class="page-title">AI 采集入库</h2>

    <!-- 配置横幅 -->
    <section v-if="config" class="card warn-banner" :class="{ ok: config.tavily_configured && config.llm_configured }">
      <template v-if="!config.tavily_configured">
        ⚠️ 未配置 Tavily 搜索：请在 <code>.env</code> 中填写 <code>TAVILY_API_KEY</code>（tavily.com 免费注册）。
      </template>
      <template v-else-if="!config.llm_configured">
        ⚠️ 未配置 LLM：默认使用本地 Ollama（<code>LLM_PROVIDER=ollama</code>），或配置 Anthropic key 后设置 <code>LLM_PROVIDER=anthropic</code>。
      </template>
      <template v-else>
        ✅ 搜索与 LLM 均已配置（{{ config.llm_provider }}）。输入菜名/食材，联网搜索并总结为待审菜谱。
      </template>
    </section>

    <!-- 提交采集 -->
    <section class="card">
      <h3>提交采集</h3>
      <div class="mode-tabs">
        <button class="mode-tab" :class="{ active: form.mode === 'topic' }" @click="form.mode = 'topic'">菜名 / 主题</button>
        <button class="mode-tab" :class="{ active: form.mode === 'ingredients' }" @click="form.mode = 'ingredients'">一组食材</button>
        <button class="mode-tab" :class="{ active: form.mode === 'complete' }" @click="form.mode = 'complete'">补全不完整菜谱</button>
      </div>

      <div v-if="form.mode === 'complete'" class="target-select-wrap">
        <select v-model="form.target_recipe_id" class="target-select">
          <option value="">选择要补全的菜谱…</option>
          <option v-for="r in candidateTargets" :key="r.id" :value="r.id">
            {{ r.title }}{{ r.status === 'draft' ? '（草稿）' : '' }}
          </option>
        </select>
        <p class="hint">将联网搜索「目标菜谱」的完整做法，确认后只补全缺失字段。</p>
      </div>

      <div class="search-bar">
        <input
          v-model="form.request_text"
          class="search-input"
          type="text"
          maxlength="200"
          :placeholder="form.mode === 'ingredients' ? '输入一组食材，如：西红柿, 鸡蛋' : (form.mode === 'complete' ? '输入目标菜名（选中的菜谱将自动填入）' : '输入想新增的菜名/主题，如：西红柿相关菜谱')"
          @keyup.enter="submit"
        />
        <select v-model="form.max_results" class="topk-select">
          <option :value="3">3 条</option>
          <option :value="5">5 条</option>
          <option :value="8">8 条</option>
        </select>
        <button class="btn btn-primary" :disabled="submitting || polling" @click="submit">
          {{ submitting ? '提交中…' : (polling ? '采集中…' : '开始采集') }}
        </button>
      </div>
    </section>

    <!-- 当前任务进度 -->
    <section v-if="job" class="card">
      <div class="card-head">
        <h3>任务 #{{ job.id.slice(0, 8) }}</h3>
        <span class="status-chip" :class="statusClass(job.status)">{{ statusLabel(job.status) }} · {{ stageLabel(job.stage) }}</span>
      </div>
      <div v-if="job.error_code" class="error-text">错误：{{ errorText(job.error_code) }}</div>
      <div v-if="job.reason" class="reason-text"><pre>{{ job.reason }}</pre></div>
      <div v-if="job.stage !== 'review' && job.status === 'running'" class="empty-hint">正在联网搜索并总结…（本地 LLM 可能较慢，请稍候）</div>
    </section>

    <!-- 候选列表 -->
    <section v-if="candidates.length" class="card">
      <div class="card-head">
        <h3>待审候选（{{ candidates.length }}）</h3>
        <button class="btn btn-secondary btn-small" @click="loadPending">刷新待审队列</button>
      </div>
      <div class="candidate-list">
        <div v-for="c in candidates" :key="c.id" class="candidate-item">
          <div class="candidate-head">
            <span class="candidate-title">{{ c.recipe?.title || '（无标题）' }}</span>
            <span class="merge-chip" v-if="c.merge_mode === 'merge'">补全</span>
          </div>
          <div v-if="c.recipe?.summary" class="candidate-summary">{{ c.recipe.summary }}</div>

          <div v-if="c.recipe" class="candidate-meta">
            <span v-if="c.recipe.servings">份量 {{ c.recipe.servings }}</span>
            <span v-if="c.recipe.prep_minutes">备 {{ c.recipe.prep_minutes }}min</span>
            <span v-if="c.recipe.cook_minutes">烹 {{ c.recipe.cook_minutes }}min</span>
            <span v-if="c.recipe.difficulty">{{ c.recipe.difficulty }}</span>
          </div>

          <div v-if="c.core_ingredients.length" class="candidate-tags">
            <span v-for="name in c.core_ingredients" :key="name" class="tag">{{ name }}</span>
          </div>

          <!-- 去重提示 -->
          <div v-if="hasMatches(c)" class="dup-hint">
            <div v-for="(d, i) in c.match_scores.title_duplicates || []" :key="'t' + i" class="dup-line">
              ⚠️ 与已有《{{ d.title }}》标题重合（{{ d.status }}）
            </div>
            <div v-for="(d, i) in c.match_scores.ingredient_overlaps || []" :key="'i' + i" class="dup-line">
              🔗 与《{{ d.title }}》核心食材重合 {{ Math.round(d.overlap * 100) }}%（{{ d.status }}）
            </div>
          </div>

          <div v-if="c.source_url" class="source-line">
            来源：<a :href="c.source_url" target="_blank" rel="noopener noreferrer">{{ c.source_url }}</a>
          </div>

          <div class="candidate-actions">
            <button class="btn btn-primary btn-small" @click="approve(c)">
              {{ c.merge_mode === 'merge' ? '确认合并' : '确认入库' }}
            </button>
            <button v-if="c.recipe" class="btn btn-secondary btn-small" @click="edit(c)">编辑</button>
            <button class="btn btn-danger btn-small" @click="reject(c)">拒绝</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 全局待审队列 -->
    <section class="card">
      <div class="card-head">
        <h3>待审队列</h3>
        <button class="btn btn-secondary btn-small" :disabled="loadingPending" @click="loadPending">
          {{ loadingPending ? '加载中…' : '刷新' }}
        </button>
      </div>
      <p class="search-hint">所有采集任务产生的待审候选（确认前不会进入菜谱库）。</p>
      <div v-if="!pendingCandidates.length" class="empty-hint">暂无待审候选</div>
      <div v-else class="candidate-list">
        <div v-for="c in pendingCandidates" :key="c.id" class="candidate-item pending">
          <div class="candidate-head">
            <span class="candidate-title">{{ c.recipe?.title || '（无标题）' }}</span>
            <span class="merge-chip" v-if="c.merge_mode === 'merge'">补全</span>
          </div>
          <div v-if="c.recipe?.summary" class="candidate-summary">{{ c.recipe.summary }}</div>
          <div v-if="c.core_ingredients.length" class="candidate-tags">
            <span v-for="name in c.core_ingredients" :key="name" class="tag">{{ name }}</span>
          </div>
          <div v-if="c.source_url" class="source-line">
            来源：<a :href="c.source_url" target="_blank" rel="noopener noreferrer">{{ c.source_url }}</a>
          </div>
          <div class="candidate-actions">
            <button class="btn btn-primary btn-small" @click="approve(c)">{{ c.merge_mode === 'merge' ? '确认合并' : '确认入库' }}</button>
            <button v-if="c.recipe" class="btn btn-secondary btn-small" @click="edit(c)">编辑</button>
            <button class="btn btn-danger btn-small" @click="reject(c)">拒绝</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { aiCollectApi, recipeApi } from '../services/api';
import { toast } from '../composables/useToast';
import type { AICollectCandidate, AICollectConfigStatus, AICollectJob, Recipe } from '../types';

const router = useRouter();

const config = ref<AICollectConfigStatus | null>(null);
const form = ref<{ mode: 'topic' | 'ingredients' | 'complete'; request_text: string; target_recipe_id: string; max_results: number }>({
  mode: 'topic',
  request_text: '',
  target_recipe_id: '',
  max_results: 5
});

const submitting = ref(false);
const job = ref<AICollectJob | null>(null);
const polling = ref(false);
let pollTimer: number | undefined;

const candidates = ref<AICollectCandidate[]>([]);
const candidateTargets = ref<Recipe[]>([]);
const pendingCandidates = ref<AICollectCandidate[]>([]);
const loadingPending = ref(false);

// ---- 配置状态 ----
async function loadConfig() {
  try {
    config.value = await aiCollectApi.configStatus();
  } catch (e) {
    console.error('load ai-collect config failed', e);
  }
}

// ---- 补全模式：目标菜谱 ----
async function loadTargets() {
  try {
    const res = await recipeApi.list({ page_size: 100 });
    candidateTargets.value = res.data.filter(r => r.status !== 'published');
  } catch (e) {
    console.error('load recipe targets failed', e);
  }
}

watch(() => form.value.mode, (mode) => {
  if (mode === 'complete') loadTargets();
});

// ---- 提交与轮询 ----
async function submit() {
  const text = form.value.request_text.trim();
  if (!text) {
    toast('请输入菜名或食材', 'error');
    return;
  }
  if (form.value.mode === 'complete' && !form.value.target_recipe_id) {
    toast('补全模式请先选择目标菜谱', 'error');
    return;
  }
  submitting.value = true;
  try {
    const created = await aiCollectApi.createJob({
      request_text: text,
      mode: form.value.mode,
      target_recipe_id: form.value.mode === 'complete' ? form.value.target_recipe_id : undefined,
      max_results: form.value.max_results
    });
    toast('已提交采集任务');
    startPolling(created.id);
  } catch (e: any) {
    console.error('create ai job failed', e);
    toast(errorText(e?.response?.data?.detail) || '提交失败', 'error');
  } finally {
    submitting.value = false;
  }
}

function startPolling(jobId: string) {
  stopPolling();
  polling.value = true;
  job.value = null;
  candidates.value = [];
  pollTimer = window.setInterval(async () => {
    try {
      const j = await aiCollectApi.getJob(jobId);
      job.value = j;
      if (j.stage === 'review') {
        candidates.value = j.candidates.filter(c => c.action === 'pending');
        stopPolling();
        toast(`采集完成，共 ${j.candidates_count} 条候选`);
        return;
      }
      if (j.status === 'failed' || j.status === 'rejected' || j.status === 'succeeded') {
        stopPolling();
        if (j.status === 'failed') toast(errorText(j.error_code) || '采集失败', 'error');
        else if (j.status === 'succeeded') toast('该任务候选已全部处理');
      }
    } catch (e) {
      console.error('poll ai job failed', e);
      stopPolling();
      toast('查询任务状态失败', 'error');
    }
  }, 2000);
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = undefined;
  }
  polling.value = false;
}

// ---- 审核动作 ----
async function approve(c: AICollectCandidate) {
  try {
    const updated = await aiCollectApi.approve(c.id);
    toast(updated.merge_mode === 'merge' ? '已合并进目标菜谱' : '已发布到菜谱库');
    removeCandidate(c.id);
    if (job.value) job.value = await aiCollectApi.getJob(job.value.id);
  } catch (e: any) {
    console.error('approve candidate failed', e);
    toast('确认失败', 'error');
  }
}

async function reject(c: AICollectCandidate) {
  if (!window.confirm(`确定拒绝《${c.recipe?.title || '该候选'}》吗？`)) return;
  try {
    await aiCollectApi.reject(c.id);
    toast('已拒绝');
    removeCandidate(c.id);
  } catch (e) {
    console.error('reject candidate failed', e);
    toast('拒绝失败', 'error');
  }
}

function removeCandidate(id: string) {
  candidates.value = candidates.value.filter(c => c.id !== id);
  pendingCandidates.value = pendingCandidates.value.filter(c => c.id !== id);
}

function edit(c: AICollectCandidate) {
  if (c.recipe) router.push(`/recipes/${c.recipe.id}/edit`);
}

// ---- 待审队列 ----
async function loadPending() {
  loadingPending.value = true;
  try {
    const res = await aiCollectApi.listCandidates({ page: 1, page_size: 50 });
    pendingCandidates.value = res.data;
  } catch (e) {
    console.error('load pending failed', e);
    toast('加载待审队列失败', 'error');
  } finally {
    loadingPending.value = false;
  }
}

// ---- 展示辅助 ----
function hasMatches(c: AICollectCandidate): boolean {
  return !!((c.match_scores.title_duplicates?.length) || (c.match_scores.ingredient_overlaps?.length));
}

const STAGE_LABELS: Record<string, string> = {
  submitted: '已提交', fetched: '抓取中', review: '待审', published: '已发布'
};
function stageLabel(stage: string): string {
  return STAGE_LABELS[stage] || stage;
}
function statusClass(status: string): string {
  return status === 'failed' ? 'status-fail' : status === 'succeeded' ? 'status-ok' : '';
}
function statusLabel(status: string): string {
  const m: Record<string, string> = {
    queued: '排队中', running: '进行中', succeeded: '已完成', failed: '失败', rejected: '已拒绝'
  };
  return m[status] || status;
}
const ERROR_TEXT: Record<string, string> = {
  TAVILY_NOT_CONFIGURED: '未配置 TAVILY_API_KEY',
  TAVILY_FAILED: '联网搜索失败（请检查 TAVILY_API_KEY 与网络）',
  LLM_UNAVAILABLE: 'LLM 服务不可用（检查 Ollama/Anthropic 配置）',
  NO_SEARCH_RESULTS: '未找到匹配内容，请更换关键词',
  EXTRACTION_FAILED: '抽取失败，无法生成候选',
  COLLECTION_FAILED: '采集过程出错'
};
function errorText(code?: string): string {
  return (code && ERROR_TEXT[code]) || code || '';
}

onMounted(() => {
  loadConfig();
  loadPending();
});
onUnmounted(stopPolling);
</script>

<style scoped>
.ai-collect { padding: 20px; max-width: 900px; }
.page-title { font-size: 1.3rem; margin: 0 0 16px; }

.card {
  background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.card h3 { margin: 0; font-size: 1rem; }

.warn-banner { background: #fff7ed; color: #c05621; font-size: 13px; }
.warn-banner.ok { background: #f0fdf4; color: #166534; }
.warn-banner code { background: rgba(0, 0, 0, 0.06); padding: 1px 4px; border-radius: 4px; }

.mode-tabs { display: flex; gap: 8px; margin-bottom: 14px; }
.mode-tab {
  padding: 8px 14px; border: 1px solid #e0e0e0; border-radius: 20px;
  background: white; color: #555; font-size: 13px; cursor: pointer;
}
.mode-tab.active { background: #4a90d9; color: white; border-color: #4a90d9; }

.target-select-wrap { margin-bottom: 12px; }
.target-select {
  width: 100%; padding: 10px 12px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 14px; min-height: 44px; background: white;
}
.hint { font-size: 12px; color: #888; margin: 6px 0 0; }

.search-bar { display: flex; gap: 10px; }
.search-input {
  flex: 1; padding: 12px 14px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 15px; min-height: 46px; outline: none;
}
.search-input:focus { border-color: #4a90d9; }
.topk-select {
  padding: 0 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: white;
  font-size: 14px; min-height: 46px;
}
.btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; min-height: 44px; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary { background: #4a90d9; color: white; }
.btn-secondary { background: #f0f0f0; color: #333; }
.btn-danger { background: #fde8e8; color: #c0392b; }
.btn-small { padding: 8px 14px; min-height: 36px; font-size: 13px; }

.status-chip { font-size: 12px; padding: 3px 10px; border-radius: 20px; background: #eef4fb; color: #4a90d9; }
.status-chip.status-fail { background: #fde8e8; color: #c0392b; }
.status-chip.status-ok { background: #e8f5e9; color: #2e7d32; }

.error-text { margin-top: 8px; color: #d9534f; font-size: 13px; }
.reason-text { margin-top: 8px; }
.reason-text pre { font-size: 12px; color: #999; white-space: pre-wrap; word-break: break-all; background: #fafafa; padding: 8px; border-radius: 6px; }
.empty-hint { color: #999; padding: 16px; text-align: center; font-size: 14px; }
.search-hint { font-size: 13px; color: #888; margin: 8px 0 14px; }

.candidate-list { margin-top: 4px; }
.candidate-item {
  border: 1px solid #f0f0f0; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
}
.candidate-item.pending { background: #fcfcfc; }
.candidate-head { display: flex; align-items: center; gap: 8px; }
.candidate-title { font-size: 16px; font-weight: 600; color: #333; }
.merge-chip { background: #e8f4fd; color: #2f7ac9; border-radius: 20px; padding: 2px 8px; font-size: 11px; }
.candidate-summary { margin-top: 6px; font-size: 13px; color: #666; }
.candidate-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; font-size: 12px; color: #888; }
.candidate-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.tag { background: #f2f6ee; color: #5a7a3a; border-radius: 4px; padding: 2px 8px; font-size: 12px; }

.dup-hint { margin-top: 8px; }
.dup-line { font-size: 12px; color: #b7791f; background: #fdf6e3; border-radius: 6px; padding: 5px 10px; margin-bottom: 4px; }

.source-line { margin-top: 8px; font-size: 12px; color: #999; word-break: break-all; }
.source-line a { color: #4a90d9; text-decoration: none; }

.candidate-actions { display: flex; gap: 8px; margin-top: 12px; }

@media (max-width: 767px) {
  .ai-collect { padding: 16px; }
  .search-bar { flex-wrap: wrap; }
  .search-input { min-width: 100%; }
  .topk-select { min-height: 44px; }
}
</style>
