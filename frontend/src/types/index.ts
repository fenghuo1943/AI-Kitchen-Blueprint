/** 类型定义 */

// 分类相关
export type CategoryType = 'recipe' | 'ingredient' | 'seasoning';

export interface Category {
  id: string;
  name: string;
  parent_id?: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

// 食材相关
export interface Ingredient {
  id: string;
  canonical_name: string;
  pinyin?: string;
  category?: string;
  category_id?: string;
  category_name?: string;
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

// 调料相关
export interface Seasoning {
  id: string;
  canonical_name: string;
  pinyin?: string;
  category_id?: string;
  category_name?: string;
  created_at: string;
  updated_at: string;
}

// 菜谱相关
export interface Recipe {
  id: string;
  title: string;
  pinyin?: string;
  summary?: string;
  cover?: string;
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
  seasonings: RecipeSeasoning[];
  categories: RecipeCategoryItem[];
  is_favorited: boolean;
  is_in_today_menu: boolean;
  cooked_count: number;
  deleted_at?: string;
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

export interface RecipeSeasoning {
  id: string;
  seasoning_id: string;
  seasoning_name: string;
  quantity?: string;
}

export interface RecipeCategoryItem {
  id: string;
  name: string;
}

/** 菜谱创建/编辑的输入（不包含服务端生成的字段） */
export interface RecipeInput {
  title: string;
  summary?: string;
  cover?: string;
  servings?: number;
  prep_minutes?: number;
  cook_minutes?: number;
  difficulty?: string;
  status?: string;
  category_ids?: string[];
  ingredients?: {
    ingredient_id: string;
    quantity?: string;
    unit?: string;
    preparation?: string;
    optional?: boolean;
    sort_order?: number;
  }[];
  seasonings?: { seasoning_id: string; quantity?: string }[];
  steps?: {
    step_no: number;
    instruction: string;
    duration_minutes?: number;
    image_url?: string;
  }[];
  tags?: string[];
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

// AI 采集入库相关
export interface AICollectCandidate {
  id: string;
  job_id: string;
  recipe: Recipe | null;
  action: string;
  merge_mode: string;
  source_url?: string;
  source_urls?: string[];
  normalized_title?: string;
  core_ingredients: string[];
  match_scores: {
    title_duplicates?: { recipe_id: string; title: string; status?: string; score: number }[];
    ingredient_overlaps?: { recipe_id: string; title: string; status?: string; overlap: number }[];
  };
  reason?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface AICollectJob extends IngestionJob {
  request_text?: string;
  collection_mode: string;
  target_recipe_id?: string;
  candidates_count: number;
  reason?: string;
  llm_provider?: string;
  llm_model?: string;
  search_sites?: string[];
  manual_url?: string;
  candidates: AICollectCandidate[];
}

export interface AICollectionCreate {
  request_text: string;
  mode: 'topic' | 'ingredients' | 'complete' | 'manual';
  target_recipe_id?: string;
  max_results?: number;
  llm_provider?: string;
  llm_model?: string;
  search_sites?: string[];
  manual_url?: string;
  manual_content?: string;
}

export interface LLMModelOption {
  provider: string;
  model: string;
  label: string;
}

export interface LLMModelsResponse {
  models: LLMModelOption[];
  default_provider: string;
  default_model: string;
}

export interface AICollectConfigStatus {
  tavily_configured: boolean;
  llm_provider: string;
  llm_configured: boolean;
  llm_model?: string;
  llm_health: Record<string, any>;
  default_search_sites: string[];
}

// 收藏相关
export interface FavoriteItem {
  id: string;
  recipe_id: string;
  recipe_title: string;
  cover?: string;
  created_at: string;
}

// 浏览历史相关
export interface HistoryItem {
  id: string;
  recipe_id: string;
  recipe_title: string;
  cover?: string;
  viewed_at: string;
}

// 每日菜单相关
export interface MealPlanItem {
  recipe_id: string;
  title: string;
  cover?: string;
  cook_time?: number;
  added_at?: string;
}

export interface MenuNameItem {
  id: string;
  name: string;
}

export interface MenuByDate {
  date: string;
  list: MealPlanItem[];
  ing_list: MenuNameItem[];
  sea_list: MenuNameItem[];
}

export interface WaterfallGroup {
  date: string;
  recipes: MealPlanItem[];
}

export interface WaterfallResponse {
  list: WaterfallGroup[];
  total_page: number;
  page: number;
  page_size: number;
}

// 发现/推荐相关
export type DiscoverType = 'today' | 'hot' | 'new' | 'random';

export interface DiscoverRecipe {
  id: string;
  title: string;
  cover?: string;
  summary?: string;
  difficulty?: string;
  cook_time?: number;
  is_favorited: boolean;
  is_in_today_menu: boolean;
  cooked_count: number;
}

// RAG 语义检索相关
export interface RagChunk {
  chunk_type: string;
  text: string;
  vector_score: number;
}

export interface RagSearchItem {
  recipe_id: string;
  title: string;
  cover?: string;
  summary?: string;
  score: number;
  matched_ingredients: string[];
  reasons: string[];
  chunks: RagChunk[];
}

export interface RagSearchResponse {
  results: RagSearchItem[];
  total: number;
  engine_available: boolean;
  took_ms: number;
  error?: string;
}

export interface IndexStatus {
  indexed_count: number;
  published_count: number;
  last_rebuild_at?: string;
  running: string[];
  queued: string[];
  failed: number;
  last_error: Record<string, string>;
  breakdown_by_type: Record<string, number>;
}

// API 响应
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
}
