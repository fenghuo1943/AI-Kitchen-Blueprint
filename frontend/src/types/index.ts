/** 类型定义 */

// 食材相关
export interface Ingredient {
  id: string;
  canonical_name: string;
  category?: string;
  season_months?: string[];
  allergens?: string[];
  nutrition_ref?: string;
  confidence_status: string;
  aliases: IngredientAlias[];
  created_at: string;
  updated_at: string;
}

export interface IngredientAlias {
  id: string;
  alias: string;
  created_at: string;
}

// 菜谱相关
export interface Recipe {
  id: string;
  title: string;
  summary?: string;
  servings?: number;
  prep_minutes?: number;
  cook_minutes?: number;
  difficulty?: string;
  source_id?: string;
  status: string;
  revision: number;
  created_by?: string;
  ingredients: RecipeIngredient[];
  steps: RecipeStep[];
  tags: RecipeTag[];
  created_at: string;
  updated_at: string;
}

export interface RecipeIngredient {
  id: string;
  ingredient_id: string;
  ingredient_name: string;
  quantity?: string;
  unit?: string;
  preparation?: string;
  optional: boolean;
  sort_order: number;
}

export interface RecipeStep {
  id: string;
  step_no: number;
  instruction: string;
  duration_minutes?: number;
  image_url?: string;
}

export interface RecipeTag {
  id: string;
  name: string;
  type: string;
}

// 库存相关
export interface InventoryItem {
  id: string;
  household_id: string;
  ingredient_id: string;
  ingredient_name: string;
  quantity?: string;
  unit?: string;
  expires_at?: string;
  note?: string;
  is_expired: boolean;
  created_at: string;
  updated_at: string;
}

export interface Household {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

// 推荐相关
export interface RecommendationRequest {
  ingredients: string[];
  season_month?: string;
  max_minutes?: number;
  people_count?: number;
  equipment?: string[];
  diet_restrictions?: string[];
  goals?: string[];
  allow_missing: boolean;
}

export interface RecommendationResult {
  recipe_id: string;
  recipe_title: string;
  recipe_summary?: string;
  servings?: number;
  total_minutes?: number;
  difficulty?: string;
  matched_ingredients: string[];
  missing_ingredients: string[];
  coverage_score: number;
  overall_score: number;
  reason: string;
}

export interface RecommendationResponse {
  results: RecommendationResult[];
  total: number;
  filters_applied: Record<string, any>;
  fallback_reason?: string;
}

// 入库相关
export interface IngestionJob {
  id: string;
  source_id?: string;
  status: string;
  stage: string;
  error_code?: string;
  result_recipe_id?: string;
  started_at?: string;
  finished_at?: string;
  created_at: string;
  updated_at: string;
}

// API 响应
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
}
