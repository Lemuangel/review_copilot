"""
Prompt 版本管理与 A/B 测试框架

功能：
1. Prompt 版本注册与管理
2. A/B 分组测试（随机分流）
3. 效果指标收集（评分维度覆盖率、JSON 解析成功率、分析耗时）
4. 版本对比报告生成
5. 运营人员反馈标记（手动标注"好"/"差"）

使用方式：
    # 注册新版本
    pm = PromptVersionManager()
    pm.register("v1", "原始8维分析模板")
    pm.register("v2", "优化版：增加根因分析引导")

    # A/B 测试
    ab = ABTestRunner(pm)
    version = ab.assign_version(user_id="user_123")  # 一致性哈希分流

    # 记录结果
    ab.record(version, metrics)

    # 生成报告
    ab.report()
"""
from __future__ import annotations

import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field


# ============================================================
# 1. Prompt 版本管理
# ============================================================
@dataclass
class PromptVersion:
    """Prompt 版本"""
    name: str
    description: str
    system_prompt: str
    human_prompt: str
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    author: str = "system"


class PromptVersionManager:
    """
    Prompt 版本管理器
    
    支持多版本注册、切换、回滚
    """
    
    def __init__(self):
        self._versions: Dict[str, PromptVersion] = {}
        self._active: Optional[str] = None
        self._default: Optional[str] = None
    
    def register(self, name: str, description: str, 
                 system_prompt: str = "", human_prompt: str = "",
                 tags: List[str] = None, author: str = "system",
                 set_default: bool = False) -> PromptVersion:
        """注册新版本"""
        if name in self._versions:
            raise ValueError(f"版本 {name} 已存在")
        
        version = PromptVersion(
            name=name,
            description=description,
            system_prompt=system_prompt,
            human_prompt=human_prompt,
            tags=tags or [],
            author=author,
        )
        self._versions[name] = version
        
        if set_default or self._default is None:
            self._default = name
            self._active = name
        
        return version
    
    def get(self, name: str) -> Optional[PromptVersion]:
        """获取指定版本"""
        return self._versions.get(name)
    
    def get_active(self) -> Optional[PromptVersion]:
        """获取当前活跃版本"""
        if self._active and self._active in self._versions:
            return self._versions[self._active]
        return self._versions.get(self._default) if self._default else None
    
    def set_active(self, name: str):
        """切换活跃版本"""
        if name not in self._versions:
            raise ValueError(f"版本 {name} 不存在")
        self._active = name
    
    def list_versions(self) -> List[Dict]:
        """列出所有版本"""
        return [
            {
                "name": v.name,
                "description": v.description,
                "tags": v.tags,
                "author": v.author,
                "created_at": v.created_at,
                "is_active": v.name == self._active,
                "is_default": v.name == self._default,
            }
            for v in self._versions.values()
        ]
    
    def rollback(self):
        """回滚到默认版本"""
        if self._default:
            self._active = self._default
    
    def to_dict(self) -> dict:
        """序列化"""
        return {
            "versions": {
                name: {
                    "name": v.name,
                    "description": v.description,
                    "system_prompt": v.system_prompt[:100] + "..." if len(v.system_prompt) > 100 else v.system_prompt,
                    "human_prompt": v.human_prompt[:100] + "..." if len(v.human_prompt) > 100 else v.human_prompt,
                    "tags": v.tags,
                    "author": v.author,
                    "created_at": v.created_at,
                }
                for name, v in self._versions.items()
            },
            "active": self._active,
            "default": self._default,
        }


