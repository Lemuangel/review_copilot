# amazon_dataset 项目说明文档


## 一、项目概述

amazon_dataset 是竞品情报智能分析系统的数据测试模块，负责对 Amazon Computers 类别评论数据进行全流程处理，包括数据清洗、向量化入库、分类标注、物流与仓储数据生成，为后续竞品情报分析提供标准化的测试数据集。

## 二、数据来源

| 项目 | 内容                              |
| :--- |:--------------------------------|
| 数据源 | UCSD Amazon Review Dataset 2018 |
| 类别 | Computers                       |
| 原始文件 | Computers.json                  |
| 原始格式 | JSON Lines                      |
| 加载条数 | 10,000 条                        |


## 三、各脚本功能说明

| 脚本文件 | 功能说明 | 输入 | 输出 |
| :--- | :--- | :--- | :--- |
| **load_and_clean.py** | 加载原始数据，清洗无效记录，去除重复项，过滤短文本 | Computers.json | cleaned_reviews.csv |
| **vectorize.py** | 筛选差评，文本分块，使用 bge-m3 模型向量化，存入 Chroma | cleaned_reviews.csv | chroma_db/ |
| **label_data.py** | 基于关键词匹配自动标注类别（Price/Product/Sentiment/Other） | cleaned_reviews.csv | labeled_reviews.csv |
| **generate_logistics.py** | 生成订单、物流、仓储全链路数据 | labeled_reviews.csv | full_dataset.csv |
| **test_utils.py** | 运行单元测试，验证数据完整性和向量库可用性 | full_dataset.csv + chroma_db/ | 测试报告 |


## 四、执行顺序

```bash
python scripts/load_and_clean.py
python scripts/vectorize.py
python scripts/label_data.py
python scripts/generate_logistics.py
python scripts/test_utils.py
```

## 五、输出文件清单

| 文件 | 内容 | 条数 | 说明 |
| :--- | :--- | :--- | :--- |
| `cleaned_reviews.csv` | 清洗后评论数据 | 8,092 | 去重并过滤短文本 |
| `labeled_reviews.csv` | 带分类标签数据 | 8,092 | 含 Price/Product/Sentiment/Other 标签 |
| `full_dataset.csv` | 完整数据集 | 8,092 | 含订单、物流、仓储信息 |
| `chroma_db/` | 向量库 | 1,668 | 基于差评文本生成 |


## 六、数据结果统计

### 分类标注分布

| 类别 | 数量 | 占比 |
| :--- | :--- | :--- |
| Other | 4,636 | 57.3% |
| Price | 1,792 | 22.1% |
| Sentiment | 949 | 11.7% |
| Product | 715 | 8.8% |

### 物流状态分布

| 状态 | 数量 | 占比 |
| :--- | :--- | :--- |
| Delivered | 6,129 | 75.7% |
| In Transit | 1,526 | 18.9% |
| Exception | 437 | 5.4% |


## 七、分类类别说明

| 类别 | 含义 |
| :--- | :--- |
| **Price** | 涉及定价、折扣、促销、性价比、涨价降价等价格因素 |
| **Product** | 涉及新品发布、功能迭代、版本更新、技术升级等产品信息 |
| **Sentiment** | 包含负面反馈、投诉抱怨、质量问题、失望情绪等情感表达 |
| **Other** | 不匹配以上三类或评价偏向中性的评论 |