"""
LangChain Agent + 工具模块

提供 4 个 Tool 供 Agent 调度：
1. analyze_review_tool: 分析8大维度
2. rag_retrieve_tool: 查询向量库获取相似案例策略
3. generate_reply_tool: 生成多语言回复
4. get_logistics_tool: 查询订单物流状态

所有重依赖（langchain.agents, langchain_core.tools）均 Lazy 导入。
"""
from __future__ import annotations

import json
from typing import Dict, Optional, TYPE_CHECKING

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from app.generator import (
    analyze_review,
    generate_reply,
    get_logistics_status,
    translate_to_english,
    LOGISTICS_STATUSES,
)
from app.vector_store import get_vector_store
from app.prompts import format_rag_context


# ============================================================
# 1. 初始化 LLM（供 Agent 使用）
# ============================================================
def init_agent_llm(temperature: float = 0.3):
    """初始化 Agent 使用的 LLM"""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        openai_api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
    )


# ============================================================
# 2. Agent 创建（包含所有 Tool 的 Lazy 定义）
# ============================================================
def create_review_agent():
    """
    创建差评分析 Agent，所有 Tool 在函数内部 Lazy 构建。

    Agent 会根据用户输入自主决定调用哪些工具，完成：
    - 差评分析 → 调用 analyze_review_tool
    - 历史案例检索 → 调用 rag_retrieve_tool
    - 物流状态查询 → 调用 get_logistics_tool
    - 回复文案生成 → 调用 generate_reply_tool
    """
    from langchain_core.tools import tool
    from langchain.agents import create_agent

    # --- Tool 1: 差评分析 ---
    @tool
    def analyze_review_tool(review_json: str) -> str:
        """
        对差评进行8维度结构化分析。
        输入: review_json (JSON字符串，包含 asin, reviewText, overall, summary, style, category, country)
        输出: 8维评分、根因分析、紧急程度、标签
        """
        try:
            review_data = json.loads(review_json)
            result = analyze_review(review_data, use_rag=False)
            return json.dumps(result["analysis"], ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # --- Tool 2: RAG 检索 ---
    @tool
    def rag_retrieve_tool(query: str, top_k: int = 3) -> str:
        """
        从向量库中检索与当前差评最相似的历史案例及处理策略。
        输入: query (差评内容或关键词), top_k (结果数量，默认3)
        输出: 相似案例列表，含相似度评分
        """
        try:
            vs = get_vector_store()
            results = vs.similarity_search(query, k=top_k)
            if not results:
                return json.dumps({"found": False, "message": "未找到相似案例", "cases": []}, ensure_ascii=False)
            cases = []
            for doc, score in results:
                cases.append({
                    "similarity": round(score, 4),
                    "asin": doc.metadata.get("asin", ""),
                    "overall": doc.metadata.get("overall", 0),
                    "content": doc.page_content[:300],
                    "review_time": doc.metadata.get("review_time", ""),
                })
            return json.dumps({"found": True, "count": len(cases), "cases": cases}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # --- Tool 3: 回复生成 ---
    @tool
    def generate_reply_tool(input_json: str) -> str:
        """
        根据分析结果生成多语言客服回复文案。
        输入: input_json (包含 analysis_result, review_text, target_language)
        输出: 回复文案 JSON (subject, body, tone, compensation_suggestion)
        """
        try:
            data = json.loads(input_json)
            reply = generate_reply(
                analysis_result=data.get("analysis_result", {}),
                review_text=data.get("review_text", ""),
                target_language=data.get("target_language", "en"),
            )
            return json.dumps(reply, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # --- Tool 4: 物流查询 ---
    @tool
    def get_logistics_tool(tracking_info: str) -> str:
        """
        查询订单最新物流状态（从评论文本推断）。
        输入: tracking_info (评论文本或物流单号)
        输出: 物流状态 (delivered/in_transit/abnormal/unknown) 及处理建议
        """
        try:
            status = get_logistics_status(tracking_info)
            return json.dumps({
                "status": status,
                "description": LOGISTICS_STATUSES.get(status, "未知状态"),
                "actions": {
                    "delivered": "核实包裹信息，安抚买家，询问是否接受补偿",
                    "in_transit": "致歉并主动提供售后保障承诺",
                    "abnormal": "直接引导客服人工介入处理",
                    "unknown": "建议人工联系买家确认物流状态",
                }.get(status, ""),
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    llm = init_agent_llm(temperature=0.3)
    tools = [analyze_review_tool, rag_retrieve_tool, generate_reply_tool, get_logistics_tool]

    system_prompt = """你是一个跨境电商差评处理助手。

你的工作流程：
1. 收到差评后，先调用 analyze_review_tool 进行8维分析
2. 调用 rag_retrieve_tool 检索历史相似案例的处理策略
3. 如果差评涉及物流问题，调用 get_logistics_tool 查询物流状态
4. 最后调用 generate_reply_tool 生成客服回复文案

对于非物流类差评，跳过物流查询步骤。
请用中文回复用户，但生成的回复文案应使用买家语言。"""

    return create_agent(llm=llm, tools=tools, system_prompt=system_prompt)


# ============================================================
# 7. 全局 Agent 实例
# ============================================================
_agent_instance = None


def get_agent():
    """获取全局 Agent 实例"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_review_agent()
    return _agent_instance