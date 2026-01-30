# MapReduce Shuffle阶段失败 故障测试用例

## 故障描述

MapReduce Shuffle阶段失败 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `mapreduce_shuffle_failed`
- **故障名称**: MapReduce Shuffle阶段失败
- **类别**: MAPREDUCE
- **严重程度**: high
- **经典性评分**: 4/5

## 典型症状

- MapReduce任务在Shuffle阶段失败
- 任务日志中出现 'shuffle failed' 或 'ShuffleException'
- Reduce任务无法获取Map任务的输出
- Shuffle服务连接失败
- 网络连接问题导致Shuffle失败

## 可能原因

- Shuffle服务未启动或配置错误
- 网络问题（延迟、丢包）
- 磁盘I/O问题
- 端口冲突
- 防火墙阻止Shuffle端口

## 检测方法

- 日志关键词匹配：'shuffle failed', 'ShuffleHandler', 'ShuffleException'
- 任务日志检查：yarn logs -applicationId <app_id>
- 网络检查：ping、telnet Shuffle端口
- 服务检查：Shuffle服务是否运行

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
