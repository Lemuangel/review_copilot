"""
真实数据导入脚本
================================
读取同学数据流水线产出的 full_dataset.csv，
按字段映射方案导入 MySQL 的 6 张业务表。

数据流：
    full_dataset.csv → 字段映射 + 模拟缺失字段 → MySQL

幂等设计：可按业务唯一键去重，支持反复执行。

使用方式:
    cd backend
    python -m app.database.import_data
"""

import csv
import os
import random
import sys
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

# 确保 backend 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database.database import SessionLocal
from app.models import (
    Product, Warehouse, Inventory, Order,
    Logistics, Review,
)


# ============================================================
# 模拟数据常量
# ============================================================

SUPPLIERS = [
    "Shenzhen Electronics Co.",
    "Dongguan Tech Ltd.",
    "Hangzhou Supply Chain",
    "Yiwu Trading Co.",
    "Guangzhou Manufacturing",
]

WAREHOUSE_LOCATIONS = {
    "US-WEST": "Los Angeles, CA, USA",
    "US-EAST": "New Jersey, NY, USA",
    "UK": "London, UK",
    "DE": "Frankfurt, Germany",
}

ADDRESS_TO_COUNTRY = {
    "US-CA": "USA",
    "US-NY": "USA",
    "US-TX": "USA",
    "US-FL": "USA",
    "UK-LON": "UK",
    "DE-FRA": "Germany",
    "FR-PAR": "France",
}

STATUS_TO_ORDER_STATUS = {
    "Delivered": "delivered",
    "In Transit": "shipped",
    "Exception": "exception",
}

EXCEPTION_REASONS = [
    "海关查验",
    "地址错误",
    "天气延误",
    "包裹破损",
    "物流信息丢失",
]

# ============================================================
# 工具函数
# ============================================================

def detect_language(text: str) -> str:
    """检测文本语言：包含中文字符则返回 zh，否则 en"""
    if not isinstance(text, str):
        return "en"
    for ch in text:
        if '一' <= ch <= '鿿':
            return "zh"
    return "en"


def safe_int(val: Any, default: int = 0) -> int:
    """安全转换为 int"""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def safe_float(val: Any, default: float = 0.0) -> float:
    """安全转换为 float"""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def parse_date(val: Any) -> datetime:
    """解析日期字符串为 datetime"""
    if pd.isna(val) or val == "" or val is None:
        return None
    try:
        return pd.to_datetime(val).to_pydatetime()
    except Exception:
        return None


def parse_unix_time(val: Any) -> datetime:
    """Unix 时间戳 → datetime"""
    ts = safe_int(val)
    if ts <= 0:
        return datetime.utcnow()
    try:
        return datetime.fromtimestamp(ts)
    except Exception:
        return datetime.utcnow()


# ============================================================
# 主导入逻辑
# ============================================================

