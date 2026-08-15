"""入库业务逻辑层"""
import uuid
import hashlib
import json
from typing import Optional, List
from datetime import datetime

from app.db.models import (
    IngestionJob, RecipeSource, Recipe, RecipeCategoryLink,
    RecipeIngredient, RecipeStep,
)
from app.repositories.category_repository import DEFAULT_CATEGORY_NAME, get_default_category_id
from app.repositories.ingestion_repository import IngestionRepository
from app.repositories.ingredient_repository import IngredientRepository
from app.schemas.ingestion import (
    IngestionCreate, IngestionResponse, IngestionListResponse,
    IngestionDetailResponse, IngestionStageLog, IngestionRecipeData
)


class IngestionService:
    """入库服务类"""

    def __init__(
        self,
        ingestion_repository: IngestionRepository,
        ingredient_repository: IngredientRepository
    ):
        self.ingestion_repository = ingestion_repository
        self.ingredient_repository = ingredient_repository

    def create_job(self, data: IngestionCreate, actor: str = "system") -> IngestionResponse:
        """创建入库任务"""
        # 验证输入
        if data.source_type == "manual" and not data.recipe_data:
            raise ValueError("人工录入模式需要提供 recipe_data")
        if data.source_type in ("file", "url") and not data.source_ref:
            raise ValueError(f"{data.source_type} 模式需要提供 source_ref")

        # 创建来源记录
        source = None
        raw_hash = None
        if data.source_ref:
            # 计算哈希用于去重
            raw_hash = hashlib.sha256(data.source_ref.encode()).hexdigest()

            # 检查是否已存在
            existing_source = self.ingestion_repository.get_source_by_hash(raw_hash)
            if existing_source:
                raise ValueError("该来源已存在，可能重复导入")

            source = RecipeSource(
                id=str(uuid.uuid4()),
                source_type=data.source_type,
                source_url=data.source_ref if data.source_type == "url" else None,
                raw_hash=raw_hash
            )
            source = self.ingestion_repository.create_source(source)

        # 创建入库任务
        job = IngestionJob(
            id=str(uuid.uuid4()),
            source_id=source.id if source else None,
            status="queued",
            stage="submitted"
        )
        job = self.ingestion_repository.create(job)

        # 如果是人工录入，直接处理
        if data.source_type == "manual" and data.recipe_data:
            self._process_manual_ingestion(job, data.recipe_data, data.import_mode, actor)

        return self._to_response(job)

    def get_job(self, job_id: str) -> Optional[IngestionDetailResponse]:
        """获取入库任务详情"""
        job = self.ingestion_repository.get_by_id(job_id)
        if not job:
            return None
        return self._to_detail_response(job)

    def list_jobs(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> IngestionListResponse:
        """获取入库任务列表"""
        jobs, total = self.ingestion_repository.search(
            status=status,
            page=page,
            page_size=page_size
        )
        return IngestionListResponse(
            data=[self._to_response(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size
        )

    def _process_manual_ingestion(
        self,
        job: IngestionJob,
        recipe_data: IngestionRecipeData,
        import_mode: str,
        actor: str
    ):
        """处理人工录入的菜谱"""
        try:
            # 更新状态为运行中
            self.ingestion_repository.update_job_status(
                job.id, status="running", stage="parsed"
            )

            # 验证必填字段
            if not recipe_data.title:
                self.ingestion_repository.update_job_status(
                    job.id, status="failed", stage="validated",
                    error_code="RECIPE_REQUIRED_FIELD_MISSING"
                )
                return

            # 创建菜谱
            recipe = Recipe(
                id=str(uuid.uuid4()),
                title=recipe_data.title,
                summary=recipe_data.summary,
                servings=recipe_data.servings,
                prep_minutes=recipe_data.prep_minutes,
                cook_minutes=recipe_data.cook_minutes,
                difficulty=recipe_data.difficulty,
                status="draft" if import_mode == "draft" else "review",
                revision=1,
                created_by=actor
            )
            recipe = self.ingestion_repository.create_recipe(recipe)

            # 未指定分类的菜谱落到默认分类（入库规则）
            self.ingestion_repository.db.add(RecipeCategoryLink(
                id=str(uuid.uuid4()),
                recipe_id=recipe.id,
                category_id=get_default_category_id(self.ingestion_repository.db, "recipe"),
            ))

            # 处理食材
            for i, ing_data in enumerate(recipe_data.ingredients):
                ingredient_name = ing_data.get("name", "")
                if not ingredient_name:
                    continue

                # 查找或创建食材
                ingredient = self.ingredient_repository.get_by_name(ingredient_name)
                if not ingredient:
                    from app.db.models import Ingredient
                    # 未指定分类的食材落到默认分类（入库规则）
                    ingredient = Ingredient(
                        id=str(uuid.uuid4()),
                        canonical_name=ingredient_name,
                        confidence_status="candidate",
                        category=DEFAULT_CATEGORY_NAME,
                        category_id=get_default_category_id(self.ingredient_repository.db, "ingredient"),
                    )
                    ingredient = self.ingredient_repository.create(ingredient)

                # 创建菜谱食材关联
                recipe_ingredient = RecipeIngredient(
                    id=str(uuid.uuid4()),
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=ing_data.get("quantity"),
                    unit=ing_data.get("unit"),
                    preparation=ing_data.get("preparation"),
                    optional=1 if ing_data.get("optional") else 0,
                    sort_order=i
                )
                self.ingestion_repository.db.add(recipe_ingredient)

            # 处理步骤
            for i, step_data in enumerate(recipe_data.steps, 1):
                instruction = step_data.get("instruction", "")
                if not instruction:
                    continue

                recipe_step = RecipeStep(
                    id=str(uuid.uuid4()),
                    recipe_id=recipe.id,
                    step_no=i,
                    instruction=instruction,
                    duration_minutes=step_data.get("duration_minutes")
                )
                self.ingestion_repository.db.add(recipe_step)

            self.ingestion_repository.db.commit()

            # 更新任务状态
            self.ingestion_repository.update_job_status(
                job.id,
                status="succeeded",
                stage="published",
                result_recipe_id=recipe.id
            )

        except Exception as e:
            # 更新失败状态
            self.ingestion_repository.update_job_status(
                job.id,
                status="failed",
                stage=job.stage,
                error_code="PROCESSING_FAILED"
            )

    def _to_response(self, job: IngestionJob) -> IngestionResponse:
        """转换为响应模式"""
        return IngestionResponse(
            id=job.id,
            source_id=job.source_id,
            status=job.status,
            stage=job.stage,
            error_code=job.error_code,
            result_recipe_id=job.result_recipe_id,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            updated_at=job.updated_at
        )

    def _to_detail_response(self, job: IngestionJob) -> IngestionDetailResponse:
        """转换为详情响应模式"""
        # 获取来源信息
        source_type = None
        source_url = None
        raw_hash = None
        if job.source_id:
            source = self.ingestion_repository.db.query(RecipeSource).filter(
                RecipeSource.id == job.source_id
            ).first()
            if source:
                source_type = source.source_type
                source_url = source.source_url
                raw_hash = source.raw_hash

        return IngestionDetailResponse(
            id=job.id,
            source_id=job.source_id,
            status=job.status,
            stage=job.stage,
            error_code=job.error_code,
            result_recipe_id=job.result_recipe_id,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
            source_type=source_type,
            source_url=source_url,
            raw_hash=raw_hash,
            logs=[]
        )
