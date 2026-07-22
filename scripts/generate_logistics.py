import os
import sys
import pandas as pd
import random
import uuid
from datetime import datetime, timedelta
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 承运商列表
CARRIERS = ['Yanwen', 'YunExpress', 'USPS', 'DHL', 'FedEx', 'UPS']
# 运输方式
SHIPPING_METHODS = ['Standard', 'Express', 'Economy']
# 物流状态
LOGISTICS_STATUS = ['Delivered', 'In Transit', 'Exception']
# 仓库信息（ID, 名称, 区域）
WAREHOUSES = [
    {'id': 'WH-US-WEST', 'name': '美西洛杉矶仓', 'region': 'US-WEST'},
    {'id': 'WH-US-EAST', 'name': '美东新泽西仓', 'region': 'US-EAST'},
    {'id': 'WH-UK', 'name': '英国伦敦仓', 'region': 'UK'},
    {'id': 'WH-DE', 'name': '德国法兰克福仓', 'region': 'DE'},
]
# 支付方式
PAYMENT_METHODS = ['Credit Card', 'PayPal', 'Gift Card', 'Amazon Pay']
# 收货地址（简化为国家/地区代码）
SHIPPING_REGIONS = ['US-CA', 'US-NY', 'US-TX', 'US-FL', 'UK-LON', 'DE-FRA', 'FR-PAR']


def generate_order_logistics_warehouse(review_row):
    """
    根据一条评论生成对应的订单、物流、仓储信息
    返回一个字典，包含所有新增字段
    """
    # 基于评论时间生成订单日期（评论时间往前推 5~30 天）
    review_time = datetime.fromtimestamp(review_row['unixReviewTime'])
    order_date = review_time - timedelta(days=random.randint(5, 30))

    # 订单信息
    order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    customer_id = review_row['reviewerID']
    total_amount = round(random.uniform(10, 250), 2)
    payment_method = random.choice(PAYMENT_METHODS)
    shipping_address = random.choice(SHIPPING_REGIONS)

    # 物流信息
    carrier = random.choice(CARRIERS)
    tracking_number = f"TN{random.randint(10000000, 99999999)}"
    shipping_method = random.choice(SHIPPING_METHODS)
    ship_date = order_date + timedelta(days=random.randint(1, 3))

    # 预计送达天数（根据运输方式估算）
    if shipping_method == 'Express':
        est_days = random.randint(3, 7)
    elif shipping_method == 'Standard':
        est_days = random.randint(7, 15)
    else:  # Economy
        est_days = random.randint(12, 25)

    # 实际送达情况（可能延误或异常）
    is_exception = random.random() < 0.05  # 5% 概率异常
    if is_exception:
        logistics_status = 'Exception'
        actual_delivery_days = None
    else:
        # 80% 概率已送达，20% 仍在运输中
        if random.random() < 0.8:
            logistics_status = 'Delivered'
            # 实际送达天数 = 预计天数 + 随机偏差（-2 到 +5 天），至少为 1
            actual_delivery_days = max(1, est_days + random.randint(-2, 5))
        else:
            logistics_status = 'In Transit'
            actual_delivery_days = None

    # 仓储信息
    warehouse = random.choice(WAREHOUSES)
    warehouse_id = warehouse['id']
    warehouse_name = warehouse['name']
    warehouse_region = warehouse['region']

    # 仓储操作时间轴
    # 假设货物在 ship_date 后 3~7 天到达仓库
    receive_date = ship_date + timedelta(days=random.randint(3, 7))
    # 上架、拣货、出库各间隔 1~2 天
    putaway_date = receive_date + timedelta(days=random.randint(1, 2))
    pick_date = putaway_date + timedelta(days=random.randint(1, 2))
    dispatch_date = pick_date + timedelta(days=random.randint(1, 2))

    # 如果是异常订单，部分日期可能缺失（模拟实际）
    if is_exception:
        # 异常情况下，可能收不到货，后续日期置空或延迟
        # 这里简单将物流状态设为异常，保留日期但实际分析时会标记
        pass

    return {
        'order_id': order_id,
        'order_date': order_date.strftime('%Y-%m-%d'),
        'customer_id': customer_id,
        'total_amount': total_amount,
        'payment_method': payment_method,
        'shipping_address': shipping_address,
        'carrier': carrier,
        'tracking_number': tracking_number,
        'shipping_method': shipping_method,
        'ship_date': ship_date.strftime('%Y-%m-%d'),
        'estimated_delivery_days': est_days,
        'actual_delivery_days': actual_delivery_days if actual_delivery_days is not None else '',
        'logistics_status': logistics_status,
        'warehouse_id': warehouse_id,
        'warehouse_name': warehouse_name,
        'warehouse_region': warehouse_region,
        'receive_date': receive_date.strftime('%Y-%m-%d'),
        'putaway_date': putaway_date.strftime('%Y-%m-%d'),
        'pick_date': pick_date.strftime('%Y-%m-%d'),
        'dispatch_date': dispatch_date.strftime('%Y-%m-%d'),
    }


def main():
    print("Step 4: Generate Full Data with Order, Logistics, Warehouse")

    # 读取标注后的数据
    in_path = os.path.join(config.OUTPUT_DIR, "labeled_reviews.csv")
    if not os.path.exists(in_path):
        print("Please run label_data.py first")
        return

    df_reviews = pd.read_csv(in_path, encoding='utf-8-sig')
    print(f"Loaded {len(df_reviews)} labeled reviews")

    # 为每条评论生成扩展信息
    extra_info = []
    for _, row in tqdm(df_reviews.iterrows(), total=len(df_reviews), desc="Generating order/logistics/warehouse"):
        info = generate_order_logistics_warehouse(row)
        extra_info.append(info)

    df_extra = pd.DataFrame(extra_info)

    # 合并原始评论和新增字段
    df_full = pd.concat([df_reviews.reset_index(drop=True), df_extra], axis=1)

    # 保存完整数据集
    out_path = os.path.join(config.OUTPUT_DIR, "full_dataset.csv")
    df_full.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Full dataset saved to {out_path}")

    # 额外输出独立的订单、物流、仓储表（可选）
    # 这里可根据需要决定是否导出


if __name__ == "__main__":
    main()