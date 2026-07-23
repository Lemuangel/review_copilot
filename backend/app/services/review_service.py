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
