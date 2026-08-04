"""AI 采集候选数据访问层"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.db.models import IngestionCandidate, IngestionJob


class AICollectionRepository:
    """AI 采集候选仓储类"""

    def __init__(self, db: Session):
        self.db = db

    # ---- 任务 ----
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        """根据 ID 获取采集任务"""
        return self.db.query(IngestionJob).filter(IngestionJob.id == job_id).first()

    def create_job(self, job: IngestionJob) -> IngestionJob:
        """创建采集任务"""
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def commit(self) -> None:
        """提交当前会话"""
        self.db.commit()

    # ---- 候选 ----
    def get_candidate(self, candidate_id: str) -> Optional[IngestionCandidate]:
        """根据 ID 获取候选"""
        return self.db.query(IngestionCandidate).filter(
            IngestionCandidate.id == candidate_id
        ).first()

    def list_by_job(self, job_id: str) -> List[IngestionCandidate]:
        """任务下的所有候选（按创建时间正序）"""
        return self.db.query(IngestionCandidate).filter(
            IngestionCandidate.job_id == job_id
        ).order_by(IngestionCandidate.created_at.asc()).all()

    def list_pending(self, page: int, page_size: int) -> Tuple[List[IngestionCandidate], int]:
        """全局待审队列（分页，最新优先）"""
        base = self.db.query(IngestionCandidate).filter(
            IngestionCandidate.action == "pending"
        )
        total = base.count()
        items = base.order_by(
            IngestionCandidate.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_by_dedup_key(self, dedup_key: str) -> Optional[IngestionCandidate]:
        """按归一标题哈希查候选（同次任务内去重）"""
        return self.db.query(IngestionCandidate).filter(
            IngestionCandidate.dedup_key == dedup_key
        ).first()

    def count_pending(self, job_id: str) -> int:
        """任务下待审候选数"""
        return self.db.query(IngestionCandidate.id).filter(
            IngestionCandidate.job_id == job_id,
            IngestionCandidate.action == "pending",
        ).count()

    def count_approved(self, job_id: str) -> int:
        """任务下已通过（approved/merged）候选数"""
        return self.db.query(IngestionCandidate.id).filter(
            IngestionCandidate.job_id == job_id,
            IngestionCandidate.action.in_(("approved", "merged")),
        ).count()
