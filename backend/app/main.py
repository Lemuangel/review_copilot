"""
AI差评驱动跨境运营Copilot — FastAPI 应用入口
"""

import os
import hashlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import review, analysis, customer
from app.routers.analysis import frontend_router

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI驱动的差评分析、运营建议与客服回复生成系统",
)

# CORS 中间件（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== /api 前缀路由（前端调用） ==========

from fastapi import APIRouter

api_router = APIRouter(prefix="/api")
api_router.include_router(review.router)
api_router.include_router(analysis.router)
api_router.include_router(customer.router)
api_router.include_router(frontend_router)
app.include_router(api_router)

# ========== 原始路由（向后兼容 Swagger 直接测试） ==========

app.include_router(review.router)
app.include_router(analysis.router)
app.include_router(customer.router)
app.include_router(frontend_router)


# ========== 启动时自动检测 CSV 更新 ==========

@app.on_event("startup")
def auto_sync_on_startup():
    """
    后端启动时自动检测 full_dataset.csv 是否有更新。
    如果有更新或首次启动，自动执行 MySQL + Chroma 双库同步。
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 直接读沈东阳 data/output/ 的输出
    csv_path = os.path.join(base_dir, "..", "data", "output", "full_dataset.csv")
    csv_path = os.path.normpath(csv_path)
    hash_path = os.path.join(base_dir, "data", ".last_sync")

    if not os.path.exists(csv_path):
        logger.info("未找到 full_dataset.csv，跳过自动同步")
        return

    # 计算当前 CSV 的 SHA256
    with open(csv_path, "rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()

    # 读取上次同步的 hash
    last_hash = ""
    if os.path.exists(hash_path):
        with open(hash_path, "r") as f:
            last_hash = f.read().strip()

    if current_hash == last_hash:
        logger.info("CSV 无变化，跳过自动同步")
        return

    logger.info("检测到 CSV 更新，开始自动同步...")
    try:
        from app.database.import_data import import_from_csv
        from app.services.vector_service import sync_reviews_to_chroma

        stats = import_from_csv(csv_path)
        new_reviews = stats.get("_new_reviews", [])
        if new_reviews:
            sync_reviews_to_chroma(new_reviews)

        # 记录本次 hash
        with open(hash_path, "w") as f:
            f.write(current_hash)

        logger.info(
            f"自动同步完成: MySQL {stats['review']['total']}条, "
            f"Chroma {len(new_reviews)}条新增"
        )
    except Exception as e:
        logger.warning(f"自动同步失败（可稍后手动 POST /api/sync）: {e}")


# ========== 根路径 ==========

@app.get("/", tags=["系统"])
async def root():
    """系统健康检查"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}
