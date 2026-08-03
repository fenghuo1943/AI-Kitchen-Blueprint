/** API 服务 */
import axios from 'axios';
import type {
  Ingredient,
  Recipe,
  InventoryItem,
  Household,
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
  RecipeInput
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

/** 获取当前家庭 ID（从 store 的 localStorage 读取） */
export function getHouseholdId(): string | undefined {
  return localStorage.getItem('householdId') || undefined;
}

// 食材 API
export const ingredientApi = {
  list: (params?: { query?: string; category?: string; category_id?: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<Ingredient>>('/ingredients', { params }),

  get: (id: string) =>
    api.get<any, Ingredient>(`/ingredients/${id}`),

  create: (data: { canonical_name: string; category?: string; category_id?: string; aliases?: string[] }) =>
    api.post<any, Ingredient>('/ingredients', data),

  update: (id: string, data: Partial<Ingredient>) =>
    api.patch<any, Ingredient>(`/ingredients/${id}`, data),

  delete: (id: string) =>
    api.delete(`/ingredients/${id}`),

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
  list: (params?: { query?: string; category_id?: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<Seasoning>>('/seasonings', { params }),

  getAll: () =>
    api.get<any, PaginatedResponse<Seasoning>>('/seasonings/all'),

  get: (id: string) =>
    api.get<any, Seasoning>(`/seasonings/${id}`),

  create: (data: { canonical_name: string; category_id?: string }) =>
    api.post<any, Seasoning>('/seasonings', data),

  update: (id: string, data: Partial<Seasoning>) =>
    api.patch<any, Seasoning>(`/seasonings/${id}`, data),

  delete: (id: string) =>
    api.delete(`/seasonings/${id}`)
};

// 菜谱 API
export const recipeApi = {
  list: (params?: {
    query?: string; q?: string; status?: string; difficulty?: string; tags?: string;
    ingredients?: string; match?: 'exact' | 'any'; category_id?: string;
    household_id?: string; sort?: string; order?: string; deleted?: boolean;
    page?: number; page_size?: number;
  }) =>
    api.get<any, PaginatedResponse<Recipe>>('/recipes', { params }),

  get: (id: string, householdId?: string) =>
    api.get<any, Recipe>(`/recipes/${id}`, { params: { household_id: householdId } }),

  create: (data: RecipeInput) =>
    api.post<any, Recipe>('/recipes', data),

  update: (id: string, data: Partial<RecipeInput>) =>
    api.patch<any, Recipe>(`/recipes/${id}`, data),

  delete: (id: string, forever = false) =>
    api.delete(`/recipes/${id}`, { params: { forever: forever || undefined } }),

  publish: (id: string) =>
    api.post<any, Recipe>(`/recipes/${id}/publish`),

  restore: (id: string) =>
    api.post<any, Recipe>(`/recipes/${id}/restore`)
};

// 库存 API
export const inventoryApi = {
  listHouseholds: () =>
    api.get<any, PaginatedResponse<Household>>('/inventory/households'),

  createHousehold: (data: { name: string; description?: string }) =>
    api.post<any, Household>('/inventory/households', data),

  getHousehold: (id: string) =>
    api.get<any, Household>(`/inventory/households/${id}`),

  listItems: (params: { household_id: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<InventoryItem>>('/inventory/items', { params }),

  getItem: (id: string) =>
    api.get<any, InventoryItem>(`/inventory/items/${id}`),

  createItem: (data: {
    household_id: string;
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

  getExpiringSoon: (params: { household_id: string; days?: number }) =>
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
  list: (params: { household_id: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<FavoriteItem>>('/favorites', { params }),

  add: (recipeId: string, householdId: string) =>
    api.post<any, FavoriteItem>('/favorites', { recipe_id: recipeId }, { params: { household_id: householdId } }),

  remove: (recipeId: string, householdId: string) =>
    api.delete(`/favorites/${recipeId}`, { params: { household_id: householdId } })
};

// 浏览历史 API
export const historyApi = {
  list: (params: { household_id: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<HistoryItem>>('/history', { params }),

  record: (recipeId: string, householdId: string) =>
    api.post<any, HistoryItem>('/history', { recipe_id: recipeId }, { params: { household_id: householdId } }),

  removeOne: (recipeId: string, householdId: string) =>
    api.delete(`/history/${recipeId}`, { params: { household_id: householdId } }),

  clear: (householdId: string) =>
    api.delete('/history', { params: { household_id: householdId } })
};

// 每日菜单 API
export const menuApi = {
  getByDate: (householdId: string, date: string) =>
    api.get<any, MenuByDate>('/menu', { params: { household_id: householdId, date } }),

  getMonthDates: (householdId: string, month: string) =>
    api.get<any, { dates: string[] }>('/menu', { params: { household_id: householdId, month } }),

  getWaterfall: (householdId: string, params: { page?: number; page_size?: number }) =>
    api.get<any, WaterfallResponse>('/menu', { params: { household_id: householdId, mode: 'waterfall', ...params } }),

  add: (householdId: string, recipeId: string, date: string) =>
    api.post('/menu', { recipe_id: recipeId, date }, { params: { household_id: householdId } }),

  remove: (householdId: string, recipeId: string, date: string) =>
    api.delete(`/menu/${recipeId}`, { params: { household_id: householdId, date } })
};

// 发现 API
export const discoverApi = {
  get: (params: { type: DiscoverType; household_id?: string; limit?: number }) =>
    api.get<any, { list: DiscoverRecipe[] }>('/discover', { params })
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
