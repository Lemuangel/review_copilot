"""
翻译质量评估模块

对多语言翻译进行自动化质量评估，支持：
1. BLEU 评分（基于 n-gram 重叠）
2. 文本完整性检查（长度比、字符丢失）
3. 语义相似度（基于 Embedding 余弦相似度）
4. 关键信息保留率

评估流程：
- 对每条翻译结果，自动计算各项指标
- 输出综合质量评分（0-100）和分项详情
- 低质量翻译自动标记，建议人工复核
"""
from __future__ import annotations

import re
import math
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from collections import Counter

if TYPE_CHECKING:
    from langchain_huggingface import HuggingFaceEmbeddings


# ============================================================
# 1. BLEU 评分计算
# ============================================================
def _ngrams(tokens: List[str], n: int) -> Counter:
    """生成 n-gram"""
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


def _tokenize(text: str) -> List[str]:
    """简单分词（按空格+标点）"""
    return re.findall(r'\w+', text.lower())


def calculate_bleu(reference: str, candidate: str, max_n: int = 4) -> float:
    """
    计算 BLEU 分数
    
    Args:
        reference: 参考译文
        candidate: 机器翻译结果
        max_n: 最大 n-gram 阶数
        
    Returns:
        BLEU 分数 (0-1)
    """
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)
    
    if not cand_tokens:
        return 0.0
    
    # 各阶 n-gram 精度
    precisions = []
    for n in range(1, max_n + 1):
        ref_ngrams = _ngrams(ref_tokens, n)
        cand_ngrams = _ngrams(cand_tokens, n)
        
        if not cand_ngrams:
            precisions.append(0.0)
            continue
        
        # 剪切计数
        clipped = sum(min(cand_ngrams[ng], ref_ngrams[ng]) for ng in cand_ngrams)
        total = sum(cand_ngrams.values())
        precisions.append(clipped / total if total > 0 else 0.0)
    
    # 几何平均
    if any(p == 0 for p in precisions):
        geo_mean = 0.0
    else:
        geo_mean = math.exp(sum(math.log(p) for p in precisions) / max_n)
    
    # 简短惩罚
    ref_len = len(ref_tokens)
    cand_len = len(cand_tokens)
    if cand_len > ref_len:
        bp = 1.0
    elif cand_len == 0:
        bp = 0.0
    else:
        bp = math.exp(1 - ref_len / cand_len)
    
    return bp * geo_mean


# ============================================================
# 2. 文本完整性检查
# ============================================================
def check_text_integrity(original: str, translated: str) -> Dict:
    """
    检查翻译文本完整性
    
    Returns:
        {
            "length_ratio": 长度比,
            "char_loss_rate": 字符丢失率,
            "has_truncation": 是否截断,
            "has_garbled": 是否有乱码
        }
    """
    orig_len = max(len(original.strip()), 1)
    trans_len = len(translated.strip())
    
    length_ratio = trans_len / orig_len
    char_loss_rate = max(0, (orig_len - trans_len) / orig_len)
    
    # 截断检测：翻译长度只有原文的 20% 以下
    has_truncation = length_ratio < 0.2
    
    # 乱码检测：非 ASCII 字符比例异常高
    non_ascii = sum(1 for c in translated if ord(c) > 127)
    has_garbled = non_ascii / max(trans_len, 1) > 0.8 and len(translated) > 20
    
    return {
        "length_ratio": round(length_ratio, 4),
        "char_loss_rate": round(char_loss_rate, 4),
        "has_truncation": has_truncation,
        "has_garbled": has_garbled,
        "original_length": orig_len,
        "translated_length": trans_len,
    }


# ============================================================
# 3. 关键信息保留率
# ============================================================
def check_key_info_retention(original: str, translated: str, 
                              keywords: Optional[List[str]] = None) -> Dict:
    """
    检查关键信息是否保留
    
    Args:
        original: 原文
        translated: 译文
        keywords: 需要检查的关键词列表（可选，不提供则自动提取）
        
    Returns:
        {
            "retention_rate": 保留率,
            "missing_keywords": 丢失的关键词,
            "found_keywords": 保留的关键词
        }
    """
    if keywords is None:
        # 自动提取：取原文中长度 >= 4 的单词
        keywords = list(set(
            w.lower() for w in _tokenize(original) if len(w) >= 4
        ))[:20]
    
    if not keywords:
        return {"retention_rate": 1.0, "missing_keywords": [], "found_keywords": []}
    
    trans_lower = translated.lower()
    found = [kw for kw in keywords if kw.lower() in trans_lower]
    missing = [kw for kw in keywords if kw.lower() not in trans_lower]
    
    return {
        "retention_rate": round(len(found) / len(keywords), 4),
        "missing_keywords": missing,
        "found_keywords": found,
        "total_keywords": len(keywords),
    }


# ============================================================
# 4. Embedding 语义相似度
# ============================================================
def calculate_semantic_similarity(original: str, translated: str) -> float:
    """
    基于 Embedding 的语义相似度计算
    
    注意：需要加载 BGE-M3 模型，首次调用较慢
    """
    try:
        from app.vector_store import init_embeddings
        import numpy as np
        
        embeddings = init_embeddings()
        orig_vec = embeddings.embed_query(original)
        trans_vec = embeddings.embed_query(translated)
        
        # 余弦相似度
        dot = np.dot(orig_vec, trans_vec)
        norm = np.linalg.norm(orig_vec) * np.linalg.norm(trans_vec)
        return float(dot / norm) if norm > 0 else 0.0
    except Exception as e:
        print(f"[WARN] 语义相似度计算失败: {e}")
        return -1.0


