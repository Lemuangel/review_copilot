# 差评驱动跨境电商Copilot

## 一、项目概述

### 1.1 项目背景
跨境电商运营中，差评管理是核心痛点。一条差评可能涉及产品质量、物流时效、仓储操作、Listing描述、客服响应等多个环节，运营人员难以快速定位根因。传统人工处理方式效率低下，且容易遗漏关键问题。

### 1.2 项目目标
构建一款AI驱动的差评分析工具，实现：
自动整合多平台差评数据，关联订单、物流、仓储全链路信息，从8个维度智能分析差评根因，自动生成多语言客服回复话术和运营优化建议，提供可视化仪表盘，宏观掌握差评态势。

### 1.3 核心价值
将一条孤立差评还原为完整业务链路，精准定位问题出在物流、产品、描述还是服务环节，帮助运营从"被动查看"升级为"主动解决"。
## 二、核心功能

| 功能模块 | 说明 |
|:---|:---|
| 差评数据导入 | 支持 CSV 文件上传，自动清洗、翻译、入库 |
| 多维度根因分析 | 从产品、物流、描述、客服、仓储、客户画像、运营上下文、外部环境 8 个维度定位差评根因 |
| AI 客服回复 | 基于差评内容自动生成多语言（中/英）客服回复话术 |
| 运营优化建议 | AI 给出供应链、客服、Listing 优化等改进建议 |
| 数据仪表盘 | KPI 指标卡片、差评趋势、类别分布饼图、高频词云 |
| 全链路上下文 | 单条差评关联订单、物流轨迹、仓库操作、Listing 快照 |

## 三、技术架构

|  层级   | 技术栈 |
|:------|:---|
| 前端    | Vue 3 + Element Plus + ECharts + Axios |
| 后端    | Python FastAPI + SQLAlchemy + Pydantic |
| AI 引擎 | LangChain + DeepSeek 大模型 + BGE-M3 向量模型 |
| 业务数据库 | MySQL |
| 向量数据库 | Chroma |


## 四、项目结构

