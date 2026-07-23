"""
业务编排服务 — 分析 + 建议 + 回复全流程

AI 调用全部经 LangChain LCEL 链（langchain_service.py）：
    - 差评分析：PromptTemplate | ChatOpenAI | StrOutputParser | JsonOutputParser
    - 运营建议：PromptTemplate | ChatOpenAI | StrOutputParser | JsonOutputParser
    - 客服回复：PromptTemplate | ChatOpenAI | StrOutputParser | JsonOutputParser

MySQL 持久化：
    analysis_result   ← issue_type, issue_detail, severity
    operation_suggestion ← suggestion_text, priority
    customer_reply    ← reply_content
"""

import json
import logging
from typing import Optional

from app.database.database import SessionLocal
from app.models import AnalysisResult, OperationSuggestion, CustomerReply
from app.services.langchain_service import (
    analyze_with_lcel,
    suggest_with_lcel,
    reply_with_lcel,
)
from app.config import settings

logger = logging.getLogger(__name__)


def run_full_analysis(
    review_id: int,
    review_text: str,
    save_to_db: bool = True,
) -> dict:
    """
    完整差评分析流程：

    1. AI 分析 → 写入 analysis_result
    2. AI 建议 → 写入 operation_suggestion

    返回: {"review_id": int, "analysis_id": int, "suggestion_id": int, "issues": [...], "suggestions": [...]}
    """
    result = {
        "review_id": review_id,
        "analysis_id": None,
        "suggestion_id": None,
        "issues": [],
        "suggestions": [],
    }

    # 无有效 review_id 时跳过数据库写入（避免 FK 约束错误）
    if review_id <= 0:
        save_to_db = False

    # ---- Step 1: LangChain LCEL 链分析差评 ----
    try:
        analysis_data = analyze_with_lcel(review_text)
    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        raise

    issues = analysis_data.get("issues", [])
    sentiment = analysis_data.get("sentiment", "negative")
    severity = analysis_data.get("severity", "medium")
    result["issues"] = issues

    # ---- Step 2: 保存 analysis_result ----
    if save_to_db:
        db = SessionLocal()
        try:
            analysis_record = AnalysisResult(
                review_id=review_id,
                issue_type=", ".join(issues) if issues else "未分类",
                issue_detail=json.dumps(analysis_data, ensure_ascii=False),
                severity=severity,
            )
            db.add(analysis_record)
            db.flush()
            analysis_id = analysis_record.analysis_id
            result["analysis_id"] = analysis_id
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"保存analysis_result失败: {e}")
            raise
        finally:
            db.close()
    else:
        analysis_id = None

    # ---- Step 3: LangChain LCEL 链生成运营建议 ----
    if issues:
        try:
            suggestion_data = suggest_with_lcel(review_text, issues)
        except Exception as e:
            logger.warning(f"运营建议生成失败: {e}")
            suggestion_data = {"suggestions": ["请稍后重试"], "priority": [], "estimated_impact": "unknown"}

        suggestions = suggestion_data.get("suggestions", [])
        priority_list = suggestion_data.get("priority", [])
        result["suggestions"] = suggestions

        # ---- Step 4: 保存 operation_suggestion ----
        if save_to_db and analysis_id:
            db = SessionLocal()
            try:
                suggestion_record = OperationSuggestion(
                    analysis_id=analysis_id,
                    suggestion_text=json.dumps(suggestion_data, ensure_ascii=False),
                    priority=", ".join(priority_list) if priority_list else "中",
                )
                db.add(suggestion_record)
                db.flush()
                result["suggestion_id"] = suggestion_record.suggestion_id
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"保存operation_suggestion失败: {e}")
            finally:
                db.close()
    else:
        result["suggestions"] = ["未检测到明确问题，建议人工复核"]

    return result


def run_customer_reply(
    review_id: int,
    review_text: str,
    language: str = "中文",
    save_to_db: bool = True,
) -> dict:
    """
    生成客服回复 → 保存 customer_reply。

    返回: {"review_id": int, "reply_id": int, "reply_text": str}
    """
    try:
        reply_data = reply_with_lcel(review_text, language)
    except Exception as e:
        logger.error(f"客服回复生成失败: {e}")
        raise

    reply_text = reply_data.get("reply", "") or "生成回复失败，请稍后重试"
    result = {
        "review_id": review_id,
        "reply_id": None,
        "reply_text": reply_text,
    }

    # 无有效 review_id 时跳过数据库写入
    if review_id <= 0:
        save_to_db = False

    if save_to_db:
        db = SessionLocal()
        try:
            reply_record = CustomerReply(
                review_id=review_id,
                reply_content=reply_text,
                language=language if language in ("中文", "英文") else "zh",
            )
            db.add(reply_record)
            db.flush()
            result["reply_id"] = reply_record.reply_id
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"保存customer_reply失败: {e}")
        finally:
            db.close()

    return result
