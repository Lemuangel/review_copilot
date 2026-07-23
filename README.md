# amazon_dataset 项目说明文档


## 一、项目概述

amazon_dataset 是竞品情报智能分析系统的数据测试模块，负责对 Amazon Computers 类别评论数据进行全流程处理，包括数据清洗、LLM 自动分类标注、向量化入库、真实感物流与仓储数据生成。最终输出一份“一评论一订单”的完整数据集，用于定位差评根因（物流/仓储/产品/描述等环节）。


## 二、数据来源

| 项目 | 内容 |
| :--- | :--- |
| 数据源 | UCSD Amazon Review Dataset 2018 |
| 类别 | Computers |
| 原始文件 | Computers.json |
| 原始格式 | JSON Lines |
| 加载条数 | 100 条（样本） |


## 三、各脚本功能说明

| 脚本文件 | 功能说明 | 输入 | 输出 |
| :--- | :--- | :--- | :--- |
| **load_and_clean.py** | 加载原始数据，清洗无效记录，去除重复项，过滤短文本 | Computers.json | cleaned_reviews.csv |
| **label_data.py** | 随机抽样，调用 DeepSeek LLM 进行六分类标注（Logistics / ProductQuality / DescriptionMismatch / Price / CustomerService / Other） | cleaned_reviews.csv | labeled_reviews.csv |
| **vectorize.py** | 构建结构化内容（评分 + 类别 + 标题 + 正文），使用 bge-m3 向量化，存入 Chroma | labeled_reviews.csv | chroma_db/ |
| **generate_logistics.py** | 为每条评论生成一一对应的订单、物流、仓储全链路数据（含承运商、仓库、时效、异常模拟） | labeled_reviews.csv | full_dataset.csv |
| **test_utils.py** | 全面测试数据完整性、字段非空、分类分布、物流分布，并输出样本预览 | full_dataset.csv + chroma_db/ | 测试报告 |


## 四、执行顺序

```bash
python scripts/load_and_clean.py
python scripts/label_data.py
python scripts/vectorize.py
python scripts/generate_logistics.py
python scripts/test_utils.py
```

## 五、输出文件清单

| 文件 | 内容 | 说明 |
| :--- | :--- | :--- |
| `cleaned_reviews.csv` | 清洗后评论数据 | 不含标签，仅差评 |
| `labeled_reviews.csv` | LLM 六分类标注后数据 | 含 `label` 列 |
| `full_dataset.csv` | 完整数据集 | 含订单、物流、仓储字段 |
| `chroma_db/` | 向量库 | 存储差评向量 |


## 六、数据结果统计（基于当前 100 条样本）

### 分类标注分布（LLM）

| 类别 | 数量 |
| :--- | :--- |
| ProductQuality | 80 |
| DescriptionMismatch | 15 |
| Other | 2 |
| Price | 1 |
| Logistics | 1 |
| CustomerService | 1 |

### 物流状态分布

| 状态 | 数量 |
| :--- | :--- |
| Delivered | 77 |
| In Transit | 14 |
| Exception | 9 |


## 七、分类类别说明

| 类别 | 含义 |
| :--- | :--- |
| **Logistics** | 物流问题：配送延迟、丢包、包装破损 |
| **ProductQuality** | 产品质量：功能失效、不耐用、做工差 |
| **DescriptionMismatch** | 描述不符：尺寸/颜色/功能与页面不一致 |
| **Price** | 价格问题：定价过高、性价比低 |
| **CustomerService** | 客服问题：售后响应慢、退货困难 |
| **Other** | 不属于以上任何类别 |