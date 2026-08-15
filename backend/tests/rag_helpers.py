"""RAG 测试共用工具：伪嵌入器 + 造菜谱辅助。"""
import hashlib
import uuid

from app.db.models import Ingredient, Recipe, RecipeIngredient, RecipeStep


class FakeEmbedder:
    """确定性伪嵌入器（dims=1024），测试不触碰真实 Ollama。"""

    dim = 1024

    def embed_texts(self, texts):
        return [self.embed_text(t) for t in texts]

    def embed_text(self, text):
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [((h[i % len(h)]) / 255.0) * 2 - 1 for i in range(self.dim)]

    def health_check(self):
        return {"ok": True, "model_available": True, "detail": "fake"}


def make_recipe(db_session, title="番茄炒鸡蛋", summary="家常快手菜",
                status="published", revision=1, ingredient_name="番茄"):
    """创建一道菜谱（含食材与步骤）并 commit，返回 Recipe。"""
    ing = Ingredient(
        id=str(uuid.uuid4()),
        canonical_name=ingredient_name,
        confidence_status="verified",
    )
    db_session.add(ing)
    db_session.flush()

    recipe = Recipe(
        id=str(uuid.uuid4()),
        title=title,
        summary=summary,
        pinyin="fanqiechaodan" if title == "番茄炒鸡蛋" else "test",
        servings=2,
        prep_minutes=5,
        cook_minutes=10,
        difficulty="简单",
        status=status,
        revision=revision,
    )
    db_session.add(recipe)
    db_session.flush()

    db_session.add(RecipeIngredient(
        id=str(uuid.uuid4()),
        recipe_id=recipe.id,
        ingredient_id=ing.id,
        quantity="2",
        unit="个",
        sort_order=0,
    ))
    for i in range(3):
        db_session.add(RecipeStep(
            id=str(uuid.uuid4()),
            recipe_id=recipe.id,
            step_no=i + 1,
            instruction=f"步骤{i + 1}",
        ))
    db_session.commit()
    return recipe
