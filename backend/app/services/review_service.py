"""
评论处理服务
负责 CSV 文件解析、数据清洗和入库到 review 表，
以及评论上下文查询、列表、详情。
"""

import csv
import io
import logging
from typing import Any

from app.utils.text_clean import clean_text
from app.database.database import SessionLocal
from app.models import Review, Order, Logistics, Product, Warehouse

logger = logging.getLogger(__name__)


def parse_csv(file_content: bytes) -> list[dict[str, Any]]:
    """解析 CSV 文件内容"""
    content_str = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content_str))
    return [row for row in reader]


def process_reviews(rows: list[dict[str, Any]], source_filename: str) -> tuple[int, list[int]]:
    """
    清洗并保存评论到 review 表，同时关联 product、orders、logistics、warehouse。

    支持 CSV 列名（来自 full_dataset.csv）：
        - 评论：reviewerID, asin, reviewerName, reviewText, overall, summary, unixReviewTime, label
        - 订单：order_id, total_amount, payment_method, shipping_address, customer_country, order_date
        - 物流：carrier, tracking_number, shipping_method, ship_date,
               estimated_delivery_days, actual_delivery_days, logistics_status
        - 仓库：warehouse_id, warehouse_name, warehouse_region,
               receive_date, putaway_date, pick_date, dispatch_date, warehouse_processing_days

    返回: (导入数量, review_id列表)
    """
    db = SessionLocal()
    count = 0
    review_ids = []

    try:
        for idx, row in enumerate(rows):
            # ============================================================
            # 1. 提取并验证核心字段
            # ============================================================
            review_text = (
                row.get("reviewText")
                or row.get("review_text")
                or row.get("review_content")
                or row.get("content")
                or ""
            )
            if not review_text.strip():
                logger.warning(f"第 {idx+1} 行: 评论内容为空，跳过")
                continue

            # ============================================================
            # 2. 商品 (Product)
            # ============================================================
            asin = row.get("asin") or None
            if not asin:
                logger.warning(f"第 {idx+1} 行: asin 为空，跳过")
                continue

            product = db.query(Product).filter(Product.asin == asin).first()
            if not product:
                product = Product(
                    asin=asin,
                    product_name=row.get("product_name") or row.get("title") or f"Product {asin[:8]}",
                    category=row.get("category") or row.get("categories") or "unknown",
                    price=float(row.get("price") or 0),
                    supplier=row.get("supplier") or "",
                )
                db.add(product)
                db.flush()
                logger.debug(f"创建商品: {asin}")

            # ============================================================
            # 3. 仓库 (Warehouse)
            # ============================================================
            warehouse_name = row.get("warehouse_name") or ""
            warehouse = None
            if warehouse_name:
                warehouse_id_raw = row.get("warehouse_id")
                if warehouse_id_raw:
                    warehouse = db.query(Warehouse).filter(
                        Warehouse.warehouse_code == str(warehouse_id_raw)
                    ).first()
                if not warehouse:
                    warehouse = db.query(Warehouse).filter(
                        Warehouse.warehouse_name == warehouse_name
                    ).first()
                if not warehouse:
                    warehouse = Warehouse(
                        warehouse_code=row.get("warehouse_code") or f"WH-{warehouse_name[:6].upper()}",
                        warehouse_name=warehouse_name,
                        region=row.get("warehouse_region") or "unknown",
                        location=row.get("warehouse_location") or "",
                        capacity=int(row.get("warehouse_capacity") or 0),
                    )
                    db.add(warehouse)
                    db.flush()
                    logger.debug(f"创建仓库: {warehouse_name}")

            # ============================================================
            # 4. 订单 (Order)
            # ============================================================
            order_code = row.get("order_id") or row.get("order_code") or ""
            if not order_code:
                logger.warning(f"第 {idx+1} 行: order_id 为空，跳过")
                continue

            order = db.query(Order).filter(Order.order_code == order_code).first()
            if not order:
                order = Order(
                    order_code=order_code,
                    product_id=product.product_id,
                    warehouse_id=warehouse.warehouse_id if warehouse else None,
                    customer_country=row.get("customer_country") or row.get("country") or "US",
                    shipping_address=row.get("shipping_address") or "",
                    quantity=int(row.get("quantity") or 1),
                    total_amount=float(row.get("total_amount") or 0),
                    payment_method=row.get("payment_method") or "unknown",
                    order_status=(
                        "completed" if row.get("logistics_status") == "Delivered"
                        else row.get("order_status") or "pending"
                    ),
                    order_time=row.get("order_date") or row.get("order_time"),
                )
                db.add(order)
                db.flush()
                logger.debug(f"创建订单: {order_code}")

            # ============================================================
            # 5. 物流 (Logistics)
            # ============================================================
            existing_log = db.query(Logistics).filter(Logistics.order_id == order.order_id).first()
            if not existing_log:
                logistics = Logistics(
                    order_id=order.order_id,
                    carrier=row.get("carrier") or "",
                    tracking_number=row.get("tracking_number") or "",
                    shipping_method=row.get("shipping_method") or "standard",
                    shipping_status=row.get("logistics_status") or "unknown",
                    shipping_time=row.get("ship_date") or None,
                    estimated_delivery_days=int(row.get("estimated_delivery_days") or 0),
                    delay_days=(
                        max(0, int(row.get("actual_delivery_days") or 0) - int(row.get("estimated_delivery_days") or 0))
                        if row.get("actual_delivery_days")
                        else 0
                    ),
                    exception_reason=row.get("exception_reason") or "",
                    receive_date=row.get("receive_date") or None,
                    putaway_date=row.get("putaway_date") or None,
                    pick_date=row.get("pick_date") or None,
                    dispatch_date=row.get("dispatch_date") or None,
                    warehouse_processing_days=int(row.get("warehouse_processing_days") or 0),
                )
                db.add(logistics)
                db.flush()
                logger.debug(f"创建物流: {order_code}")

            # ============================================================
            # 6. 评论 (Review)
            # ============================================================
            reviewer_id = row.get("reviewerID") or row.get("reviewer_id") or ""
            existing_review = db.query(Review).filter(
                Review.asin == asin,
                Review.reviewer_id == reviewer_id,
                Review.review_text == review_text,
            ).first()

            if not existing_review:
                review = Review(
                    product_id=product.product_id,
                    order_id=order.order_id,
                    reviewer_id=reviewer_id,
                    reviewer_name=row.get("reviewerName") or row.get("reviewer_name") or "",
                    asin=asin,
                    rating=int(float(row.get("overall") or row.get("rating") or 0)),
                    review_text=review_text,
                    summary=row.get("summary") or "",
                    language=(
                        "zh" if any('一' <= c <= '鿿' for c in review_text) else "en"
                    ),
                    review_time=row.get("review_time") or row.get("unixReviewTime") or None,
                    label=row.get("label") or "Other",
                )
                db.add(review)
                db.flush()
                review_ids.append(review.review_id)
                count += 1
                logger.debug(f"创建评论: {asin} by {reviewer_id}")

        db.commit()
        return count, review_ids
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================
# 评论上下文查询（任务3）
# ============================================================

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
    from app.models import Inventory

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
            logistics = db.query(Logistics).filter(
                Logistics.order_id == order.order_id
            ).first()
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
    """
    lines = []

    order = context.get("order")
    if order:
        lines.append(
            f"【订单信息】订单编号: {order.order_code or 'N/A'}，客户国家: {order.customer_country or 'N/A'}，"
            f"收货地址: {order.shipping_address or 'N/A'}，购买数量: {order.quantity or 1}，"
            f"订单金额: ${order.total_amount or 0}，支付方式: {order.payment_method or 'N/A'}，"
            f"订单状态: {order.order_status or 'N/A'}"
        )

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
        lines.append(
            f"【仓储信息】仓库名称: {warehouse.warehouse_name}，"
            f"所在区域: {warehouse.region or 'N/A'}，仓库地址: {warehouse.location or 'N/A'}"
        )

    inventory = context.get("inventory")
    if inventory:
        lines.append(
            f"【库存信息】库存总量: {inventory.get('stock_quantity', 0)}，"
            f"可用库存: {inventory.get('available_quantity', 0)}"
        )

    return "\n".join(lines) if lines else ""


def get_review_list(page: int = 1, size: int = 20) -> tuple[list[dict], int]:
    """
    分页查询评论列表，返回前端兼容格式。
    """
    from sqlalchemy import func

    db = SessionLocal()
    try:
        total = db.query(func.count(Review.review_id)).scalar() or 0
        offset = (page - 1) * size
        reviews = db.query(Review).order_by(Review.review_time.desc()).offset(offset).limit(size).all()

        items = []
        for r in reviews:
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
                "aiSuggestion": None,
            })
        return items, total
    finally:
        db.close()


def get_review_detail(review_id: int) -> dict:
    """
    查询单条评论详情，返回前端兼容格式。
    """
    db = SessionLocal()
    try:
        r = db.query(Review).filter(Review.review_id == review_id).first()
        if r is None:
            raise ValueError(f"评论不存在: review_id={review_id}")

        country = "US"
        if r.order:
            country = r.order.customer_country or "US"

        ai_reply = r.customer_reply.reply_content if r.customer_reply else None

        ai_suggestion = None
        if r.analysis_result and r.analysis_result.operation_suggestions:
            suggestions = r.analysis_result.operation_suggestions
            if suggestions:
                try:
                    import json
                    sug_obj = json.loads(suggestions[0].suggestion_text)
                    ai_suggestion = "\n".join(sug_obj.get("suggestions", []))
                except Exception:
                    ai_suggestion = suggestions[0].suggestion_text

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
