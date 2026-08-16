/** API 服务 */
import axios from 'axios';
import type {
  Ingredient,
  Recipe,
  InventoryItem,
  RecommendationRequest,
  RecommendationResponse,
  IngestionJob,
  PaginatedResponse,
  Category,
  CategoryType,
  Seasoning,
  FavoriteItem,
  HistoryItem,
  MenuByDate,
  WaterfallResponse,
  DiscoverRecipe,
  DiscoverType,
  RecipeInput,
  IndexStatus,
  RagSearchResponse,
  AICollectJob,
  AICollectCandidate,
  AICollectionCreate,
  AICollectConfigStatus,
  LLMModelsResponse,
  BrowserStatus,
  BrowserFetch,
  UserSettings,
  BatchDeleteResult
} from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// 食材 API
export const ingredientApi = {
  list: (params?: { query?: string; category_id?: string; deleted?: boolean; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<Ingredient>>('/ingredients', { params }),

  get: (id: string) =>
    api.get<any, Ingredient>(`/ingredients/${id}`),

  create: (data: { canonical_name: string; category_id?: string; aliases?: string[] }) =>
    api.post<any, Ingredient>('/ingredients', data),

  update: (id: string, data: Partial<Ingredient>) =>
    api.patch<any, Ingredient>(`/ingredients/${id}`, data),

  delete: (id: string, forever = false) =>
    api.delete(`/ingredients/${id}`, { params: { forever: forever || undefined } }),

  restore: (id: string) =>
    api.post<any, Ingredient>(`/ingredients/${id}/restore`),

  batchDelete: (ids: string[]) =>
    api.post<any, BatchDeleteResult>('/ingredients/batch-delete', { ids }),

  addAlias: (id: string, aliasName: string) =>
    api.post(`/ingredients/${id}/aliases`, null, { params: { alias_name: aliasName } }),

  removeAlias: (aliasId: string) =>
    api.delete(`/ingredients/aliases/${aliasId}`)
};

// 分类 API
export const categoryApi = {
  list: (type: CategoryType) =>
    api.get<any, { data: Category[]; total: number }>('/categories', { params: { type } }),

  create: (type: CategoryType, data: { name: string; parent_id?: string }) =>
    api.post<any, Category>('/categories', data, { params: { type } }),

  update: (type: CategoryType, id: string, data: { name?: string; sort_order?: number }) =>
    api.patch<any, Category>(`/categories/${id}`, data, { params: { type } }),

  delete: (type: CategoryType, id: string) =>
    api.delete(`/categories/${id}`, { params: { type } })
};

// 调料 API
export const seasoningApi = {
  list: (params?: { query?: string; category_id?: string; deleted?: boolean; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<Seasoning>>('/seasonings', { params }),

  getAll: () =>
    api.get<any, PaginatedResponse<Seasoning>>('/seasonings/all'),

  get: (id: string) =>
    api.get<any, Seasoning>(`/seasonings/${id}`),

  create: (data: { canonical_name: string; category_id?: string }) =>
    api.post<any, Seasoning>('/seasonings', data),

  update: (id: string, data: Partial<Seasoning>) =>
    api.patch<any, Seasoning>(`/seasonings/${id}`, data),

  delete: (id: string, forever = false) =>
    api.delete(`/seasonings/${id}`, { params: { forever: forever || undefined } }),

  restore: (id: string) =>
    api.post<any, Seasoning>(`/seasonings/${id}/restore`),

  batchDelete: (ids: string[]) =>
    api.post<any, BatchDeleteResult>('/seasonings/batch-delete', { ids })
};

// 菜谱 API
export const recipeApi = {
  list: (params?: {
    query?: string; q?: string; status?: string; difficulty?: string; tags?: string;
    ingredients?: string; match?: 'exact' | 'any'; category_id?: string;
    sort?: string; order?: string; deleted?: boolean;
    page?: number; page_size?: number;
  }) =>
    api.get<any, PaginatedResponse<Recipe>>('/recipes', { params }),

  get: (id: string) =>
    api.get<any, Recipe>(`/recipes/${id}`),

  create: (data: RecipeInput) =>
    api.post<any, Recipe>('/recipes', data),

  update: (id: string, data: Partial<RecipeInput>) =>
    api.patch<any, Recipe>(`/recipes/${id}`, data),

  delete: (id: string, forever = false) =>
    api.delete(`/recipes/${id}`, { params: { forever: forever || undefined } }),

  publish: (id: string) =>
    api.post<any, Recipe>(`/recipes/${id}/publish`),

  restore: (id: string) =>
    api.post<any, Recipe>(`/recipes/${id}/restore`),

  batchDelete: (ids: string[]) =>
    api.post<any, BatchDeleteResult>('/recipes/batch-delete', { ids })
};

// 库存 API
export const inventoryApi = {
  listItems: (params: { page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<InventoryItem>>('/inventory/items', { params }),

  getItem: (id: string) =>
    api.get<any, InventoryItem>(`/inventory/items/${id}`),

  createItem: (data: {
    ingredient_id: string;
    quantity?: string;
    unit?: string;
    expires_at?: string;
    note?: string;
  }) =>
    api.post<any, InventoryItem>('/inventory/items', data),

  updateItem: (id: string, data: Partial<InventoryItem>) =>
    api.patch<any, InventoryItem>(`/inventory/items/${id}`, data),

  deleteItem: (id: string) =>
    api.delete(`/inventory/items/${id}`),

  getExpiringSoon: (params: { days?: number }) =>
    api.get<any, InventoryItem[]>('/inventory/expiring-soon', { params })
};

// 推荐 API
export const recommendationApi = {
  getRecommendations: (data: RecommendationRequest) =>
    api.post<any, RecommendationResponse>('/recommendations', data),

  calculateCoverage: (data: { recipe_id: string; available_ingredients: string[] }) =>
    api.post<any, any>('/recommendations/coverage', data)
};

// 收藏 API
export const favoriteApi = {
  list: (params: { page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<FavoriteItem>>('/favorites', { params }),

  add: (recipeId: string) =>
    api.post<any, FavoriteItem>('/favorites', { recipe_id: recipeId }),

  remove: (recipeId: string) =>
    api.delete(`/favorites/${recipeId}`)
};

// 浏览历史 API
export const historyApi = {
  list: (params: { page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<HistoryItem>>('/history', { params }),

  record: (recipeId: string) =>
    api.post<any, HistoryItem>('/history', { recipe_id: recipeId }),

  removeOne: (recipeId: string) =>
    api.delete(`/history/${recipeId}`),

  clear: () =>
    api.delete('/history')
};

// 每日菜单 API
export const menuApi = {
  getByDate: (date: string) =>
    api.get<any, MenuByDate>('/menu', { params: { date } }),

  getMonthDates: (month: string) =>
    api.get<any, { dates: string[] }>('/menu', { params: { month } }),

  getWaterfall: (params: { page?: number; page_size?: number }) =>
    api.get<any, WaterfallResponse>('/menu', { params: { mode: 'waterfall', ...params } }),

  add: (recipeId: string, date: string) =>
    api.post('/menu', { recipe_id: recipeId, date }),

  remove: (recipeId: string, date: string) =>
    api.delete(`/menu/${recipeId}`, { params: { date } })
};

// 发现 API
export const discoverApi = {
  get: (params: { type: DiscoverType; limit?: number }) =>
    api.get<any, { list: DiscoverRecipe[] }>('/discover', { params })
};

// RAG 语义检索 API
export const ragApi = {
  search: (data: {
    query: string;
    top_k?: number;
    max_cook_time?: number;
    tags?: string[];
    ingredient_ids?: string[];
    category_id?: string;
  }) =>
    api.post<any, RagSearchResponse>('/rag/search', data),

  status: () =>
    api.get<any, IndexStatus>('/rag/index/status'),

  rebuild: () =>
    api.post<any, { status: string; task: string }>('/rag/index/rebuild'),

  indexRecipe: (recipeId: string) =>
    api.post<any, { status: string; recipe_id: string }>(`/rag/index/${recipeId}`)
};

// AI 采集入库 API
export const aiCollectApi = {
  createJob: (data: AICollectionCreate) =>
    api.post<any, AICollectJob>('/ai-collect/jobs', data),

  getJob: (jobId: string) =>
    api.get<any, AICollectJob>(`/ai-collect/jobs/${jobId}`),

  listCandidates: (params?: { page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<AICollectCandidate>>('/ai-collect/candidates', { params }),

  approve: (candidateId: string) =>
    api.post<any, AICollectCandidate>(`/ai-collect/candidates/${candidateId}/approve`),

  reject: (candidateId: string) =>
    api.post<any, AICollectCandidate>(`/ai-collect/candidates/${candidateId}/reject`),

  configStatus: () =>
    api.get<any, AICollectConfigStatus>('/ai-collect/config/status'),

  listModels: () =>
    api.get<any, LLMModelsResponse>('/ai-collect/models'),

  // 浏览器抓取（Playwright，小红书登录墙）：登录态持久化 + 同步抓正文
  browserStatus: () =>
    api.get<any, BrowserStatus>('/ai-collect/browser/status'),

  browserLogin: (url?: string) =>
    api.post<any, { ok: boolean; message: string }>(
      '/ai-collect/browser/login',
      url ? { url } : {},
      { timeout: 360000 }  // 阻塞到用户关闭浏览器窗口
    ),

  browserFetch: (url: string) =>
    api.post<any, BrowserFetch>('/ai-collect/browser/fetch', { url }, { timeout: 120000 })
};

// 用户/家庭设置 API
export const settingsApi = {
  get: () =>
    api.get<any, UserSettings>('/settings'),

  update: (data: Partial<UserSettings>) =>
    api.put<any, UserSettings>('/settings', data)
};

// 入库 API
export const ingestionApi = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<IngestionJob>>('/ingestions', { params }),

  get: (id: string) =>
    api.get<any, IngestionJob>(`/ingestions/${id}`),

  create: (data: {
    source_type: 'file' | 'url' | 'manual';
    source_ref?: string;
    recipe_data?: any;
    import_mode?: string;
  }) =>
    api.post<any, IngestionJob>('/ingestions', data)
};

export default api;
