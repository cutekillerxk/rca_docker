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
    
    "resourcemanager_down": {
        "name": "ResourceManager下线",
        "symptoms": [
            "ResourceManager进程停止",
            "任务无法提交，报错 'Connection refused'",
            "ResourceManager Web UI无法访问 (http://localhost:8088)",
            "jps命令看不到ResourceManager进程",
            "端口8032未监听",
        ],
        "possible_causes": [
            "ResourceManager服务崩溃",
            "容器停止运行",
            "端口占用",
            "配置错误",
            "内存不足",
        ],
        "diagnosis_steps": [
            "检查ResourceManager进程: docker exec namenode sh -c 'su - hadoop -c \"jps\"'",
            "检查端口8032: docker exec namenode netstat -tlnp | grep 8032",
            "查看ResourceManager日志: docker exec namenode tail -50 /usr/local/hadoop/logs/hadoop-hadoop-resourcemanager-namenode.log",
            "检查容器状态: docker ps -a | grep namenode",
        ],
        "fix_commands": {
            "restart_resourcemanager": 'docker exec namenode sh -c \'su - hadoop -c "yarn --daemon stop resourcemanager && yarn --daemon start resourcemanager"\'',
        },
    },
    
    "nodemanager_down": {
        "name": "NodeManager下线",
        "symptoms": [
            "NodeManager进程停止",
            "ResourceManager报告 lost/unhealthy NMs",
            "任务无法分配Container，一直处于ACCEPTED状态",
            "ResourceManager Web UI显示 '0 active nodes'",
            "jps命令看不到NodeManager进程",
        ],
        "possible_causes": [
            "NodeManager服务崩溃",
            "容器停止运行",
            "配置错误",
            "资源不足",
            "网络连接问题",
        ],
        "diagnosis_steps": [
            "检查NodeManager进程: docker exec {container} sh -c 'su - hadoop -c \"jps\"'",
            "查看ResourceManager Web UI: http://localhost:8088/cluster/nodes",
            "查看NodeManager日志: docker exec {container} tail -50 /usr/local/hadoop/logs/hadoop-hadoop-nodemanager-*.log",
            "检查容器状态: docker ps -a | grep {container}",
        ],
        "fix_commands": {
            "restart_nodemanager": 'docker exec {container} sh -c \'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"\'',
        },
    },
    
    "yarn_config_error": {
        "name": "YARN配置错误",
        "symptoms": [
            "NodeManager日志出现 'UnknownHostException: wrong-hostname'",
            "NodeManager日志出现 'Connection refused'",
            "ResourceManager Web UI中该NodeManager显示为离线",
            "yarn node -list 显示该节点为 'lost' 或 'unhealthy'",
            "NodeManager无法连接到ResourceManager",
        ],
        "possible_causes": [
            "yarn-site.xml中yarn.resourcemanager.hostname配置错误",
            "网络配置错误",
            "DNS解析问题",
            "配置文件格式错误",
        ],
        "diagnosis_steps": [
            "检查NodeManager日志: docker exec {container} tail -50 /usr/local/hadoop/logs/hadoop-hadoop-nodemanager-*.log",
            "检查yarn-site.xml配置: docker exec {container} cat /usr/local/hadoop/etc/hadoop/yarn-site.xml | grep resourcemanager",
            "检查ResourceManager Web UI: http://localhost:8088/cluster/nodes",
            "检查网络连通性: docker exec {container} ping namenode",
        ],
        "fix_commands": {
            "check_config": 'docker exec {container} cat /usr/local/hadoop/etc/hadoop/yarn-site.xml | grep resourcemanager',
            "fix_config": 'docker exec {container} sh -c \'su - hadoop -c "sed -i \\"s/<value>wrong-hostname<\\/value>/<value>namenode<\\/value>/\\" /usr/local/hadoop/etc/hadoop/yarn-site.xml"\'',
            "restart_nodemanager": 'docker exec {container} sh -c \'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"\'',
        },
    },
    
    "mapreduce_memory_insufficient": {
        "name": "MapReduce任务内存不足",
        "symptoms": [
            "Container被YARN杀死",
            "任务失败，日志中出现 'Container killed on request. Exit code is 143'",
            "任务日志中出现 'OutOfMemoryError'",
            "YARN Web UI显示任务失败，原因：Container killed",
            "NodeManager日志显示内存不足",
        ],
        "possible_causes": [
            "任务申请内存过大，超过YARN配置的最大值",
            "YARN内存配置过小（yarn.scheduler.maximum-allocation-mb）",
            "数据量过大，处理需要更多内存",
            "任务代码存在内存泄漏",
        ],
        "diagnosis_steps": [
            "查看任务日志: yarn logs -applicationId <application_id>",
            "检查YARN内存配置: docker exec namenode cat /usr/local/hadoop/etc/hadoop/yarn-site.xml | grep memory",
            "查看YARN Web UI: http://localhost:8088，查看任务失败原因",
            "检查NodeManager日志: docker exec {container} tail -50 /usr/local/hadoop/logs/hadoop-hadoop-nodemanager-*.log",
        ],
        "fix_commands": {
            "check_config": 'docker exec namenode cat /usr/local/hadoop/etc/hadoop/yarn-site.xml | grep -E "(maximum-allocation-mb|resource.memory-mb)"',
            "increase_memory": 'docker exec namenode sh -c \'su - hadoop -c "sed -i \\"s/<value>128<\\/value>/<value>2048<\\/value>/\\" /usr/local/hadoop/etc/hadoop/yarn-site.xml"\'',
            "restart_yarn": 'docker exec namenode sh -c \'su - hadoop -c "yarn --daemon stop resourcemanager && yarn --daemon start resourcemanager"\'',
        },
    },
    
    "mapreduce_disk_insufficient": {
        "name": "MapReduce任务磁盘空间不足",
        "symptoms": [
            "任务失败，日志中出现 'No space left on device'",
            "HDFS写操作失败",
            "DataNode或NodeManager本地磁盘空间不足",
            "hdfs dfsadmin -report 显示磁盘使用率接近100%",
            "df -h 显示磁盘空间不足",
        ],
        "possible_causes": [
            "HDFS磁盘空间不足",
            "NodeManager本地磁盘空间不足（用于中间结果）",
            "临时文件未清理",
            "日志文件占用过多空间",
            "数据量过大",
        ],
        "diagnosis_steps": [
            "检查磁盘使用情况: docker exec {container} df -h",
            "检查HDFS使用情况: hdfs dfsadmin -report",
            "查看任务日志: yarn logs -applicationId <application_id>",
            "检查DataNode日志: docker exec {container} tail -50 /usr/local/hadoop/logs/hadoop-hadoop-datanode-*.log",
        ],
        "fix_commands": {
            "check_disk": 'docker exec {container} df -h',
            "clean_logs": 'docker exec {container} sh -c "find /usr/local/hadoop/logs -name \\"*.log.*\\" -mtime +7 -delete"',
            "clean_hdfs_temp": 'hdfs dfs -rm -r /tmp/*',
        },
    },
    
    "mapreduce_shuffle_failed": {
        "name": "MapReduce Shuffle阶段失败",
        "symptoms": [
            "MapReduce任务在Shuffle阶段失败",
            "任务日志中出现 'shuffle failed' 或 'ShuffleException'",
            "Reduce任务无法获取Map任务的输出",
            "Shuffle服务连接失败",
            "网络连接问题导致Shuffle失败",
        ],
        "possible_causes": [
            "Shuffle服务未启动或配置错误",
            "网络问题（延迟、丢包）",
            "磁盘I/O问题",
            "端口冲突",
            "防火墙阻止Shuffle端口",
        ],
        "diagnosis_steps": [
            "查看任务日志: yarn logs -applicationId <application_id>",
            "检查Shuffle服务端口: docker exec {container} netstat -tlnp | grep 13562",
            "检查网络连接: docker exec {container} ping namenode",
            "检查mapred-site.xml配置: docker exec {container} cat /usr/local/hadoop/etc/hadoop/mapred-site.xml | grep shuffle",
        ],
        "fix_commands": {
            "check_shuffle_port": 'docker exec {container} netstat -tlnp | grep 13562',
            "restart_nodemanager": 'docker exec {container} sh -c \'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"\'',
            "check_network": 'docker exec {container} ping -c 3 namenode',
        },
    },
    
    "mapreduce_task_timeout": {
        "name": "MapReduce任务超时",
        "symptoms": [
            "任务超时失败",
            "任务日志中出现 'timeout' 或 'SocketTimeoutException'",
            "任务执行时间超过配置的超时时间",
            "网络连接超时",
            "任务一直处于RUNNING状态，最终超时",
        ],
        "possible_causes": [
            "网络延迟过高",
            "数据量过大，处理时间过长",
            "超时配置过短",
            "节点负载过高，处理速度慢",
            "网络拥塞",
        ],
        "diagnosis_steps": [
            "查看任务状态: yarn application -status <application_id>",
            "查看任务日志: yarn logs -applicationId <application_id>",
            "检查网络延迟: docker exec {container} ping -c 10 namenode",
            "检查超时配置: docker exec namenode cat /usr/local/hadoop/etc/hadoop/yarn-site.xml | grep timeout",
        ],
        "fix_commands": {
            "check_task_status": 'yarn application -status <application_id>',
            "check_network_latency": 'docker exec {container} ping -c 10 namenode',
            "optimize_task": "优化任务：增加并行度、优化数据分区、减少数据量",
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

## 诊断输出格式要求（重要！）

### 输出格式
请以**对话风格的文本**输出诊断结果，使用清晰、专业的语言，便于用户理解。

### 输出结构要求

诊断结果应包含以下内容（以自然语言表述）：

1. **整体状态**：用简洁的语言描述集群整体状态（正常/警告/严重故障）
2. **诊断摘要**：简要总结检测到的故障情况
3. **故障详情**：对每个检测到的故障，提供：
   - 故障名称和严重程度（高/中/低）
   - 识别置信度（用百分比表示，如"95%"或"高度确信"）
   - 受影响的节点
   - 观察到的症状（列表形式）
   - 根本原因分析
   - 可能的相关因素（如有）
   - 诊断依据（日志片段、指标等证据）
   - 建议的修复步骤（按顺序列出）

### 故障类型标准库

诊断时，请识别故障类型并明确说明。标准故障类型包括：

**HDFS故障**：
- datanode_down: DataNode下线
- cluster_id_mismatch: 集群ID不匹配
- namenode_safemode: NameNode安全模式

**YARN故障**：
- resourcemanager_down: ResourceManager下线
- nodemanager_down: NodeManager下线
- yarn_config_error: YARN配置错误

**MapReduce故障**：
- mapreduce_memory_insufficient: MapReduce任务内存不足
- mapreduce_disk_insufficient: MapReduce任务磁盘空间不足
- mapreduce_shuffle_failed: MapReduce Shuffle阶段失败
- mapreduce_task_timeout: MapReduce任务超时

### 输出要求

1. **使用对话风格**：用自然、专业的语言描述，避免技术术语堆砌
2. **结构化表述**：使用标题、列表等Markdown格式增强可读性
3. **提供置信度**：对每个故障识别，说明置信度（如"95%确信"或"需要进一步确认"）
4. **明确严重性**：清楚说明每个故障的严重程度
5. **提供证据**：列出支持诊断的具体证据（日志片段、指标等）

### 输出示例

```
## 诊断结果

🔴 集群存在严重故障

经过全面检查，检测到1个严重故障：集群ID不匹配。这导致DataNode无法连接到NameNode，需要立即修复。

### 检测到的故障详情

**🔴 故障 1: 集群ID不匹配**

识别置信度: 95%（高度确信）
受影响节点: namenode, datanode1 和 datanode2

**观察到的症状：**
- DataNode日志出现 'Incompatible clusterIDs' 错误
- DataNode无法连接到NameNode
- hdfs dfsadmin -report 显示容量为0

**根本原因：**
NameNode被重新格式化，生成新的clusterID，但DataNode保留了旧的VERSION文件。

**诊断依据：**
- DataNode日志：'Incompatible clusterIDs'
- NameNode clusterID: cluster-1234567890
- DataNode clusterID: cluster-0987654321

**建议的修复步骤：**
1. 停止整个集群
2. 清理DataNode元数据（删除VERSION文件）
3. 重新启动集群
```

### 注意事项

- 如果检测到多个故障，按严重程度排序，优先描述最严重的故障
- 如果没有检测到故障，明确说明"经过全面检查，未发现任何故障，集群运行正常"
- 置信度较低时（低于70%），在描述中说明不确定性，建议进一步检查
- 使用清晰的分段和格式，便于用户阅读和理解

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

