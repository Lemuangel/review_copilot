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
    suggestions: list[str] = Field(default_factory=list, description="运营优化建议列表")


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


# ========== 查询相关 ==========

class ReviewDetail(BaseModel):
    """评论详情"""
    review_id: int
    product_id: Optional[int] = None
    order_id: Optional[int] = None
    rating: Optional[float] = None
    review_text: str
    language: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
