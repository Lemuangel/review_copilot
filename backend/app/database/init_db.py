"""
数据库初始化脚本
创建所有 MySQL 表并可选填充测试数据
"""

from app.database.database import engine, Base

# 导入所有模型以注册到 Base.metadata
from app.models import (  # noqa: F401
    Product, Warehouse, Inventory, Order,
    Logistics, Review, AnalysisResult,
    OperationSuggestion, CustomerReply,
)


def init_db():
    """创建所有数据库表"""
    print("正在初始化数据库...")
    Base.metadata.create_all(bind=engine)
    print("所有表创建完成！")


if __name__ == "__main__":
    init_db()
