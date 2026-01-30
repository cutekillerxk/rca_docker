# MapReduce任务磁盘空间不足 故障测试用例

## 故障描述

MapReduce任务磁盘空间不足 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `mapreduce_disk_insufficient`
- **故障名称**: MapReduce任务磁盘空间不足
- **类别**: MAPREDUCE
- **严重程度**: high
- **经典性评分**: 4/5

## 典型症状

- 任务失败，日志中出现 'No space left on device'
- HDFS写操作失败
- DataNode或NodeManager本地磁盘空间不足
- hdfs dfsadmin -report 显示磁盘使用率接近100%
- df -h 显示磁盘空间不足

## 可能原因

- HDFS磁盘空间不足
- NodeManager本地磁盘空间不足（用于中间结果）
- 临时文件未清理
- 日志文件占用过多空间
- 数据量过大

## 检测方法

- 日志关键词匹配：'No space left on device', 'DiskError'
- 磁盘检查：df -h
- HDFS检查：hdfs dfsadmin -report
- 任务日志检查：yarn logs -applicationId <app_id>

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
