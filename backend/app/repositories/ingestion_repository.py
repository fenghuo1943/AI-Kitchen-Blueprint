"""入库任务数据访问层"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.db.models import IngestionJob, RecipeSource, Recipe


class IngestionRepository:
    """入库任务仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_id: str) -> Optional[IngestionJob]:
        """根据ID获取入库任务"""
        return self.db.query(IngestionJob).filter(IngestionJob.id == job_id).first()

    def search(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[IngestionJob], int]:
        """搜索入库任务"""
        stmt = self.db.query(IngestionJob)

        if status:
            stmt = stmt.filter(IngestionJob.status == status)

        total = stmt.count()

        offset = (page - 1) * page_size
        jobs = stmt.order_by(IngestionJob.created_at.desc()).offset(offset).limit(page_size).all()

        return jobs, total

    def create(self, job: IngestionJob) -> IngestionJob:
        """创建入库任务"""
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update(self, job: IngestionJob) -> IngestionJob:
        """更新入库任务"""
        self.db.commit()
        self.db.refresh(job)
        return job

    def create_source(self, source: RecipeSource) -> RecipeSource:
        """创建菜谱来源"""
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def create_recipe(self, recipe: Recipe) -> Recipe:
        """创建菜谱"""
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def get_source_by_hash(self, raw_hash: str) -> Optional[RecipeSource]:
        """根据原始哈希获取来源（用于去重）"""
        return self.db.query(RecipeSource).filter(RecipeSource.raw_hash == raw_hash).first()

    def update_job_status(
        self,
        job_id: str,
        status: str,
        stage: str,
        error_code: Optional[str] = None,
        result_recipe_id: Optional[str] = None
    ) -> Optional[IngestionJob]:
        """更新任务状态"""
        from datetime import datetime

        job = self.get_by_id(job_id)
        if not job:
            return None

        job.status = status
        job.stage = stage
        job.error_code = error_code
        job.result_recipe_id = result_recipe_id
        job.updated_at = datetime.utcnow()

        if status in ("succeeded", "failed", "rejected"):
            job.finished_at = datetime.utcnow()

        if status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(job)
        return job
