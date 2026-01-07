#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hadoop操作工具模块
包含Hadoop操作相关的辅助函数
"""

import os
import subprocess
from typing import List, Tuple, Optional

from .config import (
    ALLOWED_CONTAINERS,
    ALLOWED_HADOOP_OPERATIONS,
    ALLOWED_HADOOP_COMMANDS
)


def _is_safe_hadoop_command(command: str) -> bool:
    """
    检查命令是否在允许的白名单中
    
    Args:
        command: 要执行的命令
    
    Returns:
        True表示命令安全，False表示命令不安全
    """
    command = command.strip()
    
    # 禁止的危险命令
    dangerous_keywords = ['rm', 'delete', 'format', 'kill', 'killall', 'shutdown', 'reboot']
    for keyword in dangerous_keywords:
        if keyword in command.lower():
            return False
    
    # 检查是否在允许的命令列表中
    parts = command.split()
    if not parts:
        return False
    
    base_cmd = parts[0]
    
    # 检查是否是hadoop/hdfs相关命令
    if base_cmd in ['hdfs', 'hadoop']:
        if len(parts) > 1:
            subcmd = parts[1]
            if base_cmd in ALLOWED_HADOOP_COMMANDS:
                allowed_subcmds = ALLOWED_HADOOP_COMMANDS[base_cmd]
                if not allowed_subcmds or subcmd in allowed_subcmds:
                    return True
    
    # 检查是否是脚本命令
    if base_cmd in ALLOWED_HADOOP_COMMANDS:
        return True
    
    # 检查是否是daemon命令
    if 'daemon.sh' in base_cmd:
        if len(parts) > 1:
            action = parts[1]
            if action in ['start', 'stop', 'status']:
                return True
    
    return False


def _get_docker_compose_path() -> str:
    """
    动态获取 docker-compose.yml 文件的绝对路径
    
    Returns:
        docker-compose.yml 的绝对路径
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))  # rca/cl_agent
    project_root = os.path.dirname(current_dir)  # rca
    docker_compose_file = os.path.join(project_root, "docker-compose.yml")
    return docker_compose_file


def _check_container_running(container: str) -> bool:
    """
    检查容器是否运行
    
    Args:
        container: 容器名称
    
    Returns:
        True表示容器运行中，False表示容器未运行
    """
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=5
        )
        if result.returncode == 0:
            running_containers = result.stdout.strip().split('\n')
            return container in running_containers
        return False
    except Exception:
        return False


def _validate_hadoop_operation_command(command_args: List[str]) -> Tuple[bool, Optional[str]]:
    """
    验证Hadoop操作命令参数的安全性
    
    Args:
        command_args: 命令参数列表（如 ["restart", "namenode"] 或 ["stop"]）
    
    Returns:
        (是否安全, 错误信息)，如果安全返回 (True, None)，否则返回 (False, 错误信息)
    """
    if not command_args or len(command_args) == 0:
        return False, "命令参数不能为空"
    
    # 获取操作类型（第一个参数）
    operation = command_args[0].lower()
    
    # 验证操作类型
    if operation not in ALLOWED_HADOOP_OPERATIONS:
        return False, f"不支持的操作类型 '{operation}'。支持的操作：{', '.join(sorted(ALLOWED_HADOOP_OPERATIONS))}"
    
    # 对于单节点操作（start/stop/restart + 容器名），验证容器名
    if len(command_args) >= 2:
        container = command_args[1]
        if container not in ALLOWED_CONTAINERS:
            return False, f"不支持的容器名称 '{container}'。支持的容器：{', '.join(ALLOWED_CONTAINERS)}"
    
    # 检查是否有危险参数
    dangerous_keywords = ['rm', 'delete', 'format', 'kill', 'killall', 'shutdown', 'reboot', 'down']
    for arg in command_args:
        if any(keyword in arg.lower() for keyword in dangerous_keywords):
            return False, f"检测到危险操作参数: {arg}"
    
    return True, None

