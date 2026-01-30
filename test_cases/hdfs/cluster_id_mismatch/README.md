# 集群ID不匹配 故障测试用例

## 故障描述

集群ID不匹配 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `cluster_id_mismatch`
- **故障名称**: 集群ID不匹配
- **类别**: HDFS
- **严重程度**: high
- **经典性评分**: 4/5

## 典型症状

- DataNode日志出现 'Incompatible clusterIDs'
- DataNode无法连接到NameNode
- hdfs dfsadmin -report 显示容量为0
- DataNode启动失败

## 可能原因

- NameNode被重新格式化，生成新的clusterID
- DataNode保留了旧的VERSION文件
- 集群重建后未清理DataNode元数据

## 检测方法

- 日志关键词匹配：'Incompatible clusterIDs'
- 配置文件检查：对比NameNode和DataNode的VERSION文件
- 命令检查：hdfs dfsadmin -report 显示容量为0

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
