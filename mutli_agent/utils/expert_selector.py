#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专家选择器
根据故障类型选择相关专家
"""

from typing import List, Dict, Optional
import sys
import os

# 添加路径以导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cl_agent.config import FAULT_TYPE_LIBRARY


class ExpertSelector:
    """
    专家选择器
    根据故障类型选择主要专家和可能相关的专家
    """
    
    def __init__(self):
        """初始化专家选择器"""
        # 故障类型到专家的映射
        self.fault_expert_mapping = self._build_fault_expert_mapping()
    
    def _build_fault_expert_mapping(self) -> Dict[str, Dict[str, List[str]]]:
        """
        构建故障类型到专家的映射
        
        Returns:
            映射字典，格式：{
                "fault_type": {
                    "primary": ["expert1", "expert2"],
                    "related": ["expert3"]
                }
            }
        """
        mapping = {}
        
        # 遍历故障类型库，根据category字段确定主要专家
        for fault_type, fault_info in FAULT_TYPE_LIBRARY.items():
            category = fault_info.get("category", "generic")
            
            # 确定主要专家
            primary_experts = []
            if category == "hdfs":
                primary_experts = ["hdfs_expert"]
            elif category == "yarn":
                primary_experts = ["yarn_expert"]
            elif category == "mapreduce":
                primary_experts = ["mapreduce_expert"]
            else:
                primary_experts = ["generic_expert"]
            
            # 确定可能相关的专家
            related_experts = []
            
            # 根据故障类型添加相关专家
            if fault_type == "datanode_down":
                # DataNode下线可能与网络问题相关
                related_experts = ["network_expert"]
            elif fault_type in ["mapreduce_memory_insufficient", "mapreduce_disk_insufficient"]:
                # MapReduce资源问题可能与YARN相关
                related_experts = ["yarn_expert"]
            elif fault_type == "yarn_config_error":
                # YARN配置错误可能与网络相关
                related_experts = ["network_expert"]
            
            mapping[fault_type] = {
                "primary": primary_experts,
                "related": related_experts
            }
        
        return mapping
    
    def select_experts(
        self,
        fault_type: str,
        include_related: bool = True
    ) -> List[str]:
        """
        选择专家
        
        Args:
            fault_type: 故障类型
            include_related: 是否包含相关专家
        
        Returns:
            专家名称列表
        """
        if fault_type not in self.fault_expert_mapping:
            # 未知故障类型，返回通用专家
            return ["generic_expert"]
        
        mapping = self.fault_expert_mapping[fault_type]
        experts = mapping["primary"].copy()
        
        if include_related:
            experts.extend(mapping["related"])
        
        # 去重
        return list(dict.fromkeys(experts))
    
    def get_primary_expert(self, fault_type: str) -> Optional[str]:
        """
        获取主要专家
        
        Args:
            fault_type: 故障类型
        
        Returns:
            主要专家名称，如果不存在则返回None
        """
        if fault_type not in self.fault_expert_mapping:
            return "generic_expert"
        
        primary_experts = self.fault_expert_mapping[fault_type]["primary"]
        return primary_experts[0] if primary_experts else None
    
    def identify_related_faults(
        self,
        primary_fault: str,
        context: Dict
    ) -> List[str]:
        """
        识别可能相关的故障类型（用于联动错误检测）
        
        Args:
            primary_fault: 主要故障类型
            context: 全局上下文
        
        Returns:
            可能相关的故障类型列表
        """
        related_faults = []
        
        # 根据主要故障类型和上下文识别相关故障
        if primary_fault == "datanode_down":
            # DataNode下线可能导致副本数不足
            if context.get("cluster_state", {}).get("hdfs_status") == "degraded":
                related_faults.append("under_replicated_blocks")
        
        elif primary_fault == "mapreduce_memory_insufficient":
            # 内存不足可能导致任务超时
            related_faults.append("mapreduce_task_timeout")
        
        return related_faults
