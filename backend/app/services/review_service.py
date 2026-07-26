"""
评论处理服务
负责 CSV 文件解析、数据清洗和入库到 review 表
"""

import csv
import io
from typing import Any

from ..utils.text_clean import clean_text
from ..database.database import SessionLocal
from ..models import Review,Order,Logistics, Product, Warehouse
import logging
from datetime import datetime


def parse_csv(file_content: bytes) -> list[dict[str, Any]]:
    """解析 CSV 文件内容"""
    content_str = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content_str))
    return [row for row in reader]


def process_reviews(rows: list[dict[str, Any]], source_filename: str) -> tuple[int, list[int]]:
    """
    清洗并保存评论到 review 表，同时关联 product、orders、logistics、warehouse

    支持 CSV 列名（来自 full_dataset.csv）：
        - 评论：reviewerID, asin, reviewerName, reviewText, overall, summary, unixReviewTime, label
        - 订单：order_id, total_amount, payment_method, shipping_address, customer_country, order_date
        - 物流：carrier, tracking_number, shipping_method, ship_date,
               estimated_delivery_days, actual_delivery_days, logistics_status
        - 仓库：warehouse_id, warehouse_name, warehouse_region,
               receive_date, putaway_date, pick_date, dispatch_date, warehouse_processing_days

    返回: (导入数量, review_id列表)
    """

    logger = logging.getLogger(__name__)
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
                # 先尝试用 warehouse_id 查询（如果 CSV 中有）
                warehouse_id_raw = row.get("warehouse_id")
                if warehouse_id_raw:
                    warehouse = db.query(Warehouse).filter(
                        Warehouse.warehouse_code == str(warehouse_id_raw)
                    ).first()
                # 如果没有找到，用名称查
                if not warehouse:
                    warehouse = db.query(Warehouse).filter(
                        Warehouse.warehouse_name == warehouse_name
                    ).first()
                # 如果还找不到，创建
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
                # 仓储时间轴
                receive_date=row.get("receive_date") or None,
                putaway_date=row.get("putaway_date") or None,
                pick_date=row.get("pick_date") or None,
                dispatch_date=row.get("dispatch_date") or None,
                warehouse_processing_days=int(row.get("warehouse_processing_days") or 0),
            )
            db.add(logistics)
            db.flush()
            logger.debug(f"创建物流: {order_code} -> {logistics.logistics_id}")

            # ============================================================
            # 6. 评论 (Review)
            # ============================================================
            review = Review(
                product_id=product.product_id,
                order_id=order.order_id,
                reviewer_id=row.get("reviewerID") or None,
                reviewer_name=row.get("reviewerName") or None,
                asin=asin,
                rating=float(row.get("overall") or row.get("rating") or 0),
                review_text=review_text,
                summary=row.get("summary") or "",
                language=row.get("language") or "en",
                review_time=datetime.fromtimestamp(int(row.get("unixReviewTime"))) if row.get("unixReviewTime") else None,
                label=row.get("label") or "",
            )
            db.add(review)
            db.flush()
            review_ids.append(review.review_id)
            count += 1

            # 每 100 条打印一次进度
            if count % 100 == 0:
                logger.info(f"已处理 {count} 条评论")

        # 提交所有数据
        db.commit()
        logger.info(f"成功导入 {count} 条评论")
        return count, review_ids

    except Exception as e:
        db.rollback()
        logger.error(f"数据入库失败: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()