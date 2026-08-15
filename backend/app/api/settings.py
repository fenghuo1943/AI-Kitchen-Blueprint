"""用户/家庭设置 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_resolved_household_id
from app.db.database import get_db
from app.services.settings_service import SettingsService
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["用户设置"])


@router.get("", response_model=SettingsResponse)
def get_settings(
    household_id: str = Depends(get_resolved_household_id),
    db: Session = Depends(get_db)
):
    """读取设置（未设置项返回默认值）"""
    return SettingsService(db).get(household_id)


@router.put("", response_model=SettingsResponse)
def update_settings(
    data: SettingsUpdate,
    household_id: str = Depends(get_resolved_household_id),
    db: Session = Depends(get_db)
):
    """部分更新设置，返回合并后的完整设置"""
    return SettingsService(db).update(household_id, data)
