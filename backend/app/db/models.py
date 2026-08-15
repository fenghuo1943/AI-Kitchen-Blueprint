"""数据库实体模型定义"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, Date, ForeignKey,
    UniqueConstraint, Index, text
)
from sqlalchemy.orm import relationship, backref
from app.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    """时间戳混入类

    server_default 保证即使通过原生 SQL 插入（未显式提供时间戳），
    也能取到数据库默认值，而不会产生零值日期（'0000-00-00 00:00:00'）。
    """
    created_at = Column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class Household(Base, TimestampMixin):
    """家庭/用户组"""
    __tablename__ = "households"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)

    # 关系
    inventory_items = relationship("InventoryItem", back_populates="household")


class Ingredient(Base, TimestampMixin):
    """食材"""
    __tablename__ = "ingredients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    canonical_name = Column(String(100), nullable=False, unique=True)
    category_id = Column(String(36), ForeignKey("ingredient_categories.id"), nullable=True)
    pinyin = Column(String(255), nullable=True)
    season_months = Column(String(200), nullable=True)  # JSON 格式: ["1","2","3"]
    allergens = Column(String(200), nullable=True)  # JSON 格式: ["gluten","dairy"]
    nutrition_ref = Column(String(500), nullable=True)
    confidence_status = Column(String(20), default="verified")

    # 关系
    aliases = relationship("IngredientAlias", back_populates="ingredient", cascade="all, delete-orphan")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
    inventory_items = relationship("InventoryItem", back_populates="ingredient")
    category_obj = relationship("IngredientCategory", back_populates="ingredients")


class IngredientAlias(Base, TimestampMixin):
    """食材别名"""
    __tablename__ = "ingredient_aliases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ingredient_id = Column(String(36), ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String(100), nullable=False, unique=True)

    # 关系
    ingredient = relationship("Ingredient", back_populates="aliases")


class Tag(Base, TimestampMixin):
    """标签"""
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False)
    type = Column(String(20), nullable=False)
    description = Column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint("name", "type", name="uq_tag_name_type"),
    )

    # 关系
    recipe_tags = relationship("RecipeTag", back_populates="tag")


class RecipeSource(Base, TimestampMixin):
    """菜谱来源"""
    __tablename__ = "recipe_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_type = Column(String(20), nullable=False)
    source_url = Column(String(500), nullable=True)
    author = Column(String(100), nullable=True)
    license = Column(String(100), nullable=True)
    fetched_at = Column(DateTime, nullable=True)
    raw_hash = Column(String(64), nullable=True)

    # 关系
    recipes = relationship("Recipe", back_populates="source")


class Recipe(Base, TimestampMixin):
    """菜谱"""
    __tablename__ = "recipes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200), nullable=False)
    pinyin = Column(String(255), nullable=True)
    summary = Column(String(1000), nullable=True)
    cover = Column(String(500), nullable=True)
    servings = Column(Integer, nullable=True)
    prep_minutes = Column(Integer, nullable=True)
    cook_minutes = Column(Integer, nullable=True)
    difficulty = Column(String(20), nullable=True)
    status = Column(String(20), default="draft")
    source_id = Column(String(36), ForeignKey("recipe_sources.id"), nullable=True)
    revision = Column(Integer, default=1, nullable=False)
    created_by = Column(String(100), nullable=True)

    # 关系
    source = relationship("RecipeSource", back_populates="recipes")
    revisions = relationship("RecipeRevision", back_populates="recipe", cascade="all, delete-orphan")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    recipe_steps = relationship("RecipeStep", back_populates="recipe", cascade="all, delete-orphan")
    recipe_tags = relationship("RecipeTag", back_populates="recipe", cascade="all, delete-orphan")
    recipe_seasonings = relationship("RecipeSeasoning", back_populates="recipe", cascade="all, delete-orphan")
    recipe_category_links = relationship("RecipeCategoryLink", back_populates="recipe", cascade="all, delete-orphan")
    document_chunks = relationship("DocumentChunk", back_populates="recipe", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_recipes_status_updated", "status", "updated_at"),
    )


class RecipeRevision(Base, TimestampMixin):
    """菜谱版本历史"""
    __tablename__ = "recipe_revisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    revision_no = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    summary = Column(String(1000), nullable=True)
    servings = Column(Integer, nullable=True)
    prep_minutes = Column(Integer, nullable=True)
    cook_minutes = Column(Integer, nullable=True)
    difficulty = Column(String(20), nullable=True)
    status = Column(String(20), default="draft")
    source_id = Column(String(36), ForeignKey("recipe_sources.id"), nullable=True)
    version_note = Column(String(500), nullable=True)

    # 关系
    recipe = relationship("Recipe", back_populates="revisions")

    __table_args__ = (
        UniqueConstraint("recipe_id", "revision_no", name="uq_recipe_revision_no"),
    )


class RecipeIngredient(Base, TimestampMixin):
    """菜谱食材关联"""
    __tablename__ = "recipe_ingredients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(String(36), ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(String(50), nullable=True)
    unit = Column(String(20), nullable=True)
    raw_quantity = Column(String(100), nullable=True)
    preparation = Column(String(100), nullable=True)
    optional = Column(Integer, default=0)
    sort_order = Column(Integer, default=0, nullable=False)

    # 关系
    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")

    __table_args__ = (
        UniqueConstraint("recipe_id", "ingredient_id", "sort_order", name="uq_recipe_ingredient_order"),
        Index("idx_recipe_ingredients_ingredient", "ingredient_id"),
    )


class RecipeStep(Base, TimestampMixin):
    """菜谱步骤"""
    __tablename__ = "recipe_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    step_no = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    image_url = Column(String(500), nullable=True)

    # 关系
    recipe = relationship("Recipe", back_populates="recipe_steps")

    __table_args__ = (
        UniqueConstraint("recipe_id", "step_no", name="uq_recipe_step_no"),
    )


class RecipeTag(Base, TimestampMixin):
    """菜谱标签关联"""
    __tablename__ = "recipe_tags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)

    # 关系
    recipe = relationship("Recipe", back_populates="recipe_tags")
    tag = relationship("Tag", back_populates="recipe_tags")

    __table_args__ = (
        UniqueConstraint("recipe_id", "tag_id", name="uq_recipe_tag"),
    )


class InventoryItem(Base, TimestampMixin):
    """库存物品"""
    __tablename__ = "inventory_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    household_id = Column(String(36), ForeignKey("households.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(String(36), ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(String(50), nullable=True)
    unit = Column(String(20), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    note = Column(String(500), nullable=True)
    is_expired = Column(Integer, default=0)

    # 关系
    household = relationship("Household", back_populates="inventory_items")
    ingredient = relationship("Ingredient", back_populates="inventory_items")

    __table_args__ = (
        Index("idx_inventory_items_household_expiry", "household_id", "expires_at"),
    )


class IngestionJob(Base, TimestampMixin):
    """入库任务"""
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("recipe_sources.id"), nullable=True)
    status = Column(String(20), default="queued")
    stage = Column(String(20), default="submitted")
    error_code = Column(String(100), nullable=True)
    result_recipe_id = Column(String(36), ForeignKey("recipes.id"), nullable=True)
    job_type = Column(String(20), default="manual", nullable=False)  # manual|url|file|ai_search
    request_text = Column(String(500), nullable=True)                # 用户输入（AI 采集）
    collection_mode = Column(String(20), default="topic", nullable=False)  # topic|ingredients|complete
    target_recipe_id = Column(String(36), ForeignKey("recipes.id"), nullable=True)  # 补全模式目标
    max_results = Column(Integer, default=15, nullable=False)        # AI 采集页数上限
    candidates_count = Column(Integer, default=0, nullable=False)    # AI 采集候选数
    index_status = Column(String(20), nullable=True)
    reason = Column(Text, nullable=True)                             # 采集说明/逐页失败原因
    llm_provider = Column(String(20), nullable=True)                 # 采集时使用的 LLM 供应商
    llm_model = Column(String(100), nullable=True)                   # 采集时使用的模型名
    search_domains_json = Column(Text, nullable=True)                # JSON: 本次任务限定搜索的域名列表
    manual_url = Column(String(500), nullable=True)                  # 手动模式：来源页面 URL（登录墙/反爬站点）
    manual_content = Column(Text, nullable=True)                     # 手动模式：用户粘贴的页面正文
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # 关系
    candidates = relationship("IngestionCandidate", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ingestion_jobs_status", "status", "created_at"),
    )


class IngestionCandidate(Base, TimestampMixin):
    """AI 采集候选（待审菜谱，与补全目标关联）。

    候选菜谱本体存在 recipes 表（status='review'），本表记录其归属任务、
    补全目标、去重信息与人工审核结果。
    """
    __tablename__ = "ingestion_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(String(36), ForeignKey("recipes.id"), nullable=False)
    source_id = Column(String(36), ForeignKey("recipe_sources.id"), nullable=True)
    target_recipe_id = Column(String(36), ForeignKey("recipes.id"), nullable=True)
    action = Column(String(20), default="pending", nullable=False)   # pending|approved|rejected|merged
    merge_mode = Column(String(20), default="new", nullable=False)   # new|merge
    dedup_key = Column(String(64), nullable=True)                    # sha256(归一标题)
    normalized_title = Column(String(200), nullable=True)
    source_urls_json = Column(Text, nullable=True)                   # JSON: 参考的全部来源 URL
    core_ingredients_json = Column(Text, nullable=True)              # JSON: ["西红柿","鸡蛋"]
    match_scores_json = Column(Text, nullable=True)                  # JSON: 与已发布/候选菜谱重叠判定
    reason = Column(Text, nullable=True)                             # LLM 置信度/说明
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # 关系
    job = relationship("IngestionJob", back_populates="candidates")
    recipe = relationship("Recipe", foreign_keys=[recipe_id])
    target_recipe = relationship("Recipe", foreign_keys=[target_recipe_id])
    source = relationship("RecipeSource")

    __table_args__ = (
        Index("idx_candidate_action_created", "action", "created_at"),
        Index("idx_candidate_job", "job_id"),
        Index("idx_candidate_recipe", "recipe_id"),
        Index("idx_candidate_target", "target_recipe_id"),
        Index("idx_candidate_dedup", "dedup_key"),
    )


class DocumentChunk(Base):
    """文档分块（用于 RAG 索引）"""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    revision = Column(Integer, nullable=False)
    chunk_type = Column(String(20), nullable=False)
    content_hash = Column(String(64), nullable=False)
    vector_id = Column(String(100), nullable=True)
    source_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    recipe = relationship("Recipe", back_populates="document_chunks")

    __table_args__ = (
        Index("idx_document_chunks_recipe", "recipe_id", "chunk_type"),
    )


class RecommendationLog(Base):
    """推荐日志"""
    __tablename__ = "recommendation_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_hash = Column(String(64), nullable=False)
    filters_json = Column(Text, nullable=False)
    candidate_ids = Column(Text, nullable=False)
    rank_version = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditEvent(Base):
    """审计事件"""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ============================================================
# 分类 / 调料 / 收藏 / 历史 / 菜单（参考 cook 项目移植）
# ============================================================

class RecipeCategory(Base, TimestampMixin):
    """菜谱分类"""
    __tablename__ = "recipe_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    parent_id = Column(String(36), ForeignKey("recipe_categories.id", ondelete="SET NULL"), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)

    # 自引用层级（本期按平铺单层使用，parent_id 预留）
    parent = relationship("RecipeCategory", remote_side=[id], backref=backref("children"))

    # 关系
    recipe_links = relationship("RecipeCategoryLink", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_recipe_categories_sort", "sort_order"),
    )


class IngredientCategory(Base, TimestampMixin):
    """食材分类"""
    __tablename__ = "ingredient_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)

    # 关系
    ingredients = relationship("Ingredient", back_populates="category_obj")


class SeasoningCategory(Base, TimestampMixin):
    """调料分类"""
    __tablename__ = "seasoning_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)

    # 关系
    seasonings = relationship("Seasoning", back_populates="category_obj")


class Seasoning(Base, TimestampMixin):
    """调料"""
    __tablename__ = "seasonings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    canonical_name = Column(String(100), nullable=False, unique=True)
    pinyin = Column(String(255), nullable=True)
    category_id = Column(String(36), ForeignKey("seasoning_categories.id"), nullable=True)

    # 关系
    category_obj = relationship("SeasoningCategory", back_populates="seasonings")
    recipe_seasonings = relationship("RecipeSeasoning", back_populates="seasoning")


class RecipeSeasoning(Base, TimestampMixin):
    """菜谱调料关联"""
    __tablename__ = "recipe_seasonings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    seasoning_id = Column(String(36), ForeignKey("seasonings.id"), nullable=False)
    quantity = Column(String(50), nullable=True)

    # 关系
    recipe = relationship("Recipe", back_populates="recipe_seasonings")
    seasoning = relationship("Seasoning", back_populates="recipe_seasonings")

    __table_args__ = (
        UniqueConstraint("recipe_id", "seasoning_id", name="uq_recipe_seasoning"),
        Index("idx_recipe_seasonings_seasoning", "seasoning_id"),
    )


class RecipeCategoryLink(Base, TimestampMixin):
    """菜谱分类关联"""
    __tablename__ = "recipe_category_links"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(String(36), ForeignKey("recipe_categories.id"), nullable=False)

    # 关系
    recipe = relationship("Recipe", back_populates="recipe_category_links")
    category = relationship("RecipeCategory", back_populates="recipe_links")

    __table_args__ = (
        UniqueConstraint("recipe_id", "category_id", name="uq_recipe_category"),
        Index("idx_recipe_category_links_category", "category_id"),
    )


class Favorite(Base, TimestampMixin):
    """收藏"""
    __tablename__ = "favorites"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    household_id = Column(String(36), ForeignKey("households.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)

    # 关系
    household = relationship("Household")
    recipe = relationship("Recipe")

    __table_args__ = (
        UniqueConstraint("household_id", "recipe_id", name="uq_favorite_household_recipe"),
        Index("idx_favorites_household_created", "household_id", "created_at"),
    )


class RecipeHistory(Base, TimestampMixin):
    """浏览历史（每家庭每菜谱一条，重复浏览刷新 viewed_at）"""
    __tablename__ = "recipe_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    household_id = Column(String(36), ForeignKey("households.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    household = relationship("Household")
    recipe = relationship("Recipe")

    __table_args__ = (
        UniqueConstraint("household_id", "recipe_id", name="uq_history_household_recipe"),
        Index("idx_history_household_viewed", "household_id", "viewed_at"),
    )


class MealPlan(Base, TimestampMixin):
    """每日菜单（某天安排哪些菜谱）"""
    __tablename__ = "meal_plans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    household_id = Column(String(36), ForeignKey("households.id", ondelete="CASCADE"), nullable=False)
    recipe_id = Column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    target_date = Column(Date, nullable=False)

    # 关系
    household = relationship("Household")
    recipe = relationship("Recipe")

    __table_args__ = (
        UniqueConstraint("household_id", "recipe_id", "target_date", name="uq_meal_plan"),
        Index("idx_meal_plan_household_date", "household_id", "target_date"),
    )


class UserSetting(Base, TimestampMixin):
    """用户/家庭设置（key-value 存储，按 household 隔离）"""
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    household_id = Column(String(36), ForeignKey("households.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(String(500), nullable=True)

    # 关系
    household = relationship("Household")

    __table_args__ = (
        UniqueConstraint("household_id", "key", name="uq_user_setting_household_key"),
        Index("idx_user_settings_household", "household_id"),
    )
