"""应用层隐藏「家庭」概念：无显式 household_id 时统一落到默认家庭。

数据库 schema 不变（households 表及各表 household_id 外键/唯一约束/索引保留），
只是缺省时解析为创建最早的默认家庭；不存在则自动创建一条「默认家庭」。
"""
import uuid

from sqlalchemy.orm import Session

from app.db.models import Household

DEFAULT_HOUSEHOLD_NAME = "默认家庭"


def resolve_default_household_id(db: Session) -> str:
    """返回默认家庭 ID：最早创建（created_at 最小，同值按 id）的 household。

    不存在任何家庭时自动创建「默认家庭」并提交，保证后续读写有可用家庭。
    """
    household = db.query(Household).order_by(
        Household.created_at.asc(), Household.id.asc()
    ).first()
    if household:
        return household.id

    household = Household(
        id=str(uuid.uuid4()),
        name=DEFAULT_HOUSEHOLD_NAME,
        description="自动创建的默认家庭"
    )
    db.add(household)
    db.commit()
    db.refresh(household)
    return household.id
