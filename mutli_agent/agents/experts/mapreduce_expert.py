#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MapReduce专家Agent
负责MapReduce相关故障的深度诊断
"""

from typing import Dict, Any, Optional
from ...base import BaseAgent
import sys
import os

# 添加路径以导入配置和集群上下文
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from cl_agent.cluster_context import generate_system_prompt
from cl_agent.config import FAULT_TYPE_LIBRARY


class MapReduceExpertAgent(BaseAgent):
    """
    MapReduce专家Agent
    接收全局上下文，进行深度诊断，可以调用工具
    """
    
    def __init__(self, llm_client, tools: Optional[Dict[str, Any]] = None):
        """初始化MapReduce专家Agent"""
        system_prompt = self._load_system_prompt()
        
        # 注入MapReduce相关的工具
        mapreduce_tools = {}
        if tools:
            mapreduce_tool_names = [
                "get_cluster_logs",
                "get_node_log",
                "get_monitoring_metrics",
                "execute_hadoop_command",
                "search_logs_by_keyword",
            ]
            for tool_name in mapreduce_tool_names:
                if tool_name in tools:
                    mapreduce_tools[tool_name] = tools[tool_name]
        
        super().__init__(
            llm_client=llm_client,
            system_prompt=system_prompt,
            role="mapreduce_expert",
            tools=mapreduce_tools
        )
    
    def _load_system_prompt(self) -> str:
        """加载系统提示"""
        base_prompt = generate_system_prompt()
        
        expert_prompt = f"""{base_prompt}

## 你的角色
你是MapReduce故障诊断专家，专门处理MapReduce任务相关的故障。

## MapReduce故障类型
你需要诊断的MapReduce故障类型包括：
- mapreduce_memory_insufficient: MapReduce任务内存不足
- mapreduce_disk_insufficient: MapReduce任务磁盘空间不足
- mapreduce_shuffle_failed: MapReduce Shuffle阶段失败
- mapreduce_task_timeout: MapReduce任务超时

## 诊断要求
1. **深度分析**：基于全局上下文（日志、指标、集群状态）进行深度分析
2. **识别根因**：不仅要识别症状，还要找出根本原因
3. **提供证据**：列出支持诊断的具体证据（日志片段、指标值等）
4. **修复建议**：提供清晰的修复步骤

## 工具调用（如需要）
如果当前信息不足以完成诊断，你可以请求调用工具。请输出以下JSON格式：
{{
  "action": "call_tool",
  "tool": "execute_hadoop_command",
  "args": {{"command_args": ["yarn", "application", "-list", "-appStates", "FAILED"]}}
}}

## 输出格式
请以对话风格的文本输出诊断结果，包含：
1. **故障识别**：明确说明检测到的故障类型
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
        
        if fault_type in FAULT_TYPE_LIBRARY:
            fault_info = FAULT_TYPE_LIBRARY[fault_type]
            prompt_parts.append(f"故障名称：{fault_info['fault_type']}")
            prompt_parts.append(f"严重程度：{fault_info.get('severity', 'unknown')}")
            prompt_parts.append("")
        
        # 添加用户查询
        if "user_query" in input_data and input_data["user_query"]:
            prompt_parts.append(f"用户查询：{input_data['user_query']}")
            prompt_parts.append("")
        
        # 添加全局日志（优先显示YARN和MapReduce相关）
        if "logs" in input_data and input_data["logs"]:
            prompt_parts.append("## 全局日志上下文")
            if isinstance(input_data["logs"], dict):
                # 优先显示YARN相关节点（MapReduce任务运行在YARN上）
                yarn_nodes = ["resourcemanager", "nodemanager", "historyserver"]
                for node_name in yarn_nodes:
                    if node_name in input_data["logs"]:
                        prompt_parts.append(f"\n### {node_name}")
                        log_content = input_data["logs"][node_name]
                        log_preview = log_content[:1000] if len(log_content) > 1000 else log_content
                        prompt_parts.append(log_preview)
                        if len(log_content) > 1000:
                            prompt_parts.append(f"... (日志已截断)")
            prompt_parts.append("")
        
        # 添加监控指标
        if "metrics" in input_data and input_data["metrics"]:
            prompt_parts.append("## 关键监控指标")
            # MapReduce相关指标
            prompt_parts.append("")
        
        # 添加集群状态
        if "cluster_state" in input_data and input_data["cluster_state"]:
            prompt_parts.append("## 集群状态")
            state = input_data["cluster_state"]
            prompt_parts.append(f"- HDFS状态：{state.get('hdfs_status', 'unknown')}")
            prompt_parts.append("")
        
        # 添加诊断要求
        prompt_parts.append("## 诊断任务")
        prompt_parts.append("请基于上述全局上下文，进行深度诊断：")
        prompt_parts.append("1. 识别故障的根本原因")
        prompt_parts.append("2. 列出支持诊断的证据")
        prompt_parts.append("3. 提供清晰的修复步骤")
        prompt_parts.append("4. 说明诊断的置信度")
        
        return "\n".join(prompt_parts)
    
    def parse_output(self, response: str) -> Dict[str, Any]:
        """解析诊断输出"""
        result = {
            "expert_name": "mapreduce_expert",
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
        return 0.8
