"""
测试数据生成脚本
为所有业务表插入示例数据。
使用方式: python -m app.database.mock_data
"""

from datetime import datetime, timedelta
import random
import json

from app.database.database import SessionLocal
from app.models import (
    Product, Warehouse, Inventory, Order,
    Logistics, Review, AnalysisResult,
    OperationSuggestion, CustomerReply,
)


def create_mock_data():
    """插入全套测试数据"""
    db = SessionLocal()

    try:
        if db.query(Product).count() > 0:
            print("数据库已有数据，跳过 mock 插入。")
            return

        # ===== 商品 =====
        products = [
            Product(product_name="Wireless Bluetooth Headphones Pro", category="Electronics", price=49.99, supplier="Shenzhen Audio Co."),
            Product(product_name="Organic Cotton T-Shirt", category="Clothing", price=19.99, supplier="Hangzhou Textile Ltd."),
            Product(product_name="Stainless Steel Water Bottle 750ml", category="Home & Kitchen", price=24.99, supplier="Yongkang Metalworks"),
            Product(product_name="Yoga Mat Premium 6mm", category="Sports", price=34.99, supplier="Xiamen Sports Goods"),
            Product(product_name="USB-C Charging Cable 2m", category="Electronics", price=9.99, supplier="Dongguan Cable Factory"),
        ]
        db.add_all(products)
        db.flush()

        # ===== 仓库 =====
        warehouses = [
            Warehouse(warehouse_name="Shenzhen Main Hub", location="Shenzhen, Guangdong, China", capacity=50000),
            Warehouse(warehouse_name="Los Angeles FBA Prep", location="Los Angeles, CA, USA", capacity=30000),
            Warehouse(warehouse_name="Frankfurt EU Center", location="Frankfurt, Germany", capacity=25000),
        ]
        db.add_all(warehouses)
        db.flush()

        # ===== 库存 =====
        for p in products:
            for w in warehouses:
                qty = random.randint(50, 500)
                db.add(Inventory(
                    warehouse_id=w.warehouse_id,
                    product_id=p.product_id,
                    stock_quantity=qty,
                    available_quantity=max(0, qty - random.randint(0, 30)),
                ))
        db.flush()

        # ===== 订单 =====
        countries = ["USA", "Germany", "France", "UK", "Spain", "Japan", "Singapore", "Brazil"]
        statuses = ["delivered"] * 6 + ["shipped", "pending", "cancelled"]
        base_date = datetime.utcnow() - timedelta(days=60)

        orders = []
        for i in range(20):
            p = random.choice(products)
            w = random.choice(warehouses)
            orders.append(Order(
                product_id=p.product_id,
                warehouse_id=w.warehouse_id,
                customer_country=random.choice(countries),
                quantity=random.randint(1, 3),
                order_status=random.choice(statuses),
                order_time=base_date + timedelta(days=random.randint(0, 55)),
            ))
        db.add_all(orders)
        db.flush()

        # ===== 物流 =====
        carriers = ["DHL", "FedEx", "UPS", "YunExpress", "4PX", "Cainiao"]
        ship_statuses = ["delivered"] * 6 + ["in_transit", "out_for_delivery", "pending"]
        delay_reasons = ["", "", "", "海关查验", "地址错误", "天气延误", "包裹破损", ""]

        for o in orders:
            shipped = o.order_time + timedelta(days=random.randint(1, 3))
            delivered = shipped + timedelta(days=random.randint(3, 14))
            delay = random.choice([0, 0, 0, 0, 2, 3, 7, 14])
            actual_delivery = delivered + timedelta(days=delay) if o.order_status == "delivered" else None

            db.add(Logistics(
                order_id=o.order_id,
                carrier=random.choice(carriers),
                shipping_status=random.choice(ship_statuses),
                shipping_time=shipped,
                delivery_time=actual_delivery,
                delay_days=delay,
                exception_reason=random.choice(delay_reasons) if delay > 2 else None,
            ))
        db.flush()

        # ===== 评论（差评为主）=====
        review_data = [
            (1.0, "The product quality is terrible and package damaged"),
            (1.0, "材质很差，跟图片完全不一样，非常失望"),
            (1.0, "Broke after 3 days of use. Complete waste of money"),
            (2.0, "物流太慢了！等了三个星期才收到，包装都破了"),
            (2.0, "Package arrived 2 weeks late. Box was crushed"),
            (2.0, "Tracking never updated. Thought it was lost"),
            (2.0, "Size is completely wrong. Ordered XL but fits like M"),
            (1.0, "尺码严重偏小，我平时穿L码这个XXL都穿不进去"),
            (2.0, "颜色和图片差太多了，图片是正红色收到的是暗红色"),
            (2.0, "The color is nothing like the photo. Very misleading"),
            (1.0, "Bluetooth keeps disconnecting every 5 minutes"),
            (1.0, "无法充电，收到就是坏的！"),
            (2.0, "包装太简陋了，没有任何保护，瓶子都凹了"),
            (2.0, "No bubble wrap or anything. Product box was destroyed"),
            (1.0, "Contacted support 3 times, no response. Terrible service"),
            (1.0, "客服态度极差，退货申请都一周了没处理"),
        ]

        delivered_orders = [o for o in orders if o.order_status == "delivered"]
        reviews = []
        for i, (rating, text) in enumerate(review_data):
            o = delivered_orders[i % len(delivered_orders)] if delivered_orders else random.choice(orders)
            lang = "zh" if any('一' <= c <= '鿿' for c in text) else "en"
            reviews.append(Review(
                product_id=o.product_id,
                order_id=o.order_id,
                rating=int(rating),
                review_text=text,
                language=lang,
            ))
        db.add_all(reviews)
        db.flush()

        # ===== 分析 + 建议 + 回复（前4条差评预生成）=====
        for r in reviews[:4]:
            issues = (["产品质量问题", "包装问题"] if r.rating <= 1
                      else ["物流问题"])

            analysis = AnalysisResult(
                review_id=r.review_id,
                issue_type=", ".join(issues),
                issue_detail=json.dumps({"issues": issues, "sentiment": "negative", "severity": "high"}, ensure_ascii=False),
                severity="high" if r.rating <= 1 else "medium",
            )
            db.add(analysis)
            db.flush()

            db.add(OperationSuggestion(
                analysis_id=analysis.analysis_id,
                suggestion_text=json.dumps({
                    "suggestions": [
                        "加强产品质检流程，出厂前全检",
                        "升级包装材料，增加防震填充",
                        "建立客户投诉48小时响应机制",
                    ],
                    "priority": ["高", "中", "中"],
                    "estimated_impact": "high",
                }, ensure_ascii=False),
                priority="高, 中, 中",
            ))

            reply_lang = "zh" if r.language == "zh" else "en"
            db.add(CustomerReply(
                review_id=r.review_id,
                reply_content="尊敬的顾客，非常抱歉给您带来了不愉快的购物体验。我们已收到您的反馈，将为您安排全额退款或免费重发。请通过客服邮箱联系，我们将优先处理。",
                language=reply_lang,
            ))

        db.commit()

        print("=" * 50)
        print("Mock data created successfully!")
        print(f"  Products:    {db.query(Product).count()}")
        print(f"  Warehouses:  {db.query(Warehouse).count()}")
        print(f"  Inventories: {db.query(Inventory).count()}")
        print(f"  Orders:      {db.query(Order).count()}")
        print(f"  Logistics:   {db.query(Logistics).count()}")
        print(f"  Reviews:     {db.query(Review).count()}")
        print(f"  Analysis:    {db.query(AnalysisResult).count()}")
        print(f"  Suggestions: {db.query(OperationSuggestion).count()}")
        print(f"  Replies:     {db.query(CustomerReply).count()}")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"Mock data creation failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_mock_data()
