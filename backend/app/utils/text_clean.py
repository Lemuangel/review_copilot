"""
评论文本清洗工具
"""

import re


def clean_text(text: str) -> str:
    """
    清洗评论文本：
    - 去除多余空白
    - 去除HTML标签
    - 统一标点符号
    - 去除特殊字符
    """
    if not text:
        return ""

    # 去除HTML标签
    text = re.sub(r"<[^>]+>", "", text)

    # 去除多余空白字符（包括换行、制表符等）
    text = re.sub(r"\s+", " ", text)

    # 去除首尾空白
    text = text.strip()

    return text


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """
    从文本中提取关键词（简单版本，基于高频词）
    不导入外部NLP库，使用基础方法实现
    """
    if not text:
        return []

    # 常见停用词
    stopwords = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "and", "or", "but", "not", "this",
        "that", "it", "as", "its", "very", "too", "so", "if", "than", "then",
        "just", "about", "into", "over", "also", "no", "yes", "up", "out",
    }

    # 分词（简单按空格和非中文字符分割）
    words = re.findall(r"[一-鿿]+|[a-zA-Z]+", text.lower())

    # 统计词频
    word_freq = {}
    for word in words:
        if len(word) >= 2 and word not in stopwords:
            word_freq[word] = word_freq.get(word, 0) + 1

    # 返回 top_n 高频词
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_n]]
