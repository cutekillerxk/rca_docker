#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应格式化工具
将结构化诊断报告转换为对话式文本格式
"""

from typing import Dict, Any
import re


class ResponseFormatter:
    """
    响应格式化器
    将多智能体框架的结构化输出转换为用户友好的文本格式
    """
    
    @staticmethod
    def format_diagnosis_report(report: Dict[str, Any]) -> str:
        """
        格式化诊断报告为对话式文本
        
        Args:
            report: 诊断报告字典
        
        Returns:
            格式化的文本字符串
        """
        parts = []
        
        # 1. 分类结果
        if "classification" in report:
            classification = report["classification"]
            parts.append("## 📋 故障分类结果")
            parts.append(f"**故障类型**：{classification.get('fault_type', 'unknown')}")
            parts.append(f"**置信度**：{classification.get('confidence', 0.0):.1%}")
            parts.append(f"**类别**：{classification.get('category', 'unknown')}")
            if classification.get("reasoning"):
                parts.append(f"**分类理由**：{classification['reasoning']}")
            parts.append("")
        
        # 2. 专家诊断结果
        if "expert_diagnoses" in report and report["expert_diagnoses"]:
            parts.append("## 🔍 专家诊断详情")
            for idx, expert_diag in enumerate(report["expert_diagnoses"], 1):
                expert_name = expert_diag.get("expert_name", f"专家{idx}")
                parts.append(f"\n### {expert_name} 的诊断")
                
                # 诊断文本（如果有）
                if "diagnosis_text" in expert_diag:
                    parts.append(expert_diag["diagnosis_text"])
                else:
                    # 结构化信息
                    if "root_cause" in expert_diag:
                        parts.append(f"**根本原因**：{expert_diag['root_cause']}")
                    if "evidence" in expert_diag and expert_diag["evidence"]:
                        parts.append("**证据**：")
                        for evidence in expert_diag["evidence"]:
                            parts.append(f"- {evidence}")
                    if "fix_steps" in expert_diag and expert_diag["fix_steps"]:
                        parts.append("**修复步骤**：")
                        for step in expert_diag["fix_steps"]:
                            parts.append(f"- {step}")
                    if "confidence" in expert_diag:
                        parts.append(f"**置信度**：{expert_diag['confidence']:.1%}")
                parts.append("")
        
        # 3. 综合讨论结果
        if "discussion" in report:
            discussion = report["discussion"]
            parts.append("## 💬 综合诊断结论")
            
            if discussion.get("consensus"):
                parts.append("✅ **专家意见一致**")
            else:
                parts.append("⚠️ **专家意见存在分歧**")
                if discussion.get("conflicts"):
                    parts.append("**冲突点**：")
                    for conflict in discussion["conflicts"]:
                        parts.append(f"- {conflict}")
            
            parts.append(f"\n**综合根因**：{discussion.get('final_root_cause', '未明确说明')}")
            
            if discussion.get("final_evidence"):
                parts.append("\n**综合证据**：")
                for evidence in discussion["final_evidence"]:
                    parts.append(f"- {evidence}")
            
            if discussion.get("final_fix_steps"):
                parts.append("\n**综合修复步骤**：")
                for step in discussion["final_fix_steps"]:
                    parts.append(f"- {step}")
            
            parts.append(f"\n**综合置信度**：{discussion.get('confidence', 0.0):.1%}")
            
            if discussion.get("compound_faults"):
                parts.append("\n**联动故障分析**：")
                for fault in discussion["compound_faults"]:
                    parts.append(f"- {fault}")
            
            parts.append("")
        
        # 4. 集群状态（如果有）
        if "global_context" in report and "cluster_state" in report["global_context"]:
            state = report["global_context"]["cluster_state"]
            parts.append("## 📊 集群状态快照")
            if "datanode_count" in state:
                parts.append(f"- DataNode数量：存活 {state['datanode_count'].get('live', 0)}, "
                           f"离线 {state['datanode_count'].get('dead', 0)}")
            if "hdfs_status" in state:
                parts.append(f"- HDFS状态：{state['hdfs_status']}")
            parts.append("")
        
        return "\n".join(parts)
    
    @staticmethod
    def clean_response(response: str) -> str:
        """
        清理LLM响应（移除推理标记等）
        
        Args:
            response: 原始响应文本
        
        Returns:
            清理后的文本
        """
        # 移除常见的推理标记
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = re.sub(r'<reasoning>.*?</reasoning>', '', response, flags=re.DOTALL)
        # 移除其他可能的XML标签（但保留内容）
        # 注意：这里不删除所有XML标签，因为可能包含有用的格式标记
        # response = re.sub(r'<[^>]+>', '', response)
        
        # 清理多余的空白字符
        response = re.sub(r'\n{3,}', '\n\n', response)  # 多个换行符合并为两个
        response = response.strip()
        
        return response
