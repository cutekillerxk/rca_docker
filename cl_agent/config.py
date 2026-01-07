#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置常量模块
包含所有配置常量：日志配置、Hadoop操作配置、修复方案模板等
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==================== JMX API 配置 ====================

# JMX API 地址
# Docker环境：本机Docker容器端口映射
NAMENODE = "http://localhost:9870/jmx"
DATANODES = [
    "http://127.0.0.1:9864/jmx",  # datanode1
    "http://127.0.0.1:9865/jmx",  # datanode2
    "http://127.0.0.1:9866/jmx",  # datanode-namenode
]

# ==================== 日志文件配置 ====================

# 日志文件配置
# Docker环境：从容器内日志文件读取
# 日志路径：/usr/local/hadoop/logs/ (HADOOP_HOME=/usr/local/hadoop)
# 注意：namenode容器中运行了3个服务：namenode, datanode, secondarynamenode
# 所以需要读取5个日志文件：
# 1. namenode容器：hadoop-hadoop-namenode-namenode.log
# 2. namenode容器：hadoop-hadoop-datanode-namenode.log
# 3. namenode容器：hadoop-hadoop-secondarynamenode-namenode.log
# 4. datanode1容器：hadoop-hadoop-datanode-datanode1.log
# 5. datanode2容器：hadoop-hadoop-datanode-datanode2.log
LOG_FILES_CONFIG = [
    {
        "name": "namenode",
        "display_name": "NameNode",
        "type": "docker",
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "namenode",  # 匹配 hadoop-hadoop-namenode-namenode.log
        "ip": "127.0.0.1"
    },
    {
        "name": "datanode-namenode",
        "display_name": "DataNode (NameNode容器)",
        "type": "docker",
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "datanode",  # 匹配 hadoop-hadoop-datanode-namenode.log
        "ip": "127.0.0.1"
    },
    {
        "name": "secondarynamenode",
        "display_name": "SecondaryNameNode",
        "type": "docker",
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "secondarynamenode",  # 匹配 hadoop-hadoop-secondarynamenode-namenode.log
        "ip": "127.0.0.1"
    },
    {
        "name": "datanode1",
        "display_name": "DataNode1",
        "type": "docker",
        "container": "datanode1",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "datanode",  # 匹配 hadoop-hadoop-datanode-datanode1.log
        "ip": "127.0.0.1"
    },
    {
        "name": "datanode2",
        "display_name": "DataNode2",
        "type": "docker",
        "container": "datanode2",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "datanode",  # 匹配 hadoop-hadoop-datanode-datanode2.log
        "ip": "127.0.0.1"
    }
]

# Docker 容器配置
# 日志路径已确认：/usr/local/hadoop/logs/ (HADOOP_HOME=/usr/local/hadoop)
# 注意：namenode容器中运行了3个服务，所以有3个日志文件
DOCKER_CONFIG = {
    "namenode": {
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
    },
    "datanode-namenode": {
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
    },
    "secondarynamenode": {
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
    },
    "datanode1": {
        "container": "datanode1",
        "log_path": "/usr/local/hadoop/logs",
    },
    "datanode2": {
        "container": "datanode2",
        "log_path": "/usr/local/hadoop/logs",
    }
}

# 路径配置
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
STATE_FILE = os.path.join(LOG_DIR, "log_reader_state.json")
os.makedirs(LOG_DIR, exist_ok=True)

# 日志过滤配置
FILTER_INFO_LOGS = True      # 是否过滤INFO级别日志
FILTER_CLASSPATH_LOGS = True  # 是否过滤classpath行

# 日志读取配置
DEFAULT_MAX_LINES = 200  # 默认读取日志行数

# ==================== vLLM 配置 ====================

VLLM_BASE_URL = "http://10.157.197.76:8001/v1"
VLLM_MODEL_PATH = "/media/hnu/LLM/hnu/LLM/Qwen3-8B"

# ==================== 第三方 API 配置 ====================

# 第三方 API 配置（从环境变量读取）
THIRD_PARTY_API_BASE_URL = os.getenv("API_BASE_URL", "")  # 第三方 API base_url
THIRD_PARTY_API_KEY = os.getenv("API_KEY", "")  # 第三方 API key（DeepSeek 和 GPT 共用）

# ==================== Hadoop集群操作配置 ====================

# Docker 容器白名单
ALLOWED_CONTAINERS = ['namenode', 'datanode1', 'datanode2']

