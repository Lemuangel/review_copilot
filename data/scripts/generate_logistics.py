import os
import sys
import pandas as pd
import random
import uuid
from datetime import datetime, timedelta
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ==================== 仓库与承运商映射（基于地域） ====================

WAREHOUSES = {
    'US-WEST': {
        'warehouse_id': 'WH-US-WEST',
        'warehouse_name': '美西洛杉矶仓',
        'region': 'US-WEST',
        'carriers': ['USPS', 'UPS', 'FedEx', 'YunExpress'],
        'shipping_days_to': {'US-CA': 2, 'US-NY': 5, 'US-TX': 3, 'US-FL': 4, 'UK-LON': 7, 'DE-FRA': 8, 'FR-PAR': 8}
    },
    'US-EAST': {
        'warehouse_id': 'WH-US-EAST',
        'warehouse_name': '美东新泽西仓',
        'region': 'US-EAST',
        'carriers': ['USPS', 'UPS', 'FedEx', 'DHL'],
        'shipping_days_to': {'US-CA': 5, 'US-NY': 2, 'US-TX': 3, 'US-FL': 2, 'UK-LON': 5, 'DE-FRA': 6, 'FR-PAR': 6}
    },
    'UK': {
        'warehouse_id': 'WH-UK',
        'warehouse_name': '英国伦敦仓',
        'region': 'UK',
        'carriers': ['DHL', 'Royal Mail', 'UPS', 'FedEx'],
        'shipping_days_to': {'US-CA': 7, 'US-NY': 5, 'US-TX': 6, 'US-FL': 6, 'UK-LON': 1, 'DE-FRA': 2, 'FR-PAR': 2}
    },
    'DE': {
        'warehouse_id': 'WH-DE',
        'warehouse_name': '德国法兰克福仓',
        'region': 'DE',
        'carriers': ['DHL', 'UPS', 'FedEx', 'DPD'],
        'shipping_days_to': {'US-CA': 8, 'US-NY': 6, 'US-TX': 7, 'US-FL': 7, 'UK-LON': 2, 'DE-FRA': 1, 'FR-PAR': 1}
    }
}

# 收货地址 → 推荐仓库（就近原则）
ADDRESS_TO_WAREHOUSE = {
    'US-CA': ['US-WEST'],
    'US-NY': ['US-EAST'],
    'US-TX': ['US-WEST', 'US-EAST'],
    'US-FL': ['US-EAST'],
    'UK-LON': ['UK'],
    'DE-FRA': ['DE'],
    'FR-PAR': ['DE', 'UK'],
}

# 地址 → 承运商偏好（地区匹配）
ADDRESS_TO_CARRIERS = {
    'US-CA': ['USPS', 'UPS', 'FedEx'],
    'US-NY': ['USPS', 'UPS', 'FedEx'],
    'US-TX': ['USPS', 'UPS', 'FedEx'],
    'US-FL': ['USPS', 'UPS', 'FedEx'],
    'UK-LON': ['DHL', 'Royal Mail', 'UPS'],
    'DE-FRA': ['DHL', 'UPS', 'DPD'],
    'FR-PAR': ['DHL', 'UPS', 'DPD'],
}

# 运输方式与时效对应
SHIPPING_METHODS = {
    'Express': {'days_range': (3, 7), 'weight': 0.15},
    'Standard': {'days_range': (7, 15), 'weight': 0.65},
    'Economy': {'days_range': (12, 25), 'weight': 0.20},
}

# 物流状态与概率
LOGISTICS_STATUS = {
    'Delivered': 0.78,
    'In Transit': 0.15,
    'Exception': 0.07,
}

# 异常关键词（如果差评包含这些词，提高 Exception 概率）
EXCEPTION_KEYWORDS = [
    'delay', 'late', 'shipping', 'delivery', 'tracking', 'lost',
    'never arrived', 'not received', 'damaged', 'package', 'box',
    'shipped', 'shipment', 'mail', 'post', 'carrier'
]


def get_warehouse_for_address(address):
    """根据收货地址获取推荐仓库"""
    possible = ADDRESS_TO_WAREHOUSE.get(address, ['US-WEST'])
    return random.choice(possible)


def get_carrier_for_address(address):
    """根据收货地址获取承运商"""
    carriers = ADDRESS_TO_CARRIERS.get(address, ['USPS', 'UPS', 'FedEx'])
    return random.choice(carriers)


def get_shipping_method():
    """根据权重选择运输方式"""
    methods = list(SHIPPING_METHODS.keys())
    weights = [SHIPPING_METHODS[m]['weight'] for m in methods]
    return random.choices(methods, weights=weights)[0]


def get_delivery_days(shipping_method, warehouse_key, address):
    """根据运输方式和仓库到地址的距离估算送达天数"""
    base_days = random.randint(*SHIPPING_METHODS[shipping_method]['days_range'])

    # 根据仓库到地址的距离调整
    warehouse = WAREHOUSES[warehouse_key]
    distance_factor = warehouse['shipping_days_to'].get(address, 5)

    # 实际天数 = 基础天数 + 距离因子（近的加 0-2 天，远的加 2-5 天）
    if distance_factor <= 2:
        extra = random.randint(0, 2)
    elif distance_factor <= 4:
        extra = random.randint(1, 3)
    else:
        extra = random.randint(2, 5)

    return base_days + extra


