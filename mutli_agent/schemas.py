#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输出格式Schema定义
定义各个Agent的输出格式
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class FaultCategory(str, Enum):
    """故障类别"""
    HDFS = "hdfs"
    YARN = "yarn"
    MAPREDUCE = "mapreduce"
    NETWORK = "network"
    GENERIC = "generic"


@dataclass
class ClassificationResult:
    """分类Agent的输出格式"""
    fault_type: str  # 故障类型，如 "datanode_down"
    confidence: float  # 置信度 0.0-1.0
    category: str  # 故障类别，如 "hdfs"
    related_faults: Optional[List[str]] = None  # 可能相关的故障类型
    reasoning: Optional[str] = None  # 分类理由
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class ExpertDiagnosis:
    """专家Agent的诊断结果"""
    expert_name: str  # 专家名称，如 "hdfs_expert"
    root_cause: str  # 根本原因
    evidence: List[str]  # 证据列表
    fix_steps: List[str]  # 修复步骤
    confidence: float  # 置信度 0.0-1.0
    affected_components: Optional[List[str]] = None  # 受影响的组件
    severity: Optional[str] = None  # 严重程度：low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class DiscussionResult:
    """Discussion Agent的综合结果"""
    consensus: bool  # 专家意见是否一致
    final_root_cause: str  # 综合根因
    final_evidence: List[str]  # 综合证据
    final_fix_steps: List[str]  # 综合修复步骤
    confidence: float  # 综合置信度 0.0-1.0
    conflicts: Optional[List[str]] = None  # 冲突描述（如有）
    compound_faults: Optional[List[str]] = None  # 联动故障分析（如有）
    expert_agreement: Optional[Dict[str, float]] = None  # 专家一致性分析
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class DiagnosisReport:
    """完整的诊断报告"""
    classification: ClassificationResult  # 分类结果
    expert_diagnoses: List[ExpertDiagnosis]  # 各专家诊断结果
    discussion: DiscussionResult  # 综合讨论结果
    global_context: Optional[Dict[str, Any]] = None  # 全局上下文快照
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "classification": self.classification.to_dict(),
            "expert_diagnoses": [d.to_dict() for d in self.expert_diagnoses],
            "discussion": self.discussion.to_dict(),
        }
        if self.global_context:
            result["global_context"] = self.global_context
        return result
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
