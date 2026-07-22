import os
import sys
import pandas as pd
import chromadb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def test_data_quality(csv_path):
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    assert len(df) > 0, "Data is empty"
    # 检查原有字段
    assert 'reviewText' in df.columns, "Missing reviewText column"
    assert 'label' in df.columns, "Missing label column"
    # 检查新增字段
    new_fields = ['order_id', 'order_date', 'carrier', 'tracking_number', 'shipping_method',
                  'estimated_delivery_days', 'logistics_status', 'warehouse_id', 'warehouse_name',
                  'receive_date', 'putaway_date', 'pick_date', 'dispatch_date']
    for field in new_fields:
        assert field in df.columns, f"Missing {field} column"

    print("Data quality check passed")
    print(f"Total records: {len(df)}")
    print(f"Label distribution:\n{df['label'].value_counts()}")
    # 打印物流状态分布
    print(f"Logistics status distribution:\n{df['logistics_status'].value_counts()}")


def test_vector_store():
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    collection_names = client.list_collections()
    assert len(collection_names) > 0, "Vector store is empty"
    for name in collection_names:
        collection = client.get_collection(name)
        print(f"Collection: {name}, Count: {collection.count()}")


def main():
    print("Step 5: Unit Tests and Validation")
    full_path = os.path.join(config.OUTPUT_DIR, "full_dataset.csv")
    if os.path.exists(full_path):
        test_data_quality(full_path)
    else:
        print("full_dataset.csv not found, skipping data quality test")
    if os.path.exists(config.CHROMA_DIR):
        test_vector_store()
    else:
        print("chroma_db not found, skipping vector store test")
    print("All available tests passed")


if __name__ == "__main__":
    main()