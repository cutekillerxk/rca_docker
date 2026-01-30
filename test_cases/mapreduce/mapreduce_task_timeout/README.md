# MapReduce任务超时 故障测试用例

## 故障描述

MapReduce任务超时 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `mapreduce_task_timeout`
- **故障名称**: MapReduce任务超时
- **类别**: MAPREDUCE
- **严重程度**: medium
- **经典性评分**: 3/5

## 典型症状

- 任务超时失败
- 任务日志中出现 'timeout' 或 'SocketTimeoutException'
- 任务执行时间超过配置的超时时间
- 网络连接超时
- 任务一直处于RUNNING状态，最终超时

## 可能原因

- 网络延迟过高
- 数据量过大，处理时间过长
- 超时配置过短
- 节点负载过高，处理速度慢
- 网络拥塞

## 检测方法

- 日志关键词匹配：'timeout', 'SocketTimeoutException'
- 任务日志检查：yarn logs -applicationId <app_id>
- 任务状态检查：yarn application -status <app_id>
- 网络检查：ping延迟、网络质量

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
