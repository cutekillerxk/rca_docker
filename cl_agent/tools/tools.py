#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
包含所有Agent使用的工具函数定义
"""

import os
import re
import logging
import subprocess
import time
from typing import List, Optional
from datetime import datetime

from langchain.tools import tool

# 导入配置
from ..config import (
    LOG_FILES_CONFIG,
    DEFAULT_MAX_LINES,
    ALLOWED_CONTAINERS,
    CONTAINER_TO_DAEMON,
    REPAIR_TEMPLATES
)

# 导入日志读取相关函数
from ..log_reader import (
    read_all_cluster_logs,
    get_node_log_by_name,
    load_log_reader_state,
    save_log_reader_state,
    _extract_timestamp
)

# 导入Hadoop操作辅助函数
from ..hadoop_utils import (
    _check_container_running,
    _validate_hadoop_operation_command,
    _is_safe_hadoop_command
)


@tool("get_cluster_logs", description="获取集群所有节点的最新日志内容，用于查看集群状态和分析集群问题。返回所有节点（NameNode、DataNode、SecondaryNameNode）的最新日志，已过滤INFO级别日志。")
def get_cluster_logs() -> str:
    """获取集群所有节点的最新日志内容。"""
    print("调用get_cluster_logs工具")
    try:
        num_log_files = len(LOG_FILES_CONFIG)
        last_positions, last_files = load_log_reader_state(num_log_files)
        
        all_logs, new_positions, new_files = read_all_cluster_logs(
            max_lines=DEFAULT_MAX_LINES,
            last_positions=last_positions,
            last_files=last_files
        )
        
        save_log_reader_state(new_positions, new_files)
        
        # 构建带思考检查点的返回内容
        result = []
        result.append("[集群日志分析任务]")
        result.append(f"共发现 {len(all_logs)} 个节点需要分析。")
        result.append("请逐个分析每个节点的日志，每个节点分析一次。")
        result.append("分析完一个节点后，记录分析结果，然后继续下一个节点。")
        result.append("")
        
        node_list = list(all_logs.items())
        for idx, (node_name, log_content) in enumerate(node_list, 1):
            result.append(f"=== {node_name} ===")
            result.append(log_content)
            result.append("")
            
            # 添加思考检查点（最后一个节点除外）
            if idx < len(node_list):
                result.append(f"[思考点{idx}] 请分析 {node_name} 的日志，识别问题并记录分析结果。")
                result.append(f"分析完成后，继续查看下一个节点（共{len(node_list)}个节点，当前第{idx}个）。")
                result.append("")
            else:
                result.append(f"[思考点{idx}] 请分析 {node_name} 的日志，识别问题并记录分析结果。")
                result.append("这是最后一个节点，分析完成后，请汇总所有节点的分析结果。")
                result.append("")
        
        result.append("[汇总提示] 所有节点已分析完毕，请汇总所有节点的分析结果，给出整体诊断和解决方案。")
        
        # 将结果写入文件
        result_text = "\n".join(result)
        try:
            # 确定result目录路径（相对于当前文件：rca/cl_agent/tools/tools.py -> rca/result）
            current_dir = os.path.dirname(os.path.abspath(__file__))  # rca/cl_agent/tools
            cl_agent_dir = os.path.dirname(current_dir)  # rca/cl_agent
            rca_dir = os.path.dirname(cl_agent_dir)  # rca
            result_dir = os.path.join(rca_dir, "result")
            
            # 确保目录存在
            os.makedirs(result_dir, exist_ok=True)
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"cluster_logs_{timestamp}.txt"
            file_path = os.path.join(result_dir, filename)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result_text)
            
            print(f"[INFO] 集群日志已保存到: {file_path}")
        except Exception as e:
            logging.warning(f"保存集群日志到文件失败: {e}")
            # 即使保存失败，也继续返回结果
        
        return result_text
    except Exception as e:
        return f"获取集群日志失败: {str(e)}"


@tool("get_node_log", description="获取指定节点的日志内容，用于分析单个节点的状态。参数node_name: 节点名称（如namenode、datanode1、datanode2等）。")
def get_node_log(node_name: str) -> str:
    """获取指定节点的日志内容。"""
    print("调用get_node_log工具")
    try:
        log_content = get_node_log_by_name(node_name)
        return log_content
    except Exception as e:
        return f"获取节点日志失败: {str(e)}"


@tool("get_monitoring_metrics", description="获取集群的实时监控指标（通过JMX接口）。返回NameNode和DataNodes的关键指标，包括节点状态、存储使用率、数据块状态等。")
def get_monitoring_metrics() -> str:
    """获取集群的实时监控指标。"""
    print("调用get_monitoring_metrics工具")
    try:
        from ..monitor_collector import collect_all_metrics, format_metrics_for_display
        
        metrics = collect_all_metrics()
        html_content = format_metrics_for_display(metrics)
        
        # 将 HTML 转换为纯文本（移除 HTML 标签，保留内容）
        text_content = re.sub(r'<[^>]+>', '', html_content)
        text_content = text_content.replace('✅', '[正常]')
        text_content = text_content.replace('⚠️', '[异常]')
        text_content = text_content.replace('❌', '[错误]')
        try:
            # 确定metrics目录路径（相对于当前文件：rca/cl_agent/tools/tools.py -> rca/metrics）
            current_dir = os.path.dirname(os.path.abspath(__file__))  # rca/cl_agent/tools
            cl_agent_dir = os.path.dirname(current_dir)  # rca/cl_agent
            rca_dir = os.path.dirname(cl_agent_dir)  # rca
            result_dir = os.path.join(rca_dir, "metrics")
            
            # 确保目录存在
            os.makedirs(result_dir, exist_ok=True)
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"metrics_{timestamp}.txt"
            file_path = os.path.join(result_dir, filename)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            print(f"[INFO] 集群监控指标已保存到: {file_path}")
        except Exception as e:
            logging.warning(f"保存集群监控指标到文件失败: {e}")
            # 即使保存失败，也继续返回结果
        return text_content
    except Exception as e:
        return f"获取监控指标失败: {str(e)}"


@tool("search_logs_by_keyword", description="在指定节点日志中搜索关键词，快速定位问题。参数：node_name（节点名称）、keyword（搜索关键词，如ERROR、WARN、Exception）、max_results（最大返回结果数，默认50）。")
def search_logs_by_keyword(node_name: str, keyword: str, max_results: int = 50) -> str:
    """在指定节点日志中搜索关键词。"""
    print(f"调用search_logs_by_keyword工具: node={node_name}, keyword={keyword}, max_results={max_results}")
    try:
        # 1. 获取节点日志
        log_content = get_node_log_by_name(node_name)
        
        if not log_content or log_content.startswith("未找到节点") or log_content.startswith("读取日志失败"):
            return f"无法获取 {node_name} 的日志: {log_content}"
        
        # 2. 搜索关键词
        lines = log_content.split('\n')
        matches = []
        keyword_lower = keyword.lower()
        
        for i, line in enumerate(lines):
            if keyword_lower in line.lower():
                # 获取上下文（前后各2行）
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context_lines = lines[start:end]
                context = '\n'.join(context_lines)
                matches.append({
                    'line_num': i + 1,
                    'context': context,
                    'matched_line': line
                })
                
                if len(matches) >= max_results:
                    break
        
        # 3. 格式化返回
        if not matches:
            return f"在 {node_name} 的日志中未找到关键词 '{keyword}'（共搜索了 {len(lines)} 行）"
        
        result = []
        result.append(f"在 {node_name} 的日志中找到 {len(matches)} 条匹配 '{keyword}' 的记录（共搜索 {len(lines)} 行）：\n")
        result.append("=" * 80)
        
        for idx, match in enumerate(matches, 1):
            result.append(f"\n[匹配 {idx}] 第 {match['line_num']} 行:")
            result.append("-" * 80)
            result.append(match['context'])
            result.append("-" * 80)
        
        if len(matches) >= max_results:
            result.append(f"\n[提示] 已显示前 {max_results} 条匹配结果，可能还有更多结果。")
        
        return "\n".join(result)
    except Exception as e:
        error_msg = f"搜索日志失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


@tool("get_error_logs_summary", description="统计各节点的错误/警告数量，快速了解问题分布。参数node_name（可选）：如果提供则只统计指定节点，不提供则统计所有节点。返回错误数量、错误类型分布、最新错误时间等。")
def get_error_logs_summary(node_name: Optional[str] = None) -> str:
    """统计各节点的错误/警告数量。"""
    print(f"调用get_error_logs_summary工具: node_name={node_name}")
    try:
        error_keywords = ['ERROR', 'WARN', 'Exception', 'FATAL', 'CRITICAL']
        all_summaries = []
        
        # 确定要统计的节点列表
        if node_name:
            # 只统计指定节点
            nodes_to_check = [node_name]
        else:
            # 统计所有节点
            nodes_to_check = [config["display_name"] for config in LOG_FILES_CONFIG]
        
        # 遍历节点统计错误
        for node in nodes_to_check:
            try:
                log_content = get_node_log_by_name(node)
                
                if not log_content or log_content.startswith("未找到节点") or log_content.startswith("读取日志失败"):
                    all_summaries.append({
                        'node': node,
                        'status': 'error',
                        'error': log_content
                    })
                    continue
                
                lines = log_content.split('\n')
                errors = []
                warnings = []
                
                # 解析日志，查找错误和警告
                for i, line in enumerate(lines):
                    line_upper = line.upper()
                    
                    # 检查是否是错误
                    if any(keyword in line_upper for keyword in ['ERROR', 'FATAL', 'CRITICAL', 'EXCEPTION']):
                        errors.append({
                            'line_num': i + 1,
                            'line': line.strip(),
                            'timestamp': _extract_timestamp(line)
                        })
                    # 检查是否是警告
                    elif 'WARN' in line_upper:
                        warnings.append({
                            'line_num': i + 1,
                            'line': line.strip(),
                            'timestamp': _extract_timestamp(line)
                        })
                
                # 统计错误类型
                error_types = {}
                for err in errors:
                    # 尝试提取错误类型（简单方法：取第一个单词或关键词）
                    error_type = "Unknown"
                    for keyword in ['ERROR', 'FATAL', 'CRITICAL', 'EXCEPTION']:
                        if keyword in err['line'].upper():
                            error_type = keyword
                            break
                    error_types[error_type] = error_types.get(error_type, 0) + 1
                
                all_summaries.append({
                    'node': node,
                    'status': 'success',
                    'total_lines': len(lines),
                    'error_count': len(errors),
                    'warning_count': len(warnings),
                    'error_types': error_types,
                    'latest_error': errors[-1] if errors else None,
                    'latest_warning': warnings[-1] if warnings else None,
                    'errors': errors[:10],  # 只保留前10个错误
                    'warnings': warnings[:10]  # 只保留前10个警告
                })
            except Exception as e:
                all_summaries.append({
                    'node': node,
                    'status': 'error',
                    'error': f"处理节点日志时出错: {str(e)}"
                })
        
        # 格式化返回结果
        result = []
        result.append("=" * 80)
        result.append("错误日志统计摘要")
        result.append("=" * 80)
        
        total_errors = 0
        total_warnings = 0
        
        for summary in all_summaries:
            if summary['status'] == 'error':
                result.append(f"\n[{summary['node']}] ❌ 无法获取日志: {summary['error']}")
                continue
            
            node = summary['node']
            error_count = summary['error_count']
            warning_count = summary['warning_count']
            total_errors += error_count
            total_warnings += warning_count
            
            result.append(f"\n[{node}]")
            result.append(f"  总行数: {summary['total_lines']}")
            result.append(f"  错误数: {error_count}")
            result.append(f"  警告数: {warning_count}")
            
            if error_count > 0:
                result.append(f"  错误类型分布: {summary['error_types']}")
                if summary['latest_error']:
                    result.append(f"  最新错误 (第{summary['latest_error']['line_num']}行): {summary['latest_error']['line'][:100]}")
            
            if warning_count > 0 and summary['latest_warning']:
                result.append(f"  最新警告 (第{summary['latest_warning']['line_num']}行): {summary['latest_warning']['line'][:100]}")
            
            # 显示前几个错误示例
            if summary['errors']:
                result.append(f"\n  错误示例（前{min(3, len(summary['errors']))}个）:")
                for err in summary['errors'][:3]:
                    result.append(f"    - 第{err['line_num']}行: {err['line'][:80]}")
        
        result.append("\n" + "=" * 80)
        result.append(f"总计: {len(nodes_to_check)} 个节点, {total_errors} 个错误, {total_warnings} 个警告")
        result.append("=" * 80)
        
        return "\n".join(result)
    except Exception as e:
        error_msg = f"统计错误日志失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


@tool("hadoop_auto_operation", description="""
执行Hadoop集群操作（在容器内启动/停止/重启Hadoop服务）。

