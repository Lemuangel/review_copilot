"""
AI算法模块配置
"""
import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# HuggingFace 镜像（国内加速）
if not os.getenv("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("VOLC_ACCESSKEY", "")
DEEPSEEK_BASE_URL = os.getenv("VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DEEPSEEK_MODEL = os.getenv("VOLC_MODEL_ID", "ep-20260706184104-8bdw6")

# 向量数据库配置
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "vector_db"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# RAG 检索参数
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.65"))

# 数据路径
DATA_PATH = os.getenv("DATA_PATH", os.path.join(os.path.dirname(__file__), "..", "data"))