"""
⚠️ 已废弃 — AI 调用已迁移至同学的 ai_module（analyze_review + generate_reply）

LangChain 服务 — LCEL Chain + 输出解析器
保留作为教学参考。
"""

import json
import re
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser

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
# PromptTemplate — 统一从 prompt_service.py 引用，避免重复定义
# =========================================================================

from app.services.prompt_service import (
    review_analysis_prompt,
    operation_suggestion_prompt,
    customer_reply_prompt,
)

# ChatPromptTemplate 版本（System + Human 消息分离，教学保留）
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
    """差评分析 LCEL 链。Prompt 引用 prompt_service.review_analysis_prompt"""
    llm = get_langchain_llm()
    return (
        review_analysis_prompt
        | llm
        | StrOutputParser()
        | JsonOutputParser()
    )


def create_customer_reply_chain():
    """客服回复 LCEL 链。Prompt 引用 prompt_service.customer_reply_prompt"""
    llm = get_langchain_llm()
    return (
        customer_reply_prompt
        | llm
        | StrOutputParser()
        | JsonOutputParser()
    )


def create_suggestion_chain():
    """运营建议 LCEL 链。Prompt 引用 prompt_service.operation_suggestion_prompt"""
    llm = get_langchain_llm()
    return (
        operation_suggestion_prompt
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

def analyze_with_lcel(review_text: str, context_text: str = "") -> dict:
    """
    使用 LCEL 链分析差评。

    参数:
        review_text:  差评原文
        context_text: 业务上下文（订单+物流+仓储+库存），可选

    返回:
        {"issues": [...], "root_cause": "...", "evidence": [...], "sentiment": "...", "severity": "..."}
    """
    chain = create_review_analysis_chain()
    ctx = context_text if context_text.strip() else "暂无全链路数据，请仅基于评论内容分析。"
    result = chain.invoke({"review_text": review_text, "context_text": ctx})
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


def suggest_with_lcel(review_text: str, issues: list[str], context_text: str = "") -> dict:
    """
    使用 LCEL 链生成运营建议。

    参数:
        review_text:  原始评论
        issues:       已识别的问题列表
        context_text: 业务上下文，可选

    返回:
        {"suggestions": [...], "priority": [...], "estimated_impact": "..."}
    """
    issues_str = "\n".join(f"- {issue}" for issue in issues)
    ctx = context_text if context_text.strip() else "暂无全链路数据。"
    chain = create_suggestion_chain()
    result = chain.invoke({"review_text": review_text, "issues": issues_str, "context_text": ctx})
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
    formatted = review_analysis_prompt.format(review_text=review_text, context_text="")

    # Step 2: 调用 LLM
    response = llm.invoke(formatted)
    text = response.content if hasattr(response, "content") else str(response)

    # Step 3: 解析输出
    return parser.parse(text)
