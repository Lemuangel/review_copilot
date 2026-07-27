"""
Pydantic 数据模型（请求/响应 Schema）
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ========== 评论上传 ==========

class ReviewUploadResponse(BaseModel):
    """评论上传响应"""
    total_rows: int = Field(..., description="CSV总行数")
    imported_count: int = Field(..., description="成功导入数量")
    message: str = Field(..., description="处理结果信息")
    review_ids: list[int] = Field(default_factory=list, description="导入的评论ID列表")


# ========== 差评分析 ==========

class AnalysisRequest(BaseModel):
    """分析请求"""
    review_id: Optional[int] = Field(None, description="评论ID（数据库记录ID）")
    review_text: str = Field(..., min_length=1, max_length=5000, description="评论文本")


class AnalysisResponse(BaseModel):
    """分析响应"""
    review_id: Optional[int] = Field(None, description="评论ID")
    analysis_id: Optional[int] = Field(None, description="分析结果ID")
    suggestion_id: Optional[int] = Field(None, description="运营建议ID")
    issues: list[str] = Field(default_factory=list, description="问题分类列表")
    root_cause: Optional[str] = Field(None, description="根因分析")
    evidence: list[str] = Field(default_factory=list, description="证据列表（如 delay_days=7）")
    suggestions: list[str] = Field(default_factory=list, description="运营优化建议列表")
    context_used: bool = Field(False, description="是否使用了全链路上下文")


# ========== 客服回复 ==========

class CustomerReplyRequest(BaseModel):
    """客服回复请求"""
    review_id: Optional[int] = Field(None, description="评论ID（数据库记录ID）")
    review_text: str = Field(..., min_length=1, max_length=5000, description="差评内容")


class CustomerReplyResponse(BaseModel):
    """客服回复响应"""
    review_id: Optional[int] = Field(None, description="评论ID")
    reply_id: Optional[int] = Field(None, description="回复记录ID")
    reply_text: str = Field(..., description="AI生成的客服回复")


# ========== 评论上下文查询 ==========

class ReviewContextItem(BaseModel):
    """评论上下文 — 评论信息"""
    review_id: int
    rating: Optional[float] = None
    review_text: str
    label: Optional[str] = None
    language: Optional[str] = None
    review_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductContextItem(BaseModel):
    """评论上下文 — 商品信息"""
    product_id: int
    product_name: str
    category: Optional[str] = None
    price: Optional[float] = None
    asin: Optional[str] = None

    class Config:
        from_attributes = True


class OrderContextItem(BaseModel):
    """评论上下文 — 订单信息"""
    order_id: int
    order_code: Optional[str] = None
    customer_country: Optional[str] = None
    shipping_address: Optional[str] = None
    quantity: Optional[int] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    order_status: Optional[str] = None
    order_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class LogisticsContextItem(BaseModel):
    """评论上下文 — 物流信息"""
    logistics_id: int
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipping_method: Optional[str] = None
    shipping_status: Optional[str] = None
    shipping_time: Optional[datetime] = None
    delivery_time: Optional[datetime] = None
    estimated_delivery_days: Optional[int] = None
    delay_days: Optional[int] = None
    exception_reason: Optional[str] = None
    warehouse_processing_days: Optional[int] = None

    class Config:
        from_attributes = True


class WarehouseContextItem(BaseModel):
    """评论上下文 — 仓库信息"""
    warehouse_id: int
    warehouse_name: str
    location: Optional[str] = None
    region: Optional[str] = None

    class Config:
        from_attributes = True


class InventoryContextItem(BaseModel):
    """评论上下文 — 库存信息"""
    stock_quantity: Optional[int] = None
    available_quantity: Optional[int] = None

    class Config:
        from_attributes = True


class ReviewContextResponse(BaseModel):
    """评论全链路上下文"""
    review: ReviewContextItem
    product: ProductContextItem
    order: OrderContextItem
    logistics: Optional[LogisticsContextItem] = None
    warehouse: Optional[WarehouseContextItem] = None
    inventory: Optional[InventoryContextItem] = None


# ========== 统计分析 ==========

class StatisticsResponse(BaseModel):
    """统计分析响应"""
    total_reviews: int = Field(0, description="评论总数")
    negative_count: int = Field(0, description="差评数量（评分≤2）")
    negative_ratio: float = Field(0.0, description="差评占比")
    label_distribution: dict = Field(default_factory=dict, description="问题分类分布")
    severity_distribution: dict = Field(default_factory=dict, description="严重程度分布")
    logistics_distribution: dict = Field(default_factory=dict, description="物流状态分布")
    analyzed_count: int = Field(0, description="已分析评论数")


# ========== 前端 Dashboard 统计（对齐 view.vue） ==========

class FrontendStatsResponse(BaseModel):
    """前端统计响应（对齐 data.js mock 格式）"""
    total: int = Field(0, description="总差评数")
    categories: list[dict] = Field(default_factory=list, description="类别分布 [{name, value}]")
    starDistribution: list[dict] = Field(default_factory=list, description="星级分布 [{star, count}]")


# ========== 前端评论列表项 ==========

class ReviewListItem(BaseModel):
    """前端评论列表项（对齐 data.js mock 字段）"""
    id: str = Field(..., description="评论ID（转为字符串兼容前端）")
    starRating: int = Field(1, description="评分")
    commentText: str = Field("", description="原文")
    translatedText: str = Field("", description="翻译文本")
    category: str = Field("未分类", description="问题类别")
    country: str = Field("", description="国家")
    timestamp: Optional[str] = Field(None, description="评论时间")
    verified: bool = Field(False, description="是否验证购买")
    vineVoice: bool = Field(False, description="是否Vine")
    images: list[str] = Field(default_factory=list, description="图片URL")
    aiReply: Optional[str] = Field(None, description="AI客服回复")
    aiSuggestion: Optional[str] = Field(None, description="AI运营建议")

    class Config:
        from_attributes = True


# ========== 通用请求/响应 ==========

class GenerateRequest(BaseModel):
    """AI 生成请求"""
    review_id: str = Field(..., alias="reviewId", description="评论ID")
    reviewId: Optional[str] = Field(None, description="评论ID（兼容驼峰）")
    type: str = Field(..., description="生成类型: reply | suggestion")

    class Config:
        populate_by_name = True
