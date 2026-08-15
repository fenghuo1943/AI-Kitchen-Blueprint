"""用户/家庭设置业务逻辑"""
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import UserSetting
from app.schemas.settings import SettingsResponse, SettingsUpdate

# 默认设置：电脑端每页 30，手机端每页 20
DEFAULT_SETTINGS = {"page_size_desktop": 30, "page_size_mobile": 20}
SETTING_KEYS = set(DEFAULT_SETTINGS)


class SettingsService:
    """设置服务：key-value 仅两行，直接操作 Session，无需 repository"""

    def __init__(self, db: Session):
        self.db = db

    def get(self, household_id: str) -> SettingsResponse:
        """读取设置：DB 中已存行覆盖默认值，只认已知 key"""
        rows = self.db.query(UserSetting).filter(UserSetting.household_id == household_id).all()
        merged = dict(DEFAULT_SETTINGS)
        for r in rows:
            if r.key in SETTING_KEYS:
                try:
                    merged[r.key] = int(r.value)
                except (TypeError, ValueError):
                    pass  # 脏数据忽略，保留默认值
        return SettingsResponse(**merged)

    def update(self, household_id: str, data: SettingsUpdate) -> SettingsResponse:
        """部分更新：对每个传入 key upsert，返回合并后的完整设置"""
        patch = data.model_dump(exclude_none=True)
        for key, value in patch.items():
            row = self.db.query(UserSetting).filter_by(household_id=household_id, key=key).first()
            if row:
                row.value = str(value)
            else:
                self.db.add(UserSetting(household_id=household_id, key=key, value=str(value)))
        self.db.commit()
        return self.get(household_id)