def should_be_exception(review_text, base_prob=0.07):
    """根据差评内容判断是否为物流异常"""
    if not isinstance(review_text, str):
        return random.random() < base_prob

    text_lower = review_text.lower()
    # 检查是否包含物流相关关键词
    keyword_count = sum(1 for kw in EXCEPTION_KEYWORDS if kw in text_lower)

    # 如果包含多个物流关键词，异常概率显著提高
    if keyword_count >= 3:
        return random.random() < 0.35
    elif keyword_count >= 2:
        return random.random() < 0.20
    elif keyword_count >= 1:
        return random.random() < 0.12
    else:
        return random.random() < base_prob


def generate_order_logistics_warehouse(row):
    """为单条评论生成订单、物流、仓储信息"""
    # 1. 确定收货地址
    shipping_address = random.choice(list(ADDRESS_TO_WAREHOUSE.keys()))

    # 2. 确定仓库
    warehouse_key = get_warehouse_for_address(shipping_address)
    warehouse = WAREHOUSES[warehouse_key]

    # 3. 确定承运商
    carrier = get_carrier_for_address(shipping_address)

    # 4. 确定运输方式
    shipping_method = get_shipping_method()

    # 5. 计算时效
    est_days = get_delivery_days(shipping_method, warehouse_key, shipping_address)

    # 6. 订单时间（基于评论时间往前推 10-45 天）
    review_time = datetime.fromtimestamp(row['unixReviewTime'])
    order_date = review_time - timedelta(days=random.randint(10, 45))

    # 7. 发货时间（下单后 1-3 天）
    ship_date = order_date + timedelta(days=random.randint(1, 3))

    # 8. 检查差评内容，决定物流状态
    review_text = row.get('reviewText', '')
    is_exception = should_be_exception(review_text, base_prob=0.07)

    if is_exception:
        logistics_status = 'Exception'
        actual_delivery_days = None
        # 异常情况下，部分仓储日期可能延迟
        receive_delay = random.randint(5, 15)
        putaway_delay = random.randint(3, 10)
        pick_delay = random.randint(2, 8)
        dispatch_delay = random.randint(2, 6)
    else:
        # 80% 概率已送达，20% 仍在运输中
        if random.random() < 0.8:
            logistics_status = 'Delivered'
            # 实际送达天数 = 预计天数 + 随机偏差（-2 到 +5 天），至少为 1
            actual_delivery_days = max(1, est_days + random.randint(-2, 5))
        else:
            logistics_status = 'In Transit'
            actual_delivery_days = None
        receive_delay = random.randint(3, 7)
        putaway_delay = random.randint(1, 3)
        pick_delay = random.randint(1, 3)
        dispatch_delay = random.randint(1, 3)

    # 9. 仓储操作时间轴
    receive_date = ship_date + timedelta(days=receive_delay)
    putaway_date = receive_date + timedelta(days=putaway_delay)
    pick_date = putaway_date + timedelta(days=pick_delay)
    dispatch_date = pick_date + timedelta(days=dispatch_delay)

    # 10. 订单信息
    order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    total_amount = round(random.uniform(15, 250), 2)
    payment_method = random.choice(['Credit Card', 'PayPal', 'Gift Card', 'Amazon Pay'])

    return {
        'order_id': order_id,
        'order_date': order_date.strftime('%Y-%m-%d'),
        'total_amount': total_amount,
        'payment_method': payment_method,
        'shipping_address': shipping_address,
        'carrier': carrier,
        'tracking_number': f"TN{random.randint(10000000, 99999999)}",
        'shipping_method': shipping_method,
        'ship_date': ship_date.strftime('%Y-%m-%d'),
        'estimated_delivery_days': est_days,
        'actual_delivery_days': actual_delivery_days if actual_delivery_days is not None else '',
        'logistics_status': logistics_status,
        'warehouse_id': warehouse['warehouse_id'],
        'warehouse_name': warehouse['warehouse_name'],
        'warehouse_region': warehouse['region'],
        'receive_date': receive_date.strftime('%Y-%m-%d'),
        'putaway_date': putaway_date.strftime('%Y-%m-%d'),
        'pick_date': pick_date.strftime('%Y-%m-%d'),
        'dispatch_date': dispatch_date.strftime('%Y-%m-%d'),
        # 计算仓储处理时长（天），用于分析仓储效率
        'warehouse_processing_days': (dispatch_date - receive_date).days,
    }


def main():
    print("Step 4: Generate Realistic Logistics and Warehouse Data")

    in_path = os.path.join(config.OUTPUT_DIR, "labeled_reviews.csv")
    if not os.path.exists(in_path):
        print("Please run label_data.py first")
        return

    df = pd.read_csv(in_path, encoding='utf-8-sig')
    print(f"Loaded {len(df)} labeled reviews")

    # 为每条评论生成全链路数据
    extra_info = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Generating logistics"):
        info = generate_order_logistics_warehouse(row)
        extra_info.append(info)

    df_extra = pd.DataFrame(extra_info)
    df_full = pd.concat([df.reset_index(drop=True), df_extra], axis=1)

    out_path = os.path.join(config.OUTPUT_DIR, "full_dataset.csv")
    df_full.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Saved to {out_path}")

    # 输出统计信息
    print("\n--- 物流统计 ---")
    print(df_full['logistics_status'].value_counts())
    print("\n--- 承运商分布 ---")
    print(df_full['carrier'].value_counts())
    print("\n--- 仓库分布 ---")
    print(df_full['warehouse_name'].value_counts())


if __name__ == "__main__":
    main()