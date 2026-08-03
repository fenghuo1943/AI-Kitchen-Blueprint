"""数据库实体模型定义"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
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
    category = Column(String(50), nullable=True)
    season_months = Column(String(200), nullable=True)  # JSON 格式: ["1","2","3"]
    allergens = Column(String(200), nullable=True)  # JSON 格式: ["gluten","dairy"]
    nutrition_ref = Column(String(500), nullable=True)
    confidence_status = Column(String(20), default="verified")

    # 关系
    aliases = relationship("IngredientAlias", back_populates="ingredient", cascade="all, delete-orphan")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
    inventory_items = relationship("InventoryItem", back_populates="ingredient")


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
    summary = Column(String(1000), nullable=True)
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
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ingestion_jobs_status", "status", "created_at"),
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
