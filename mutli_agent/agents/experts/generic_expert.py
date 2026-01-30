#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用专家Agent
负责处理未知或通用故障的深度诊断
"""

from typing import Dict, Any, Optional
from ...base import BaseAgent
import sys
import os

# 添加路径以导入配置和集群上下文
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from cl_agent.cluster_context import generate_system_prompt
from cl_agent.config import FAULT_TYPE_LIBRARY


class GenericExpertAgent(BaseAgent):
    """
    通用专家Agent
    接收全局上下文，进行深度诊断，可以调用工具
    用于处理未知故障或通用故障
    """
    
    def __init__(self, llm_client, tools: Optional[Dict[str, Any]] = None):
        """初始化通用专家Agent"""
        system_prompt = self._load_system_prompt()
        
        # 注入所有可用工具（通用专家需要更多工具）
        generic_tools = tools or {}
        
        super().__init__(
            llm_client=llm_client,
            system_prompt=system_prompt,
            role="generic_expert",
            tools=generic_tools
        )
    
    def _load_system_prompt(self) -> str:
        """加载系统提示"""
        base_prompt = generate_system_prompt()
        
        expert_prompt = f"""{base_prompt}

## 你的角色
你是通用故障诊断专家，负责处理未知故障或跨组件的复合故障。

## 诊断范围
你需要诊断的故障包括：
- 未知类型的故障
- 跨组件的复合故障
- 无法明确归类的故障

## 诊断要求
1. **全面分析**：基于全局上下文（日志、指标、集群状态）进行全面分析
2. **识别根因**：不仅要识别症状，还要找出根本原因
3. **提供证据**：列出支持诊断的具体证据（日志片段、指标值等）
4. **修复建议**：提供清晰的修复步骤

## 工具调用（如需要）
如果当前信息不足以完成诊断，你可以请求调用工具。请输出以下JSON格式：
{{
  "action": "call_tool",
  "tool": "get_cluster_logs",
  "args": {{}}
}}

## 输出格式
请以对话风格的文本输出诊断结果，包含：
1. **故障识别**：明确说明检测到的故障类型（如果可能）
2. **根本原因**：详细分析根本原因
3. **证据列表**：列出支持诊断的证据（日志片段、指标等）
4. **修复步骤**：提供清晰的修复步骤
5. **置信度**：说明诊断的置信度（0.0-1.0）

请用专业、清晰的语言进行诊断。"""
        
        return expert_prompt
    
    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        """构建诊断prompt"""
        prompt_parts = []
        
        # 添加故障类型
        fault_type = input_data.get("fault_type", "unknown")
        prompt_parts.append(f"## 故障类型")
        prompt_parts.append(f"故障类型：{fault_type}")
        if fault_type != "unknown" and fault_type in FAULT_TYPE_LIBRARY:
            fault_info = FAULT_TYPE_LIBRARY[fault_type]
            prompt_parts.append(f"故障名称：{fault_info['fault_type']}")
            prompt_parts.append(f"严重程度：{fault_info.get('severity', 'unknown')}")
        else:
            prompt_parts.append("注意：这是一个未知或通用故障，需要全面分析")
        prompt_parts.append("")
        
        # 添加用户查询
        if "user_query" in input_data and input_data["user_query"]:
            prompt_parts.append(f"用户查询：{input_data['user_query']}")
            prompt_parts.append("")
        
        # 添加全局日志（显示所有节点）
        if "logs" in input_data and input_data["logs"]:
            prompt_parts.append("## 全局日志上下文（所有节点）")
            if isinstance(input_data["logs"], dict):
                for node_name, log_content in list(input_data["logs"].items())[:5]:
                    prompt_parts.append(f"\n### {node_name}")
                    log_preview = log_content[:800] if len(log_content) > 800 else log_content
                    prompt_parts.append(log_preview)
                    if len(log_content) > 800:
                        prompt_parts.append(f"... (日志已截断)")
            prompt_parts.append("")
        
        # 添加监控指标
        if "metrics" in input_data and input_data["metrics"]:
            prompt_parts.append("## 监控指标")
            metrics = input_data["metrics"]
            # 显示关键指标
            prompt_parts.append("")
        
        # 添加集群状态
        if "cluster_state" in input_data and input_data["cluster_state"]:
            prompt_parts.append("## 集群状态")
            state = input_data["cluster_state"]
            if "datanode_count" in state:
                prompt_parts.append(f"- DataNode数量：存活 {state['datanode_count'].get('live', 0)}, "
                                  f"离线 {state['datanode_count'].get('dead', 0)}")
            prompt_parts.append(f"- HDFS状态：{state.get('hdfs_status', 'unknown')}")
            prompt_parts.append("")
        
        # 添加可能相关的故障
        if "related_faults" in input_data and input_data["related_faults"]:
            prompt_parts.append("## 可能相关的故障")
            for related_fault in input_data["related_faults"]:
                prompt_parts.append(f"- {related_fault}")
            prompt_parts.append("")
        
        # 添加诊断要求
        prompt_parts.append("## 诊断任务")
        prompt_parts.append("请基于上述全局上下文，进行全面诊断：")
        prompt_parts.append("1. 识别故障的根本原因（可能是复合故障）")
        prompt_parts.append("2. 列出支持诊断的证据")
        prompt_parts.append("3. 提供清晰的修复步骤")
        prompt_parts.append("4. 说明诊断的置信度")
        
        return "\n".join(prompt_parts)
    
    def parse_output(self, response: str) -> Dict[str, Any]:
        """解析诊断输出"""
        result = {
            "expert_name": "generic_expert",
            "diagnosis_text": response,
            "root_cause": self._extract_root_cause(response),
            "evidence": self._extract_evidence(response),
            "fix_steps": self._extract_fix_steps(response),
            "confidence": self._extract_confidence(response),
        }
        return result
    
    def _extract_root_cause(self, text: str) -> str:
        """从文本中提取根本原因"""
        import re
        patterns = [
            r"根本原因[：:]\s*(.+?)(?:\n|$)",
            r"原因[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return "未明确说明"
    
    def _extract_evidence(self, text: str) -> list:
        """从文本中提取证据"""
        import re
        evidence = []
        patterns = [
            r"证据[：:]\s*(.+?)(?:\n\n|\n##|$)",
            r"[-*]\s*(.+?)(?=\n[-*]|\n##|$)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                evidence.extend([m.strip() for m in matches[:5]])
                break
        return evidence if evidence else ["详见诊断文本"]
    
    def _extract_fix_steps(self, text: str) -> list:
        """从文本中提取修复步骤"""
        import re
        steps = []
        patterns = [
            r"修复步骤[：:]\s*(.+?)(?:\n\n|\n##|$)",
            r"(\d+[\.、])\s*(.+?)(?=\n\d+[\.、]|\n##|$)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                if isinstance(matches[0], tuple):
                    steps = [m[1].strip() if len(m) > 1 else m[0].strip() for m in matches[:10]]
                else:
                    steps = [m.strip() for m in matches[:10]]
                break
        return steps if steps else ["详见诊断文本"]
    
    def _extract_confidence(self, text: str) -> float:
        """从文本中提取置信度"""
        import re
        patterns = [
            r"置信度[：:]\s*(\d+\.?\d*)%?",
            r"(\d+\.?\d*)\s*%?\s*确信",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    confidence = float(match.group(1))
                    if confidence > 1.0:
                        confidence = confidence / 100.0
                    return min(1.0, max(0.0, confidence))
                except:
                    pass
        return 0.7  # 通用专家默认置信度稍低
