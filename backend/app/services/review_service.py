"""
评论处理服务
负责 CSV 文件解析、数据清洗和入库到 review 表
"""

import csv
import io
from typing import Any

from app.utils.text_clean import clean_text
from app.database.database import SessionLocal
from app.models import Review


def parse_csv(file_content: bytes) -> list[dict[str, Any]]:
    """解析 CSV 文件内容"""
    content_str = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content_str))
    return [row for row in reader]


def process_reviews(rows: list[dict[str, Any]], source_filename: str) -> tuple[int, list[int]]:
    """
    清洗并保存评论到 review 表。

    支持 CSV 列名（中英文兼容）：
        product_id / 商品ID
        order_id / 订单ID
        rating / 评分
        review_text / review_content / content / 评论内容
        language / 语言

    返回: (导入数量, review_id列表)
    """
    db = SessionLocal()
    count = 0
    review_ids = []

    try:
        for row in rows:
            review_text = (
                row.get("review_text")
                or row.get("review_content")
                or row.get("content")
                or row.get("评论内容")
                or ""
            )

            if not review_text.strip():
                continue

            product_id = row.get("product_id") or row.get("商品ID") or None
            order_id = row.get("order_id") or row.get("订单ID") or None
            rating = int(float(row.get("rating") or row.get("评分") or 0))

            review = Review(
                product_id=int(product_id) if product_id else None,
                order_id=int(order_id) if order_id else None,
                rating=rating,
                review_text=clean_text(review_text),
                language=row.get("language") or row.get("语言") or "zh",
            )
            db.add(review)
            db.flush()
            review_ids.append(review.review_id)
            count += 1

        db.commit()
        return count, review_ids
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_review_context(review_id: int) -> dict:
    """
    查询一条评论的全链路上下文。

    查询链：
        Review → Product
        Review → Order → Logistics
        Review → Order → Warehouse
        Product → Inventory (匹配当前仓库)

    返回: 包含 review/product/order/logistics/warehouse/inventory 的 dict
    异常: ValueError — review 不存在
    """
    from app.models import Product, Order, Logistics, Warehouse, Inventory

    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.review_id == review_id).first()
        if review is None:
            raise ValueError(f"评论不存在: review_id={review_id}")

        product = review.product

        order = review.order

        logistics = None
        warehouse = None
        if order:
            logistics_records = db.query(Logistics).filter(
                Logistics.order_id == order.order_id
            ).first()
            logistics = logistics_records
            warehouse = order.warehouse

        inventory = None
        if product and warehouse:
            inv = db.query(Inventory).filter(
                Inventory.product_id == product.product_id,
                Inventory.warehouse_id == warehouse.warehouse_id,
            ).first()
            if inv:
                inventory = {
                    "stock_quantity": inv.stock_quantity,
                    "available_quantity": inv.available_quantity,
                }

        return {
            "review": review,
            "product": product,
            "order": order,
            "logistics": logistics,
            "warehouse": warehouse,
            "inventory": inventory,
        }
    finally:
        db.close()


