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
from app.models import AnalysisResult, OperationSuggestion, CustomerReply, Review
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

    1. 获取全链路上下文（任务4新增）
    2. AI 分析（带上下文）→ 写入 analysis_result
    3. AI 建议（带上下文）→ 写入 operation_suggestion

    返回: {"review_id": int, "analysis_id": int, "suggestion_id": int,
           "issues": [...], "suggestions": [...], "context_used": bool}
    """
    result = {
        "review_id": review_id,
        "analysis_id": None,
        "suggestion_id": None,
        "issues": [],
        "suggestions": [],
        "context_used": False,
    }

    # 无有效 review_id 时跳过数据库写入（避免 FK 约束错误）
    if review_id <= 0:
        save_to_db = False

    # ---- Step 0: 获取全链路上下文（任务4） ----
    context_text = ""
    if review_id > 0:
        try:
            from app.services.review_service import get_review_context, format_context
            ctx = get_review_context(review_id)
            context_text = format_context(ctx)
            if context_text:
                result["context_used"] = True
        except ValueError:
            pass  # review 不存在
        except Exception:
            pass  # 上下文获取失败不影响主流程

    # ---- Step 0.5: 检索历史相似差评（Chroma RAG） ----
    try:
        from app.services.vector_service import search_similar_reviews
        similar = search_similar_reviews(review_text, k=3)
        if similar:
            lines = ["## 历史相似差评（供参考）"]
            for i, s in enumerate(similar, 1):
                meta = s.get("metadata", {})
                label = meta.get("label", "未分类")
                lines.append(f"{i}. [{label}] {s['content'][:200]}")
            similar_text = "\n".join(lines)
            context_text = context_text + "\n\n" + similar_text if context_text else similar_text
    except Exception:
        pass  # Chroma 不可用不影响主流程

    # ---- Step 1: LangChain LCEL 链分析差评 ----
    try:
        analysis_data = analyze_with_lcel(review_text, context_text)
    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        raise

    issues = analysis_data.get("issues", [])
    sentiment = analysis_data.get("sentiment", "negative")
    severity = analysis_data.get("severity", "medium")
    root_cause = analysis_data.get("root_cause", "")
    evidence = analysis_data.get("evidence", [])
    result["issues"] = issues
    result["root_cause"] = root_cause
    result["evidence"] = evidence

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
            suggestion_data = suggest_with_lcel(review_text, issues, context_text)
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


def get_statistics() -> dict:
    """
    聚合统计分析：差评比例、问题分类分布、严重程度分布、物流状态分布。

    SQL 聚合 review + analysis_result + logistics 三张表。
    """
    from sqlalchemy import func
    from app.models import Review, AnalysisResult, Logistics

    db = SessionLocal()
    try:
        # 评论总量
        total = db.query(func.count(Review.review_id)).scalar() or 0
        negative = db.query(func.count(Review.review_id)).filter(Review.rating <= 2).scalar() or 0
        negative_ratio = round(negative / total, 2) if total > 0 else 0.0

        # 问题分类分布（label 列）
        label_dist = {}
        if total > 0:
            rows = db.query(Review.label, func.count(Review.review_id)).filter(
                Review.label.isnot(None)
            ).group_by(Review.label).all()
            label_dist = {label: count for label, count in rows}

        # 严重程度分布
        severity_dist = {}
        analyzed = db.query(func.count(AnalysisResult.analysis_id)).scalar() or 0
        if analyzed > 0:
            rows = db.query(AnalysisResult.severity, func.count(AnalysisResult.analysis_id)).filter(
                AnalysisResult.severity.isnot(None)
            ).group_by(AnalysisResult.severity).all()
            severity_dist = {sev: count for sev, count in rows}

        # 物流状态分布
        logistics_dist = {}
        logistics_total = db.query(func.count(Logistics.logistics_id)).scalar() or 0
        if logistics_total > 0:
            rows = db.query(Logistics.shipping_status, func.count(Logistics.logistics_id)).filter(
                Logistics.shipping_status.isnot(None)
            ).group_by(Logistics.shipping_status).all()
            logistics_dist = {status: count for status, count in rows}

        return {
            "total_reviews": total,
            "negative_count": negative,
            "negative_ratio": negative_ratio,
            "label_distribution": label_dist,
            "severity_distribution": severity_dist,
            "logistics_distribution": logistics_dist,
            "analyzed_count": analyzed,
        }
    finally:
        db.close()


def get_frontend_statistics() -> dict:
    """
    前端兼容的统计数据，格式对齐 data.js mock。
    返回: { total, categories: [{name, value}], starDistribution: [{star, count}] }
    """
    from sqlalchemy import func
    from app.models import Review

    db = SessionLocal()
    try:
        total = db.query(func.count(Review.review_id)).scalar() or 0

        # 类别分布（label → 中文映射）
        label_cn = {
            "Logistics": "物流问题",
            "ProductQuality": "质量问题",
            "DescriptionMismatch": "描述不符",
            "Price": "价格问题",
            "CustomerService": "客服问题",
            "Other": "未分类",
        }
        label_rows = db.query(Review.label, func.count(Review.review_id)).filter(
            Review.label.isnot(None)
        ).group_by(Review.label).all()
        categories = [
            {"name": label_cn.get(label, label or "未分类"), "value": count}
            for label, count in label_rows
        ]

        # 星级分布
        star_rows = db.query(Review.rating, func.count(Review.review_id)).filter(
            Review.rating.isnot(None)
        ).group_by(Review.rating).all()
        star_distribution = [
            {"star": int(star), "count": count}
            for star, count in star_rows
        ]

        return {
            "total": total,
            "categories": categories,
            "starDistribution": star_distribution,
        }
    finally:
        db.close()


def run_generate(review_id: int, gen_type: str) -> str:
    """
    统一 AI 生成：根据 type 调用客服回复或运营建议。

    参数:
        review_id: 评论ID
        gen_type:  "reply" | "suggestion"
    返回: 生成文本
    """
    from app.services.review_service import get_review_context, format_context

    # 获取评论内容
    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.review_id == review_id).first()
        if review is None:
            raise ValueError(f"评论不存在: review_id={review_id}")
        review_text = review.review_text
    finally:
        db.close()

    # 获取全链路上下文
    context_text = ""
    try:
        ctx = get_review_context(review_id)
        context_text = format_context(ctx)
    except Exception:
        pass

    if gen_type == "reply":
        reply_data = reply_with_lcel(review_text, "中文")
        return reply_data.get("reply", "")

    elif gen_type == "suggestion":
        analysis_data = analyze_with_lcel(review_text, context_text)
        issues = analysis_data.get("issues", [])
        if issues:
            suggestion_data = suggest_with_lcel(review_text, issues, context_text)
            suggestions = suggestion_data.get("suggestions", [])
            return "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
        return "未检测到明确问题，建议人工复核"

    else:
        raise ValueError(f"不支持的生成类型: {gen_type}，仅支持 reply 或 suggestion")


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
