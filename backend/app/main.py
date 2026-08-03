import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.database import init_db
from app.api.recipes import router as recipes_router
from app.api.ingredients import router as ingredients_router
from app.api.inventory import router as inventory_router
from app.api.recommendations import router as recommendations_router
from app.api.ingestions import router as ingestions_router
from app.api.categories import router as categories_router
from app.api.seasonings import router as seasonings_router
from app.api.favorites import router as favorites_router
from app.api.history import router as history_router
from app.api.menu import router as menu_router
from app.api.discover import router as discover_router

# 配置日志
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("应用启动中...")
    logger.info(f"数据库连接: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

    # 初始化数据库
    logger.info("初始化数据库...")
    init_db()
    logger.info("数据库初始化完成")

    yield

    logger.info("应用关闭中...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.APP_DEBUG,
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（添加 /api/v1 前缀）
app.include_router(recipes_router, prefix="/api/v1")
app.include_router(ingredients_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(ingestions_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(seasonings_router, prefix="/api/v1")
app.include_router(favorites_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(menu_router, prefix="/api/v1")
app.include_router(discover_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }
