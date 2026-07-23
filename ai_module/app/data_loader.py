"""
Amazon 2018 Review Dataset 数据加载模块

数据来源：https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/
格式说明（5-core JSON）：
每条 review 是一个 JSON 对象，包含以下字段：
- reviewerID:   用户ID
- asin:         产品ID (Amazon Standard Identification Number)
- reviewerName: 用户名
- vote:         有用投票数
- style:        变体信息 (如 {"Size": "Large", "Color": "Black"})
- reviewText:   评论文本
- overall:      评分 (1.0-5.0)
- summary:      评论摘要
- unixReviewTime: Unix时间戳
- reviewTime:   评论时间 (如 "01 1, 2018")
- image:        买家上传的图片URL列表
- verified:     是否验证购买 (新版数据)
"""
import json
import gzip
import os
import glob
from typing import List, Dict, Optional
from langchain_core.documents import Document


class AmazonReviewLoader:
    """Amazon 5-core 数据集加载器"""

    def __init__(self, data_dir: str):
        """
        Args:
            data_dir: 数据目录路径，包含 .json 或 .json.gz 文件
        """
        self.data_dir = data_dir

    def load_reviews(self, max_reviews: int = 500) -> List[Dict]:
        """
        加载评论数据，返回原始 dict 列表

        Args:
            max_reviews: 最大加载条数，默认500
        """
        reviews = []
        files = self._find_data_files()

        if not files:
            # 如果没找到数据文件，创建模拟数据用于开发测试
            print(f"[WARNING] 未在 {self.data_dir} 找到数据文件，使用模拟数据")
            return self._generate_mock_data(max_reviews)

        for filepath in files:
            try:
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    for line in f:
                        if len(reviews) >= max_reviews:
                            break
                        try:
                            review = json.loads(line.strip())
                            reviews.append(review)
                        except json.JSONDecodeError:
                            continue
            except (gzip.BadGzipFile, OSError):
                # 尝试作为普通 JSON 读取
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if len(reviews) >= max_reviews:
                            break
                        try:
                            review = json.loads(line.strip())
                            reviews.append(review)
                        except json.JSONDecodeError:
                            continue

            if len(reviews) >= max_reviews:
                break

        print(f"[INFO] 加载了 {len(reviews)} 条评论")
        return reviews

    def _find_data_files(self) -> List[str]:
        """查找数据目录下的 JSON 文件"""
        patterns = [
            os.path.join(self.data_dir, "*.json.gz"),
            os.path.join(self.data_dir, "*.json"),
            os.path.join(self.data_dir, "**", "*.json.gz"),
            os.path.join(self.data_dir, "**", "*.json"),
        ]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))
        return files

    def to_documents(self, reviews: List[Dict]) -> List[Document]:
        """
        将评论 dict 转换为 LangChain Document 格式

        每条评论作为一个 Document，包含：
        - page_content: 评论文本正文
        - metadata: 所有结构化字段
        """
        documents = []
        for i, review in enumerate(reviews):
            # 提取关键字段
            review_text = review.get("reviewText", "") or review.get("text", "")
            summary = review.get("summary", "")
            overall = review.get("overall", 0.0)
            asin = review.get("asin", "unknown")
            style = review.get("style", {})

            # 构建 page_content: 摘要 + 正文
            content_parts = []
            if summary:
                content_parts.append(f"[Summary] {summary}")
            if review_text:
                content_parts.append(review_text)

            page_content = "\n".join(content_parts) if content_parts else ""

            if not page_content.strip():
                continue

            # 构建 metadata（Chroma 不允许空列表，需过滤）
            images = review.get("image", [])
            if isinstance(images, list) and len(images) > 0:
                images_str = ",".join(str(img) for img in images[:3])
            else:
                images_str = ""

            style_str = json.dumps(style, ensure_ascii=False) if style else ""

            metadata = {
                "reviewer_id": review.get("reviewerID", ""),
                "asin": asin,
                "reviewer_name": review.get("reviewerName", ""),
                "vote": str(review.get("vote", "0")),
                "overall": float(overall),
                "unix_review_time": int(review.get("unixReviewTime", 0)),
                "review_time": review.get("reviewTime", ""),
                "verified": str(review.get("verified", False)),
                "images": images_str,
                "style": style_str,
            }

            doc = Document(page_content=page_content, metadata=metadata)
            documents.append(doc)

        print(f"[INFO] 转换为 {len(documents)} 个 Document")
        return documents

    def filter_by_rating(self, reviews: List[Dict], max_rating: float = 3.0) -> List[Dict]:
        """
        过滤出差评（评分 <= max_rating）

        Args:
            reviews: 原始评论列表
            max_rating: 最大评分阈值，默认3.0（包含3星及以下）
        """
        return [r for r in reviews if float(r.get("overall", 5.0)) <= max_rating]

    def _generate_mock_data(self, count: int = 50) -> List[Dict]:
        """
        生成模拟数据用于开发测试
        模拟速卖通/亚马逊跨境差评场景
        """
        mock_reviews = [
            {
                "reviewerID": "A1B2C3D4E5F6G7",
                "asin": "B08N5WRWNW",
                "reviewerName": "John D.",
                "vote": "15",
                "style": {"Color": "Black", "Size": "Large"},
                "reviewText": "The product arrived with a cracked screen. I was very disappointed because I waited two weeks for delivery. The packaging was not sufficient to protect the item during international shipping. I contacted customer service but they haven't responded in 3 days.",
                "overall": 1.0,
                "summary": "Arrived damaged, poor customer service",
                "unixReviewTime": 1514764800,
                "reviewTime": "01 1, 2018",
                "image": [],
                "verified": True,
                "category": "Electronics",
                "country": "US"
            },
            {
                "reviewerID": "A2X3Y4Z5W6V7U",
                "asin": "B07XYZ12345",
                "reviewerName": "Maria S.",
                "vote": "8",
                "style": {"Size": "M", "Color": "Red"},
                "reviewText": "The size is way off. I ordered Medium according to the size chart but it fits like an XS. Also the color is more orange than red. The fabric quality is ok but the sizing issue makes it unusable for me. Returning from Spain is too expensive.",
                "overall": 2.0,
                "summary": "Sizing completely wrong, color not as shown",
                "unixReviewTime": 1522569600,
                "reviewTime": "04 1, 2018",
                "image": [],
                "verified": True,
                "category": "Clothing",
                "country": "ES"
            },
            {
                "reviewerID": "A9P8O7I6U5Y4T",
                "asin": "B09ABC98765",
                "reviewerName": "Hans M.",
                "vote": "23",
                "style": {},
                "reviewText": "I ordered this Bluetooth speaker and it worked for exactly 3 days before it stopped charging. The battery life was terrible even when it worked. I tried different cables and chargers, nothing helps. The sound quality was mediocre at best. For the price I expected much better.",
                "overall": 1.0,
                "summary": "Stopped working after 3 days, waste of money",
                "unixReviewTime": 1525132800,
                "reviewTime": "05 1, 2018",
                "image": [],
                "verified": True,
                "category": "Electronics",
                "country": "DE"
            },
            {
                "reviewerID": "A3R4E5W6Q7A8S",
                "asin": "B06DEF45678",
                "reviewerName": "Sophie L.",
                "vote": "5",
                "style": {"Package": "Standard"},
                "reviewText": "The product description said it includes a USB cable and wall adapter, but only the device arrived in the box. No accessories at all. I had to buy a separate cable just to use it. Very misleading product page.",
                "overall": 2.0,
                "summary": "Missing accessories, misleading description",
                "unixReviewTime": 1527811200,
                "reviewTime": "06 1, 2018",
                "image": [],
                "verified": True,
                "category": "Electronics",
                "country": "FR"
            },
            {
                "reviewerID": "A5T6G7B8N9M0K",
                "asin": "B05GHI11111",
                "reviewerName": "Carlos R.",
                "vote": "12",
                "style": {"Color": "White"},
                "reviewText": "Shipping took 45 days! The estimated delivery was 15-20 days. When I finally received it, the box was crushed and the product had minor scratches. The seller didn't respond to my messages about the delay. Product itself is fine but the whole experience was terrible.",
                "overall": 2.0,
                "summary": "Extremely slow shipping, damaged packaging",
                "unixReviewTime": 1530403200,
                "reviewTime": "07 1, 2018",
                "image": [],
                "verified": True,
                "category": "Home",
                "country": "BR"
            },
            {
                "reviewerID": "A1M2N3B4V5C6X",
                "asin": "B04JKL22222",
                "reviewerName": "Yuki T.",
                "vote": "3",
                "style": {"Size": "One Size"},
                "reviewText": "The material feels very cheap, not like the photos at all. It looks elegant in the pictures but in reality it's thin and see-through. I can't wear this to work. Definitely not worth the money. 写真と全然違います。",
                "overall": 1.0,
                "summary": "Poor quality, photos are misleading",
                "unixReviewTime": 1533081600,
                "reviewTime": "08 1, 2018",
                "image": [],
                "verified": True,
                "category": "Clothing",
                "country": "JP"
            },
            {
                "reviewerID": "A7Z8X9C0V1B2N",
                "asin": "B03MNO33333",
                "reviewerName": "Ahmed K.",
                "vote": "18",
                "style": {"Color": "Blue"},
                "reviewText": "The product arrived with EU plug but I need US plug. Nowhere in the description did it mention this. I had to buy an adapter separately. Also the instruction manual is only in Chinese, I can't understand how to use all the features.",
                "overall": 2.0,
                "summary": "Wrong plug type, no English manual",
                "unixReviewTime": 1535760000,
                "reviewTime": "09 1, 2018",
                "image": [],
                "verified": True,
                "category": "Electronics",
                "country": "AE"
            },
            {
                "reviewerID": "A4F5G6H7J8K9L",
                "asin": "B02PQR44444",
                "reviewerName": "Anna K.",
                "vote": "7",
                "style": {"Size": "L", "Color": "Green"},
                "reviewText": "I ordered Large but received Small. The packaging says Large but the actual item inside is clearly marked S. I don't know if this is a warehouse mistake or what. I need this for an event next week and now I have to find something else.",
                "overall": 1.0,
                "summary": "Wrong size shipped, label doesn't match content",
                "unixReviewTime": 1538352000,
                "reviewTime": "10 1, 2018",
                "image": [],
                "verified": True,
                "category": "Clothing",
                "country": "UK"
            },
            {
                "reviewerID": "A0P1O2I3U4Y5T",
                "asin": "B01STU55555",
                "reviewerName": "David W.",
                "vote": "2",
                "style": {},
                "reviewText": "It's been a month and I still haven't received my order. The tracking shows it's been stuck at customs for 3 weeks. The seller keeps saying 'please wait' but I need this product for my business. I want a refund but they refuse until the item is returned - but I never received it!",
                "overall": 1.0,
                "summary": "Never received, stuck at customs, seller unhelpful",
                "unixReviewTime": 1541030400,
                "reviewTime": "11 1, 2018",
                "image": [],
                "verified": True,
                "category": "Office",
                "country": "CA"
            },
            {
                "reviewerID": "A6H7J8K9L0M1N",
                "asin": "B00VWX66666",
                "reviewerName": "Lisa M.",
                "vote": "10",
                "style": {"Color": "Pink"},
                "reviewText": "The product worked fine for the first month, but then it started making a loud buzzing noise. Now it doesn't turn on at all. I tried contacting the manufacturer warranty but they said international purchases aren't covered. Very disappointed because I bought this based on the good reviews.",
                "overall": 2.0,
                "summary": "Failed after one month, warranty doesn't cover international",
                "unixReviewTime": 1543622400,
                "reviewTime": "12 1, 2018",
                "image": [],
                "verified": True,
                "category": "Home",
                "country": "AU"
            },
        ]

        # 生成更多变体
        extended = []
        templates = mock_reviews.copy()
        for i in range(count):
            base = templates[i % len(templates)].copy()
            base["reviewerID"] = f"GEN{i:06d}"
            base["asin"] = f"B{i:08d}"
            base["overall"] = float(1 + (i % 3))  # 1.0, 2.0, 3.0
            base["unixReviewTime"] = 1514764800 + (i * 86400)
            extended.append(base)

        return extended[:count]


def load_and_filter_negative_reviews(data_dir: str, max_reviews: int = 500, max_rating: float = 3.0) -> List[Dict]:
    """
    快捷方法：加载并过滤差评

    Args:
        data_dir: 数据目录
        max_reviews: 最大加载数
        max_rating: 差评阈值（≤此分数的视为差评）
    """
    loader = AmazonReviewLoader(data_dir)
    all_reviews = loader.load_reviews(max_reviews)
    negative = loader.filter_by_rating(all_reviews, max_rating)
    print(f"[INFO] 过滤后差评数: {len(negative)} / {len(all_reviews)}")
    return negative