def import_from_csv(csv_path: str) -> dict:
    """
    读取 full_dataset.csv 并导入 MySQL。

    参数:
        csv_path: full_dataset.csv 的绝对路径

    返回:
        {"product": (total, new), "warehouse": (total, new), ...}
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV 文件不存在: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"读取到 {len(df)} 条记录\n")

    db = SessionLocal()
    new_reviews = []  # 收集新增的 review，后续同步到 Chroma
    stats = {
        "product":     {"total": 0, "new": 0},
        "warehouse":   {"total": 0, "new": 0},
        "inventory":   {"total": 0, "new": 0},
        "orders":      {"total": 0, "new": 0},
        "logistics":   {"total": 0, "new": 0},
        "review":      {"total": 0, "new": 0},
    }

    try:
        for idx, row in df.iterrows():
            try:
                # ========================================
                # 1. product — UPSERT by asin
                # ========================================
                asin = str(row.get("asin", "")).strip()
                product = db.query(Product).filter(Product.asin == asin).first()

                if product is None:
                    total_amount = safe_float(row.get("total_amount", 0))
                    product = Product(
                        product_name=f"Computer Accessory {asin}",
                        category="Computers",
                        price=total_amount if total_amount > 0 else round(random.uniform(15, 250), 2),
                        supplier=random.choice(SUPPLIERS),
                        asin=asin,
                    )
                    db.add(product)
                    db.flush()
                    stats["product"]["new"] += 1

                product_id = product.product_id
                stats["product"]["total"] += 1

                # ========================================
                # 2. warehouse — UPSERT by warehouse_code
                # ========================================
                wh_code = str(row.get("warehouse_id", "")).strip()
                wh_name = str(row.get("warehouse_name", "")).strip()
                wh_region = str(row.get("warehouse_region", "")).strip()

                warehouse = db.query(Warehouse).filter(
                    Warehouse.warehouse_code == wh_code
                ).first()

                if warehouse is None:
                    warehouse = Warehouse(
                        warehouse_code=wh_code,
                        warehouse_name=wh_name if wh_name else f"Warehouse {wh_code}",
                        location=WAREHOUSE_LOCATIONS.get(wh_region, "Unknown"),
                        region=wh_region,
                        capacity=random.randint(20000, 50000),
                    )
                    db.add(warehouse)
                    db.flush()
                    stats["warehouse"]["new"] += 1

                warehouse_id = warehouse.warehouse_id
                stats["warehouse"]["total"] += 1

                # ========================================
                # 3. inventory — UPSERT by product + warehouse
                # ========================================
                inventory = db.query(Inventory).filter(
                    Inventory.product_id == product_id,
                    Inventory.warehouse_id == warehouse_id,
                ).first()

                if inventory is None:
                    stock = random.randint(50, 500)
                    inventory = Inventory(
                        warehouse_id=warehouse_id,
                        product_id=product_id,
                        stock_quantity=stock,
                        available_quantity=max(0, stock - random.randint(0, 30)),
                    )
                    db.add(inventory)
                    db.flush()
                    stats["inventory"]["new"] += 1

                stats["inventory"]["total"] += 1

                # ========================================
                # 4. orders — UPSERT by order_code
                # ========================================
                order_code = str(row.get("order_id", "")).strip()
                shipping_address = str(row.get("shipping_address", "")).strip()
                logistics_status = str(row.get("logistics_status", "")).strip()

                order = db.query(Order).filter(Order.order_code == order_code).first()

                if order is None:
                    order_date = parse_date(row.get("order_date"))
                    if order_date is None:
                        order_date = datetime.utcnow()

                    order = Order(
                        order_code=order_code,
                        product_id=product_id,
                        warehouse_id=warehouse_id,
                        customer_country=ADDRESS_TO_COUNTRY.get(shipping_address, "USA"),
                        shipping_address=shipping_address,
                        quantity=random.randint(1, 3),
                        total_amount=safe_float(row.get("total_amount"), round(random.uniform(15, 250), 2)),
                        payment_method=str(row.get("payment_method", "Credit Card")).strip(),
                        order_status=STATUS_TO_ORDER_STATUS.get(logistics_status, "pending"),
                        order_time=order_date,
                    )
                    db.add(order)
                    db.flush()
                    stats["orders"]["new"] += 1

                order_id = order.order_id
                stats["orders"]["total"] += 1

                # ========================================
                # 5. logistics — UPSERT by order_id
                # ========================================
                existing_log = db.query(Logistics).filter(
                    Logistics.order_id == order_id
                ).first()

                if existing_log is None:
                    ship_date = parse_date(row.get("ship_date"))
                    receive_date = parse_date(row.get("receive_date"))
                    putaway_date = parse_date(row.get("putaway_date"))
                    pick_date = parse_date(row.get("pick_date"))
                    dispatch_date = parse_date(row.get("dispatch_date"))

                    est_days = safe_int(row.get("estimated_delivery_days"))
                    actual_days_raw = row.get("actual_delivery_days")

                    # delay_days 计算
                    if logistics_status == "Delivered" and actual_days_raw and str(actual_days_raw).strip() != "":
                        actual_days = safe_int(actual_days_raw)
                        delay_days = max(0, actual_days - est_days)
                    else:
                        actual_days = None
                        delay_days = 0

                    # delivery_time 计算
                    if ship_date and actual_days:
                        delivery_time = ship_date + timedelta(days=actual_days)
                    else:
                        delivery_time = None

                    # exception_reason
                    exception_reason = None
                    if logistics_status == "Exception":
                        exception_reason = random.choice(EXCEPTION_REASONS)

                    logistics = Logistics(
                        order_id=order_id,
                        carrier=str(row.get("carrier", "")).strip(),
                        tracking_number=str(row.get("tracking_number", "")).strip(),
                        shipping_method=str(row.get("shipping_method", "")).strip(),
                        shipping_status=logistics_status,
                        shipping_time=ship_date,
                        delivery_time=delivery_time,
                        estimated_delivery_days=est_days if est_days > 0 else None,
                        delay_days=delay_days,
                        exception_reason=exception_reason,
                        receive_date=receive_date,
                        putaway_date=putaway_date,
                        pick_date=pick_date,
                        dispatch_date=dispatch_date,
                        warehouse_processing_days=safe_int(row.get("warehouse_processing_days")),
                    )
                    db.add(logistics)
                    db.flush()
                    stats["logistics"]["new"] += 1

                stats["logistics"]["total"] += 1

                # ========================================
                # 6. review — UPSERT by asin + reviewerID + reviewText
                # ========================================
                reviewer_id = str(row.get("reviewerID", "")).strip()
                reviewer_name = str(row.get("reviewerName", "")).strip()
                review_text = str(row.get("reviewText", "")).strip()

                existing_review = db.query(Review).filter(
                    Review.asin == asin,
                    Review.reviewer_id == reviewer_id,
                    Review.review_text == review_text,
                ).first()

                if existing_review is None:
                    review_time = datetime.utcnow()
                    unix_ts = row.get("unixReviewTime")
                    if unix_ts and str(unix_ts).strip():
                        review_time = parse_unix_time(unix_ts)

                    summary = str(row.get("summary", "")).strip() if pd.notna(row.get("summary")) else ""
                    label = str(row.get("label", "")).strip() if pd.notna(row.get("label")) else "Other"

                    review = Review(
                        product_id=product_id,
                        order_id=order_id,
                        reviewer_id=reviewer_id,
                        reviewer_name=reviewer_name,
                        asin=asin,
                        rating=safe_int(row.get("overall"), 1),
                        review_text=review_text,
                        summary=summary if summary else None,
                        language=detect_language(review_text),
                        review_time=review_time,
                        label=label if label else "Other",
                    )
                    db.add(review)
                    db.flush()
                    stats["review"]["new"] += 1
                    new_reviews.append(review)

                stats["review"]["total"] += 1

                # ========================================
                # 逐行提交（单行事务，某行失败不影响其他行）
                # ========================================
                db.commit()

                if (idx + 1) % 20 == 0:
                    print(f"  已处理 {idx + 1}/{len(df)} 条...")

            except Exception as row_error:
                db.rollback()
                print(f"  ⚠ 第 {idx + 1} 行导入失败: {row_error}")
                continue

    except Exception as e:
        db.rollback()
        print(f"\n导入过程中发生致命错误: {e}")
        raise
    finally:
        db.close()

    stats["_new_reviews"] = new_reviews
    return stats


# ============================================================
# 入口
# ============================================================

def main():
    """读取 full_dataset.csv 并导入 MySQL"""
    # 定位 CSV 文件：直接读沈东阳 data/output/ 的输出
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    csv_path = os.path.join(base_dir, "..", "data", "output", "full_dataset.csv")
    csv_path = os.path.normpath(csv_path)

    if not os.path.exists(csv_path):
        print("=" * 50)
        print("  ⚠ full_dataset.csv 未找到")
        print(f"  期望路径: {csv_path}")
        print()
        print("  请先将同学的数据产物放到 data/output/ 目录下。")
        print("=" * 50)
        return

    print("=" * 50)
    print("  数据导入开始")
    print(f"  数据源: {csv_path}")
    print("=" * 50)
    print()

    stats = import_from_csv(csv_path)

    # ========================================
    # 同步到 Chroma 向量库
    # ========================================
    try:
        from app.services.vector_service import sync_reviews_to_chroma, get_chroma_stats
        chroma_count = sync_reviews_to_chroma(stats.get("_new_reviews", []))
        chroma_stats = get_chroma_stats()
    except Exception as e:
        chroma_count = 0
        chroma_stats = {"error": str(e)}
        print(f"  ⚠ 向量库同步失败: {e}")

    print()
    print("=" * 50)
    print("  数据导入完成！")
    print(f"  Products:     {stats['product']['total']:>5} (新增: {stats['product']['new']})")
    print(f"  Warehouses:   {stats['warehouse']['total']:>5} (新增: {stats['warehouse']['new']})")
    print(f"  Inventories:  {stats['inventory']['total']:>5} (新增: {stats['inventory']['new']})")
    print(f"  Orders:       {stats['orders']['total']:>5} (新增: {stats['orders']['new']})")
    print(f"  Logistics:    {stats['logistics']['total']:>5} (新增: {stats['logistics']['new']})")
    print(f"  Reviews:      {stats['review']['total']:>5} (新增: {stats['review']['new']})")
    if chroma_stats.get("vector_count"):
        print(f"  Chroma向量:   {chroma_stats['vector_count']:>5} (新增: {chroma_count})")
    print("=" * 50)


if __name__ == "__main__":
    main()