# 允许的 Hadoop 操作类型
ALLOWED_HADOOP_OPERATIONS = {
    'start',      # 启动单个Hadoop服务或整个集群
    'stop',       # 停止单个Hadoop服务或整个集群
    'restart',    # 重启单个Hadoop服务（先stop再start）
}

# 容器到Hadoop服务类型的映射
CONTAINER_TO_DAEMON = {
    'namenode': 'namenode',
    'datanode1': 'datanode',
    'datanode2': 'datanode',
}

# Hadoop操作命令白名单（安全控制）
ALLOWED_HADOOP_COMMANDS = {
    # 查询类命令（只读，安全）
    'hdfs': ['dfsadmin', '-report', '-safemode', 'get', 'df', 'ls', 'du', 'fsck'],
    'hadoop': ['fs', 'version', 'classpath'],
    # 集群管理命令（需要谨慎使用）
    'start-dfs.sh': [],
    'stop-dfs.sh': [],
    'start-yarn.sh': [],
    'stop-yarn.sh': [],
    'start-all.sh': [],
    'stop-all.sh': [],
    # 节点管理命令
    'hadoop-daemon.sh': ['start', 'stop', 'status'],
    'hdfs-daemon.sh': ['start', 'stop', 'status'],
    'yarn-daemon.sh': ['start', 'stop', 'status'],
}

# ==================== 修复方案模板库 ====================