**参数说明**：
- operation: 操作类型，可选值：start/stop/restart
- container: 容器名称（可选），可选值：namenode, datanode1, datanode2
  - 如果指定container，则操作单个节点的Hadoop服务
  - 如果不指定container（None），则操作整个集群（在namenode容器内执行start-dfs.sh/stop-dfs.sh）

**使用示例**：
- 启动NameNode: operation="start", container="namenode"
- 停止DataNode1: operation="stop", container="datanode1"
- 重启NameNode: operation="restart", container="namenode"
- 启动整个集群: operation="start", container=None
- 停止整个集群: operation="stop", container=None

**注意**：容器必须已运行，否则返回错误
""")
def hadoop_auto_operation(operation: str, container: Optional[str] = None) -> str:
    """执行Hadoop集群操作（在容器内执行Hadoop服务命令）。"""
    print(f"调用hadoop_auto_operation工具: operation={operation}, container={container}")
    
    # 参数验证
    operation = operation.lower().strip()
    if operation not in ['start', 'stop', 'restart']:
        return f"❌ 错误：不支持的操作类型 '{operation}'。支持的操作：start, stop, restart"
    
    # 如果是单节点操作，验证容器名
    if container is not None:
        container = container.lower().strip()
        if container not in ALLOWED_CONTAINERS:
            return f"❌ 错误：不支持的容器名称 '{container}'。支持的容器：{', '.join(ALLOWED_CONTAINERS)}"
    
    # 构建command_args用于验证（兼容原有验证逻辑）
    if container:
        command_args = [operation, container]
    else:
        command_args = [operation]
    
    # 安全性验证
    is_safe, error_msg = _validate_hadoop_operation_command(command_args)
    if not is_safe:
        return f"❌ 错误：{error_msg}"
    
    # 确定是单节点操作还是整个集群操作
    is_cluster_operation = container is None
    
    # 确定操作名称（中文）
    operation_name_map = {
        'start': '启动',
        'stop': '停止',
        'restart': '重启'
    }
    operation_name = operation_name_map.get(operation, operation)
    
    # 如果是整个集群操作
    if is_cluster_operation:
        if operation == 'restart':
            return "❌ 错误：重启整个集群不支持，请先停止整个集群，再启动整个集群"
        
        # 检查namenode容器是否运行
        if not _check_container_running('namenode'):
            return "❌ 错误：namenode容器未运行，无法执行集群操作"
        
        # 构建命令：在namenode容器内执行start-dfs.sh或stop-dfs.sh
        script_name = 'start-dfs.sh' if operation == 'start' else 'stop-dfs.sh'
        # 使用su - hadoop切换到hadoop用户，并设置环境变量
        hadoop_env = "export HADOOP_HOME=/usr/local/hadoop && export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH && "
        command_str = f"su - hadoop -c '{hadoop_env}{script_name}'"
        docker_command = ['docker', 'exec', 'namenode', 'sh', '-c', command_str]
        target_desc = "整个集群"
        
    else:
        # 单节点操作（container已经验证过，直接使用）
        
        # 检查容器是否运行
        if not _check_container_running(container):
            return f"❌ 错误：容器 '{container}' 未运行，无法执行操作"
        
        # 获取Hadoop服务类型
        daemon_type = CONTAINER_TO_DAEMON.get(container)
        if not daemon_type:
            return f"❌ 错误：无法确定容器 '{container}' 对应的Hadoop服务类型"
        
        # 处理重启操作（先stop再start）
        if operation == 'restart':
            # 先停止
            hadoop_env = "export HADOOP_HOME=/usr/local/hadoop && export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH && "
            stop_command_str = f"su - hadoop -c '{hadoop_env}hdfs --daemon stop {daemon_type}'"
            stop_docker_command = ['docker', 'exec', container, 'sh', '-c', stop_command_str]
            
            # 再启动
            start_command_str = f"su - hadoop -c '{hadoop_env}hdfs --daemon start {daemon_type}'"
            start_docker_command = ['docker', 'exec', container, 'sh', '-c', start_command_str]
            
            try:
                # 执行停止
                print(f"执行停止命令：{' '.join(stop_docker_command)}")
                stop_result = subprocess.run(
                    stop_docker_command,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    timeout=30
                )
                
                # 等待一下
                time.sleep(2)
                
                # 执行启动
                print(f"执行启动命令：{' '.join(start_docker_command)}")
                start_result = subprocess.run(
                    start_docker_command,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    timeout=30
                )
                
                # 组合输出
                output_parts = []
                output_parts.append(f"节点 {container} 重启操作结果:")
                output_parts.append("-" * 60)
                output_parts.append("停止阶段:")
                if stop_result.stdout:
                    output_parts.append(f"标准输出:\n{stop_result.stdout}")
                if stop_result.stderr:
                    output_parts.append(f"标准错误:\n{stop_result.stderr}")
                output_parts.append("\n启动阶段:")
                if start_result.stdout:
                    output_parts.append(f"标准输出:\n{start_result.stdout}")
                if start_result.stderr:
                    output_parts.append(f"标准错误:\n{start_result.stderr}")
                output = "\n".join(output_parts)
                print(output)
                return output
                
            except subprocess.TimeoutExpired:
                return "❌ 执行超时（超过30秒）"
            except Exception as e:
                return f"❌ 执行失败: {str(e)}"
        
        # 构建命令：在容器内执行hdfs --daemon命令
        hadoop_env = "export HADOOP_HOME=/usr/local/hadoop && export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH && "
        command_str = f"su - hadoop -c '{hadoop_env}hdfs --daemon {operation} {daemon_type}'"
        docker_command = ['docker', 'exec', container, 'sh', '-c', command_str]
        target_desc = f"节点 {container}"
    
    # 执行命令
    try:
        print(f"执行命令：{' '.join(docker_command)}")
        result = subprocess.run(
            docker_command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=60  # 60秒超时
        )
        
        # 组合输出
        output_parts = []
        output_parts.append(f"{target_desc} {operation_name}操作结果:")
        output_parts.append("-" * 60)
        
        if result.stdout:
            output_parts.append(f"标准输出:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"标准错误:\n{result.stderr}")
        
        if result.returncode == 0:
            output_parts.append(f"\n✅ {operation_name}操作成功")
        else:
            output_parts.append(f"\n❌ {operation_name}操作失败 (返回码: {result.returncode})")
        
        output = "\n".join(output_parts)
        print(output)
        return output
        
    except subprocess.TimeoutExpired:
        error_msg = f"❌ 执行超时（超过60秒）"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ 执行失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


@tool("execute_hadoop_command", description="""
执行Hadoop命令（hdfs、hadoop、yarn等）。在容器内执行Hadoop管理命令。

