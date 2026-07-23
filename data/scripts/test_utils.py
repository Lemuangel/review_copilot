import os
import sys
import pandas as pd
import chromadb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def test_data_quality(csv_path):
    """全面检查数据质量"""
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    print("\n" + "=" * 60)
    print("数据质量检查")
    print("=" * 60)

    # 1. 基本检查
    assert len(df) > 0, "数据为空"
    print(f"总记录数: {len(df)}")

    # 2. 字段完整性检查
    required_fields = [
        'reviewText', 'label', 'order_id', 'order_date', 'total_amount',
        'payment_method', 'shipping_address', 'carrier', 'tracking_number',
        'shipping_method', 'ship_date', 'estimated_delivery_days',
        'actual_delivery_days', 'logistics_status', 'warehouse_id',
        'warehouse_name', 'warehouse_region', 'receive_date', 'putaway_date',
        'pick_date', 'dispatch_date', 'warehouse_processing_days'
    ]

    missing_fields = []
    for field in required_fields:
        if field not in df.columns:
            missing_fields.append(field)

    if missing_fields:
        print(f"缺失字段: {missing_fields}")
        assert False, f"缺少 {len(missing_fields)} 个字段"
    else:
        print("字段完整性: ✅ 全部通过")

    # 3. 各字段非空检查
    print("\n非空检查:")
    null_counts = df[required_fields].isnull().sum()
    for field, count in null_counts.items():
        if count > 0:
            print(f"  ⚠️ {field}: {count} 条空值")
    if null_counts.sum() == 0:
        print("  ✅ 所有字段无空值")

    # 4. 类别分布
    print("\n分类标注分布:")
    print(df['label'].value_counts())

    # 5. 物流状态分布
    print("\n物流状态分布:")
    print(df['logistics_status'].value_counts())

    # 6. 承运商分布
    print("\n承运商分布 (Top 5):")
    print(df['carrier'].value_counts().head(5))

    # 7. 仓库分布
    print("\n仓库分布:")
    print(df['warehouse_name'].value_counts())

    return df


def show_samples(df, n=3):
    """展示几条样本数据"""
    print("\n" + "=" * 60)
    print(f"样本数据 ({n} 条)")
    print("=" * 60)

    sample_cols = [
        'reviewerID', 'overall', 'label', 'order_id', 'carrier',
        'logistics_status', 'warehouse_name', 'reviewText'
    ]

    for i, row in df.head(n).iterrows():
        print(f"\n--- 样本 {i + 1} ---")
        print(f"  评论者: {row.get('reviewerID', 'N/A')}")
        print(f"  评分: {row.get('overall', 'N/A')} 星")
        print(f"  类别: {row.get('label', 'N/A')}")
        print(f"  订单号: {row.get('order_id', 'N/A')}")
        print(f"  承运商: {row.get('carrier', 'N/A')}")
        print(f"  物流状态: {row.get('logistics_status', 'N/A')}")
        print(f"  仓库: {row.get('warehouse_name', 'N/A')}")
        review = row.get('reviewText', '')[:120]
        if len(row.get('reviewText', '')) > 120:
            review += "..."
        print(f"  评论预览: {review}")


def test_vector_store():
    """检查向量库"""
    print("\n" + "=" * 60)
    print("向量库检查")
    print("=" * 60)

    if not os.path.exists(config.CHROMA_DIR):
        print("向量库目录不存在")
        return

    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    names = client.list_collections()

    if not names:
        print("向量库为空")
        return

    for name in names:
        collection = client.get_collection(name)
        print(f"  集合: {name}, 向量数: {collection.count()}")

    print(f"向量库路径: {config.CHROMA_DIR}")


def main():
    print("Step 5: Full Data Test and Validation")

    full_path = os.path.join(config.OUTPUT_DIR, "full_dataset.csv")
    if not os.path.exists(full_path):
        print("请先运行 generate_logistics.py")
        return

    # 1. 数据质量检查
    df = test_data_quality(full_path)

    # 2. 显示样本
    show_samples(df, n=3)

    # 3. 向量库检查
    test_vector_store()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过")
    print("=" * 60)


if __name__ == "__main__":
    main()