# ============================================================
# 5. 综合评估
# ============================================================
def evaluate_translation(
    original: str,
    translated: str,
    reference: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    use_semantic: bool = False,
) -> Dict:
    """
    综合翻译质量评估
    
    Args:
        original: 原文
        translated: 译文
        reference: 参考译文（用于 BLEU 计算）
        keywords: 关键信息词列表
        use_semantic: 是否进行语义相似度评估（耗时较长）
        
    Returns:
        {
            "overall_score": 综合评分 (0-100),
            "grade": "A/B/C/D/F",
            "details": {...},
            "issues": [],
            "needs_review": bool
        }
    """
    issues = []
    scores = {}
    
    # 1. 文本完整性
    integrity = check_text_integrity(original, translated)
    scores["integrity"] = integrity
    if integrity["has_truncation"]:
        issues.append("翻译可能被截断")
    if integrity["has_garbled"]:
        issues.append("翻译存在乱码")
    
    # 2. 关键信息保留
    retention = check_key_info_retention(original, translated, keywords)
    scores["retention"] = retention
    if retention["retention_rate"] < 0.5:
        issues.append(f"关键信息丢失严重 (保留率: {retention['retention_rate']:.0%})")
    
    # 3. BLEU 评分（如果有参考译文）
    if reference:
        bleu = calculate_bleu(reference, translated)
        scores["bleu"] = round(bleu, 4)
        if bleu < 0.1:
            issues.append(f"BLEU 评分过低: {bleu:.4f}")
    
    # 4. 语义相似度（可选）
    if use_semantic:
        sim = calculate_semantic_similarity(original, translated)
        scores["semantic_similarity"] = round(sim, 4)
        if sim > 0 and sim < 0.3:
            issues.append(f"语义相似度过低: {sim:.4f}")
    
    # 综合评分
    # 权重：完整性 0.3, 保留率 0.3, BLEU 0.2 (if available), 语义 0.2 (if available)
    overall = 0.0
    total_weight = 0.0
    
    # 完整性评分
    if not integrity["has_truncation"] and not integrity["has_garbled"]:
        len_score = min(1.0, integrity["length_ratio"]) if integrity["length_ratio"] <= 1.0 else 1.0 / integrity["length_ratio"]
    else:
        len_score = 0.0
    overall += len_score * 0.3
    total_weight += 0.3
    
    # 保留率评分
    overall += retention["retention_rate"] * 0.3
    total_weight += 0.3
    
    if "bleu" in scores:
        overall += scores["bleu"] * 0.2
        total_weight += 0.2
    
    if "semantic_similarity" in scores and scores["semantic_similarity"] >= 0:
        overall += scores["semantic_similarity"] * 0.2
        total_weight += 0.2
    
    overall_score = round(overall / total_weight * 100, 1) if total_weight > 0 else 0.0
    
    # 等级评定
    if overall_score >= 90:
        grade = "A"
    elif overall_score >= 75:
        grade = "B"
    elif overall_score >= 60:
        grade = "C"
    elif overall_score >= 40:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "overall_score": overall_score,
        "grade": grade,
        "details": scores,
        "issues": issues,
        "needs_review": grade in ("D", "F") or len(issues) > 0,
    }


# ============================================================
# 6. 批量评估
# ============================================================
def batch_evaluate(
    translations: List[Dict],
    use_semantic: bool = False,
) -> Dict:
    """
    批量评估翻译质量
    
    Args:
        translations: [{"original": "...", "translated": "...", "reference": "..."}, ...]
        use_semantic: 是否进行语义相似度评估
        
    Returns:
        批量评估报告
    """
    results = []
    for item in translations:
        result = evaluate_translation(
            original=item.get("original", ""),
            translated=item.get("translated", ""),
            reference=item.get("reference"),
            keywords=item.get("keywords"),
            use_semantic=use_semantic,
        )
        results.append(result)
    
    if not results:
        return {"total": 0, "avg_score": 0.0, "grade_distribution": {}, "needs_review_count": 0}
    
    avg_score = sum(r["overall_score"] for r in results) / len(results)
    grades = Counter(r["grade"] for r in results)
    needs_review = sum(1 for r in results if r["needs_review"])
    
    return {
        "total": len(results),
        "avg_score": round(avg_score, 1),
        "grade_distribution": dict(sorted(grades.items())),
        "needs_review_count": needs_review,
        "needs_review_rate": round(needs_review / len(results), 4),
        "results": results,
    }


# ============================================================
# 7. 自测
# ============================================================
if __name__ == "__main__":
    import json
    # 测试 BLEU
    ref = "The product arrived damaged and the packaging was crushed"
    cand = "The item arrived broken and the packaging was smashed"
    bleu = calculate_bleu(ref, cand)
    print(f"BLEU: {bleu:.4f}")
    
    # 测试完整性
    integrity = check_text_integrity(ref, cand)
    print(f"Integrity: {integrity}")
    
    # 测试关键信息保留
    retention = check_key_info_retention(ref, cand)
    print(f"Retention: {retention}")
    
    # 综合评估
    eval_result = evaluate_translation(ref, cand, reference=ref)
    print(f"Evaluation: {json.dumps(eval_result, ensure_ascii=False, indent=2)}")
    
    print("\n✅ 翻译质量评估模块就绪")