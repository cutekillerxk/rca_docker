#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具适配器
将LangChain的@tool装饰器函数转换为普通函数
适配现有工具系统，供新框架使用
"""

import inspect
from typing import Dict, Callable, Any
import sys
import os

# 添加路径以导入现有工具
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cl_agent.tools.tools import (
    get_cluster_logs,
    get_node_log,
    get_monitoring_metrics,
    search_logs_by_keyword,
    get_error_logs_summary,
    hadoop_auto_operation,
    execute_hadoop_command,
    generate_repair_plan
)


class ToolAdapter:
    """
    工具适配器
    将LangChain工具转换为普通函数字典
    """
    
    @staticmethod
    def extract_tool_function(tool_func: Callable) -> Callable:
        """
        提取工具的实际函数（移除LangChain装饰器）
        
        Args:
            tool_func: LangChain工具函数
        
        Returns:
            原始函数
        """
        # LangChain的@tool装饰器会包装原始函数
        # 通常原始函数在 __wrapped__ 属性中
        if hasattr(tool_func, '__wrapped__'):
            return tool_func.__wrapped__
        return tool_func
    
    @staticmethod
    def get_tool_signature(tool_func: Callable) -> Dict[str, Any]:
        """
        获取工具函数的签名信息
        
        Args:
            tool_func: 工具函数
        
        Returns:
            签名信息字典
        """
        sig = inspect.signature(tool_func)
        params = {}
        for param_name, param in sig.parameters.items():
            params[param_name] = {
                "name": param_name,
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
            }
        return params
    
    @staticmethod
    def create_tools_registry() -> Dict[str, Callable]:
        """
        创建工具注册表
        将现有LangChain工具转换为普通函数字典
        
        Returns:
            工具字典，格式：{"tool_name": tool_func}
        """
        tools = {}
        
        # 提取每个工具的实际函数
        tool_mappings = {
            "get_cluster_logs": get_cluster_logs,
            "get_node_log": get_node_log,
            "get_monitoring_metrics": get_monitoring_metrics,
            "search_logs_by_keyword": search_logs_by_keyword,
            "get_error_logs_summary": get_error_logs_summary,
            "hadoop_auto_operation": hadoop_auto_operation,
            "execute_hadoop_command": execute_hadoop_command,
            "generate_repair_plan": generate_repair_plan,
        }
        
        for tool_name, tool_func in tool_mappings.items():
            # 提取实际函数
            actual_func = ToolAdapter.extract_tool_function(tool_func)
            tools[tool_name] = actual_func
        
        return tools
    
    @staticmethod
    def get_tool_description(tool_name: str) -> str:
        """
        获取工具描述
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具描述
        """
        descriptions = {
            "get_cluster_logs": "获取集群所有节点的最新日志内容，用于查看集群状态和分析集群问题",
            "get_node_log": "获取指定节点的日志内容，用于分析单个节点的状态",
            "get_monitoring_metrics": "获取集群的实时监控指标（通过JMX接口）",
            "search_logs_by_keyword": "在指定节点日志中搜索关键词，快速定位问题",
            "get_error_logs_summary": "统计各节点的错误/警告数量，快速了解问题分布",
            "hadoop_auto_operation": "执行Hadoop集群操作（在容器内启动/停止/重启Hadoop服务）",
            "execute_hadoop_command": "执行Hadoop命令（hdfs、hadoop、yarn等）",
            "generate_repair_plan": "生成Hadoop集群修复计划",
        }
        return descriptions.get(tool_name, f"工具: {tool_name}")
