"""
数据库 ORM 模型 — MySQL 表映射（字段与数据库严格一致）

表关系：
    product  1──N  review
    orders   1──N  review
    product  1──N  inventory
    warehouse 1──N inventory
    orders   1──N  logistics
    review   1──1  analysis_result
    analysis_result 1──N operation_suggestion
    review   1──1  customer_reply
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Numeric,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database.database import Base


# ============================================================
# 商品表
# ============================================================

class Product(Base):
    __tablename__ = "product"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(100), nullable=False, comment="商品名称")
    category = Column(String(50), comment="商品分类")
    price = Column(Numeric(10, 2), comment="价格")
    supplier = Column(String(100), comment="供应商")
    created_time = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # relationships
    reviews = relationship("Review", back_populates="product")
    inventories = relationship("Inventory", back_populates="product")


# ============================================================
# 仓库表
# ============================================================

class Warehouse(Base):
    __tablename__ = "warehouse"

    warehouse_id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_name = Column(String(100), comment="仓库名称")
    location = Column(String(100), comment="仓库地址")
    capacity = Column(Integer, comment="库容")
    created_time = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # relationships
    inventories = relationship("Inventory", back_populates="warehouse")


# ============================================================
# 库存表
# ============================================================

class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey("warehouse.warehouse_id"), comment="仓库ID")
    product_id = Column(Integer, ForeignKey("product.product_id"), comment="商品ID")
    stock_quantity = Column(Integer, default=0, comment="库存总数")
    available_quantity = Column(Integer, default=0, comment="可用库存")
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # relationships
    product = relationship("Product", back_populates="inventories")
    warehouse = relationship("Warehouse", back_populates="inventories")


# ============================================================
# 订单表
# ============================================================

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.product_id"), comment="商品ID")
    warehouse_id = Column(Integer, ForeignKey("warehouse.warehouse_id"), comment="仓库ID")
    customer_country = Column(String(50), comment="客户国家")
    quantity = Column(Integer, default=1, comment="购买数量")
    order_status = Column(String(50), default="pending", comment="订单状态")
    order_time = Column(DateTime, default=datetime.utcnow, comment="下单时间")

    # relationships
    product = relationship("Product")
    warehouse = relationship("Warehouse")
    reviews = relationship("Review", back_populates="order")
    logistics = relationship("Logistics", back_populates="order")


# ============================================================
# 物流表
# ============================================================

class Logistics(Base):
    __tablename__ = "logistics"

    logistics_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False, comment="订单ID")
    carrier = Column(String(50), comment="物流公司")
    shipping_status = Column(String(50), default="pending", comment="物流状态")
    shipping_time = Column(DateTime, comment="发货时间")
    delivery_time = Column(DateTime, comment="送达时间")
    delay_days = Column(Integer, default=0, comment="延迟天数")
    exception_reason = Column(String(200), comment="异常原因")

    # relationships
    order = relationship("Order", back_populates="logistics")


# ============================================================
# 评论表
# ============================================================

class Review(Base):
    __tablename__ = "review"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.product_id"), comment="商品ID")
    order_id = Column(Integer, ForeignKey("orders.order_id"), comment="订单ID")
    rating = Column(Integer, comment="评分(1-5)")
    review_text = Column(Text, nullable=False, comment="评论原文")
    language = Column(String(20), default="zh", comment="语言")
    review_time = Column(DateTime, default=datetime.utcnow, comment="评论时间")

    # relationships
    product = relationship("Product", back_populates="reviews")
    order = relationship("Order", back_populates="reviews")
    analysis_result = relationship(
        "AnalysisResult", back_populates="review", uselist=False
    )
    customer_reply = relationship(
        "CustomerReply", back_populates="review", uselist=False
    )


# ============================================================
# 分析结果表
# ============================================================

class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("review.review_id"), nullable=False, comment="评论ID")
    issue_type = Column(String(100), comment="问题类型（逗号分隔）")
    issue_detail = Column(Text, comment="问题详情（JSON字符串）")
    severity = Column(String(20), comment="严重程度")
    created_time = Column(DateTime, default=datetime.utcnow, comment="分析时间")

    # relationships
    review = relationship("Review", back_populates="analysis_result")
    operation_suggestions = relationship(
        "OperationSuggestion", back_populates="analysis_result"
    )


# ============================================================
# 运营建议表
# ============================================================

class OperationSuggestion(Base):
    __tablename__ = "operation_suggestion"

    suggestion_id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analysis_result.analysis_id"), nullable=False, comment="分析结果ID")
    suggestion_text = Column(Text, comment="建议内容（JSON字符串）")
    priority = Column(String(20), comment="优先级")
    created_time = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # relationships
    analysis_result = relationship(
        "AnalysisResult", back_populates="operation_suggestions"
    )


# ============================================================
# 客服回复表
# ============================================================

class CustomerReply(Base):
    __tablename__ = "customer_reply"

    reply_id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(Integer, ForeignKey("review.review_id"), nullable=False, comment="评论ID")
    reply_content = Column(Text, nullable=False, comment="AI生成回复")
    language = Column(String(20), default="zh", comment="回复语言")
    created_time = Column(DateTime, default=datetime.utcnow, comment="生成时间")

    # relationships
    review = relationship("Review", back_populates="customer_reply")
