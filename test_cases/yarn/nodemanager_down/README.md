# NodeManager下线 故障测试用例

## 故障描述

NodeManager下线 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `nodemanager_down`
- **故障名称**: NodeManager下线
- **类别**: YARN
- **严重程度**: high
- **经典性评分**: 4/5

## 典型症状

- NodeManager进程停止
- ResourceManager报告 lost/unhealthy NMs
- 任务无法分配Container，一直处于ACCEPTED状态
- ResourceManager Web UI显示 '0 active nodes'
- jps命令看不到NodeManager进程

## 可能原因

- NodeManager服务崩溃
- 容器停止运行
- 配置错误
- 资源不足
- 网络连接问题

## 检测方法

- 监控指标：NumLostNMs > 0 或 NumUnhealthyNMs > 0
- 进程检查：jps | grep NodeManager
- Web UI检查：http://localhost:8088/cluster/nodes
- 日志关键词匹配：'lost', 'unhealthy'

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