**参数格式**：
- command_args: List[str]，Hadoop命令参数列表
- 示例：
  - HDFS命令：["hdfs", "dfsadmin", "-report"]、["hdfs", "dfsadmin", "-safemode", "get"]
  - YARN命令：["yarn", "application", "-list"]、["yarn", "application", "-status", "<application_id>"]、["yarn", "logs", "-applicationId", "<application_id>"]

**支持的命令**：
- hdfs: dfsadmin、fsck、dfs等（只读查询命令）
- hadoop: fs、version、classpath等
- yarn: application（-list、-status、-kill）、node（-list、-status）、logs（-applicationId）、top、queue等（只读查询命令）

**执行容器**：通常为namenode（集群级命令）
""")
def execute_hadoop_command(command_args: List[str]) -> str:
    """执行Hadoop命令（在容器内执行）。"""
    print(f"调用execute_hadoop_command工具: command_args={command_args}")
    
    # 参数验证
    if not isinstance(command_args, list):
        return f"❌ 错误：command_args 必须是列表格式，当前类型：{type(command_args).__name__}"
    
    if len(command_args) == 0:
        return "❌ 错误：command_args 不能为空"
    
    # 构建完整命令
    base_cmd = command_args[0]
    if base_cmd not in ['hdfs', 'hadoop', 'yarn']:
        return f"❌ 错误：不支持的命令 '{base_cmd}'。支持的命令：hdfs, hadoop, yarn"
    
    # 安全检查
    full_command_str = ' '.join(command_args)
    if not _is_safe_hadoop_command(full_command_str):
        return f"❌ 错误：命令 '{full_command_str}' 不在允许的白名单中或包含危险操作"
    
    # 确定目标容器（集群级命令通常在namenode执行）
    target_container = "namenode"
    
    # 构建docker exec命令
    # 设置Hadoop环境变量并切换到hadoop用户
    hadoop_env = "export HADOOP_HOME=/usr/local/hadoop && export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH && "
    command_str = f"su - hadoop -c '{hadoop_env}{' '.join(command_args)}'"
    full_command = ['docker', 'exec', target_container, 'sh', '-c', command_str]
    
    try:
        # 执行命令
        print(f"执行命令：{' '.join(full_command)}")
        result = subprocess.run(
            full_command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=60  # 60秒超时
        )
        
        # 组合输出
        output_parts = []
        output_parts.append(f"Hadoop命令执行结果:")
        output_parts.append("-" * 60)
        
        if result.stdout:
            output_parts.append(f"标准输出:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"标准错误:\n{result.stderr}")
        
        if result.returncode == 0:
            output_parts.append(f"\n✅ 命令执行成功")
        else:
            output_parts.append(f"\n❌ 命令执行失败 (返回码: {result.returncode})")
        
        output = "\n".join(output_parts)
        print(output)
        return output
        
    except subprocess.TimeoutExpired:
        error_msg = f"❌ 执行超时（超过60秒）"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ 执行失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


@tool("generate_repair_plan", description="""
生成Hadoop集群修复计划。根据诊断结果生成结构化的修复计划。

