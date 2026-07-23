"""
Prompt 模板模块

包含：
1. 8维差评分析 Prompt
2. 多语言翻译 Prompt
3. 客服回复生成 Prompt
4. RAG 增强 Prompt

ChatPromptTemplate 在函数内部 Lazy 导入，避免拖慢启动。
"""


# ============================================================
# 1. 8维差评分析 Prompt
# ============================================================
REVIEW_ANALYSIS_SYSTEM = """你是一个专业的跨境电商差评分析师。请对以下差评进行多维度分析，输出结构化 JSON。

## 评分维度（每个维度 1-10 分，1分最差，10分最好）：

1. **商品质量 (product_quality)**: 产品本身的质量，如材质、做工、耐用性
2. **物流时效 (logistics_speed)**: 配送速度、是否准时到达
3. **包装完好度 (packaging)**: 包装是否完好，有无破损
4. **描述相符度 (description_match)**: 实物与页面描述是否一致（尺寸/颜色/功能等）
5. **客服态度 (customer_service)**: 客服响应速度、解决问题的能力
6. **性价比 (value_for_money)**: 价格是否合理，是否物有所值
7. **使用体验 (user_experience)**: 上手难度、日常使用感受
8. **复购意愿 (repurchase_intent)**: 从评论推断买家是否愿意再次购买

## 分析要求：
- 如果某个维度在评论中未提及，评分为 null
- 提供每个维度的评分依据（从原文中引用关键信息）
- 判断差评的根因 (root_cause)
- 评估紧急程度 (urgency): "高" / "中" / "低"
- 提取关键标签 (tags): 如 ["质量问题", "物流延迟", "描述不符", "客服差", "配件缺失", "包装破损"]

## 输出格式（严格 JSON）：
{{
  "scores": {{
    "product_quality": {{"score": 2, "evidence": "..."}},
    "logistics_speed": {{"score": null, "evidence": "未提及"}},
    "packaging": {{"score": 3, "evidence": "..."}},
    "description_match": {{"score": 1, "evidence": "..."}},
    "customer_service": {{"score": 2, "evidence": "..."}},
    "value_for_money": {{"score": 3, "evidence": "..."}},
    "user_experience": {{"score": null, "evidence": "未提及"}},
    "repurchase_intent": {{"score": 1, "evidence": "..."}}
  }},
  "root_cause": "产品质量不达标",
  "urgency": "高",
  "tags": ["质量问题", "物流延迟"],
  "summary_cn": "买家因产品质量问题和物流延迟给出差评，建议优先处理质量问题并优化物流渠道。"
}}"""

REVIEW_ANALYSIS_HUMAN = """请分析以下差评：

【产品信息】
- SKU/ASIN: {asin}
- 类目: {category}
- 变体: {style}
- 买家国家: {country}

【评论内容】
- 评分: {overall}/5.0
- 摘要: {summary}
- 正文: {review_text}

请输出 JSON 格式分析结果。"""


# ============================================================
# 2. 小语种翻译 Prompt（先翻译为英文再分析）
# ============================================================
TRANSLATION_SYSTEM = """You are a professional translator for cross-border e-commerce.
Translate the following customer review into English. Preserve the original tone, emotion, and all details.
If the text is already in English, return it as-is.

Output ONLY the translated text, no explanations."""

TRANSLATION_HUMAN = "Translate this review:\n\n{review_text}"


# ============================================================
# 3. 客服回复生成 Prompt
# ============================================================
REPLY_GENERATION_SYSTEM = """你是一个跨境电商客服专家。请根据差评分析结果和RAG检索到的历史处理策略，生成面向买家的回复文案。

## 要求：
1. 语气真诚、具体，不要使用模板化的套话
2. 针对具体问题给出具体回应（不要笼统道歉）
3. 提供明确的解决方案或补偿措施
4. 如果涉及物流问题，根据物流状态提供差异化话术
5. 回复语言与买家语言一致（或使用英语作为通用语言）

## 物流状态差异化策略：
- 已签收 (delivered): 核实包裹信息，安抚买家，询问是否愿意接受补偿
- 在途中 (in_transit): 致歉并解释物流延迟原因，主动提供售后保障承诺
- 异常 (abnormal): 直接引导客服人工介入，提供紧急联系方式

## 输出格式（JSON）：
{{
  "subject": "回复主题/标题",
  "body": "回复正文",
  "tone": "语气类型（apologetic/compensatory/informative）",
  "compensation_suggestion": "建议的补偿措施",
  "follow_up_action": "建议的后续跟进动作"
}}"""

REPLY_GENERATION_HUMAN = """请为以下差评生成回复文案：

【差评分析结果】
{analysis_result}

【RAG检索到的历史相似案例处理策略】
{rag_context}

【物流状态】: {logistics_status}
【目标语言】: {target_language}

请生成回复。"""


# ============================================================
# 4. RAG 检索增强的上下文构建
# ============================================================
def format_rag_context(docs_with_scores) -> str:
    """
    格式化 RAG 检索结果为提示词上下文

    Args:
        docs_with_scores: [(Document, score), ...] 列表

    Returns:
        格式化的上下文字符串
    """
    if not docs_with_scores:
        return "未找到历史相似案例。"

    parts = []
    for i, (doc, score) in enumerate(docs_with_scores, 1):
        meta = doc.metadata
        parts.append(
            f"【案例 {i}】相似度: {score:.2%}\n"
            f"  ASIN: {meta.get('asin', 'N/A')}\n"
            f"  评分: {meta.get('overall', 'N/A')}/5.0\n"
            f"  内容: {doc.page_content[:300]}..."
        )

    return "\n\n".join(parts)


# ============================================================
# 5. 构建 Prompt 模板
# ============================================================
def build_analysis_prompt():
    """构建差评分析 Prompt"""
    from langchain_core.prompts import ChatPromptTemplate
    return ChatPromptTemplate.from_messages([
        ("system", REVIEW_ANALYSIS_SYSTEM),
        ("human", REVIEW_ANALYSIS_HUMAN),
    ])


def build_translation_prompt():
    """构建翻译 Prompt"""
    from langchain_core.prompts import ChatPromptTemplate
    return ChatPromptTemplate.from_messages([
        ("system", TRANSLATION_SYSTEM),
        ("human", TRANSLATION_HUMAN),
    ])


def build_reply_prompt():
    """构建回复生成 Prompt"""
    from langchain_core.prompts import ChatPromptTemplate
    return ChatPromptTemplate.from_messages([
        ("system", REPLY_GENERATION_SYSTEM),
        ("human", REPLY_GENERATION_HUMAN),
    ])