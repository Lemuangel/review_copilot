# AI差评驱动跨境运营 Copilot

AI驱动的差评分析、运营建议与客服回复生成系统（MVP版本）。

## 功能概述

| 模块 | 说明 |
|------|------|
| 📥 评论上传 | 上传 CSV 评论文件，自动清洗、入库 |
| 🔍 差评分析 | 调用 DeepSeek 大模型，识别问题分类（物流、包装、质量、尺寸等） |
| 💡 运营建议 | 基于分析结果，生成可落地的运营优化方案 |
| ✉️ 客服回复 | 针对差评自动生成专业、真诚的客服回复模板 |

## 技术栈

- **Web框架**: FastAPI
- **大模型**: DeepSeek（兼容 OpenAI SDK）
- **数据库**: SQLite（MVP阶段，可快速替换为 PostgreSQL）
- **ORM**: SQLAlchemy
- **数据验证**: Pydantic

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，填入你的 DeepSeek API Key
# MODEL_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 3. 启动服务

```bash
# 开发模式启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问接口文档

启动后访问：
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 项目结构

```
backend/
├── app/
│   ├── config.py                  # 应用配置（从.env加载）
│   ├── main.py                    # FastAPI入口，路由注册
│   ├── models.py                  # SQLAlchemy数据库模型
│   ├── schemas.py                 # Pydantic请求/响应模型
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py            # 数据库连接与会话管理
│   │   └── init_db.py             # 数据库初始化脚本
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── review.py              # 评论上传接口
│   │   ├── analysis.py            # 差评分析接口
│   │   └── customer.py            # 客服回复接口
│   ├── services/
│   │   ├── __init__.py
│   │   ├── review_service.py      # 评论处理服务（CSV解析、清洗）
│   │   ├── ai_service.py          # DeepSeek大模型调用封装
│   │   └── prompt_service.py      # Prompt模板管理
│   └── utils/
│       ├── __init__.py
│       └── text_clean.py          # 文本清洗工具
├── .env.example                   # 环境变量示例
├── requirements.txt               # Python依赖
└── README.md                      # 项目说明
```

## API 接口

### `POST /reviews/upload`
上传 CSV 评论文件。

**请求**: `multipart/form-data`
- `file`: CSV 文件（必填）

**响应**:
```json
{
  "total_rows": 100,
  "imported_count": 95,
  "message": "成功处理 95/100 条评论"
}
```

### `POST /analysis/review`
分析一条差评，返回问题分类和优化建议。

**请求**:
```json
{
  "review_text": "物流太慢了，等了两个星期才收到，包装也破了..."
}
```

**响应**:
```json
{
  "issues": ["物流问题", "包装问题"],
  "suggestions": ["更换物流服务商，优先使用DHL/FedEx", "升级包装材料，增加防震填充物"]
}
```

### `POST /customer/reply`
基于差评生成客服回复。

**请求**:
```json
{
  "review_text": "质量太差了，穿一次就坏了，完全不值这个价！"
}
```

**响应**:
```json
{
  "reply_text": "亲爱的客户，非常抱歉给您带来了不愉快的购物体验...我们已为您安排全额退款..."
}
```

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MODEL_API_KEY` | 大模型 API Key（必填） | - |
| `MODEL_BASE_URL` | 大模型 API 地址 | `https://api.deepseek.com` |
| `MODEL_NAME` | 模型名称 | `deepseek-chat` |
| `DEBUG` | 调试模式 | `false` |
| `DATABASE_URL` | 数据库连接地址 | `sqlite:///./app.db` |
| `AI_MAX_TOKENS` | AI 最大输出 Token | `2000` |
| `AI_TEMPERATURE` | AI 生成温度 | `0.3` |

## 下一步计划

- [ ] 完善用户认证
- [ ] 支持更多文件格式（Excel、JSON）
- [ ] 批量分析优化
- [ ] 分析结果仪表盘
- [ ] 支持多种大模型切换
