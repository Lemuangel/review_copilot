"""
LangChain 服务 — PromptTemplate + LCEL Chain + 输出解析器

本文件作为 LangChain 的独立封装层，展示：
1. PromptTemplate 定义与复用
2. LCEL (|) 链式调用
3. 自定义输出解析器
4. LLMChain 兼容模式（教学保留）

与 ai_service.py 的区别：
    - ai_service.py: 实际业务调用的轻量封装
    - langchain_service.py: LangChain 完整能力展示层
"""

import json
import re
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.config import settings

logger = logging.getLogger(__name__)

# =========================================================================
# 统一 LLM 实例
# =========================================================================

def get_langchain_llm() -> ChatOpenAI:
    """获取 LangChain ChatOpenAI 实例"""
    if not settings.MODEL_API_KEY:
        raise ValueError("MODEL_API_KEY 未配置")

    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.MODEL_API_KEY,
        base_url=settings.MODEL_BASE_URL,
        temperature=settings.AI_TEMPERATURE,
        max_tokens=settings.AI_MAX_TOKENS,
    )


# =========================================================================
# 自定义 JSON 输出解析器
# =========================================================================

class JsonOutputParser(BaseOutputParser[dict]):
    """
    将模型文本输出解析为 Python dict。

    自动处理：
    - 直接 JSON
    - ```json ... ``` 包裹的 JSON
    - 嵌入文本中的 { ... }
    """

    def parse(self, text: str) -> dict:
        # 尝试1：直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试2：去除 markdown 标记
        cleaned = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 尝试3：正则提取
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法解析为 JSON: {text[:300]}")

    @property
    def _type(self) -> str:
        return "json_output_parser"


# =========================================================================
# PromptTemplate 定义
# =========================================================================

REVIEW_ANALYSIS_TEMPLATE = PromptTemplate(
    input_variables=["review_text"],
    template="""你是一位资深的跨境电商运营专家。请分析以下用户差评，识别出产品存在的问题。

## 分析维度
- 产品质量、包装问题、物流问题、尺寸问题、色差问题、功能问题、售后问题、价格问题

## 输出格式（纯JSON，无markdown标记）
{{
    "issues": ["问题1", "问题2"],
    "sentiment": "negative",
    "severity": "high|medium|low"
}}

## 用户评论
{review_text}

请分析：""",
)

CUSTOMER_REPLY_TEMPLATE = PromptTemplate(
    input_variables=["review_text", "language"],
    template="""你是一位专业的跨境电商客服代表。请撰写专业、真诚的客服回复。

## 要求
- 先致歉和理解
- 给出具体解决方案
- 150字以内
- 使用{language}

## 差评
{review_text}

## 输出（纯JSON，无markdown标记）
{{
    "reply": "回复文本"
}}""",
)

OPERATION_SUGGESTION_TEMPLATE = PromptTemplate(
    input_variables=["review_text", "issues"],
    template="""你是一位资深的跨境电商运营顾问。基于差评分析结果，请给出具体可落地的运营优化建议。

## 已知问题
{issues}

## 原始评论
{review_text}

## 要求
- 每条建议要具体、可执行
- 区分短期可解决的（1-2周）和长期改进的（1-3个月）
- 考虑成本和实施难度

## 输出（纯JSON，无markdown标记）
{{
    "suggestions": ["建议1", "建议2"],
    "priority": ["高", "中"],
    "estimated_impact": "高|中|低"
}}

请给出建议：""",
)

# ChatPromptTemplate 版本（System + Human 消息分离）
REVIEW_ANALYSIS_CHAT_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "你是一位资深的跨境电商运营专家，擅长分析用户差评。"
        "请以纯JSON格式返回结果，不要包含任何markdown代码块标记。"
    ),
    HumanMessagePromptTemplate.from_template(
        "请分析以下差评：\n{review_text}"
    ),
])


# =========================================================================
# LCEL 链定义
# =========================================================================

def create_review_analysis_chain():
    """
    创建差评分析 LCEL 链。

    Chain: PromptTemplate | ChatOpenAI | StrOutputParser | JsonOutputParser
    """
    llm = get_langchain_llm()
    return (
        REVIEW_ANALYSIS_TEMPLATE
        | llm
        | StrOutputParser()
        | JsonOutputParser()
    )


def create_customer_reply_chain():
    """
    创建客服回复 LCEL 链。

    Chain: PromptTemplate | ChatOpenAI | StrOutputParser | JsonOutputParser
    """
    llm = get_langchain_llm()
    return (
        CUSTOMER_REPLY_TEMPLATE
        | llm
        | StrOutputParser()
        | JsonOutputParser()
    )


def create_suggestion_chain():
    """
    创建运营建议 LCEL 链。

    Chain: PromptTemplate | ChatOpenAI | StrOutputParser | JsonOutputParser
    """
    llm = get_langchain_llm()
    return (
        OPERATION_SUGGESTION_TEMPLATE
        | llm
        | StrOutputParser()
        | JsonOutputParser()
    )


def create_chat_analysis_chain():
    """
    创建 ChatPromptTemplate 版本的 LCEL 链。

    展示 SystemMessage + HumanMessage 分离的 Prompt 结构。
    """
    llm = get_langchain_llm()
    return (
        REVIEW_ANALYSIS_CHAT_PROMPT
        | llm
        | StrOutputParser()
        | JsonOutputParser()
    )


# =========================================================================
# 便捷调用函数
# =========================================================================

def analyze_with_lcel(review_text: str) -> dict:
    """
    使用 LCEL 链分析差评。

    返回:
        {"issues": [...], "sentiment": "...", "severity": "..."}
    """
    chain = create_review_analysis_chain()
    result = chain.invoke({"review_text": review_text})
    logger.debug("LCEL 分析结果: %s", result)
    return result


def reply_with_lcel(review_text: str, language: str = "中文") -> dict:
    """
    使用 LCEL 链生成客服回复。

    返回:
        {"reply": "客服回复文本"}
    """
    chain = create_customer_reply_chain()
    result = chain.invoke({"review_text": review_text, "language": language})
    logger.debug("LCEL 回复结果: %s", result)
    return result


def suggest_with_lcel(review_text: str, issues: list[str]) -> dict:
    """
    使用 LCEL 链生成运营建议。

    参数:
        review_text: 原始评论
        issues:      已识别的问题列表

    返回:
        {"suggestions": [...], "priority": [...], "estimated_impact": "..."}
    """
    issues_str = "\n".join(f"- {issue}" for issue in issues)
    chain = create_suggestion_chain()
    result = chain.invoke({"review_text": review_text, "issues": issues_str})
    logger.debug("LCEL 建议结果: %s", result)
    return result


# =========================================================================
# LLMChain 兼容模式（教学保留）
# =========================================================================

def analyze_with_legacy_llmchain(review_text: str) -> dict:
    """
    使用 LLMChain 传统模式分析差评（LangChain 1.x 已移除 LLMChain 类）。

    此函数手动模拟 LLMChain 的经典三步：
        prompt.format() → llm.invoke() → output_parser.parse()

    教学目的：理解 LLMChain 的底层行为。
    生产环境请使用 create_review_analysis_chain() 返回的 LCEL 链。
    """
    llm = get_langchain_llm()
    parser = JsonOutputParser()

    # Step 1: 渲染 Prompt
    formatted = REVIEW_ANALYSIS_TEMPLATE.format(review_text=review_text)

    # Step 2: 调用 LLM
    response = llm.invoke(formatted)
    text = response.content if hasattr(response, "content") else str(response)

    # Step 3: 解析输出
    return parser.parse(text)
