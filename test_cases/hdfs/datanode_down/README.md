# DataNode下线故障测试用例

## 故障描述

DataNode 服务停止运行，NameNode 检测到节点下线。

## 故障类型信息

- **故障类型ID**: `datanode_down`
- **故障名称**: DataNode下线
- **类别**: HDFS
- **严重程度**: 高
- **经典性评分**: 5/5

## 典型症状

1. `hdfs dfsadmin -report` 显示 Dead datanodes > 0
2. JMX中 NumDeadDataNodes > 0
3. NameNode日志出现 'dead' 或 'removed' 关键字
4. `jps` 命令看不到DataNode进程
5. DataNode Web UI无法访问

## 可能原因

- DataNode服务崩溃
- 容器停止运行
- 网络连接问题
- 磁盘空间不足
- 配置错误

## 检测方法

- 监控指标：NumDeadDataNodes > 0
- 日志关键词匹配：'dead', 'removed', 'heartbeat'
- 命令检查：`hdfs dfsadmin -report`
- 进程检查：`jps | grep DataNode`

## 测试用例

### case1: DataNode1 服务停止
- **场景**: 手动停止 datanode1 容器
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`

## 修复步骤

1. 检查容器状态: `docker ps -a | grep datanode1`
2. 检查DataNode进程: `docker exec datanode1 sh -c 'su - hadoop -c "jps"'`
3. 查看DataNode日志的最后错误
4. 检查磁盘空间: `docker exec datanode1 df -h`
5. 重启DataNode: `docker exec datanode1 sh -c 'su - hadoop -c "hdfs --daemon start datanode"'`
