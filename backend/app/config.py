"""
应用配置模块
从 .env 文件和环境变量中加载配置
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _build_database_url() -> str:
    """从独立环境变量构建 MySQL 连接串，兼容直接设置 DATABASE_URL"""
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url

    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "ai_review_copilot")

    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


class Settings:
    """应用全局配置"""

    # 应用基础信息
    APP_NAME: str = "AI差评驱动跨境运营Copilot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 大模型配置
    MODEL_API_KEY: str = os.getenv("MODEL_API_KEY", "")
    MODEL_BASE_URL: str = os.getenv("MODEL_BASE_URL", "https://api.deepseek.com/v1")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek-chat")

    # MySQL 配置
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: str = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "ai_review_copilot")

    # 数据库连接串（自动构建）
    DATABASE_URL: str = _build_database_url()

    # 文件上传配置
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: list = [".csv"]

    # AI 分析配置
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "2000"))
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.3"))


settings = Settings()