**参数说明**：
- fault_type: 故障类型，可选值：
  - HDFS故障：
    - "datanode_down": DataNode下线
    - "cluster_id_mismatch": 集群ID不匹配
    - "namenode_safemode": NameNode安全模式
  - YARN故障：
    - "resourcemanager_down": ResourceManager下线
    - "nodemanager_down": NodeManager下线
    - "yarn_config_error": YARN配置错误
  - MapReduce故障：
    - "mapreduce_memory_insufficient": MapReduce任务内存不足
    - "mapreduce_disk_insufficient": MapReduce任务磁盘空间不足
    - "mapreduce_shuffle_failed": MapReduce Shuffle阶段失败
    - "mapreduce_task_timeout": MapReduce任务超时
  - "custom": 自定义故障（将使用LLM生成计划）
- diagnosis_info: 诊断信息（字符串），包含故障详情、影响的节点等
- affected_nodes: 受影响的节点列表（可选），如：["datanode1", "datanode2"]

**返回格式**：JSON格式的修复计划，包含：
- plan_id: 计划ID
- fault_type: 故障类型
- description: 故障描述
- steps: 修复步骤列表（每个步骤包含action、description、tool、expected_result等）
- estimated_time: 预计修复时间（分钟）

**使用场景**：
1. 诊断完成后自动生成修复计划
2. 用户明确请求生成修复计划
""")
def generate_repair_plan(fault_type: str, diagnosis_info: str, affected_nodes: Optional[List[str]] = None) -> str:
    """
    生成修复计划
    
    Args:
        fault_type: 故障类型
        diagnosis_info: 诊断信息
        affected_nodes: 受影响的节点列表
    
    Returns:
        JSON格式的修复计划
    """
    print(f"调用generate_repair_plan工具: fault_type={fault_type}, affected_nodes={affected_nodes}")
    
    # 标准化故障类型
    fault_type = fault_type.lower().strip()
    
    # 如果故障类型在模板库中，使用模板生成计划
    if fault_type in REPAIR_TEMPLATES:
        template = REPAIR_TEMPLATES[fault_type]
        
        # 创建修复计划
        plan = {
            "plan_id": f"plan_{fault_type}_{int(datetime.now().timestamp())}",
            "fault_type": template["fault_type"],
            "description": template["description"],
            "diagnosis_info": diagnosis_info,
            "affected_nodes": affected_nodes or [],
            "steps": [],
            "estimated_time": len(template["steps"]) * 5,  # 每个步骤预计5分钟
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 填充步骤参数
        for step_template in template["steps"]:
            step = step_template.copy()
            
            # 如果步骤需要container参数，且模板中没有指定具体容器，使用受影响的节点
            if "container" in step:
                # 如果模板中已经指定了具体容器（如"datanode1"），保持原样
                if step["container"] in ALLOWED_CONTAINERS:
                    pass  # 保持模板中的容器设置
                # 如果模板中container为None（集群操作），保持原样
                elif step["container"] is None:
                    pass  # 保持None，表示集群操作
                # 如果模板中container是占位符（如"datanode"），且affected_nodes不为空，使用第一个节点
                elif affected_nodes and len(affected_nodes) > 0:
                    step["container"] = affected_nodes[0]
            # 如果步骤没有container参数，但需要操作DataNode，且affected_nodes不为空，添加container
            elif "target" in step and step["target"] in ["datanode", "datanode1", "datanode2"]:
                if affected_nodes and len(affected_nodes) > 0:
                    step["container"] = affected_nodes[0]
            
            plan["steps"].append(step)
        
        # 转换为JSON格式
        import json
        plan_json = json.dumps(plan, ensure_ascii=False, indent=2)
        
        print(f"✅ 修复计划生成成功（基于模板：{fault_type}）")
        return f"修复计划已生成：\n\n{plan_json}"
    
    # 如果故障类型不在模板库中，返回提示信息
    else:
        available_types = ", ".join(REPAIR_TEMPLATES.keys())
        return f"""❌ 错误：不支持的故障类型 '{fault_type}'。

支持的故障类型：
{available_types}

或者使用 "custom" 类型生成自定义修复计划。

当前诊断信息：
{diagnosis_info}

受影响的节点：{affected_nodes or '未指定'}"""

