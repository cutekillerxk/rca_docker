#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类Agent
负责故障类型分类，输出结构化JSON
"""

import json
import re
from typing import Dict, Any
from ..base import BaseAgent
from ..schemas import ClassificationResult
import sys
import os

# 添加路径以导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cl_agent.config import FAULT_TYPE_LIBRARY


class FaultClassifierAgent(BaseAgent):
    """
    故障分类Agent
    无工具，只做分类任务
    """
    
    def __init__(self, llm_client):
        """初始化分类Agent"""
        system_prompt = self._load_system_prompt()
        super().__init__(
            llm_client=llm_client,
            system_prompt=system_prompt,
            role="classifier",
            tools=None  # 分类Agent不使用工具
        )
    
    def _load_system_prompt(self) -> str:
        """加载系统提示"""
        # 构建故障类型列表
        fault_types = []
        for fault_type, fault_info in FAULT_TYPE_LIBRARY.items():
            fault_types.append(f"- {fault_type}: {fault_info['fault_type']} ({fault_info['category']})")
        
        fault_types_str = "\n".join(fault_types)
        
        prompt = f"""你是故障分类专家，负责分析Hadoop集群日志和监控指标，识别故障类型。

## 你的任务
1. 分析提供的日志和监控指标
2. 识别故障类型（从已知故障类型库中选择）
3. 输出JSON格式的分类结果

## 已知故障类型库
{fault_types_str}

## 输出格式要求
你必须输出有效的JSON格式，包含以下字段：
- fault_type: 故障类型（字符串，必须从已知故障类型库中选择）
- confidence: 置信度（0.0-1.0的浮点数）
- category: 故障类别（hdfs/yarn/mapreduce/generic）
- related_faults: 可能相关的故障类型列表（可选）
- reasoning: 分类理由（可选）

## 示例输出
{{
  "fault_type": "datanode_down",
  "confidence": 0.95,
  "category": "hdfs",
  "related_faults": ["under_replicated_blocks"],
  "reasoning": "日志显示DataNode下线，监控指标显示NumDeadDataNodes > 0"
}}

请仔细分析日志和监控指标，给出准确的分类结果。"""
        return prompt
    
    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        """
        构建分类prompt
        
        Args:
            input_data: 输入数据，包含：
                - logs: 日志内容（可选）
                - metrics: 监控指标（可选）
                - user_query: 用户查询（可选）
        """
        prompt_parts = []
        
        # 添加用户查询（如果有）
        if "user_query" in input_data:
            prompt_parts.append(f"用户查询：{input_data['user_query']}")
            prompt_parts.append("")
        
        # 添加日志（如果有）
        if "logs" in input_data and input_data["logs"]:
            prompt_parts.append("## 集群日志")
            if isinstance(input_data["logs"], dict):
                # 如果是字典，格式化显示
                for node_name, log_content in input_data["logs"].items():
                    prompt_parts.append(f"\n### {node_name}")
                    # 限制日志长度，避免prompt过长
                    log_preview = log_content[:2000] if len(log_content) > 2000 else log_content
                    prompt_parts.append(log_preview)
                    if len(log_content) > 2000:
                        prompt_parts.append(f"\n... (日志已截断，共{len(log_content)}字符)")
            else:
                log_preview = str(input_data["logs"])[:2000] if len(str(input_data["logs"])) > 2000 else str(input_data["logs"])
                prompt_parts.append(log_preview)
            prompt_parts.append("")
        
        # 添加监控指标（如果有）
        if "metrics" in input_data and input_data["metrics"]:
            prompt_parts.append("## 监控指标")
            # 简化显示监控指标
            metrics_str = json.dumps(input_data["metrics"], ensure_ascii=False, indent=2)
            metrics_preview = metrics_str[:2000] if len(metrics_str) > 2000 else metrics_str
            prompt_parts.append(metrics_preview)
            if len(metrics_str) > 2000:
                prompt_parts.append(f"\n... (指标已截断，共{len(metrics_str)}字符)")
            prompt_parts.append("")
        
        # 添加分类要求
        prompt_parts.append("## 分类任务")
        prompt_parts.append("请分析上述日志和监控指标，识别故障类型，并输出JSON格式的分类结果。")
        
        return "\n".join(prompt_parts)
    
    def parse_output(self, response: str) -> Dict[str, Any]:
        """
        解析分类输出
        
        Args:
            response: LLM返回的文本（应该是JSON格式）
        
        Returns:
            解析后的分类结果字典
        """
        # 尝试解析JSON
        try:
            # 移除可能的markdown代码块标记
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # 解析JSON
            result_dict = json.loads(response)
            
            # 验证必需字段
            if "fault_type" not in result_dict:
                raise ValueError("缺少必需字段: fault_type")
            if "confidence" not in result_dict:
                result_dict["confidence"] = 0.5  # 默认置信度
            if "category" not in result_dict:
                # 从故障类型库中获取category
                fault_type = result_dict["fault_type"]
                if fault_type in FAULT_TYPE_LIBRARY:
                    result_dict["category"] = FAULT_TYPE_LIBRARY[fault_type]["category"]
                else:
                    result_dict["category"] = "generic"
            
            # 创建ClassificationResult对象
            classification = ClassificationResult(
                fault_type=result_dict["fault_type"],
                confidence=float(result_dict["confidence"]),
                category=result_dict["category"],
                related_faults=result_dict.get("related_faults"),
                reasoning=result_dict.get("reasoning")
            )
            
            return classification.to_dict()
        
        except json.JSONDecodeError as e:
            # JSON解析失败，尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    result_dict = json.loads(json_match.group())
                    return result_dict
                except:
                    pass
            
            # 如果还是失败，返回错误信息
            print(f"[WARNING] 分类输出解析失败: {e}")
            print(f"[WARNING] 原始响应: {response[:200]}")
            
            # 返回默认分类结果
            return {
                "fault_type": "unknown",
                "confidence": 0.0,
                "category": "generic",
                "reasoning": f"解析失败: {str(e)}"
            }
