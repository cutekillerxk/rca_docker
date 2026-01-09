#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志读取模块
包含 DockerLogReader 类和日志读取相关函数
"""

import os
import json
import re
import logging
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .config import (
    LOG_FILES_CONFIG,
    DEFAULT_MAX_LINES,
    FILTER_INFO_LOGS,
    FILTER_CLASSPATH_LOGS,
    LOG_DIR,
    STATE_FILE
)

# 全局变量
docker_readers: Dict[str, 'DockerLogReader'] = {}  # Docker日志读取器

# ==================== Docker 日志读取器类 ====================

class DockerLogReader:
    """通过 Docker exec 读取容器日志文件"""
    
    def __init__(self, container: str, log_path: str):
        self.container = container
        self.log_path = log_path
        self._connected = True  # Docker exec不需要持久连接
    
    def list_log_files(self, node_pattern: Optional[str] = None) -> List[str]:
        """列出容器中的日志文件"""
        try:
            # 首先检查容器是否运行（跨平台方式：使用Python直接检查）
            check_result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=5
            )
            
            if check_result.returncode != 0 or self.container not in check_result.stdout:
                logging.warning(f"容器 {self.container} 未运行，无法列出日志文件")
                return []
            
            # 使用docker exec执行ls命令（兼容Windows PowerShell）
            # 先尝试列出所有文件，包括.log和.audit文件
            result = subprocess.run(
                f'docker exec {self.container} sh -c "ls -1 {self.log_path} 2>&1"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logging.warning(f"无法列出容器 {self.container} 的日志文件: {result.stderr}")
                return []
            
            files = result.stdout.strip().split('\n')
            files = [f for f in files if f.strip()]  # 移除空行
            # 包含.log和.audit文件（Hadoop的日志文件）
            log_files = [f for f in files if f.endswith(".log") or f.endswith(".audit") or f.endswith(".out")]
            
            if node_pattern:
                log_files = [f for f in log_files if node_pattern.lower() in f.lower()]
            
            return log_files
        except Exception as e:
            logging.error(f"列出日志文件失败: {e}")
            return []
    
    def read_log_file(self, file_path: str, start_pos: int = 0, 
                     max_lines: Optional[int] = None) -> Tuple[str, int]:
        """从容器文件读取日志"""
        try:
            # 如果文件路径不是绝对路径，拼接日志目录
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.log_path, file_path)
            
            # 确保路径使用正斜杠（容器内路径）
            file_path = file_path.replace('\\', '/')
            
            # 使用docker exec执行tail命令读取日志（兼容Windows PowerShell）
            # 使用字节位置确保完全准确
            escaped_path = file_path.replace("'", "'\"'\"'")
            
            if max_lines:
                # 读取指定行数（从文件末尾或指定位置）
                if start_pos == 0:
                    # 从文件末尾读取
                    result = subprocess.run(
                        f'docker exec {self.container} sh -c "tail -n {max_lines} \'{escaped_path}\' 2>&1"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                else:
                    # 从指定字节位置读取，然后在Python中限制行数（完全准确）
                    result = subprocess.run(
                        f'docker exec {self.container} sh -c "tail -c +{start_pos} \'{escaped_path}\' 2>&1"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
            else:
                # 读取全部（从指定位置）
                if start_pos == 0:
                    result = subprocess.run(
                        f'docker exec {self.container} sh -c "cat \'{escaped_path}\' 2>&1"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                else:
                    result = subprocess.run(
                        f'docker exec {self.container} sh -c "tail -c +{start_pos} \'{escaped_path}\' 2>&1"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                logging.error(f"读取日志文件失败 (容器: {self.container}, 文件: {file_path}, 返回码: {result.returncode}): {error_msg}")
                return "", start_pos
            
            content = result.stdout
            
            # 如果指定了max_lines且从指定位置读取，需要在Python中限制行数
            if max_lines and start_pos != 0:
                lines = content.split('\n')
                content = '\n'.join(lines[:max_lines])
            
            # 计算新位置：使用实际读取内容的字节数（完全准确）
            new_pos = start_pos + len(content.encode('utf-8'))
            
            return content, new_pos
            
        except Exception as e:
            logging.error(f"读取日志文件失败 (容器: {self.container}, 文件: {file_path}): {e}")
            import traceback
            logging.debug(traceback.format_exc())
            return "", start_pos
    
    def get_file_mtime(self, file_path: str) -> Optional[float]:
        """获取容器内文件的修改时间"""
        try:
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.log_path, file_path)
            
            result = subprocess.run(
                f'docker exec {self.container} sh -c "stat -c %Y {file_path} 2>&1"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                try:
                    return float(result.stdout.strip())
                except ValueError:
                    return None
            return None
        except Exception as e:
            logging.error(f"获取文件修改时间失败: {e}")
            return None
    
    def check_file_exists(self, file_path: str) -> bool:
        """检查容器内文件是否存在"""
        try:
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.log_path, file_path)
            
            result = subprocess.run(
                f'docker exec {self.container} sh -c "test -f {file_path} 2>&1"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logging.error(f"检查文件是否存在失败: {e}")
            return False

# ==================== 日志读取功能 ====================

def should_filter_log_line(line: str, filter_info: bool = True, filter_classpath: bool = True) -> bool:
    """
    判断是否应该过滤该日志行
    
    Args:
        line: 日志行内容
        filter_info: 是否过滤INFO级别日志
        filter_classpath: 是否过滤classpath行
    
    Returns:
        True表示应该过滤（跳过），False表示保留
    """
    if not line.strip():
        return False  # 空行保留
    
    # 过滤classpath行
    if filter_classpath:
        if re.search(r'STARTUP_MSG:\s+classpath\s*=', line, re.IGNORECASE):
            return True
    
    # 过滤INFO级别日志
    if filter_info:
        # 匹配标准格式：时间戳 + INFO
        if re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\s]+\d+\s+INFO\s+', line):
            return True
    
    return False  # 保留该行


def read_latest_logs(path: str, last_pos: int, node_pattern: Optional[str] = None, max_lines: int = DEFAULT_MAX_LINES) -> Tuple[List[str], int]:
    """滚动读取最新日志（本地）"""
    print(f"读取最新日志: {path}")
    try:
        if not os.path.exists(path) or not os.path.isdir(path):
            return [], last_pos
        
        if not os.access(path, os.R_OK):
            logging.warning(f"无读取权限: {path}")
            return [], last_pos
        
        try:
            all_log_files = [f for f in os.listdir(path) if f.endswith(".log")]
        except PermissionError:
            logging.warning(f"无权限列出目录内容: {path}")
            return [], last_pos
        
        if node_pattern:
            log_files = [f for f in all_log_files if node_pattern.lower() in f.lower()]
        else:
            log_files = all_log_files
        
        if not log_files:
            return [], last_pos
        
        log_files_with_time = []
        for f in log_files:
            try:
                file_path = os.path.join(path, f)
                mtime = os.path.getmtime(file_path)
                log_files_with_time.append((f, mtime))
            except (OSError, PermissionError):
                continue
        
        if not log_files_with_time:
            return [], last_pos
        
        log_files_with_time.sort(key=lambda x: x[1], reverse=True)
        latest_file = os.path.join(path, log_files_with_time[0][0])
        
        if not os.access(latest_file, os.R_OK):
            logging.warning(f"无读取权限: {latest_file}")
            return [], last_pos
        
        current_size = os.path.getsize(latest_file)
        if last_pos > current_size:
            logging.info(f"日志文件可能被轮转，重置读取位置: {latest_file}")
            last_pos = 0
        
        with open(latest_file, "r", encoding='utf-8', errors='ignore') as f:
            f.seek(last_pos)
            lines = [] 
            for i in range(max_lines):
                line = f.readline()
                if not line:
                    break
                # 过滤日志
                if not should_filter_log_line(line, FILTER_INFO_LOGS, FILTER_CLASSPATH_LOGS):
                    lines.append(line)
            new_pos = f.tell()
        
        return lines, new_pos
        
    except Exception as e:
        logging.warning(f"Failed to read logs from {path}: {e}")
        return [], last_pos


def read_latest_logs_docker(docker_reader: DockerLogReader, last_pos: int,
                            node_pattern: Optional[str] = None, max_lines: int = DEFAULT_MAX_LINES,
                            last_file: Optional[str] = None) -> Tuple[List[str], int, Optional[str]]:
    """通过 Docker exec 读取容器最新日志（强制从日志文件读取，不回退到docker_logs）"""
    print(f"通过 Docker 读取容器日志: {docker_reader.container}")
    try:
        # 强制从日志文件读取，不回退到docker_logs
        log_files = docker_reader.list_log_files(node_pattern)
        
        if not log_files:
            # 如果没有找到日志文件，返回错误信息
            error_msg = f"未找到日志文件（容器: {docker_reader.container}, 路径: {docker_reader.log_path}, 模式: {node_pattern}）"
            logging.warning(error_msg)
            return [], last_pos, last_file
        
        # 有日志文件，尝试读取文件
        log_files_with_time = []
        for f in log_files:
            mtime = docker_reader.get_file_mtime(f)
            if mtime:
                log_files_with_time.append((f, mtime))
        
        if not log_files_with_time:
            # 如果无法获取文件时间，使用第一个文件
            logging.warning(f"无法获取日志文件修改时间，使用第一个文件: {log_files[0]}")
            latest_file = log_files[0]
        else:
            log_files_with_time.sort(key=lambda x: x[1], reverse=True)
            latest_file = log_files_with_time[0][0]
        
        if last_file and last_file != latest_file:
            logging.info(f"检测到日志文件切换: {last_file} -> {latest_file}，重置读取位置")
            last_pos = 0
        
        # 读取日志文件内容
        content, new_pos = docker_reader.read_log_file(latest_file, last_pos, max_lines=max_lines)
        
        if not content:
            # 文件为空，返回空列表
            logging.info(f"日志文件 {latest_file} 为空")
            return [], new_pos, latest_file
        
        lines = content.splitlines(keepends=True)
        
        # 过滤日志（去除INFO级别和classpath行）
        filtered_lines = []
        for line in lines:
            if not should_filter_log_line(line, FILTER_INFO_LOGS, FILTER_CLASSPATH_LOGS):
                filtered_lines.append(line)
        
        # 始终返回过滤后的内容（即使为空）
        # 如果过滤后为空，说明日志都是INFO级别，无需展示
        if not filtered_lines:
            logging.info(f"日志文件 {latest_file} 过滤后无异常日志（全为INFO级别）")
        
        return filtered_lines, new_pos, latest_file
        
    except Exception as e:
        error_msg = f"读取容器日志文件失败（容器: {docker_reader.container}, 路径: {docker_reader.log_path}）: {str(e)}"
        logging.error(error_msg)
        # 出错时返回空列表，不回退到docker_logs
        return [], last_pos, last_file


def init_docker_readers():
    """初始化 Docker 读取器"""
    print("初始化 Docker 读取器")
    global docker_readers
    
    for log_config in LOG_FILES_CONFIG:
        if log_config["type"] == "docker":
            container = log_config.get("container")
            if container and container not in docker_readers:
                docker_readers[container] = DockerLogReader(
                    container=container,
                    log_path=log_config["log_path"]
                )


def load_log_reader_state(num_log_files: int) -> Tuple[List[int], List[Optional[str]]]:
    """从文件加载日志读取器的状态"""
    print("从文件加载日志读取器的状态")
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                last_positions = state.get('last_positions', [0] * num_log_files)
                last_files = state.get('last_files', [None] * num_log_files)
                
                if len(last_positions) != num_log_files:
                    last_positions = [0] * num_log_files
                if len(last_files) != num_log_files:
                    last_files = [None] * num_log_files
                
                return last_positions, last_files
        else:
            return [0] * num_log_files, [None] * num_log_files
    except Exception as e:
        logging.warning(f"加载状态文件失败: {e}，使用默认值")
        return [0] * num_log_files, [None] * num_log_files


def save_log_reader_state(last_positions: List[int], last_files: List[Optional[str]]):
    """保存日志读取器的状态到文件"""
    print("保存日志读取器的状态到文件")
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        
        state = {
            'last_positions': last_positions,
            'last_files': last_files,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.warning(f"保存状态文件失败: {e}")


def read_all_cluster_logs(max_lines: int = DEFAULT_MAX_LINES, 
                          last_positions: Optional[List[int]] = None,
                          last_files: Optional[List[Optional[str]]] = None) -> Tuple[Dict[str, str], List[int], List[Optional[str]]]:
    """读取所有5个节点的日志"""
    print("读取所有5个节点的日志")
    logs = {}
    num_log_files = len(LOG_FILES_CONFIG)
    
    if last_positions is None:
        last_positions = [0] * num_log_files
    if last_files is None:
        last_files = [None] * num_log_files
    
    if len(last_positions) != num_log_files:
        last_positions = [0] * num_log_files
    if len(last_files) != num_log_files:
        last_files = [None] * num_log_files
    
    init_docker_readers()  # 初始化Docker读取器
    
    new_positions = []
    new_files = []
    
    for i, log_config in enumerate(LOG_FILES_CONFIG):
        node_name = log_config["display_name"]
        log_path = log_config["log_path"]
        node_pattern = log_config.get("node_pattern")
        
        try:
            if log_config["type"] == "local":
                lines, new_pos = read_latest_logs(
                    log_path, 
                    last_pos=last_positions[i],
                    node_pattern=node_pattern,
                    max_lines=max_lines
                )
                log_content = "".join(lines)
                new_positions.append(new_pos)
                new_files.append(None)
            elif log_config["type"] == "docker":
                container = log_config.get("container")
                docker_reader = docker_readers.get(container) if container else None
                
                if docker_reader:
                    lines, new_pos, current_file = read_latest_logs_docker(
                        docker_reader,
                        last_pos=last_positions[i],
                        node_pattern=node_pattern,
                        max_lines=max_lines,
                        last_file=last_files[i]
                    )
                    log_content = "".join(lines)
                    new_positions.append(new_pos)
                    new_files.append(current_file)
                else:
                    log_content = f"无法连接到容器 {container}"
                    new_positions.append(last_positions[i])
                    new_files.append(last_files[i])
            else:
                # 其他类型（如ssh，已废弃）
                log_content = f"不支持的日志类型: {log_config.get('type')}"
                new_positions.append(last_positions[i])
                new_files.append(last_files[i])
            
            logs[node_name] = log_content if log_content else "无新日志"
            
        except Exception as e:
            logs[node_name] = f"读取日志失败: {str(e)}"
            new_positions.append(last_positions[i])
            new_files.append(last_files[i])
    
    return logs, new_positions, new_files


def get_node_log_by_name(node_name: str) -> str:
    """根据节点名称获取日志"""
    print(f"根据节点名称获取日志: {node_name}")
    node_name_lower = node_name.lower()
    target_config = None
    
    for config in LOG_FILES_CONFIG:
        display_name = config.get("display_name", "").lower()
        if (node_name_lower in display_name or 
            display_name in node_name_lower or
            (node_name_lower == "namenode" and "namenode" in display_name) or
            (node_name_lower == "secondarynamenode" and "secondarynamenode" in display_name)):
            target_config = config
            break
    
    if not target_config:
        # 更新支持的节点列表
        supported_nodes = [config["display_name"] for config in LOG_FILES_CONFIG]
        return f"未找到节点: {node_name}。支持的节点: {', '.join(supported_nodes)}"
    
    # 加载状态
    num_log_files = len(LOG_FILES_CONFIG)
    last_positions, last_files = load_log_reader_state(num_log_files)
    
    # 找到目标节点的索引
    target_idx = None
    for i, config in enumerate(LOG_FILES_CONFIG):
        if config == target_config:
            target_idx = i
            break
    
    if target_idx is None:
        return f"未找到节点配置: {node_name}"
    
    # 读取该节点的日志
    log_path = target_config["log_path"]
    node_pattern = target_config.get("node_pattern")
    
    try:
        if target_config["type"] == "local":
            lines, _ = read_latest_logs(
                log_path,
                last_pos=last_positions[target_idx],
                node_pattern=node_pattern,
                max_lines=DEFAULT_MAX_LINES
            )
            log_content = "".join(lines)
        elif target_config["type"] == "docker":
            container = target_config.get("container")
            init_docker_readers()
            docker_reader = docker_readers.get(container) if container else None
            
            if docker_reader:
                lines, _, _ = read_latest_logs_docker(
                    docker_reader,
                    last_pos=last_positions[target_idx],
                    node_pattern=node_pattern,
                    max_lines=DEFAULT_MAX_LINES,
                    last_file=last_files[target_idx]
                )
                log_content = "".join(lines)
            else:
                log_content = f"无法连接到容器 {container}"
        else:
            log_content = f"不支持的日志类型: {target_config.get('type')}"
        
        return log_content if log_content else "无新日志"
    except Exception as e:
        return f"读取日志失败: {str(e)}"


def _extract_timestamp(line: str) -> Optional[str]:
    """从日志行中提取时间戳（简单实现）"""
    # 尝试匹配常见的时间戳格式
    # 例如: 2024-01-01 12:00:00, 2024-01-01T12:00:00, 01/01/2024 12:00:00
    patterns = [
        r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
        r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(0)
    
    return None

