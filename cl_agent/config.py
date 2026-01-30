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
        "node_pattern": "namenode-namenode",  # 精确匹配 hadoop-hadoop-namenode-namenode.log（避免匹配到historyserver等）
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
        "node_pattern": "datanode-datanode1",  # 精确匹配 hadoop-hadoop-datanode-datanode1.log（避免匹配到nodemanager日志）
        "ip": "127.0.0.1"
    },
    {
        "name": "datanode2",
        "display_name": "DataNode2",
        "type": "docker",
        "container": "datanode2",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "datanode-datanode2",  # 精确匹配 hadoop-hadoop-datanode-datanode2.log（避免匹配到nodemanager日志）
        "ip": "127.0.0.1"
    },
    # YARN 组件日志配置
    {
        "name": "resourcemanager",
        "display_name": "ResourceManager",
        "type": "docker",
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "resourcemanager",  # 匹配 hadoop-hadoop-resourcemanager-namenode.log
        "ip": "127.0.0.1"
    },
    {
        "name": "nodemanager-namenode",
        "display_name": "NodeManager (NameNode容器)",
        "type": "docker",
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "nodemanager",  # 匹配 hadoop-hadoop-nodemanager-namenode.log
        "ip": "127.0.0.1"
    },
    {
        "name": "nodemanager-datanode1",
        "display_name": "NodeManager (DataNode1)",
        "type": "docker",
        "container": "datanode1",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "nodemanager",  # 匹配 hadoop-hadoop-nodemanager-datanode1.log
        "ip": "127.0.0.1"
    },
    {
        "name": "nodemanager-datanode2",
        "display_name": "NodeManager (DataNode2)",
        "type": "docker",
        "container": "datanode2",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "nodemanager",  # 匹配 hadoop-hadoop-nodemanager-datanode2.log
        "ip": "127.0.0.1"
    },
    # JobHistoryServer日志配置
    {
        "name": "historyserver",
        "display_name": "JobHistoryServer",
        "type": "docker",
        "container": "namenode",
        "log_path": "/usr/local/hadoop/logs",
        "node_pattern": "historyserver",  # 匹配 hadoop-hadoop-historyserver-namenode.log
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
    # YARN命令（查询类，只读，安全）
    'yarn': [
        'application', '-list', '-status', '-kill',
        'node', '-list', '-status',
        'logs', '-applicationId',
        'top', 'queue', '-status'
    ],
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

# ==================== 故障类型标准库 ====================

# 故障类型标准库
# 定义所有支持的故障类型，包含完整的元数据信息
# 用于故障识别、分类和诊断
FAULT_TYPE_LIBRARY = {
    "datanode_down": {
        "fault_type": "DataNode下线",
        "category": "hdfs",
        "severity": "high",
        "classic_score": 5,  # 经典性评分（1-5）
        "keywords": [
            "dead", "removed", "heartbeat", "connection refused",
            "NumDeadDataNodes", "Dead datanodes", "lost datanode"
        ],
        "symptoms": [
            "hdfs dfsadmin -report 显示 Dead datanodes > 0",
            "JMX中 NumDeadDataNodes > 0",
            "NameNode日志出现 'dead' 或 'removed' 关键字",
            "jps命令看不到DataNode进程",
            "DataNode Web UI无法访问"
        ],
        "possible_causes": [
            "DataNode服务崩溃",
            "容器停止运行",
            "网络连接问题",
            "磁盘空间不足",
            "配置错误"
        ],
        "affected_components": ["DataNode", "NameNode", "HDFS"],
        "detection_methods": [
            "监控指标：NumDeadDataNodes > 0",
            "日志关键词匹配：'dead', 'removed', 'heartbeat'",
            "命令检查：hdfs dfsadmin -report",
            "进程检查：jps | grep DataNode"
        ]
    },
    
    "namenode_safemode": {
        "fault_type": "NameNode安全模式",
        "category": "hdfs",
        "severity": "high",
        "classic_score": 4,
        "keywords": [
            "Safe mode is ON", "safemode", "SafeModeException",
            "Name node is in safe mode"
        ],
        "symptoms": [
            "无法执行HDFS写操作",
            "hdfs dfsadmin -safemode get 返回 'Safe mode is ON'",
            "写操作报错：SafeModeException",
            "NameNode日志显示安全模式状态"
        ],
        "possible_causes": [
            "集群刚启动，正在进行数据块检查（正常，通常30秒内自动退出）",
            "可用DataNode数量不足",
            "数据块副本数不满足最低要求",
            "NameNode元数据损坏"
        ],
        "affected_components": ["NameNode", "HDFS"],
        "detection_methods": [
            "命令检查：hdfs dfsadmin -safemode get",
            "日志关键词匹配：'Safe mode is ON'",
            "写操作测试：hdfs dfs -mkdir /test"
        ]
    },
    
    "cluster_id_mismatch": {
        "fault_type": "集群ID不匹配",
        "category": "hdfs",
        "severity": "high",
        "classic_score": 4,
        "keywords": [
            "Incompatible clusterIDs", "Inconsistent checkpoint fields",
            "clusterID", "VERSION file"
        ],
        "symptoms": [
            "DataNode日志出现 'Incompatible clusterIDs'",
            "DataNode无法连接到NameNode",
            "hdfs dfsadmin -report 显示容量为0",
            "DataNode启动失败"
        ],
        "possible_causes": [
            "NameNode被重新格式化，生成新的clusterID",
            "DataNode保留了旧的VERSION文件",
            "集群重建后未清理DataNode元数据"
        ],
        "affected_components": ["DataNode", "NameNode", "HDFS"],
        "detection_methods": [
            "日志关键词匹配：'Incompatible clusterIDs'",
            "配置文件检查：对比NameNode和DataNode的VERSION文件",
            "命令检查：hdfs dfsadmin -report 显示容量为0"
        ]
    },
    
    "resourcemanager_down": {
        "fault_type": "ResourceManager下线",
        "category": "yarn",
        "severity": "high",
        "classic_score": 5,
        "keywords": [
            "Connection refused", "ResourceManager is not available",
            "8032", "java.net.ConnectException", "RM is not available"
        ],
        "symptoms": [
            "ResourceManager进程停止",
            "任务无法提交，报错 'Connection refused'",
            "ResourceManager Web UI无法访问 (http://localhost:8088)",
            "jps命令看不到ResourceManager进程",
            "端口8032未监听"
        ],
        "possible_causes": [
            "ResourceManager服务崩溃",
            "容器停止运行",
            "端口占用",
            "配置错误",
            "内存不足"
        ],
        "affected_components": ["ResourceManager", "YARN", "MapReduce"],
        "detection_methods": [
            "进程检查：jps | grep ResourceManager",
            "端口检查：netstat -tlnp | grep 8032",
            "日志关键词匹配：'Connection refused', '8032'",
            "Web UI检查：http://localhost:8088"
        ]
    },
    
    "nodemanager_down": {
        "fault_type": "NodeManager下线",
        "category": "yarn",
        "severity": "high",
        "classic_score": 4,
        "keywords": [
            "lost", "unhealthy", "0 active nodes", "NodeManager",
            "NumLostNMs", "NumUnhealthyNMs"
        ],
        "symptoms": [
            "NodeManager进程停止",
            "ResourceManager报告 lost/unhealthy NMs",
            "任务无法分配Container，一直处于ACCEPTED状态",
            "ResourceManager Web UI显示 '0 active nodes'",
            "jps命令看不到NodeManager进程"
        ],
        "possible_causes": [
            "NodeManager服务崩溃",
            "容器停止运行",
            "配置错误",
            "资源不足",
            "网络连接问题"
        ],
        "affected_components": ["NodeManager", "YARN", "MapReduce"],
        "detection_methods": [
            "监控指标：NumLostNMs > 0 或 NumUnhealthyNMs > 0",
            "进程检查：jps | grep NodeManager",
            "Web UI检查：http://localhost:8088/cluster/nodes",
            "日志关键词匹配：'lost', 'unhealthy'"
        ]
    },
    
    "yarn_config_error": {
        "fault_type": "YARN配置错误",
        "category": "yarn",
        "severity": "medium",
        "classic_score": 4,
        "keywords": [
            "UnknownHostException", "wrong-hostname", "Connection refused",
            "yarn.resourcemanager.hostname", "config error"
        ],
        "symptoms": [
            "NodeManager日志出现 'UnknownHostException: wrong-hostname'",
            "NodeManager日志出现 'Connection refused'",
            "ResourceManager Web UI中该NodeManager显示为离线",
            "yarn node -list 显示该节点为 'lost' 或 'unhealthy'",
            "NodeManager无法连接到ResourceManager"
        ],
        "possible_causes": [
            "yarn-site.xml中yarn.resourcemanager.hostname配置错误",
            "网络配置错误",
            "DNS解析问题",
            "配置文件格式错误"
        ],
        "affected_components": ["NodeManager", "YARN"],
        "detection_methods": [
            "日志关键词匹配：'UnknownHostException', 'Connection refused'",
            "配置文件检查：yarn-site.xml中的ResourceManager地址",
            "Web UI检查：ResourceManager中节点状态",
            "网络检查：ping ResourceManager地址"
        ]
    },
    
    "mapreduce_memory_insufficient": {
        "fault_type": "MapReduce任务内存不足",
        "category": "mapreduce",
        "severity": "high",
        "classic_score": 5,
        "keywords": [
            "Container killed", "Exit code 143", "OutOfMemoryError",
            "memory", "killed on request", "Container exited"
        ],
        "symptoms": [
            "Container被YARN杀死",
            "任务失败，日志中出现 'Container killed on request. Exit code is 143'",
            "任务日志中出现 'OutOfMemoryError'",
            "YARN Web UI显示任务失败，原因：Container killed",
            "NodeManager日志显示内存不足"
        ],
        "possible_causes": [
            "任务申请内存过大，超过YARN配置的最大值",
            "YARN内存配置过小（yarn.scheduler.maximum-allocation-mb）",
            "数据量过大，处理需要更多内存",
            "任务代码存在内存泄漏"
        ],
        "affected_components": ["MapReduce", "YARN", "Container"],
        "detection_methods": [
            "日志关键词匹配：'Container killed', 'Exit code 143', 'OutOfMemoryError'",
            "任务日志检查：yarn logs -applicationId <app_id>",
            "监控指标：Container内存使用情况",
            "配置检查：yarn-site.xml中的内存配置"
        ]
    },
    
    "mapreduce_disk_insufficient": {
        "fault_type": "MapReduce任务磁盘空间不足",
        "category": "mapreduce",
        "severity": "high",
        "classic_score": 4,
        "keywords": [
            "No space left on device", "DiskError", "disk full",
            "IOException", "disk space"
        ],
        "symptoms": [
            "任务失败，日志中出现 'No space left on device'",
            "HDFS写操作失败",
            "DataNode或NodeManager本地磁盘空间不足",
            "hdfs dfsadmin -report 显示磁盘使用率接近100%",
            "df -h 显示磁盘空间不足"
        ],
        "possible_causes": [
            "HDFS磁盘空间不足",
            "NodeManager本地磁盘空间不足（用于中间结果）",
            "临时文件未清理",
            "日志文件占用过多空间",
            "数据量过大"
        ],
        "affected_components": ["MapReduce", "HDFS", "DataNode", "NodeManager"],
        "detection_methods": [
            "日志关键词匹配：'No space left on device', 'DiskError'",
            "磁盘检查：df -h",
            "HDFS检查：hdfs dfsadmin -report",
            "任务日志检查：yarn logs -applicationId <app_id>"
        ]
    },
    
    "mapreduce_shuffle_failed": {
        "fault_type": "MapReduce Shuffle阶段失败",
        "category": "mapreduce",
        "severity": "high",
        "classic_score": 4,
        "keywords": [
            "shuffle failed", "ShuffleHandler", "shuffle error",
            "ShuffleException", "shuffle connection"
        ],
        "symptoms": [
            "MapReduce任务在Shuffle阶段失败",
            "任务日志中出现 'shuffle failed' 或 'ShuffleException'",
            "Reduce任务无法获取Map任务的输出",
            "Shuffle服务连接失败",
            "网络连接问题导致Shuffle失败"
        ],
        "possible_causes": [
            "Shuffle服务未启动或配置错误",
            "网络问题（延迟、丢包）",
            "磁盘I/O问题",
            "端口冲突",
            "防火墙阻止Shuffle端口"
        ],
        "affected_components": ["MapReduce", "Shuffle", "Network"],
        "detection_methods": [
            "日志关键词匹配：'shuffle failed', 'ShuffleHandler', 'ShuffleException'",
            "任务日志检查：yarn logs -applicationId <app_id>",
            "网络检查：ping、telnet Shuffle端口",
            "服务检查：Shuffle服务是否运行"
        ]
    },
    
    "mapreduce_task_timeout": {
        "fault_type": "MapReduce任务超时",
        "category": "mapreduce",
        "severity": "medium",
        "classic_score": 3,
        "keywords": [
            "timeout", "read timeout", "connection timeout",
            "Task timeout", "SocketTimeoutException"
        ],
        "symptoms": [
            "任务超时失败",
            "任务日志中出现 'timeout' 或 'SocketTimeoutException'",
            "任务执行时间超过配置的超时时间",
            "网络连接超时",
            "任务一直处于RUNNING状态，最终超时"
        ],
        "possible_causes": [
            "网络延迟过高",
            "数据量过大，处理时间过长",
            "超时配置过短",
            "节点负载过高，处理速度慢",
            "网络拥塞"
        ],
        "affected_components": ["MapReduce", "Network"],
        "detection_methods": [
            "日志关键词匹配：'timeout', 'SocketTimeoutException'",
            "任务日志检查：yarn logs -applicationId <app_id>",
            "任务状态检查：yarn application -status <app_id>",
            "网络检查：ping延迟、网络质量"
        ]
    }
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
    "resourcemanager_down": {
        "fault_type": "ResourceManager下线",
        "description": "ResourceManager服务停止运行，无法接收和调度任务",
        "steps": [
            {
                "step_id": 1,
                "action": "check_resourcemanager_status",
                "description": "检查ResourceManager服务状态",
                "target": "resourcemanager",
                "tool": "get_monitoring_metrics",
                "expected_result": "确认ResourceManager是否运行"
            },
            {
                "step_id": 2,
                "action": "check_resourcemanager_logs",
                "description": "查看ResourceManager日志，分析停止原因",
                "target": "resourcemanager",
                "tool": "get_node_log",
                "node_name": "resourcemanager",
                "expected_result": "找到ResourceManager停止的原因"
            },
            {
                "step_id": 3,
                "action": "restart_resourcemanager",
                "description": "重启ResourceManager服务",
                "target": "resourcemanager",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "namenode",
                "service_type": "yarn",
                "yarn_daemon_type": "resourcemanager",
                "expected_result": "ResourceManager服务成功重启"
            },
            {
                "step_id": 4,
                "action": "verify",
                "description": "验证ResourceManager是否恢复在线",
                "check": "resourcemanager_status",
                "tool": "get_monitoring_metrics",
                "expected_result": "ResourceManager显示为在线状态，可以正常接收任务"
            }
        ],
        "parameters": {}
    },
    "nodemanager_down": {
        "fault_type": "NodeManager下线",
        "description": "NodeManager服务停止运行，无法执行任务",
        "steps": [
            {
                "step_id": 1,
                "action": "check_nodemanager_status",
                "description": "检查NodeManager服务状态",
                "target": "nodemanager",
                "tool": "get_monitoring_metrics",
                "expected_result": "确认哪个NodeManager下线"
            },
            {
                "step_id": 2,
                "action": "check_nodemanager_logs",
                "description": "查看NodeManager日志，分析停止原因",
                "target": "nodemanager",
                "tool": "get_node_log",
                "node_name": "nodemanager",
                "expected_result": "找到NodeManager停止的原因"
            },
            {
                "step_id": 3,
                "action": "restart_nodemanager",
                "description": "重启NodeManager服务",
                "target": "nodemanager",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "nodemanager",
                "service_type": "yarn",
                "yarn_daemon_type": "nodemanager",
                "expected_result": "NodeManager服务成功重启"
            },
            {
                "step_id": 4,
                "action": "verify",
                "description": "验证NodeManager是否恢复在线",
                "check": "nodemanager_status",
                "tool": "get_monitoring_metrics",
                "expected_result": "NodeManager显示为在线状态，可以正常执行任务"
            }
        ],
        "parameters": {
            "nodemanager": "需要修复的NodeManager容器名称（namenode、datanode1或datanode2）"
        }
    },
    "yarn_config_error": {
        "fault_type": "YARN配置错误",
        "description": "NodeManager配置的ResourceManager地址错误，导致无法连接",
        "steps": [
            {
                "step_id": 1,
                "action": "check_nodemanager_logs",
                "description": "查看NodeManager日志，确认连接错误",
                "target": "nodemanager",
                "tool": "get_node_log",
                "node_name": "nodemanager",
                "expected_result": "日志中出现UnknownHostException或Connection refused"
            },
            {
                "step_id": 2,
                "action": "check_config",
                "description": "检查yarn-site.xml中的ResourceManager地址配置",
                "target": "nodemanager",
                "tool": "execute_hadoop_command",
                "command": ["cat", "/usr/local/hadoop/etc/hadoop/yarn-site.xml"],
                "note": "需要在容器内执行，检查yarn.resourcemanager.hostname配置",
                "expected_result": "找到配置错误的位置"
            },
            {
                "step_id": 3,
                "action": "fix_config",
                "description": "修复yarn-site.xml中的ResourceManager地址",
                "target": "nodemanager",
                "tool": "execute_hadoop_command",
                "command": ["sed", "-i", "s/<value>wrong-hostname<\\/value>/<value>namenode<\\/value>/", "/usr/local/hadoop/etc/hadoop/yarn-site.xml"],
                "note": "需要根据实际错误配置进行修复，将错误的hostname替换为正确的namenode",
                "expected_result": "配置文件已修复"
            },
            {
                "step_id": 4,
                "action": "restart_service",
                "description": "重启NodeManager服务",
                "target": "nodemanager",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "nodemanager",
                "service_type": "yarn",
                "yarn_daemon_type": "nodemanager",
                "expected_result": "NodeManager服务成功重启"
            },
            {
                "step_id": 5,
                "action": "verify",
                "description": "验证NodeManager是否成功连接到ResourceManager",
                "check": "nodemanager_connection",
                "tool": "get_monitoring_metrics",
                "expected_result": "NodeManager显示为在线状态，ResourceManager Web UI中可见"
            }
        ],
        "parameters": {
            "nodemanager": "需要修复的NodeManager容器名称（namenode、datanode1或datanode2）"
        }
    },
    "mapreduce_memory_insufficient": {
        "fault_type": "MapReduce任务内存不足",
        "description": "MapReduce任务运行时，Container因内存不足被YARN杀死",
        "steps": [
            {
                "step_id": 1,
                "action": "check_failed_applications",
                "description": "检查失败的应用列表，获取Application ID",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "application", "-list", "-appStates", "FAILED"],
                "expected_result": "获取失败任务的Application ID"
            },
            {
                "step_id": 2,
                "action": "check_job_logs",
                "description": "查看失败任务的日志，确认内存不足错误",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "logs", "-applicationId", "<application_id>"],
                "expected_result": "日志中出现'Container killed', 'Exit code 143'或'OutOfMemoryError'"
            },
            {
                "step_id": 3,
                "action": "check_yarn_config",
                "description": "检查YARN内存配置",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["cat", "/usr/local/hadoop/etc/hadoop/yarn-site.xml"],
                "note": "检查yarn.scheduler.maximum-allocation-mb和yarn.nodemanager.resource.memory-mb配置",
                "expected_result": "确认当前内存配置值"
            },
            {
                "step_id": 4,
                "action": "adjust_memory_config",
                "description": "调整YARN内存配置，增加可用内存",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["sed", "-i", "s/<value>128<\\/value>/<value>2048<\\/value>/", "/usr/local/hadoop/etc/hadoop/yarn-site.xml"],
                "note": "需要根据实际情况调整，将内存配置增加到合理值（如2048MB）",
                "expected_result": "内存配置已更新"
            },
            {
                "step_id": 5,
                "action": "restart_yarn_services",
                "description": "重启ResourceManager和所有NodeManager服务",
                "target": "yarn",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "namenode",
                "service_type": "yarn",
                "yarn_daemon_type": "resourcemanager",
                "note": "需要重启所有节点的YARN服务",
                "expected_result": "YARN服务成功重启"
            },
            {
                "step_id": 6,
                "action": "verify",
                "description": "验证内存配置和YARN服务状态",
                "check": "yarn_memory_config",
                "tool": "get_monitoring_metrics",
                "expected_result": "内存配置已生效，YARN服务正常运行"
            }
        ],
        "parameters": {
            "application_id": "失败任务的Application ID（可选）"
        }
    },
    "mapreduce_disk_insufficient": {
        "fault_type": "MapReduce任务磁盘空间不足",
        "description": "MapReduce任务运行时，因磁盘空间不足失败",
        "steps": [
            {
                "step_id": 1,
                "action": "check_failed_applications",
                "description": "检查失败的应用列表",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "application", "-list", "-appStates", "FAILED"],
                "expected_result": "获取失败任务的Application ID"
            },
            {
                "step_id": 2,
                "action": "check_job_logs",
                "description": "查看失败任务的日志，确认磁盘空间不足错误",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "logs", "-applicationId", "<application_id>"],
                "expected_result": "日志中出现'No space left on device'或'DiskError'"
            },
            {
                "step_id": 3,
                "action": "check_disk_space",
                "description": "检查DataNode和NodeManager的磁盘使用情况",
                "target": "cluster",
                "tool": "execute_hadoop_command",
                "command": ["df", "-h"],
                "note": "需要在所有节点上检查磁盘空间",
                "expected_result": "确认磁盘使用率，找到空间不足的节点"
            },
            {
                "step_id": 4,
                "action": "check_hdfs_usage",
                "description": "检查HDFS使用情况",
                "target": "hdfs",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "确认HDFS存储使用情况"
            },
            {
                "step_id": 5,
                "action": "clean_temp_files",
                "description": "清理临时文件和日志",
                "target": "cluster",
                "tool": "execute_hadoop_command",
                "command": ["find", "/usr/local/hadoop/logs", "-name", "*.log.*", "-mtime", "+7", "-delete"],
                "note": "清理7天前的日志文件，释放磁盘空间",
                "expected_result": "临时文件已清理，释放磁盘空间"
            },
            {
                "step_id": 6,
                "action": "clean_hdfs_temp",
                "description": "清理HDFS临时文件（如果存在）",
                "target": "hdfs",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfs", "-rm", "-r", "/tmp/*"],
                "note": "谨慎操作，确保不会删除重要数据",
                "expected_result": "HDFS临时文件已清理"
            },
            {
                "step_id": 7,
                "action": "verify",
                "description": "验证磁盘空间和集群状态",
                "check": "disk_space_and_cluster_status",
                "tool": "execute_hadoop_command",
                "command": ["hdfs", "dfsadmin", "-report"],
                "expected_result": "磁盘空间充足，集群正常运行"
            }
        ],
        "parameters": {
            "application_id": "失败任务的Application ID（可选）"
        }
    },
    "mapreduce_shuffle_failed": {
        "fault_type": "MapReduce Shuffle阶段失败",
        "description": "MapReduce任务在Shuffle阶段失败",
        "steps": [
            {
                "step_id": 1,
                "action": "check_failed_applications",
                "description": "检查失败的应用列表",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "application", "-list", "-appStates", "FAILED"],
                "expected_result": "获取失败任务的Application ID"
            },
            {
                "step_id": 2,
                "action": "check_job_logs",
                "description": "查看失败任务的日志，确认Shuffle失败错误",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "logs", "-applicationId", "<application_id>"],
                "expected_result": "日志中出现'shuffle failed', 'ShuffleHandler'或'ShuffleException'"
            },
            {
                "step_id": 3,
                "action": "check_shuffle_service",
                "description": "检查Shuffle服务是否运行",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["netstat", "-tlnp", "|", "grep", "13562"],
                "note": "检查Shuffle服务端口（默认13562）是否监听",
                "expected_result": "确认Shuffle服务状态"
            },
            {
                "step_id": 4,
                "action": "check_network",
                "description": "检查网络连接",
                "target": "network",
                "tool": "execute_hadoop_command",
                "command": ["ping", "-c", "3", "namenode"],
                "note": "检查节点间网络连通性",
                "expected_result": "网络连接正常"
            },
            {
                "step_id": 5,
                "action": "check_mapred_config",
                "description": "检查mapred-site.xml中的Shuffle配置",
                "target": "mapreduce",
                "tool": "execute_hadoop_command",
                "command": ["cat", "/usr/local/hadoop/etc/hadoop/mapred-site.xml"],
                "note": "检查mapreduce.shuffle.port等配置",
                "expected_result": "确认Shuffle配置正确"
            },
            {
                "step_id": 6,
                "action": "restart_nodemanagers",
                "description": "重启所有NodeManager服务（重启Shuffle服务）",
                "target": "yarn",
                "tool": "hadoop_auto_operation",
                "operation": "restart",
                "container": "nodemanager",
                "service_type": "yarn",
                "yarn_daemon_type": "nodemanager",
                "note": "需要重启所有NodeManager以重启Shuffle服务",
                "expected_result": "NodeManager服务成功重启，Shuffle服务恢复"
            },
            {
                "step_id": 7,
                "action": "verify",
                "description": "验证Shuffle服务和集群状态",
                "check": "shuffle_service_status",
                "tool": "get_monitoring_metrics",
                "expected_result": "Shuffle服务正常运行，集群状态正常"
            }
        ],
        "parameters": {
            "application_id": "失败任务的Application ID（可选）"
        }
    },
    "mapreduce_task_timeout": {
        "fault_type": "MapReduce任务超时",
        "description": "MapReduce任务执行超时失败",
        "steps": [
            {
                "step_id": 1,
                "action": "check_failed_applications",
                "description": "检查失败的应用列表",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "application", "-list", "-appStates", "FAILED"],
                "expected_result": "获取失败任务的Application ID"
            },
            {
                "step_id": 2,
                "action": "check_job_status",
                "description": "查看失败任务的详细状态",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "application", "-status", "<application_id>"],
                "expected_result": "获取任务的详细状态信息，确认超时"
            },
            {
                "step_id": 3,
                "action": "check_job_logs",
                "description": "查看失败任务的日志，确认超时错误",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["yarn", "logs", "-applicationId", "<application_id>"],
                "expected_result": "日志中出现'timeout', 'SocketTimeoutException'或'connection timeout'"
            },
            {
                "step_id": 4,
                "action": "check_network_latency",
                "description": "检查网络延迟",
                "target": "network",
                "tool": "execute_hadoop_command",
                "command": ["ping", "-c", "10", "namenode"],
                "note": "检查节点间网络延迟",
                "expected_result": "确认网络延迟情况"
            },
            {
                "step_id": 5,
                "action": "check_timeout_config",
                "description": "检查超时配置",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["cat", "/usr/local/hadoop/etc/hadoop/yarn-site.xml"],
                "note": "检查yarn.application.classpath和超时相关配置",
                "expected_result": "确认当前超时配置"
            },
            {
                "step_id": 6,
                "action": "adjust_timeout_config",
                "description": "调整超时配置（如果需要）",
                "target": "yarn",
                "tool": "execute_hadoop_command",
                "command": ["echo", "增加超时时间配置"],
                "note": "根据实际情况调整超时配置，或优化任务以减少执行时间",
                "expected_result": "超时配置已调整或任务已优化"
            },
            {
                "step_id": 7,
                "action": "suggest_optimization",
                "description": "提供任务优化建议",
                "target": "mapreduce",
                "note": "可能的优化方案：1) 增加任务并行度 2) 优化数据分区 3) 减少数据量 4) 优化任务代码",
                "expected_result": "提供任务优化建议"
            }
        ],
        "parameters": {
            "application_id": "失败任务的Application ID（可选）"
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

