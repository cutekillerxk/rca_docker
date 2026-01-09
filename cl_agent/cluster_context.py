#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集群上下文配置模块
包含Hadoop集群的完整配置信息，供Agent的System Prompt使用

配置信息来源：
- docker-compose.yml
- 容器内实际配置文件 (core-site.xml, hdfs-site.xml等)
- 运行时查询 (hdfs getconf, hdfs dfsadmin -report)

最后更新：2026-01-08
"""

# ==================== 基础设施层 (Infrastructure) ====================
# 描述集群的物理/虚拟资源部署情况

INFRASTRUCTURE = {
    # 部署方式
    "deployment": {
        "type": "Docker Compose",
        "description": "基于Docker Compose的容器化部署，所有Hadoop服务运行在Docker容器内",
        "compose_file": "docker-compose.yml",
    },
    
    # Docker网络配置
    "network": {
        "name": "hadoop-network",
        "driver": "bridge",
        "description": "所有容器在同一bridge网络中，可通过容器名(hostname)互相访问",
    },
    
    # 节点/容器列表
    "nodes": {
        "namenode": {
            "container_name": "namenode",
            "hostname": "namenode",
            "image": "cutekiller/myhadoop-namenode:v1",
            "role": "主节点，运行NameNode、DataNode、SecondaryNameNode",
            "services": ["NameNode", "DataNode", "SecondaryNameNode"],
            "ports": {
                "namenode_webui": {"host": 9870, "container": 9870, "description": "NameNode Web UI"},
                "hdfs_rpc": {"host": 9000, "container": 9000, "description": "HDFS RPC端口"},
                "hdfs_rpc_alt": {"host": 8020, "container": 8020, "description": "HDFS RPC备用端口"},
                "datanode_webui": {"host": 9866, "container": 9864, "description": "DataNode Web UI (namenode容器内)"},
                "ssh": {"host": 2225, "container": 22, "description": "SSH端口"},
            },
        },
        "datanode1": {
            "container_name": "datanode1",
            "hostname": "datanode1",
            "image": "cutekiller/myhadoop-datanode1:v1",
            "role": "数据节点1，运行DataNode",
            "services": ["DataNode"],
            "ports": {
                "datanode_webui": {"host": 9864, "container": 9864, "description": "DataNode Web UI"},
                "ssh": {"host": 2223, "container": 22, "description": "SSH端口"},
            },
        },
        "datanode2": {
            "container_name": "datanode2",
            "hostname": "datanode2",
            "image": "cutekiller/myhadoop-datanode2:v1",
            "role": "数据节点2，运行DataNode",
            "services": ["DataNode"],
            "ports": {
                "datanode_webui": {"host": 9865, "container": 9864, "description": "DataNode Web UI"},
                "ssh": {"host": 2224, "container": 22, "description": "SSH端口"},
            },
        },
    },
    
    # 容器白名单（允许操作的容器）
    "allowed_containers": ["namenode", "datanode1", "datanode2"],
}


# ==================== 组件配置层 (Components) ====================
# 描述Hadoop各组件的配置

COMPONENTS = {
    # 运行环境
    "runtime": {
        "java_version": "OpenJDK 11.0.29",
        "java_home": "/usr/lib/jvm/java-11-openjdk-amd64",
        "hadoop_version": "3.3.6",
        "hadoop_home": "/usr/local/hadoop",
        "hadoop_conf_dir": "/usr/local/hadoop/etc/hadoop",
        "hadoop_user": "hadoop",  # 重要：Hadoop服务以hadoop用户运行
    },
    
    # HDFS配置 (来自 core-site.xml 和 hdfs-site.xml)
    "hdfs": {
        "fs_default_fs": "hdfs://namenode:9000",
        "replication": 2,
        "blocksize": 134217728,  # 128MB
        "blocksize_human": "128MB",
        "namenode_dir": "/usr/local/hadoop/hdfs/namenode",
        "datanode_dir": "/usr/local/hadoop/hdfs/datanode",
        "heartbeat_interval": 3,  # 秒
    },
    
    # workers文件内容
    "workers": ["namenode", "datanode1", "datanode2"],
    
    # 期望的集群状态
    "expected_state": {
        "total_datanodes": 3,  # 包括namenode容器内的DataNode
        "live_datanodes": 3,
        "dead_datanodes": 0,
        "missing_blocks": 0,
        "corrupt_blocks": 0,
    },
    
    # YARN配置（当前未启用）
    "yarn": {
        "enabled": False,
        "description": "YARN未配置，当前只运行HDFS服务",
    },
    
    # JMX监控端点（从宿主机访问）
    "jmx_endpoints": {
        "namenode": "http://localhost:9870/jmx",
        "datanode1": "http://127.0.0.1:9864/jmx",
        "datanode2": "http://127.0.0.1:9865/jmx",
        "datanode_namenode": "http://127.0.0.1:9866/jmx",  # namenode容器内的DataNode
    },
    
    # 日志配置
    "logs": {
        "log_dir": "/usr/local/hadoop/logs",
        "log_pattern": "hadoop-hadoop-{service_type}-{hostname}.log",
        "files": {
            "namenode": {
                "container": "namenode",
                "files": [
                    "hadoop-hadoop-namenode-namenode.log",
                    "hadoop-hadoop-datanode-namenode.log",
                    "hadoop-hadoop-secondarynamenode-namenode.log",
                ],
            },
            "datanode1": {
                "container": "datanode1",
                "files": ["hadoop-hadoop-datanode-datanode1.log"],
            },
            "datanode2": {
                "container": "datanode2",
                "files": ["hadoop-hadoop-datanode-datanode2.log"],
            },
        },
    },
}


# ==================== 操作层 (Operations) ====================
# 描述如何执行命令和操作

OPERATIONS = {
    # 重要说明：用户权限
    "user_context": {
        "description": "Hadoop集群由hadoop用户部署和运行，docker exec默认以root登录，必须切换用户",
        "default_docker_user": "root",
        "hadoop_user": "hadoop",
        "switch_user_required": True,
    },
    
    # 命令执行格式模板
    "command_templates": {
        # 标准格式：在容器内以hadoop用户执行命令
        "standard": {
            "template": "docker exec {container} sh -c 'su - hadoop -c \"{command}\"'",
            "description": "在指定容器内切换到hadoop用户执行命令",
            "components": {
                "docker exec {container}": "在指定容器内执行",
                "sh -c '...'": "启动shell执行命令字符串",
                "su - hadoop": "切换到hadoop用户（'-'确保加载环境变量）",
                "-c \"{command}\"": "执行实际的Hadoop命令",
            },
        },
        # 简化格式（直接指定用户，某些场景可用）
        "direct_user": {
            "template": "docker exec -u hadoop {container} {command}",
            "description": "直接以hadoop用户身份执行（注意：可能不加载完整环境变量）",
        },
        # 使用完整路径（当PATH未设置时）
        "full_path": {
            "template": "docker exec {container} sh -c '/usr/local/hadoop/bin/{command}'",
            "description": "使用Hadoop命令的完整路径",
        },
    },
    
    # 常用命令示例
    "command_examples": {
        # 查询类命令
        "cluster_report": {
            "description": "查看HDFS集群状态报告",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs dfsadmin -report"\'',
        },
        "safemode_get": {
            "description": "检查NameNode安全模式状态",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs dfsadmin -safemode get"\'',
        },
        "safemode_leave": {
            "description": "退出NameNode安全模式",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs dfsadmin -safemode leave"\'',
        },
        "list_hdfs_root": {
            "description": "列出HDFS根目录",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs dfs -ls /"\'',
        },
        "check_java_processes": {
            "description": "查看Java进程（确认服务运行状态）",
            "command": 'docker exec {container} sh -c \'su - hadoop -c "jps"\'',
        },
        
        # 单节点服务管理
        "start_datanode": {
            "description": "启动DataNode服务",
            "command": 'docker exec {container} sh -c \'su - hadoop -c "hdfs --daemon start datanode"\'',
        },
        "stop_datanode": {
            "description": "停止DataNode服务",
            "command": 'docker exec {container} sh -c \'su - hadoop -c "hdfs --daemon stop datanode"\'',
        },
        "start_namenode": {
            "description": "启动NameNode服务",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs --daemon start namenode"\'',
        },
        "stop_namenode": {
            "description": "停止NameNode服务",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs --daemon stop namenode"\'',
        },
        
        # 集群级操作
        "start_dfs": {
            "description": "启动整个HDFS集群（在namenode执行，会SSH到其他节点）",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "start-dfs.sh"\'',
        },
        "stop_dfs": {
            "description": "停止整个HDFS集群",
            "command": 'docker exec namenode sh -c \'su - hadoop -c "stop-dfs.sh"\'',
        },
    },
    
    # 容器到Hadoop服务类型映射
    "container_to_daemon": {
        "namenode": "namenode",  # namenode容器上运行的主要服务是namenode
        "datanode1": "datanode",
        "datanode2": "datanode",
    },
    
    # 允许的操作类型
    "allowed_operations": ["start", "stop", "restart"],
}


# ==================== 诊断层 (Diagnostics) ====================
# 描述如何诊断问题

DIAGNOSTICS = {
    # 日志关键字
    "log_keywords": {
        "error_levels": ["ERROR", "FATAL", "EXCEPTION", "CRITICAL"],
        "warning_levels": ["WARN", "WARNING"],
        "important_patterns": {
            "Incompatible clusterIDs": "集群ID不匹配，DataNode与NameNode的clusterID不一致",
            "Connection refused": "连接被拒绝，服务可能未启动或网络问题",
            "No space left": "磁盘空间不足",
            "Safe mode": "NameNode处于安全模式",
            "dead": "节点离线或心跳超时",
            "removed": "节点被移除",
            "UnderReplicatedBlocks": "副本数不足的数据块",
            "MissingBlocks": "丢失的数据块",
        },
    },
    
    # JMX关键指标
    "jmx_metrics": {
        "namenode": {
            "NumLiveDataNodes": {"description": "存活的DataNode数量", "expected": 3},
            "NumDeadDataNodes": {"description": "离线的DataNode数量", "expected": 0},
            "CapacityTotal": {"description": "总容量（字节）"},
            "CapacityUsed": {"description": "已使用容量（字节）"},
            "CapacityRemaining": {"description": "剩余容量（字节）"},
            "UnderReplicatedBlocks": {"description": "副本不足的块数", "expected": 0},
            "MissingBlocks": {"description": "丢失的块数", "expected": 0},
            "CorruptBlocks": {"description": "损坏的块数", "expected": 0},
        },
        "datanode": {
            "Remaining": {"description": "剩余空间（字节）"},
            "DfsUsed": {"description": "HDFS使用空间（字节）"},
            "Capacity": {"description": "总容量（字节）"},
        },
    },
    
    # 健康检查命令
    "health_checks": {
        "cluster_status": {
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs dfsadmin -report"\'',
            "description": "检查集群整体状态",
        },
        "fsck": {
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs fsck /"\'',
            "description": "检查HDFS文件系统健康状态",
        },
        "safemode": {
            "command": 'docker exec namenode sh -c \'su - hadoop -c "hdfs dfsadmin -safemode get"\'',
            "description": "检查安全模式状态",
        },
        "container_processes": {
            "command": 'docker exec {container} sh -c \'su - hadoop -c "jps"\'',
            "description": "检查容器内的Java进程",
        },
    },
}


# ==================== 故障知识层 (Fault Knowledge) ====================
# 常见故障的诊断和修复知识

FAULT_KNOWLEDGE = {
    "datanode_down": {
        "name": "DataNode下线",
        "symptoms": [
            "hdfs dfsadmin -report 显示 Dead datanodes > 0",
            "JMX中 NumDeadDataNodes > 0",
            "NameNode日志出现 'dead' 或 'removed' 关键字",
            "jps命令看不到DataNode进程",
        ],
        "possible_causes": [
            "DataNode服务崩溃",
            "容器停止运行",
            "网络连接问题",
            "磁盘空间不足",
            "配置错误",
        ],
        "diagnosis_steps": [
            "检查容器状态: docker ps -a | grep {container}",
            "检查DataNode进程: docker exec {container} sh -c 'su - hadoop -c \"jps\"'",
            "查看DataNode日志的最后错误",
            "检查磁盘空间: docker exec {container} df -h",
        ],
        "fix_commands": {
            "restart_datanode": 'docker exec {container} sh -c \'su - hadoop -c "hdfs --daemon stop datanode; hdfs --daemon start datanode"\'',
        },
    },
    
    "cluster_id_mismatch": {
        "name": "集群ID不匹配",
        "symptoms": [
            "DataNode日志出现 'Incompatible clusterIDs'",
            "DataNode无法连接到NameNode",
            "hdfs dfsadmin -report 显示容量为0",
        ],
        "possible_causes": [
            "NameNode被重新格式化，生成新的clusterID",
            "DataNode保留了旧的VERSION文件",
        ],
        "diagnosis_steps": [
            "检查NameNode的clusterID: docker exec namenode cat /usr/local/hadoop/hdfs/namenode/current/VERSION",
            "检查DataNode的clusterID: docker exec {container} cat /usr/local/hadoop/hdfs/datanode/current/VERSION",
            "对比两者的clusterID是否一致",
        ],
        "fix_commands": {
            "stop_dfs": 'docker exec namenode sh -c \'su - hadoop -c "stop-dfs.sh"\'',
            "clean_datanode_version": 'docker exec {container} sh -c \'su - hadoop -c "rm -rf /usr/local/hadoop/hdfs/datanode/current/*"\'',
            "start_dfs": 'docker exec namenode sh -c \'su - hadoop -c "start-dfs.sh"\'',
        },
    },
    
    "namenode_safemode": {
        "name": "NameNode安全模式",
        "symptoms": [
            "无法执行HDFS写操作",
            "hdfs dfsadmin -safemode get 返回 'Safe mode is ON'",
        ],
        "possible_causes": [
            "集群刚启动，正在进行数据块检查（正常，通常30秒内自动退出）",
            "可用DataNode数量不足",
            "数据块副本数不满足最低要求",
        ],
        "diagnosis_steps": [
            "检查安全模式状态: hdfs dfsadmin -safemode get",
            "检查DataNode数量: hdfs dfsadmin -report",
            "检查是否有副本不足的块",
        ],
        "fix_commands": {
            "wait_auto_leave": "等待安全模式自动退出（如果是启动检查）",
            "force_leave": 'docker exec namenode sh -c \'su - hadoop -c "hdfs dfsadmin -safemode leave"\'',
        },
    },
    
    "namenode_down": {
        "name": "NameNode下线",
        "symptoms": [
            "无法访问HDFS",
            "NameNode Web UI无法访问 (http://localhost:9870)",
            "jps看不到NameNode进程",
        ],
        "possible_causes": [
            "NameNode服务崩溃",
            "namenode容器停止",
            "内存不足",
        ],
        "diagnosis_steps": [
            "检查容器状态: docker ps -a | grep namenode",
            "检查NameNode进程: docker exec namenode sh -c 'su - hadoop -c \"jps\"'",
            "查看NameNode日志",
        ],
        "fix_commands": {
            "restart_namenode": 'docker exec namenode sh -c \'su - hadoop -c "hdfs --daemon stop namenode; hdfs --daemon start namenode"\'',
        },
    },
}


# ==================== System Prompt 生成 ====================

def generate_system_prompt() -> str:
    """
    生成供Agent使用的System Prompt
    包含集群环境信息、命令格式、工作流程等
    """
    print("生成系统提示词")
    prompt = '''你是一位专业的分布式系统运维专家，专注于 Hadoop/HDFS 集群的故障诊断与修复。

## 当前集群环境

### 部署架构
- 部署方式：Docker Compose 容器化部署
- 网络：所有容器在 `hadoop-network` 网络中，可通过容器名互相访问
- Hadoop版本：3.3.6
- Java版本：OpenJDK 11

### 节点清单
| 容器名 | 运行的服务 | Web UI 端口 | 说明 |
|--------|-----------|-------------|------|
| namenode | NameNode, DataNode, SecondaryNameNode | 9870 | 主节点 |
| datanode1 | DataNode | 9864 | 数据节点1 |
| datanode2 | DataNode | 9865 | 数据节点2 |

### 关键路径
- HADOOP_HOME: /usr/local/hadoop
- 配置文件: /usr/local/hadoop/etc/hadoop/
- 日志目录: /usr/local/hadoop/logs/
- HDFS数据: /usr/local/hadoop/hdfs/

### HDFS配置
- fs.defaultFS: hdfs://namenode:9000
- dfs.replication: 2
- dfs.blocksize: 128MB
- 期望DataNode数量: 3

## 命令执行格式（重要！）

### 用户权限说明
- Hadoop集群由 `hadoop` 用户部署和运行
- `docker exec` 默认以 `root` 用户登录容器
- **必须切换到 `hadoop` 用户** 才能正确执行Hadoop命令

### 标准命令格式
```
docker exec {容器名} sh -c 'su - hadoop -c "{Hadoop命令}"'
```

### 格式说明
- `docker exec {容器名}`: 在指定容器内执行命令
- `sh -c '...'`: 启动shell执行命令字符串
- `su - hadoop`: 切换到hadoop用户（"-"确保加载环境变量）
- `-c "{命令}"`: 执行实际的Hadoop命令

### 常用命令示例

1. **查看集群状态报告**
   ```
   docker exec namenode sh -c 'su - hadoop -c "hdfs dfsadmin -report"'
   ```

2. **检查安全模式状态**
   ```
   docker exec namenode sh -c 'su - hadoop -c "hdfs dfsadmin -safemode get"'
   ```

3. **退出安全模式**
   ```
   docker exec namenode sh -c 'su - hadoop -c "hdfs dfsadmin -safemode leave"'
   ```

4. **启动DataNode服务**
   ```
   docker exec {容器名} sh -c 'su - hadoop -c "hdfs --daemon start datanode"'
   ```

5. **停止DataNode服务**
   ```
   docker exec {容器名} sh -c 'su - hadoop -c "hdfs --daemon stop datanode"'
   ```

6. **启动整个集群**
   ```
   docker exec namenode sh -c 'su - hadoop -c "start-dfs.sh"'
   ```

7. **停止整个集群**
   ```
   docker exec namenode sh -c 'su - hadoop -c "stop-dfs.sh"'
   ```

8. **查看Java进程**
   ```
   docker exec {容器名} sh -c 'su - hadoop -c "jps"'
   ```

## 工作流程

处理问题时，请按以下流程进行：

### 阶段1：诊断（收集信息）
- 使用 get_cluster_logs 获取所有节点日志
- 使用 get_monitoring_metrics 获取JMX监控指标
- 使用 execute_hadoop_command 执行查询命令

### 阶段2：分析（识别问题）
- 分析日志中的错误信息
- 对比监控指标与正常值
- 确定故障类型和根本原因

### 阶段3：计划（制定方案）
- 制定详细的修复步骤
- 每个步骤包含完整的可执行命令
- 说明每个步骤的预期结果

### 阶段4：执行（实施修复）
- 按计划执行修复操作
- 每执行一步后验证结果

### 阶段5：验证（确认成功）
- 重新检查集群状态
- 确认相关指标恢复正常

## 重要限制

1. 禁止执行任何删除、格式化命令（除非修复集群ID不匹配问题）
2. 修复操作前必须先完成诊断
3. 不确定时先查询状态，不要盲目操作
4. 执行命令时必须切换到hadoop用户
'''
    return prompt


def get_command(container: str, hadoop_cmd: str) -> str:
    """
    生成在指定容器内执行Hadoop命令的完整命令
    
    Args:
        container: 容器名称 (namenode, datanode1, datanode2)
        hadoop_cmd: 要执行的Hadoop命令
    
    Returns:
        完整的docker exec命令
    """
    return f'docker exec {container} sh -c \'su - hadoop -c "{hadoop_cmd}"\''


def get_cluster_info() -> dict:
    """
    获取集群的完整配置信息
    
    Returns:
        包含所有配置的字典
    """
    return {
        "infrastructure": INFRASTRUCTURE,
        "components": COMPONENTS,
        "operations": OPERATIONS,
        "diagnostics": DIAGNOSTICS,
        "fault_knowledge": FAULT_KNOWLEDGE,
    }


# ==================== 导出 ====================

# 主要导出项
__all__ = [
    "INFRASTRUCTURE",
    "COMPONENTS", 
    "OPERATIONS",
    "DIAGNOSTICS",
    "FAULT_KNOWLEDGE",
    "generate_system_prompt",
    "get_command",
    "get_cluster_info",
]

