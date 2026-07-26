"""
业务编排服务 — 分析 + 建议 + 回复全流程

AI 调用全部经同学的 ai_module（analyze_review + generate_reply）。
MySQL 持久化：
    analysis_result   ← issue_type, issue_detail, severity
    operation_suggestion ← suggestion_text, priority
    customer_reply    ← reply_content
"""

import json
import logging
import os
import sys
from typing import Optional

from app.database.database import SessionLocal
from app.models import AnalysisResult, OperationSuggestion, CustomerReply, Review
from app.config import settings

logger = logging.getLogger(__name__)

# 将 ai_module 加入 Python 路径
_AI_MODULE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai_module")
)
if _AI_MODULE_PATH not in sys.path:
    sys.path.insert(0, _AI_MODULE_PATH)


def _call_ai_analyze(review_text: str, context_text: str = "", review_id: int = 0) -> dict:
    """
    调用同学 AI 模块的 analyze_review，并映射到本系统的结果格式。

    返回: {"issues": [...], "root_cause": "...", "evidence": [...],
           "sentiment": "negative", "severity": "high|medium|low"}
    """
    from app.database.database import SessionLocal
    from app.models import Review as ReviewModel

    # 获取评论元数据
    asin = "unknown"
    category = "unknown"
    overall = 1.0
    summary = ""
    country = "unknown"

    if review_id > 0:
        db = SessionLocal()
        try:
            r = db.query(ReviewModel).filter(ReviewModel.review_id == review_id).first()
            if r:
                asin = r.asin or "unknown"
                overall = float(r.rating or 1)
                summary = r.summary or ""
                if r.order:
                    country = r.order.customer_country or "unknown"
        except Exception:
            pass
        finally:
            db.close()

    # 拼入全链路上下文
    full_text = review_text
    if context_text:
        full_text = f"{review_text}\n\n【业务上下文】\n{context_text}"

    # 调用 AI 模块
    from app.generator import analyze_review as ai_analyze

    review_data = {
        "reviewText": full_text,
        "asin": asin,
        "category": category,
        "overall": overall,
        "summary": summary,
        "style": {},
        "country": country,
    }

    result = ai_analyze(review_data, use_rag=True)
    analysis = result.get("analysis", {})

    # 映射到本系统格式
    tags = analysis.get("tags", [])
    root_cause = analysis.get("root_cause", "")
    urgency = analysis.get("urgency", "中")
    evidence_tags = [f"AI标签: {t}" for t in tags] if tags else []

    severity_map = {"高": "high", "中": "medium", "低": "low"}
    severity = severity_map.get(urgency, "medium")

    return {
        "issues": tags,
        "root_cause": root_cause,
        "evidence": evidence_tags,
        "sentiment": "negative",
        "severity": severity,
        "_raw_analysis": analysis,
        "_similar_cases": result.get("similar_cases", []),
    }


def _call_ai_reply(review_text: str, analysis_data: dict, language: str = "中文") -> dict:
    """
    调用同学 AI 模块的 generate_reply，映射到本系统格式。

    返回: {"reply": "客服回复文本"}
    """
    from app.generator import generate_reply as ai_reply

    target_lang = "zh" if language and "中" in language else "en"
    raw_analysis = analysis_data.get("_raw_analysis", analysis_data)

    result = ai_reply(
        analysis_result=raw_analysis,
        review_text=review_text,
        target_language=target_lang,
    )

    body = result.get("body", "")
    subject = result.get("subject", "")
    compensation = result.get("compensation_suggestion", "")

    reply_text = body
    if subject and subject not in body:
        reply_text = f"【{subject}】\n{body}"
    if compensation:
        reply_text += f"\n\n💡 {compensation}"

    return {"reply": reply_text, "_raw_reply": result}


