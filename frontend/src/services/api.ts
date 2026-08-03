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
  PaginatedResponse
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
  list: (params?: { query?: string; category?: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<Ingredient>>('/ingredients', { params }),

  get: (id: string) =>
    api.get<any, Ingredient>(`/ingredients/${id}`),

  create: (data: { canonical_name: string; category?: string; aliases?: string[] }) =>
    api.post<any, Ingredient>('/ingredients', data),

  update: (id: string, data: Partial<Ingredient>) =>
    api.patch<any, Ingredient>(`/ingredients/${id}`, data),

  delete: (id: string) =>
    api.delete(`/ingredients/${id}`)
};

// 菜谱 API
export const recipeApi = {
  list: (params?: { query?: string; status?: string; page?: number; page_size?: number }) =>
    api.get<any, PaginatedResponse<Recipe>>('/recipes', { params }),

  get: (id: string) =>
    api.get<any, Recipe>(`/recipes/${id}`),

  create: (data: {
    title: string;
    summary?: string;
    servings?: number;
    prep_minutes?: number;
    cook_minutes?: number;
    difficulty?: string;
    ingredients?: any[];
    steps?: any[];
    tags?: string[];
  }) =>
    api.post<any, Recipe>('/recipes', data),

  update: (id: string, data: Partial<Recipe>) =>
    api.patch<any, Recipe>(`/recipes/${id}`, data),

  delete: (id: string) =>
    api.delete(`/recipes/${id}`),

  publish: (id: string) =>
    api.post<any, Recipe>(`/recipes/${id}/publish`)
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
