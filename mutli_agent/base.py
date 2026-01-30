#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaseAgent抽象基类
极简设计，支持工具注入和Role Token
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from .llm_client import LLMClient


class BaseAgent(ABC):
    """
    Agent抽象基类
    极简设计：只包含prompt构建、LLM调用、输出解析
    工具由外部注入，不在Agent内部硬编码
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        system_prompt: str,
        role: str,
        tools: Optional[Dict[str, Callable]] = None
    ):
        """
        初始化Agent
        
        Args:
            llm_client: LLM客户端
            system_prompt: 系统提示
            role: Role名称（用于Role Token），如 "classifier", "hdfs_expert"
            tools: 工具字典，格式：{"tool_name": tool_func}
        """
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.role = role
        self.tools = tools or {}
    
    @abstractmethod
    def build_prompt(self, input_data: Dict[str, Any]) -> str:
        """
        构建prompt
        
        Args:
            input_data: 输入数据字典
        
        Returns:
            构建好的prompt字符串
        """
        pass
    
    @abstractmethod
    def parse_output(self, response: str) -> Dict[str, Any]:
        """
        解析LLM输出
        
        Args:
            response: LLM返回的原始文本
        
        Returns:
            解析后的结构化数据
        """
        pass
    
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            args: 工具参数
        
        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            raise ValueError(f"未知工具: {tool_name}")
        
        tool_func = self.tools[tool_name]
        
        # 调用工具函数
        try:
            if isinstance(args, dict):
                result = tool_func(**args)
            else:
                result = tool_func(args)
            return result
        except Exception as e:
            raise RuntimeError(f"工具 {tool_name} 执行失败: {str(e)}")
    
    def run(self, input_data: Dict[str, Any], max_tool_calls: int = 2) -> Dict[str, Any]:
        """
        运行Agent
        
        Args:
            input_data: 输入数据字典
        
        Returns:
            Agent输出（已解析的结构化数据）
        """
        tool_call_count = 0
        current_input = dict(input_data)
        
        while True:
            # 1. 构建prompt
            prompt = self.build_prompt(current_input)
            
            # 2. 调用LLM（使用Role Token）
            response = self.llm_client.generate_with_role(
                role=self.role,
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=0  # 默认temperature=0，子类可覆盖
            )
            
            # 3. 解析输出
            parsed = self.parse_output(response)
            
            # 4. 工具调用循环（可选）
            if isinstance(parsed, dict) and parsed.get("action") == "call_tool":
                tool_call_count += 1
                if tool_call_count > max_tool_calls:
                    return {
                        "error": "工具调用次数超限",
                        "last_response": response
                    }
                
                tool_name = parsed.get("tool")
                tool_args = parsed.get("args", {})
                tool_result = self._execute_tool(tool_name, tool_args)
                
                # 将工具结果写回上下文，继续下一轮
                current_input = dict(current_input)
                tool_results = current_input.get("tool_results", [])
                tool_results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result
                })
                current_input["tool_results"] = tool_results
                continue
            
            return parsed