def run_full_analysis(
    review_id: int,
    review_text: str,
    save_to_db: bool = True,
) -> dict:
    """
    完整差评分析流程：
    1. 获取 MySQL 全链路上下文
    2. Chroma 检索历史相似案例
    3. 调用同学 AI 模块 analyze_review
    4. 保存 analysis_result + operation_suggestion
    """
    result = {
        "review_id": review_id,
        "analysis_id": None,
        "suggestion_id": None,
        "issues": [],
        "suggestions": [],
        "context_used": False,
    }

    if review_id <= 0:
        save_to_db = False

    # ---- Step 0: 全链路上下文 ----
    context_text = ""
    if review_id > 0:
        try:
            from app.services.review_service import get_review_context, format_context
            ctx = get_review_context(review_id)
            context_text = format_context(ctx)
            if context_text:
                result["context_used"] = True
        except Exception:
            pass

    # ---- Step 1: 调用同学 AI 模块分析 ----
    try:
        analysis_data = _call_ai_analyze(review_text, context_text, review_id)
    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        raise

    issues = analysis_data.get("issues", [])
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
            result["analysis_id"] = analysis_record.analysis_id
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"保存analysis_result失败: {e}")
            raise
        finally:
            db.close()

    analysis_id = result["analysis_id"]

    # ---- Step 3: 生成运营建议 ----
    suggestions = []
    if root_cause:
        suggestions.append(f"根因: {root_cause}")
    if issues:
        suggestions.append(f"问题维度: {', '.join(issues)}")
    raw_analysis = analysis_data.get("_raw_analysis", {})
    summary_cn = raw_analysis.get("summary_cn", "")
    if summary_cn:
        suggestions.append(summary_cn)

    result["suggestions"] = suggestions

    # ---- Step 4: 保存 operation_suggestion ----
    if save_to_db and analysis_id:
        db = SessionLocal()
        try:
            suggestion_data = {
                "suggestions": suggestions,
                "priority": ["高" if severity == "high" else "中"],
                "estimated_impact": severity,
            }
            suggestion_record = OperationSuggestion(
                analysis_id=analysis_id,
                suggestion_text=json.dumps(suggestion_data, ensure_ascii=False),
                priority=", ".join(suggestion_data["priority"]),
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

    return result


def run_customer_reply(
    review_id: int,
    review_text: str,
    language: str = "中文",
    save_to_db: bool = True,
) -> dict:
    """
    生成客服回复 → 调用同学 AI 模块 generate_reply → 保存 customer_reply。
    """
    analysis_data = {}
    if review_id > 0:
        db = SessionLocal()
        try:
            ar = db.query(AnalysisResult).filter(
                AnalysisResult.review_id == review_id
            ).order_by(AnalysisResult.created_time.desc()).first()
            if ar and ar.issue_detail:
                analysis_data = json.loads(ar.issue_detail)
        except Exception:
            pass
        finally:
            db.close()

    try:
        reply_data = _call_ai_reply(review_text, analysis_data, language)
    except Exception as e:
        logger.error(f"客服回复生成失败: {e}")
        raise

    reply_text = reply_data.get("reply", "")
    result = {
        "review_id": review_id,
        "reply_id": None,
        "reply_text": reply_text,
    }

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


def get_statistics() -> dict:
    """聚合统计分析"""
    from sqlalchemy import func
    from app.models import AnalysisResult, Logistics

    db = SessionLocal()
    try:
        total = db.query(func.count(Review.review_id)).scalar() or 0
        negative = db.query(func.count(Review.review_id)).filter(Review.rating <= 2).scalar() or 0
        negative_ratio = round(negative / total, 2) if total > 0 else 0.0

        label_dist = {}
        if total > 0:
            rows = db.query(Review.label, func.count(Review.review_id)).filter(
                Review.label.isnot(None)
            ).group_by(Review.label).all()
            label_dist = {label: count for label, count in rows}

        severity_dist = {}
        analyzed = db.query(func.count(AnalysisResult.analysis_id)).scalar() or 0
        if analyzed > 0:
            rows = db.query(AnalysisResult.severity, func.count(AnalysisResult.analysis_id)).filter(
                AnalysisResult.severity.isnot(None)
            ).group_by(AnalysisResult.severity).all()
            severity_dist = {sev: count for sev, count in rows}

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
    """前端兼容的统计数据"""
    from sqlalchemy import func

    db = SessionLocal()
    try:
        total = db.query(func.count(Review.review_id)).scalar() or 0

        label_cn = {
            "Logistics": "物流问题", "ProductQuality": "质量问题",
            "DescriptionMismatch": "描述不符", "Price": "价格问题",
            "CustomerService": "客服问题", "Other": "未分类",
        }
        label_rows = db.query(Review.label, func.count(Review.review_id)).filter(
            Review.label.isnot(None)
        ).group_by(Review.label).all()
        categories = [
            {"name": label_cn.get(label, label or "未分类"), "value": count}
            for label, count in label_rows
        ]

        star_rows = db.query(Review.rating, func.count(Review.review_id)).filter(
            Review.rating.isnot(None)
        ).group_by(Review.rating).all()
        star_distribution = [
            {"star": int(star), "count": count} for star, count in star_rows
        ]

        return {"total": total, "categories": categories, "starDistribution": star_distribution}
    finally:
        db.close()


def run_generate(review_id: int, gen_type: str) -> str:
    """统一 AI 生成（前端 /api/generate 调用）"""
    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.review_id == review_id).first()
        if review is None:
            raise ValueError(f"评论不存在: review_id={review_id}")
        review_text = review.review_text
    finally:
        db.close()

    if gen_type == "reply":
        reply_data = _call_ai_reply(review_text, {}, "中文")
        return reply_data.get("reply", "")

    elif gen_type == "suggestion":
        analysis_data = _call_ai_analyze(review_text, "", review_id)
        issues = analysis_data.get("issues", [])
        root_cause = analysis_data.get("root_cause", "")
        parts = []
        if root_cause:
            parts.append(f"根因: {root_cause}")
        if issues:
            parts.append(f"问题: {', '.join(issues)}")
        return "\n".join(parts) if parts else "未检测到明确问题"

    else:
        raise ValueError(f"不支持的生成类型: {gen_type}")
