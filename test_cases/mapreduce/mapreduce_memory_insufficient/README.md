# MapReduce任务内存不足 故障测试用例

## 故障描述

MapReduce任务内存不足 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `mapreduce_memory_insufficient`
- **故障名称**: MapReduce任务内存不足
- **类别**: MAPREDUCE
- **严重程度**: high
- **经典性评分**: 5/5

## 典型症状

- Container被YARN杀死
- 任务失败，日志中出现 'Container killed on request. Exit code is 143'
- 任务日志中出现 'OutOfMemoryError'
- YARN Web UI显示任务失败，原因：Container killed
- NodeManager日志显示内存不足

## 可能原因

- 任务申请内存过大，超过YARN配置的最大值
- YARN内存配置过小（yarn.scheduler.maximum-allocation-mb）
- 数据量过大，处理需要更多内存
- 任务代码存在内存泄漏

## 检测方法

- 日志关键词匹配：'Container killed', 'Exit code 143', 'OutOfMemoryError'
- 任务日志检查：yarn logs -applicationId <app_id>
- 监控指标：Container内存使用情况
- 配置检查：yarn-site.xml中的内存配置

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
