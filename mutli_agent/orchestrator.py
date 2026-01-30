#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
总协调器（Orchestrator）
管理整个诊断流程：收集上下文 → 分类 → 选择专家 → 并行调用 → 讨论 → 返回结果
"""

from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .llm_client import LLMClient
from .schemas import DiagnosisReport, ClassificationResult, ExpertDiagnosis, DiscussionResult
from .agents.classifier import FaultClassifierAgent
from .agents.discussion import DiscussionAgent
from .agents.experts.hdfs_expert import HDFSExpertAgent
from .agents.experts.yarn_expert import YARNExpertAgent
from .agents.experts.mapreduce_expert import MapReduceExpertAgent
from .agents.experts.network_expert import NetworkExpertAgent
from .agents.experts.generic_expert import GenericExpertAgent
from .utils.context_collector import ContextCollector
from .utils.expert_selector import ExpertSelector
from .utils.tool_adapter import ToolAdapter


class FaultOrchestrator:
    """
    故障诊断协调器
    管理整个多智能体诊断流程
    """
    
    def __init__(self, llm_client: LLMClient, model_name: str = "qwen-8b"):
        """
        初始化协调器
        
        Args:
            llm_client: LLM客户端
            model_name: 模型名称（用于创建Agent）
        """
        self.llm_client = llm_client
        self.model_name = model_name
        
        # 初始化工具注册表
        self.tools_registry = ToolAdapter.create_tools_registry()
        
        # 初始化上下文收集器
        self.context_collector = ContextCollector()
        
        # 初始化专家选择器
        self.expert_selector = ExpertSelector()
        
        # 初始化分类Agent
        self.classifier = FaultClassifierAgent(llm_client)
        
        # 初始化Discussion Agent
        self.discussion_agent = DiscussionAgent(llm_client) 
        
        # 初始化专家Agents（延迟创建，按需创建）
        self.experts = {}
        self._init_experts()
    
    def _init_experts(self):
        """初始化专家Agents"""
        # HDFS专家
        self.experts["hdfs_expert"] = HDFSExpertAgent(
            llm_client=self.llm_client,
            tools=self.tools_registry
        )
        
        # YARN专家
        self.experts["yarn_expert"] = YARNExpertAgent(
            llm_client=self.llm_client,
            tools=self.tools_registry
        )
        
        # MapReduce专家
        self.experts["mapreduce_expert"] = MapReduceExpertAgent(
            llm_client=self.llm_client,
            tools=self.tools_registry
        )
        
        # 网络专家
        self.experts["network_expert"] = NetworkExpertAgent(
            llm_client=self.llm_client,
            tools=self.tools_registry
        )
        
        # 通用专家
        self.experts["generic_expert"] = GenericExpertAgent(
            llm_client=self.llm_client,
            tools=self.tools_registry
        )
    
    def _collect_global_context(self) -> Dict[str, Any]:
        """
        收集全局上下文
        
        Returns:
            全局上下文字典
        """
        print("[Orchestrator] 收集全局上下文...")
        context = self.context_collector.collect_all_context()
        print(f"[Orchestrator] 全局上下文收集完成（日志节点数: {len(context.get('logs', {}))}）")
        return context
    
    def _select_relevant_experts(
        self,
        fault_type: str,
        include_related: bool = True
    ) -> List[str]:
        """
        选择相关专家
        
        Args:
            fault_type: 故障类型
            include_related: 是否包含相关专家
        
        Returns:
            专家名称列表
        """
        experts = self.expert_selector.select_experts(
            fault_type=fault_type,
            include_related=include_related
        )
        print(f"[Orchestrator] 选择专家: {experts}")
        return experts
    
    def _call_expert(
        self,
        expert_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用单个专家
        
        Args:
            expert_name: 专家名称
            input_data: 输入数据
        
        Returns:
            专家诊断结果
        """
        if expert_name not in self.experts:
            print(f"[WARNING] 专家 {expert_name} 不存在，跳过")
            return {
                "expert_name": expert_name,
                "error": f"专家 {expert_name} 不存在"
            }
        
        try:
            expert = self.experts[expert_name]
            print(f"[Orchestrator] 调用专家: {expert_name}")
            result = expert.run(input_data)
            result["expert_name"] = expert_name
            print(f"[Orchestrator] 专家 {expert_name} 诊断完成")
            return result
        except Exception as e:
            print(f"[ERROR] 专家 {expert_name} 调用失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "expert_name": expert_name,
                "error": str(e)
            }
    
    def _call_experts_parallel(
        self,
        expert_names: List[str],
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        并行调用多个专家
        
        Args:
            expert_names: 专家名称列表
            input_data: 输入数据
        
        Returns:
            专家诊断结果列表
        """
        results = []
        
        # 使用线程池并行调用
        with ThreadPoolExecutor(max_workers=len(expert_names)) as executor:
            futures = {
                executor.submit(self._call_expert, expert_name, input_data): expert_name
                for expert_name in expert_names
            }
            
            for future in as_completed(futures):
                expert_name = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"[ERROR] 专家 {expert_name} 执行异常: {e}")
                    results.append({
                        "expert_name": expert_name,
                        "error": str(e)
                    })
        
        return results
    
    def diagnose(self, user_input: str, output_format: str = "text") -> Any:
        """
        完整诊断流程
        
        Args:
            user_input: 用户输入
        
        Returns:
            诊断结果（结构化或文本）
        """
        report = self._diagnose_structured(user_input)
        
        if output_format == "structured":
            return report
        
        # 默认返回文本输出（对话式）
        from .utils.response_formatter import ResponseFormatter
        formatted_text = ResponseFormatter.format_diagnosis_report(report)
        
        # 保存响应到 return 目录
        self._save_response(user_input, formatted_text)
        
        return formatted_text
    
    def _diagnose_structured(self, user_input: str) -> Dict[str, Any]:
        """返回结构化诊断报告"""
        print("\n" + "="*70)
        print("[Orchestrator] 开始诊断流程")
        print("="*70)
        
        # 步骤1：收集全局上下文
        print("\n[步骤1] 收集全局上下文...")
        global_context = self._collect_global_context()
        
        # 步骤2：分类
        print("\n[步骤2] 故障分类...")
        classification_input = {
            "logs": global_context.get("logs", {}),
            "metrics": global_context.get("metrics", {}),
            "user_query": user_input,
        }
        classification_result = self.classifier.run(classification_input)
        
        fault_type = classification_result.get("fault_type", "unknown")
        print(f"[Orchestrator] 分类结果: {fault_type} (置信度: {classification_result.get('confidence', 0.0)})")
        
        # 步骤3：选择相关专家
        print("\n[步骤3] 选择相关专家...")
        expert_names = self._select_relevant_experts(fault_type, include_related=True)
        
        # 步骤4：并行调用专家（注入全局上下文）
        print(f"\n[步骤4] 并行调用 {len(expert_names)} 个专家...")
        expert_input = {
            "fault_type": fault_type,
            "logs": global_context.get("logs", {}),
            "metrics": global_context.get("metrics", {}),
            "cluster_state": global_context.get("cluster_state", {}),
            "related_faults": classification_result.get("related_faults"),
            "user_query": user_input,
        }
        expert_results = self._call_experts_parallel(expert_names, expert_input)
        
        # 过滤掉有错误的专家结果
        valid_expert_results = [
            r for r in expert_results
            if "error" not in r
        ]
        
        if not valid_expert_results:
            print("[WARNING] 所有专家调用都失败了")
            return {
                "error": "所有专家调用都失败了",
                "classification": classification_result,
                "expert_results": expert_results,
            }
        
        # 步骤5：Discussion Agent综合
        print(f"\n[步骤5] Discussion Agent综合 {len(valid_expert_results)} 个专家的诊断结果...")
        discussion_input = {
            "fault_type": fault_type,
            "expert_results": valid_expert_results,
            "global_context": global_context,
        }
        discussion_result = self.discussion_agent.run(discussion_input)
        
        # 步骤6：构建完整诊断报告
        print("\n[步骤6] 构建诊断报告...")
        report = {
            "classification": classification_result,
            "expert_diagnoses": valid_expert_results,
            "discussion": discussion_result,
            "global_context": {
                "timestamp": global_context.get("timestamp"),
                "cluster_state": global_context.get("cluster_state", {}),
            },
        }
        
        print("\n" + "="*70)
        print("[Orchestrator] 诊断流程完成")
        print("="*70 + "\n")
        
        return report
    
    def diagnose_with_text_output(self, user_input: str) -> str:
        """
        诊断并返回格式化的文本输出（兼容现有系统）
        
        Args:
            user_input: 用户输入
        
        Returns:
            格式化的对话式文本
        """
        return self.diagnose(user_input, output_format="text")
    
    def _save_response(self, user_input: str, response: str) -> None:
        """保存诊断响应到 return 目录"""
        try:
            import os
            from datetime import datetime
            
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return_dir = os.path.join(base_dir, "return")
            os.makedirs(return_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_agent_response_{timestamp}.txt"
            filepath = os.path.join(return_dir, filename)
            
            content_lines = []
            content_lines.append("=" * 70)
            content_lines.append("Multi-Agent 响应记录")
            content_lines.append("=" * 70)
            content_lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content_lines.append(f"用户输入: {user_input}")
            content_lines.append("")
            content_lines.append("-" * 70)
            content_lines.append("最终响应:")
            content_lines.append("-" * 70)
            content_lines.append(response)
            content_lines.append("")
            content_lines.append("=" * 70)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(content_lines))
            
            print(f"[Orchestrator] 响应已保存到: {filepath}")
        except Exception as e:
            print(f"[WARNING] 保存响应失败: {e}")