# ============================================================
# 2. A/B 测试分流器
# ============================================================
class ABTestRunner:
    """
    A/B 测试运行器
    
    支持：
    - 一致性哈希分流（同一用户始终分到同一版本）
    - 多版本对比
    - 指标收集
    - 报告生成
    """
    
    def __init__(self, version_manager: PromptVersionManager, 
                 test_name: str = "default"):
        self.pm = version_manager
        self.test_name = test_name
        self._test_versions: List[str] = []  # 参与测试的版本
        self._metrics: Dict[str, List[Dict]] = defaultdict(list)  # 版本 -> 指标列表
        self._human_feedback: Dict[str, List[Dict]] = defaultdict(list)  # 人工反馈
        self._created_at = time.time()
    
    def setup_test(self, versions: List[str], weights: List[float] = None):
        """
        设置 A/B 测试
        
        Args:
            versions: 参与测试的版本名列表
            weights: 各版本流量权重（不提供则均分）
        """
        self._test_versions = versions
        if weights is None:
            self._weights = [1.0 / len(versions)] * len(versions)
        else:
            total = sum(weights)
            self._weights = [w / total for w in weights]
    
    def assign_version(self, user_id: str) -> str:
        """
        为用户分配版本（一致性哈希）
        
        同一 user_id 始终得到相同版本，避免用户在测试中看到不一致结果
        
        Args:
            user_id: 用户标识
            
        Returns:
            分配的版本名
        """
        if not self._test_versions:
            active = self.pm.get_active()
            return active.name if active else "default"
        
        # 一致性哈希
        hash_val = int(hashlib.md5(
            f"{self.test_name}:{user_id}".encode()
        ).hexdigest(), 16)
        
        # 按权重分配
        bucket = (hash_val % 10000) / 10000.0
        cumulative = 0.0
        for version, weight in zip(self._test_versions, self._weights):
            cumulative += weight
            if bucket <= cumulative:
                return version
        
        return self._test_versions[-1]
    
    def record(self, version: str, metrics: Dict):
        """
        记录分析指标
        
        Args:
            version: 使用的 Prompt 版本
            metrics: {
                "latency": 分析耗时(秒),
                "json_valid": JSON解析是否成功,
                "dimensions_covered": 覆盖的维度数,
                "has_root_cause": 是否有根因分析,
                "has_tags": 是否有标签,
                "review_length": 评论文本长度,
                "star_rating": 原始评分,
            }
        """
        metrics["timestamp"] = time.time()
        self._metrics[version].append(metrics)
    
    def add_feedback(self, version: str, feedback: Dict):
        """
        添加人工反馈
        
        Args:
            version: Prompt 版本
            feedback: {
                "rating": "good" | "bad" | "neutral",
                "comment": "人工评语",
                "review_id": "关联的差评ID",
                "reviewer": "反馈人",
            }
        """
        feedback["timestamp"] = time.time()
        self._human_feedback[version].append(feedback)
    
    def get_stats(self, version: str) -> Dict:
        """获取单版本统计"""
        metrics = self._metrics.get(version, [])
        if not metrics:
            return {"version": version, "count": 0, "message": "无数据"}
        
        latencies = [m["latency"] for m in metrics if "latency" in m]
        json_valid = sum(1 for m in metrics if m.get("json_valid", False))
        dims = [m.get("dimensions_covered", 0) for m in metrics]
        
        return {
            "version": version,
            "count": len(metrics),
            "avg_latency": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "json_valid_rate": round(json_valid / len(metrics), 4),
            "avg_dimensions_covered": round(sum(dims) / len(dims), 2) if dims else 0,
            "has_root_cause_rate": round(
                sum(1 for m in metrics if m.get("has_root_cause")) / len(metrics), 4
            ),
            "feedback_count": len(self._human_feedback.get(version, [])),
            "good_feedback_rate": round(
                sum(1 for f in self._human_feedback.get(version, [])
                    if f.get("rating") == "good") / max(len(self._human_feedback.get(version, [])), 1), 4
            ),
        }
    
    def report(self) -> Dict:
        """
        生成 A/B 测试报告
        
        Returns:
            {
                "test_name": ...,
                "duration_hours": ...,
                "total_samples": ...,
                "versions": {...},
                "winner": 综合最佳版本,
                "recommendation": 建议
            }
        """
        version_stats = {}
        for v in self._test_versions:
            version_stats[v] = self.get_stats(v)
        
        if not version_stats:
            return {"test_name": self.test_name, "status": "no_data"}
        
        # 综合评分（权重可调）
        def score(s: Dict) -> float:
            if s["count"] == 0:
                return 0.0
            return (
                s["json_valid_rate"] * 0.30 +
                (s["avg_dimensions_covered"] / 8.0) * 0.25 +
                (1.0 / max(s["avg_latency"], 1.0)) * 0.15 +  # 延迟越低越好
                s["has_root_cause_rate"] * 0.15 +
                s["good_feedback_rate"] * 0.15
            )
        
        scored = [(v, score(s), s) for v, s in version_stats.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        winner = scored[0][0] if scored else None
        
        total_samples = sum(s["count"] for _, _, s in scored)
        
        return {
            "test_name": self.test_name,
            "duration_hours": round((time.time() - self._created_at) / 3600, 2),
            "total_samples": total_samples,
            "versions": {
                v: {
                    **s,
                    "composite_score": round(sc, 4),
                }
                for v, sc, s in scored
            },
            "winner": winner,
            "recommendation": (
                f"建议将版本 '{winner}' 设为默认版本"
                if winner else "数据不足，无法判断"
            ),
        }
    
    def to_dict(self) -> dict:
        """序列化"""
        return {
            "test_name": self.test_name,
            "created_at": self._created_at,
            "test_versions": self._test_versions,
            "weights": self._weights,
            "metrics_count": {v: len(m) for v, m in self._metrics.items()},
            "feedback_count": {v: len(f) for v, f in self._human_feedback.items()},
        }


# ============================================================
# 3. 全局实例
# ============================================================
# 初始化 Prompt 版本管理器
prompt_version_manager = PromptVersionManager()

# 注册内置版本
prompt_version_manager.register(
    "v1_original",
    "原始8维分析模板（基于TS Demo交付文档）",
    tags=["baseline", "original"],
    author="张竣翔",
    set_default=True,
)

prompt_version_manager.register(
    "v2_enhanced",
    "增强版：增加根因分析引导 + 物流状态联动",
    tags=["enhanced", "logistics"],
    author="OpenClaw",
)


# ============================================================
# 4. 自测
# ============================================================
if __name__ == "__main__":
    # 测试版本管理
    pm = PromptVersionManager()
    pm.register("v1", "基础版", tags=["baseline"], set_default=True)
    pm.register("v2", "优化版", tags=["optimized"])
    
    print("版本列表:")
    for v in pm.list_versions():
        print(f"  {v['name']}: {v['description']} (active={v['is_active']})")
    
    # 测试 A/B
    ab = ABTestRunner(pm, "prompt_ab_test")
    ab.setup_test(["v1", "v2"], weights=[0.5, 0.5])
    
    print("\n分流测试:")
    for uid in ["user_a", "user_b", "user_c", "user_a", "user_d"]:
        v = ab.assign_version(uid)
        print(f"  {uid} -> {v}")
    
    # 记录指标
    ab.record("v1", {
        "latency": 12.5, "json_valid": True,
        "dimensions_covered": 7, "has_root_cause": True,
        "has_tags": True, "review_length": 200, "star_rating": 1.0,
    })
    ab.record("v2", {
        "latency": 10.2, "json_valid": True,
        "dimensions_covered": 8, "has_root_cause": True,
        "has_tags": True, "review_length": 200, "star_rating": 1.0,
    })
    
    # 人工反馈
    ab.add_feedback("v1", {"rating": "good", "comment": "分析准确", "reviewer": "运营A"})
    ab.add_feedback("v2", {"rating": "good", "comment": "更详细", "reviewer": "运营A"})
    
    print("\n测试报告:")
    report = ab.report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    
    print("\n✅ Prompt 版本管理 + A/B 测试框架就绪")