# 修复方案模板库
# 每个模板包含：故障类型、步骤列表、参数说明、预期结果
REPAIR_TEMPLATES = {
    "datanode_down": {
        "fault_type": "DataNode下线",
        "description": "DataNode节点停止运行或无法连接",
        "steps": [
            {
                "step_id": 1,
                "action": "check_container",
                "description": "检查DataNode容器状态",
                "target": "datanode",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "确认DataNode容器是否运行"
            },
            {
                "step_id": 2,
                "action": "restart_service",
                "description": "重启DataNode服务",
                "target": "datanode",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "datanode",
                "expected_result": "DataNode服务成功重启"
            },
            {
                "step_id": 3,
                "action": "verify",
                "description": "验证DataNode是否恢复在线",
                "check": "datanode_status",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "DataNode显示为在线状态"
            }
        ],
        "parameters": {
            "datanode": "需要修复的DataNode容器名称（datanode1或datanode2）"
        }
    },
    "cluster_id_mismatch": {
        "fault_type": "集群ID不匹配",
        "description": "DataNode的clusterID与NameNode不一致",
        "steps": [
            {
                "step_id": 1,
                "action": "stop_cluster",
                "description": "停止整个集群",
                "target": "cluster",
                "tool": "hadoop_auto_operation",
                "operation": "stop",
                "container": None,
                "expected_result": "集群所有服务成功停止"
            },
            {
                "step_id": 2,
                "action": "clean_metadata",
                "description": "清理DataNode元数据（删除VERSION文件）",
                "target": "datanode",
                "tool": "execute_hadoop_command",
                "command": ["rm", "-f", "/usr/local/hadoop/data/dfs/data/current/VERSION"],
                "note": "需要在容器内执行，清理所有DataNode的VERSION文件",
                "expected_result": "DataNode元数据已清理"
            },
            {
                "step_id": 3,
                "action": "start_cluster",
                "description": "启动整个集群",
                "target": "cluster",
                "tool": "hadoop_auto_operation",
                "operation": "start",
                "container": None,
                "expected_result": "集群所有服务成功启动"
            },
            {
                "step_id": 4,
                "action": "verify",
                "description": "验证集群状态",
                "check": "cluster_status",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "所有DataNode正常连接，集群ID一致"
            }
        ],
        "parameters": {
            "datanode": "需要清理元数据的DataNode容器名称（可选，如果不指定则清理所有DataNode）"
        }
    },
    "namenode_safemode": {
        "fault_type": "NameNode安全模式",
        "description": "NameNode处于安全模式，无法执行写操作",
        "steps": [
            {
                "step_id": 1,
                "action": "check_safemode",
                "description": "检查NameNode安全模式状态",
                "target": "namenode",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-safemode", "get"],
                "expected_result": "确认安全模式状态"
            },
            {
                "step_id": 2,
                "action": "wait_safemode",
                "description": "等待安全模式自动退出（如果数据块复制完成）",
                "target": "namenode",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-safemode", "get"],
                "note": "通常安全模式会在数据块复制完成后自动退出",
                "expected_result": "安全模式自动退出"
            },
            {
                "step_id": 3,
                "action": "force_exit_safemode",
                "description": "强制退出安全模式（如果自动退出失败）",
                "target": "namenode",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-safemode", "leave"],
                "expected_result": "NameNode成功退出安全模式"
            },
            {
                "step_id": 4,
                "action": "verify",
                "description": "验证安全模式已退出",
                "check": "safemode_status",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-safemode", "get"],
                "expected_result": "NameNode不在安全模式"
            }
        ],
        "parameters": {}
    },
    "datanode_disk_full": {
        "fault_type": "DataNode磁盘满",
        "description": "DataNode存储空间不足",
        "steps": [
            {
                "step_id": 1,
                "action": "check_disk_space",
                "description": "检查DataNode磁盘使用情况",
                "target": "datanode",
                "tool": "execute_hadoop_command",
                "command": ["df", "-h"],
                "note": "需要在容器内执行，检查磁盘空间",
                "expected_result": "确认磁盘使用率"
            },
            {
                "step_id": 2,
                "action": "clean_temp_files",
                "description": "清理临时文件和日志",
                "target": "datanode",
                "tool": "execute_hadoop_command",
                "command": ["find", "/usr/local/hadoop/logs", "-name", "*.log.*", "-mtime", "+7", "-delete"],
                "note": "清理7天前的日志文件",
                "expected_result": "临时文件已清理，释放磁盘空间"
            },
            {
                "step_id": 3,
                "action": "restart_service",
                "description": "重启DataNode服务（如果清理后仍不足）",
                "target": "datanode",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "datanode",
                "expected_result": "DataNode服务成功重启"
            },
            {
                "step_id": 4,
                "action": "verify",
                "description": "验证磁盘空间和DataNode状态",
                "check": "disk_space_and_status",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "磁盘空间充足，DataNode正常运行"
            }
        ],
        "parameters": {
            "datanode": "需要修复的DataNode容器名称"
        }
    },
    "namenode_down": {
        "fault_type": "NameNode下线",
        "description": "NameNode节点停止运行",
        "steps": [
            {
                "step_id": 1,
                "action": "check_container",
                "description": "检查NameNode容器状态",
                "target": "namenode",
                "tool": "execute_hadoop_command",
                "command": ["docker", "ps", "-a", "--filter", "name=namenode"],
                "note": "检查容器是否运行",
                "expected_result": "确认NameNode容器状态"
            },
            {
                "step_id": 2,
                "action": "restart_service",
                "description": "重启NameNode服务",
                "target": "namenode",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "namenode",
                "expected_result": "NameNode服务成功重启"
            },
            {
                "step_id": 3,
                "action": "verify",
                "description": "验证NameNode是否恢复在线",
                "check": "namenode_status",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "NameNode显示为在线状态，可以正常响应请求"
            }
        ],
        "parameters": {}
    },
    "multiple_datanodes_down": {
        "fault_type": "多个DataNode下线",
        "description": "多个DataNode节点同时停止运行",
        "steps": [
            {
                "step_id": 1,
                "action": "check_all_datanodes",
                "description": "检查所有DataNode状态",
                "target": "cluster",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "确认所有DataNode的状态"
            },
            {
                "step_id": 2,
                "action": "restart_datanodes",
                "description": "逐个重启下线的DataNode",
                "target": "datanode",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "datanode",
                "note": "需要为每个下线的DataNode执行重启操作",
                "expected_result": "所有DataNode服务成功重启"
            },
            {
                "step_id": 3,
                "action": "verify",
                "description": "验证所有DataNode是否恢复在线",
                "check": "all_datanodes_status",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "所有DataNode显示为在线状态"
            }
        ],
        "parameters": {
            "datanodes": "需要修复的DataNode容器名称列表（如：['datanode1', 'datanode2']）"
        }
    }
}

# ==================== 验证配置 ====================

# 验证配置常量
VERIFY_CONFIG = {
    "expected_datanode_count": 3,  # 期望的DataNode数量
    "max_missing_blocks": 0,  # 允许的最大缺失数据块数
    "max_corrupt_blocks": 0,  # 允许的最大损坏数据块数
    "check_error_logs": False,  # 是否检查错误日志（暂时关闭，避免过于复杂）
    "error_log_time_window": 300  # 检查最近N秒的错误日志
}

