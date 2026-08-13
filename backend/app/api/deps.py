"""API 通用依赖"""
from typing import Optional

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.household_resolver import resolve_default_household_id


def get_resolved_household_id(
    household_id: Optional[str] = Query(None, description="家庭ID（可选，缺省时使用默认家庭）"),
    db: Session = Depends(get_db),
) -> str:
    """返回请求指定的 household_id；缺省时解析为默认家庭（最早创建，不存在则自动创建）。"""
    return household_id or resolve_default_household_id(db)
