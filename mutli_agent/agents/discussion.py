#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discussion Agent
综合多个专家的诊断结果，识别一致性/冲突，生成最终诊断报告
"""

import json
from typing import Dict, Any, List
from ..base import BaseAgent
from ..schemas import DiscussionResult
import sys
import os

# 添加路径以导入集群上下文
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cl_agent.cluster_context import generate_system_prompt


class DiscussionAgent(BaseAgent):
    """
    Discussion Agent
    综合多个专家的诊断结果
    """
    
    def __init__(self, llm_client):
        """初始化Discussion Agent"""
        system_prompt = self._load_system_prompt()
        super().__init__(
            llm_client=llm_client,
            system_prompt=system_prompt,
            role="discussion",
            tools=None  # Discussion Agent不使用工具
        )
    
    def _load_system_prompt(self) -> str:
        """加载系统提示"""
        base_prompt = generate_system_prompt()
        
        discussion_prompt = f"""{base_prompt}

## 你的角色
你是讨论协调者，负责综合多个专家的诊断结果，生成最终诊断报告。

## 你的任务
1. **分析一致性**：检查多个专家的诊断结果是否一致
2. **识别冲突**：如果专家意见不一致，识别冲突点
3. **识别联动关系**：识别可能的复合故障（多个故障同时发生）
4. **综合结论**：基于所有专家的意见，生成综合诊断报告

## 输出格式要求
你必须输出有效的JSON格式，包含以下字段：
- consensus: 专家意见是否一致（布尔值）
- final_root_cause: 综合根因（字符串）
- final_evidence: 综合证据列表（字符串数组）
- final_fix_steps: 综合修复步骤列表（字符串数组）
- confidence: 综合置信度（0.0-1.0的浮点数）
- conflicts: 冲突描述列表（可选，字符串数组）
- compound_faults: 联动故障分析（可选，字符串数组）
- expert_agreement: 专家一致性分析（可选，字典，格式：{{"expert_name": agreement_score}}）

## 示例输出
{{
  "consensus": true,
  "final_root_cause": "DataNode下线导致副本数不足",
  "final_evidence": [
    "日志显示DataNode下线",
    "监控指标显示NumDeadDataNodes > 0",
    "集群状态显示HDFS状态为degraded"
  ],
  "final_fix_steps": [
    "检查DataNode容器状态",
    "重启DataNode服务",
    "验证DataNode恢复在线"
  ],
  "confidence": 0.95,
  "conflicts": null,
  "compound_faults": ["under_replicated_blocks"],
  "expert_agreement": {{
    "hdfs_expert": 0.95,
    "network_expert": 0.80
  }}
}}

请仔细分析所有专家的诊断结果，给出综合结论。"""
        
        return discussion_prompt
    
    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        """
        构建讨论prompt
        
        Args:
            input_data: 输入数据，包含：
                - fault_type: 故障类型
                - expert_results: 各专家的诊断结果列表
                - global_context: 全局上下文（可选）
        """
        prompt_parts = []
        
        # 添加故障类型
        fault_type = input_data.get("fault_type", "unknown")
        prompt_parts.append(f"## 故障类型")
        prompt_parts.append(f"故障类型：{fault_type}")
        prompt_parts.append("")
        
        # 添加各专家的诊断结果
        expert_results = input_data.get("expert_results", [])
        prompt_parts.append("## 各专家诊断结果")
        
        for idx, expert_result in enumerate(expert_results, 1):
            expert_name = expert_result.get("expert_name", f"expert_{idx}")
            prompt_parts.append(f"\n### {expert_name} 的诊断")
            
            # 显示诊断文本（如果有）
            if "diagnosis_text" in expert_result:
                prompt_parts.append(f"诊断文本：\n{expert_result['diagnosis_text'][:500]}...")
            
            # 显示结构化信息
            if "root_cause" in expert_result:
                prompt_parts.append(f"- 根本原因：{expert_result['root_cause']}")
            if "evidence" in expert_result:
                prompt_parts.append(f"- 证据：{expert_result['evidence']}")
            if "fix_steps" in expert_result:
                prompt_parts.append(f"- 修复步骤：{expert_result['fix_steps']}")
            if "confidence" in expert_result:
                prompt_parts.append(f"- 置信度：{expert_result['confidence']}")
            
            prompt_parts.append("")
        
        # 添加全局上下文（简化）
        if "global_context" in input_data and input_data["global_context"]:
            prompt_parts.append("## 全局上下文（参考）")
            context = input_data["global_context"]
            if "cluster_state" in context:
                state = context["cluster_state"]
                prompt_parts.append(f"- DataNode数量：存活 {state.get('datanode_count', {}).get('live', 0)}, "
                                  f"离线 {state.get('datanode_count', {}).get('dead', 0)}")
                prompt_parts.append(f"- HDFS状态：{state.get('hdfs_status', 'unknown')}")
            prompt_parts.append("")
        
        # 添加讨论要求
        prompt_parts.append("## 讨论任务")
        prompt_parts.append("请基于上述各专家的诊断结果，进行综合讨论：")
        prompt_parts.append("1. 检查专家意见是否一致")
        prompt_parts.append("2. 如果有冲突，识别冲突点")
        prompt_parts.append("3. 识别可能的联动故障")
        prompt_parts.append("4. 生成综合诊断报告（JSON格式）")
        
        return "\n".join(prompt_parts)
    
    def parse_output(self, response: str) -> Dict[str, Any]:
        """
        解析讨论输出
        
        Args:
            response: LLM返回的文本（应该是JSON格式）
        
        Returns:
            解析后的讨论结果字典
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
            required_fields = ["consensus", "final_root_cause", "final_evidence", "final_fix_steps", "confidence"]
            for field in required_fields:
                if field not in result_dict:
                    if field == "consensus":
                        result_dict[field] = True  # 默认一致
                    elif field == "confidence":
                        result_dict[field] = 0.8  # 默认置信度
                    elif field in ["final_evidence", "final_fix_steps"]:
                        result_dict[field] = []  # 默认空列表
                    elif field == "final_root_cause":
                        result_dict[field] = "未明确说明"
            
            # 创建DiscussionResult对象
            discussion = DiscussionResult(
                consensus=bool(result_dict.get("consensus", True)),
                final_root_cause=str(result_dict.get("final_root_cause", "未明确说明")),
                final_evidence=result_dict.get("final_evidence", []),
                final_fix_steps=result_dict.get("final_fix_steps", []),
                confidence=float(result_dict.get("confidence", 0.8)),
                conflicts=result_dict.get("conflicts"),
                compound_faults=result_dict.get("compound_faults"),
                expert_agreement=result_dict.get("expert_agreement")
            )
            
            return discussion.to_dict()
        
        except json.JSONDecodeError as e:
            # JSON解析失败
            print(f"[WARNING] Discussion输出解析失败: {e}")
            print(f"[WARNING] 原始响应: {response[:200]}")
            
            # 返回默认结果
            return {
                "consensus": True,
                "final_root_cause": "解析失败，请查看专家诊断结果",
                "final_evidence": ["解析失败"],
                "final_fix_steps": ["请参考各专家的诊断结果"],
                "confidence": 0.5,
                "conflicts": None,
                "compound_faults": None,
            }