```
review_copilot/
├── ai_module/                   # AI 引擎：Prompt 模板、LangChain 链、Agent 工具、向量检索
│   ├── app/
│   │   ├── angent.py            # agent智能体
│   │   ├── config.py            # AI模块配置
│   │   ├── data_loader.py       # 数据加载模块
│   │   ├── generator.py         # DeepSeek 调用封装  
│   │   ├── prompt_ab.py         # Prompt 版本管理与 A/B 测试框架
│   │   ├── prompts.py           # 分析/回复/建议 Prompt
│   │   ├── translation_eval.py  # 翻译质量评估模块
│   │   └── vector_store.py      # RAG 向量数据库模块
│   └── requirements.txt 
├── backend/                     # 后端：FastAPI 接口、业务逻辑、数据库操作
│   ├── app/
│   │   ├── main.py              # 应用入口
│   │   ├── config.py            # 配置管理
│   │   ├── models.py            # 数据库 ORM 模型
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── routers/             # 接口路由
│   │   │   ├── review.py        # 评论管理接口
│   │   │   ├── analysis.py      # 差评分析接口
│   │   │   └── customer.py      # 客服回复接口
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── review_service.py # 评论处理服务
│   │   │   ├── analysis_service.py # 业务编排服务 — 分析 + 建议 + 回复全流程
│   │   │   ├── prompt_service.py # Prompt 模板服务
│   │   │   └── ai_service.py  # AI 大模型调用服务
│   │   ├── database/database.py # 数据库连接与初始化     
│   │   └── utils/text_clean.py  # 文本清洗工具       
│   └── requirements.txt
├── frontend/                    # 前端：Vue 3 单页应用
│   └──  src/
│       ├── api/review.js        # 后端接口封装
│       ├── router/index.js      # 路由配置
│       ├── views/view.vue       # 主页面（仪表盘+分析+图表）
│       ├── request.js           # Axios 实例
│       └── data.js              # Mock 数据（开发用）
├── data/                        # 数据测试：采集、清洗、模拟、向量化
│   └── scripts/
│       ├── load_and_clean.py    # 数据加载与清洗
│       ├── label_data.py        # 自动标注分类
│       ├── vectorize.py         # 向量化入库
│       ├── generate_logistics.py # 模拟物流数据
│       └── test_utils.py        # 单元测试与验证
└── README.md
```
## 五、数据库设计
### 5.1 ER图关系
```` mermaid
erDiagram
    product ||--o{ reviews : "1:N"
    product ||--o{ orders : "1:N"
    reviews ||--o| orders : "1:1"
    orders ||--o{ logistics : "1:N"
    orders ||--o{ warehouse_operations : "1:N"
    warehouse ||--o{ warehouse_operations : "1:N"
    warehouse ||--o{ inventory : "1:N"
    product ||--o{ inventory : "1:N"
    reviews ||--o| analysis_result : "1:1"
    analysis_result ||--o{ suggestion : "1:N"
    reviews ||--o{ customer_reply : "1:N"
````
### 5.2 关系表设计
reviews评论表

| 字段            | 类型	         | 说明    |
|---------------|-------------|-------|
| review_id     | INT PK	    | 评论ID  |
| product_id    | INT         | 产品ID  |
| order_id      | INT         | 订单ID  |
| reviewer_id   | VARCHAR     | 评论用户ID |
| reviewer_name | VARCHAR     | 评论用户名 |
| asin          | VARCHAR     | 商品编号  |
| rating        | INT         | 评分    |
| review_text   | TEXT        | 评论文本  |
| summary       | TEXT        | 评论总结  |
| language      | VARCHAR(20) | 语言    |
| review_time   | DATETIME    | 评论时间  |
| label         | VARCHAR(50) | 评论标签  |

orders订单表

| 字段                | 类型            | 说明        |
|-------------------|---------------|-----------|
| order_id          | INT PK        | 订单ID      |
| order_code        | VARCHAR(50)   | 订单号       |
| product_id        | INT           | 产品ID      |
| warehouse_id      | INT           | 仓库ID      |
| customer_country  | VARCHAR(50)   | 用户国籍      |
| shipping_address  | VRACHAR(100)  | 出发国——目的国  |
| quantity          | INT           | 数量        |
| total_amount      | decimal(10,2) | 总金额       |
| payment_method    | VARCHAR(50)   | 支付方式      |
| order_status      | VARCHAR(50)   | 订单状态      |
| order_time        | DATETIME      | 下单时间      |

logistics物流事件表

| 字段                        | 类型          | 说明     |
|---------------------------|-------------|--------|
| logistics_id              | INT PK      | 事件ID   |
| order_id                  | INT         | 订单ID   |
| carrier                   | VARCHAR(50) | 承运公司   |
| tracking_number           | VARCHAR(50) | 物流单号   |
| shipping_method           | VARCHAR(50) | 运输方式   |
| shipping_status           | VARCHAR(50) | 物流状态   |
| shipping_time             | DATETIME    | 发货时间   |
| delivery_time             | DATETIME    | 妥投时间   |
| estimated_delivery_days   | INT         | 预计送达天数 |
| delay_days                | INT         | 延误天数   |
| exception_reason          | VARCAHR(50) | 延误原因   |
| receive_date              | DATETIME    | 仓库收货时间 |
| putaway_date              | DATETIME    | 上架时间   |
| pick_date                 | DATETIME    | 拣货时间   |
| dispatch_date             | DATETIME    | 出库时间   |
| warehouse_processing_days | INT         | 仓库处理时间 |


warehouse仓库表

| 字段              | 类型          | 说明   |
|-----------------|-------------|------|
| warehouse_id    | INT PK      | 仓库ID |
| warehouse_code  | VARCHAR(50) | 仓库编码 |
| warehouse_name  | VARCHAR(50) | 仓库名  |
| location        | VARCHAR(50) | 地点   |
| region          | VARCHAR(50) | 地区   |
| capacity        | INT         | 容量   |
| created_time    | DATETIME    | 建立时间 |

product产品表
		
| 字段           | 类型            | 说明   |
|--------------|---------------|------|
| product_id   | INT PK        | 产品ID |
| product_name | VARCHAR(50)   | 产品名  |
| category     | VARCHAR(50)   | 类型   |
| price        | DECIMAL(10,2) | 价格   |
| supplier     | VARCHAR(50)   | 供应商  |
| asin         | VARCHAR(50)   | 商品编号 |
| created_time | DATETIME      | 上架时间 |

inventory库存表

| 字段                 | 类型       | 说明     |
|--------------------|----------|--------|
| inventory_id       | INT PK   | 库存记录ID |
| warehouse_id       | INT      | 仓库ID   |
| product_id         | INT      | 产品ID   |
| stock_quantity     | INT      | 库存总量   |
| available_quantity | INT      | 剩余库存量  |
| update_time        | DATETIME | 更新时间   |

suggestion建议生成记录表

| 字段              | 类型          | 说明     |
|-----------------|-------------|--------|
| suggestion_id   | INT PK      | 建议记录ID |
| analysis_id     | INT         | 分析记录ID |
| suggestion_text | TEXE        | 建议内容   |
| priority        | VARCHAR(50) | 优先级    |
| created_time    | DATETIME    | 创建时间   |

customer_repay回复生成记录表

| 字段              | 类型       | 说明   |
|-----------------|----------|------|
| reply_id        | INT PK   | 回复ID |
| review_id       | INT      | 评论ID |
| reply_content   | TEXT     | 回复内容 |
| language        | VARCHAR  | 回复语言 |
| created_time    | DATETIME | 创建时间 |

analysis_result分析记录表

| 字段           | 类型          | 说明    |
|--------------|-------------|-------|
| analysis_id  | INT PK      | 分析ID  |
| review_id    | INT         | 评论ID  |
| issue_type   | VARCHAR(50) | 问题分类  |
| issue_detail | TEXT        | 问题详情  |
| severity     | VARCHAR(50) | 严重程度  |
| created_time | DATETIME    | 生成时间  |


 
## 六、快速启动

### 1. 环境要求

- Python 3.12+
- Node.js 18+
- MySQL 8.0+
- Git

### 2. 克隆项目

```bash
git clone git@github.com:Lemuangel/review_copilot.git
cd review_copilot
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要配置：

```ini
# MySQL 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_NAME=review_copilot

# DeepSeek API
DEEPSEEK_API_KEY=你的API密钥

# Chroma 向量数据库
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

### 4. 安装依赖

```bash
# 后端
pip install -r backend/requirements.txt

# AI 引擎
pip install -r ai_module/requirements.txt

# 数据处理
pip install -r data/requirements.txt

# 前端
cd frontend && npm install --legacy-peer-deps && cd ..
```

### 5. 初始化数据库

```bash
# 创建数据库（MySQL 命令行）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS ai_review_copilot DEFAULT CHARSET utf8mb4;"

# 创建表结构
cd backend
python -c "from app.models import Base; from app.database.database import engine; Base.metadata.create_all(engine); print('表结构创建成功')"
cd ..
```

### 6. 导入数据

```bash
python scripts/load_and_clean.py
python scripts/label_data.py
python scripts/vectorize.py
python scripts/generate_logistics.py
python scripts/test_utils.py
```

### 7. 启动服务

需要同时启动 **4 个终端窗口**：

| 终端 | 命令 | 端口 |
|:---|:---|:---|
| Chroma | `chroma run --host localhost --port 8000` | 8000 |
| 后端 | `cd backend && uvicorn app.main:app --reload --port 8001` | 8001 |
| 前端 | `cd frontend && npm run dev` | 5173 |
| MySQL | 系统服务，开机自启 | 3306 |

### 8. 访问系统

- **前端页面**：http://localhost:5173
- **后端 API 文档**：http://localhost:8000/docs

## 七、API 接口说明

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/reviews` | 差评列表（分页，参数 `page`、`size`） |
| GET | `/reviews/{id}` | 单条差评详情 |
| GET | `/reviews/{id}/context` | 全链路上下文（订单+物流+仓储） |
| GET | `/reviews/statistics` | 仪表盘统计数据（总数、星级分布、类别分布） |
| POST | `/reviews/upload` | 上传 CSV 文件导入差评 |
| POST | `/reviews/generate` | AI 生成回复/建议（参数 `review_id`、`type`） |
| GET | `/reviews/wordcloud` | 词云数据 |

## 八、团队分工

| 角色    | 负责人 | 核心职责 |
|:------|:----|:---|
| 组长    | 罗裕城 | 项目管理、架构设计、代码合并与版本管理 |
| 后端    | 白诗雨 | FastAPI 接口开发、数据库设计、AI 引擎集成 |
| 前端    | 刘欣怡 | Vue 页面开发、ECharts 图表、API 对接 |
| AI 引擎 | 张竣翔 | Prompt 工程、LangChain 链构建、向量检索 |
| 数据测试  | 沈东阳 | 数据采集清洗、模拟数据生成、单元测试 |

