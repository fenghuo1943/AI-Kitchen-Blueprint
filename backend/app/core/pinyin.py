"""拼音工具：为菜谱/食材/调料生成拼音列，支持拼音前缀搜索"""
from pypinyin import lazy_pinyin


def to_pinyin(text: str) -> str:
    """生成无空格拼音（如：番茄炒蛋 → fanqiechaodan）"""
    if not text:
        return ""
    return "".join(lazy_pinyin(text))
