#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HDFS专家Agent
负责HDFS相关故障的深度诊断
"""

from typing import Dict, Any, Optional
from ...base import BaseAgent
from ...schemas import ExpertDiagnosis
import sys
import os

# 添加路径以导入配置和集群上下文
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from cl_agent.cluster_context import generate_system_prompt
from cl_agent.config import FAULT_TYPE_LIBRARY


class HDFSExpertAgent(BaseAgent):
    """
    HDFS专家Agent
    接收全局上下文，进行深度诊断，可以调用工具
    """
    
    def __init__(self, llm_client, tools: Optional[Dict[str, Any]] = None):
        """初始化HDFS专家Agent"""
        system_prompt = self._load_system_prompt()
        
        # 只注入HDFS相关的工具
        hdfs_tools = {}
        if tools:
            # 选择HDFS相关的工具
            hdfs_tool_names = [
                "get_cluster_logs",
                "get_node_log",
                "get_monitoring_metrics",
                "execute_hadoop_command",
                "search_logs_by_keyword",
            ]
            for tool_name in hdfs_tool_names:
                if tool_name in tools:
                    hdfs_tools[tool_name] = tools[tool_name]
        
        super().__init__(
            llm_client=llm_client,
            system_prompt=system_prompt,
            role="hdfs_expert",
            tools=hdfs_tools
        )
    
    def _load_system_prompt(self) -> str:
        """加载系统提示"""
        base_prompt = generate_system_prompt()
        
        expert_prompt = f"""{base_prompt}

## 你的角色
你是HDFS故障诊断专家，专门处理HDFS相关的故障。

## HDFS故障类型
你需要诊断的HDFS故障类型包括：
- datanode_down: DataNode下线
- cluster_id_mismatch: 集群ID不匹配
- namenode_safemode: NameNode安全模式

## 诊断要求
1. **深度分析**：基于全局上下文（日志、指标、集群状态）进行深度分析
2. **识别根因**：不仅要识别症状，还要找出根本原因
3. **提供证据**：列出支持诊断的具体证据（日志片段、指标值等）
4. **修复建议**：提供清晰的修复步骤