def format_context(context: dict) -> str:
    """
    将 get_review_context 返回的 dict 格式化为 AI 可读的纯文本。

    用于拼接到 Prompt 中，让 AI 基于全链路数据做根因分析。
    """
    lines = []

    order = context.get("order")
    if order:
        parts = [
            f"订单编号: {order.order_code or 'N/A'}",
            f"客户国家: {order.customer_country or 'N/A'}",
            f"收货地址: {order.shipping_address or 'N/A'}",
            f"购买数量: {order.quantity or 1}",
            f"订单金额: ${order.total_amount or 0}",
            f"支付方式: {order.payment_method or 'N/A'}",
            f"订单状态: {order.order_status or 'N/A'}",
        ]
        lines.append("【订单信息】" + "，".join(parts))

    logistics = context.get("logistics")
    if logistics:
        parts = [
            f"承运商: {logistics.carrier or 'N/A'}",
            f"物流单号: {logistics.tracking_number or 'N/A'}",
            f"运输方式: {logistics.shipping_method or 'N/A'}",
            f"物流状态: {logistics.shipping_status or 'N/A'}",
            f"预计时效: {logistics.estimated_delivery_days or '?'}天",
            f"延迟天数: {logistics.delay_days or 0}天",
            f"仓储处理天数: {logistics.warehouse_processing_days or '?'}天",
        ]
        if logistics.exception_reason:
            parts.append(f"异常原因: {logistics.exception_reason}")
        lines.append("【物流信息】" + "，".join(parts))

    warehouse = context.get("warehouse")
    if warehouse:
        parts = [
            f"仓库名称: {warehouse.warehouse_name}",
            f"所在区域: {warehouse.region or 'N/A'}",
            f"仓库地址: {warehouse.location or 'N/A'}",
        ]
        lines.append("【仓储信息】" + "，".join(parts))

    inventory = context.get("inventory")
    if inventory:
        parts = [
            f"库存总量: {inventory.get('stock_quantity', 0)}",
            f"可用库存: {inventory.get('available_quantity', 0)}",
        ]
        lines.append("【库存信息】" + "，".join(parts))

    return "\n".join(lines) if lines else ""


def get_review_list(page: int = 1, size: int = 20) -> tuple[list[dict], int]:
    """
    分页查询评论列表，返回前端兼容格式。

    返回: (review_dicts, total_count)
    """
    from sqlalchemy import func

    db = SessionLocal()
    try:
        total = db.query(func.count(Review.review_id)).scalar() or 0
        offset = (page - 1) * size
        reviews = db.query(Review).order_by(Review.review_time.desc()).offset(offset).limit(size).all()

        items = []
        for r in reviews:
            # 语言检测
            lang = r.language or "en"
            country = "US"
            if r.order:
                country = r.order.customer_country or "US"

            items.append({
                "id": str(r.review_id),
                "starRating": r.rating or 1,
                "commentText": r.review_text or "",
                "translatedText": r.review_text or "",
                "category": r.label or "未分类",
                "country": country,
                "timestamp": r.review_time.isoformat() if r.review_time else None,
                "verified": False,
                "vineVoice": False,
                "images": [],
                "aiReply": r.customer_reply.reply_content if r.customer_reply else None,
                "aiSuggestion": None,  # 需要通过 analysis_result 关联获取
            })
        return items, total
    finally:
        db.close()


def get_review_detail(review_id: int) -> dict:
    """
    查询单条评论详情，返回前端兼容格式。

    异常: ValueError — review 不存在
    """
    db = SessionLocal()
    try:
        r = db.query(Review).filter(Review.review_id == review_id).first()
        if r is None:
            raise ValueError(f"评论不存在: review_id={review_id}")

        country = "US"
        if r.order:
            country = r.order.customer_country or "US"

        # 获取 AI 回复
        ai_reply = r.customer_reply.reply_content if r.customer_reply else None

        # 获取 AI 建议（从 analysis_result → operation_suggestion）
        ai_suggestion = None
        if r.analysis_result and r.analysis_result.operation_suggestions:
            suggestions = r.analysis_result.operation_suggestions
            if suggestions:
                data = suggestions[0]
                try:
                    import json
                    sug_obj = json.loads(data.suggestion_text)
                    ai_suggestion = "\n".join(sug_obj.get("suggestions", []))
                except Exception:
                    ai_suggestion = data.suggestion_text

        return {
            "id": str(r.review_id),
            "starRating": r.rating or 1,
            "commentText": r.review_text or "",
            "translatedText": r.review_text or "",
            "category": r.label or "未分类",
            "country": country,
            "timestamp": r.review_time.isoformat() if r.review_time else None,
            "verified": False,
            "vineVoice": False,
            "images": [],
            "aiReply": ai_reply,
            "aiSuggestion": ai_suggestion,
        }
    finally:
        db.close()
