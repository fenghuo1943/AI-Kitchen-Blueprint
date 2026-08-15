"""分类清单幂等建库 + 旧分类重命名。

以 app.core.category_classifier.CATEGORY_LISTS 为单一事实来源，把三套分类
的规范化清单一次性建好（幂等，已存在则复用），并为旧分类改名：
    食材  甜点 → 乳品烘焙、米面 → 谷薯主食、海鲜 → 海鲜水产
    调料  葱姜蒜料酒 → 去腥增香
菜谱空分类「焖菜」等非 canonical 分类不自动删，仅在报告中标记，由用户手动删。

发布顺序（P2 → P1）：先 seed_categories.py --apply，再 reclassify_defaults.py --apply。

用法：
    python scripts/seed_categories.py                 # dry-run，打印计划
    python scripts/seed_categories.py --apply         # 单事务执行并提交
    python scripts/seed_categories.py --report out.json
"""
import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from app.core.category_classifier import CATEGORY_LISTS
from app.db.database import get_session_local
from app.repositories.category_repository import (
    DEFAULT_CATEGORY_NAME, CATEGORY_MODELS, get_or_create_category_id,
)

# 旧分类改名（type → [(旧名, 新名), ...]；目标名已被占用则跳过并报告冲突）
RENAMES = {
    "ingredient": [("甜点", "乳品烘焙"), ("米面", "谷薯主食"), ("海鲜", "海鲜水产")],
    "seasoning": [("葱姜蒜料酒", "去腥增香")],
    "recipe": [],
}


def build_plan(db: Session) -> dict:
    """纯读：计算 需新建 / 需改名 / 非 canonical 分类。"""
    plan = {"to_create": [], "renames": [], "conflicts": [], "non_canonical": []}
    for type_, names in CATEGORY_LISTS.items():
        model = CATEGORY_MODELS[type_]
        existing = {
            obj.name: obj for obj in db.query(model).filter(model.deleted_at.is_(None)).all()
        }
        for name in names:
            if name not in existing:
                plan["to_create"].append({"type": type_, "name": name})

        for old, new in RENAMES.get(type_, ()):
            old_obj = db.query(model).filter(model.name == old).first()
            if old_obj is None or old_obj.deleted_at is not None:
                continue  # 旧分类不存在，无需改名
            if new in existing:
                plan["conflicts"].append({"type": type_, "name": old, "new": new})
                continue
            plan["renames"].append({"type": type_, "id": old_obj.id, "name": old, "new": new})

        # 非 canonical：现存活跃分类既不在清单、也不是「默认」
        for obj in db.query(model).filter(model.deleted_at.is_(None)).all():
            if obj.name != DEFAULT_CATEGORY_NAME and obj.name not in names:
                plan["non_canonical"].append({"type": type_, "name": obj.name, "id": obj.id})
    return plan


def apply_plan(db: Session, plan: dict):
    """执行计划（调用方 commit；幂等，重跑应无事可做）。

    顺序：先改名、后创建。分类表 name 有唯一约束，若先建目标分类
    （如「乳品烘焙」）再把旧分类改名成它，会撞唯一约束。
    """
    for item in plan["renames"]:
        model = CATEGORY_MODELS[item["type"]]
        obj = db.query(model).filter(model.id == item["id"]).first()
        if obj and obj.name == item["name"]:
            obj.name = item["new"]
    # 会话 autoflush=False：改名不显式 flush 则下方查询看不到 pending 改名，
    # 会把「海鲜」改名而来的「海鲜水产」再次 INSERT，撞唯一约束。
    db.flush()
    for item in plan["to_create"]:
        get_or_create_category_id(db, item["type"], item["name"])
    # conflicts / non_canonical 仅报告，不写库


def print_plan(plan: dict):
    print("=" * 68)
    print("分类清单计划（dry-run，未写库）")
    print("=" * 68)
    print(f"\n需新建（{len(plan['to_create'])}）：")
    for item in plan["to_create"]:
        print(f"  [{item['type']}] {item['name']}")
    print(f"\n需改名（{len(plan['renames'])}）：")
    for item in plan["renames"]:
        print(f"  [{item['type']}] {item['name']} → {item['new']}")
    print(f"\n改名冲突，已跳过（{len(plan['conflicts'])}）：")
    for item in plan["conflicts"]:
        print(f"  [{item['type']}] {item['name']} → {item['new']}（目标已存在）")
    print(f"\n非 canonical（不自动删，需人工处理，{len(plan['non_canonical'])}）：")
    for item in plan["non_canonical"]:
        print(f"  [{item['type']}] {item['name']}")


def main():
    parser = argparse.ArgumentParser(description="分类清单幂等建库（dry-run 默认）")
    parser.add_argument("--apply", action="store_true", help="执行写库并提交（默认仅打印计划）")
    parser.add_argument("--report", metavar="PATH", help="计划导出 JSON 路径")
    args = parser.parse_args()

    db = get_session_local()()
    try:
        plan = build_plan(db)
        if args.report:
            Path(args.report).write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"计划已导出: {args.report}\n")
        print_plan(plan)
        if args.apply:
            apply_plan(db, plan)
            db.commit()
            print("\n[apply] 已执行并提交。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