## 工具调用（如需要）
如果当前信息不足以完成诊断，你可以请求调用工具。请输出以下JSON格式：
{{
  "action": "call_tool",
  "tool": "get_node_log",
  "args": {{"node_name": "namenode"}}
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
        """
        构建诊断prompt
        
        Args:
            input_data: 输入数据，包含：
                - fault_type: 故障类型（来自分类Agent）
                - logs: 全局日志
                - metrics: 全局监控指标
                - cluster_state: 集群状态
                - related_faults: 可能相关的故障（可选）
                - user_query: 用户查询（可选）
        """
        prompt_parts = []
        
        # 添加故障类型
        fault_type = input_data.get("fault_type", "unknown")
        prompt_parts.append(f"## 故障类型")
        prompt_parts.append(f"故障类型：{fault_type}")
        
        # 添加故障类型详细信息（如果存在）
        if fault_type in FAULT_TYPE_LIBRARY:
            fault_info = FAULT_TYPE_LIBRARY[fault_type]
            prompt_parts.append(f"故障名称：{fault_info['fault_type']}")
            prompt_parts.append(f"严重程度：{fault_info.get('severity', 'unknown')}")
            prompt_parts.append("")
        
        # 添加用户查询（如果有）
        if "user_query" in input_data and input_data["user_query"]:
            prompt_parts.append(f"用户查询：{input_data['user_query']}")
            prompt_parts.append("")
        
        # 添加全局日志（简化显示）
        if "logs" in input_data and input_data["logs"]:
            prompt_parts.append("## 全局日志上下文")
            if isinstance(input_data["logs"], dict):
                for node_name, log_content in list(input_data["logs"].items())[:3]:  # 只显示前3个节点
                    prompt_parts.append(f"\n### {node_name}")
                    log_preview = log_content[:1000] if len(log_content) > 1000 else log_content
                    prompt_parts.append(log_preview)
                    if len(log_content) > 1000:
                        prompt_parts.append(f"... (日志已截断)")
            prompt_parts.append("")
        
        # 添加监控指标（关键指标）
        if "metrics" in input_data and input_data["metrics"]:
            prompt_parts.append("## 关键监控指标")
            metrics = input_data["metrics"]
            
            # NameNode指标
            if "namenode" in metrics and metrics["namenode"].get("status") != "error":
                nn_metrics = metrics["namenode"].get("metrics", {})
                key_metrics = ["NumLiveDataNodes", "NumDeadDataNodes", "MissingBlocks", "CorruptBlocks"]
                for metric_name in key_metrics:
                    if metric_name in nn_metrics:
                        metric = nn_metrics[metric_name]
                        prompt_parts.append(f"- {metric['name']}: {metric['value']} ({metric.get('status', 'unknown')})")
            prompt_parts.append("")
        
        # 添加集群状态
        if "cluster_state" in input_data and input_data["cluster_state"]:
            prompt_parts.append("## 集群状态")
            state = input_data["cluster_state"]
            prompt_parts.append(f"- DataNode数量：存活 {state.get('datanode_count', {}).get('live', 0)}, "
                              f"离线 {state.get('datanode_count', {}).get('dead', 0)}")
            prompt_parts.append(f"- HDFS状态：{state.get('hdfs_status', 'unknown')}")
            prompt_parts.append("")
        
        # 添加可能相关的故障（如果有）
        if "related_faults" in input_data and input_data["related_faults"]:
            prompt_parts.append("## 可能相关的故障")
            for related_fault in input_data["related_faults"]:
                prompt_parts.append(f"- {related_fault}")
            prompt_parts.append("")
        
        # 添加工具调用结果（如果有）
        if "tool_results" in input_data and input_data["tool_results"]:
            prompt_parts.append("## 工具调用结果")
            for tool_item in input_data["tool_results"]:
                tool_name = tool_item.get("tool", "unknown_tool")
                prompt_parts.append(f"- 工具: {tool_name}")
                prompt_parts.append(f"  结果: {tool_item.get('result')}")
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
        """
        解析诊断输出
        
        Args:
            response: LLM返回的诊断文本（对话式）
        
        Returns:
            解析后的诊断结果字典
        """
        # 如果返回的是工具调用指令（JSON），触发工具调用
        parsed_tool_call = self._try_parse_tool_call(response)
        if parsed_tool_call:
            return parsed_tool_call
        
        # HDFS专家输出对话式文本，直接返回
        result = {
            "expert_name": "hdfs_expert",
            "diagnosis_text": response,  # 对话式诊断文本
            "root_cause": self._extract_root_cause(response),
            "evidence": self._extract_evidence(response),
            "fix_steps": self._extract_fix_steps(response),
            "confidence": self._extract_confidence(response),
        }
        
        return result
    
    def _try_parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """尝试解析工具调用指令"""
        import json
        text = response.strip()
        if not (text.startswith("{") and text.endswith("}")):
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        
        if data.get("action") == "call_tool" and data.get("tool"):
            return {
                "action": "call_tool",
                "tool": data.get("tool"),
                "args": data.get("args", {})
            }
        return None
    
    def _extract_root_cause(self, text: str) -> str:
        """从文本中提取根本原因"""
        # 简单提取：查找"根本原因"、"原因"等关键词
        import re
        patterns = [
            r"根本原因[：:]\s*(.+?)(?:\n|$)",
            r"原因[：:]\s*(.+?)(?:\n|$)",
            r"Root cause[：:]\s*(.+?)(?:\n|$)",
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
        
        # 查找列表项或证据段落
        patterns = [
            r"证据[：:]\s*(.+?)(?:\n\n|\n##|$)",
            r"Evidence[：:]\s*(.+?)(?:\n\n|\n##|$)",
            r"[-*]\s*(.+?)(?=\n[-*]|\n##|$)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                evidence.extend([m.strip() for m in matches[:5]])  # 最多5条证据
                break
        
        return evidence if evidence else ["详见诊断文本"]
    
    def _extract_fix_steps(self, text: str) -> list:
        """从文本中提取修复步骤"""
        import re
        steps = []
        
        # 查找步骤列表
        patterns = [
            r"修复步骤[：:]\s*(.+?)(?:\n\n|\n##|$)",
            r"Fix steps[：:]\s*(.+?)(?:\n\n|\n##|$)",
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
        # 查找置信度数字
        patterns = [
            r"置信度[：:]\s*(\d+\.?\d*)%?",
            r"Confidence[：:]\s*(\d+\.?\d*)%?",
            r"(\d+\.?\d*)\s*%?\s*确信",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    confidence = float(match.group(1))
                    # 如果是百分比，转换为0-1
                    if confidence > 1.0:
                        confidence = confidence / 100.0
                    return min(1.0, max(0.0, confidence))
                except:
                    pass
        
        # 默认置信度
        return 0.8
