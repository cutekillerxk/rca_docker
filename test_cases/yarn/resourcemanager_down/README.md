# ResourceManager下线 故障测试用例

## 故障描述

ResourceManager下线 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `resourcemanager_down`
- **故障名称**: ResourceManager下线
- **类别**: YARN
- **严重程度**: high
- **经典性评分**: 5/5

## 典型症状

- ResourceManager进程停止
- 任务无法提交，报错 'Connection refused'
- ResourceManager Web UI无法访问 (http://localhost:8088)
- jps命令看不到ResourceManager进程
- 端口8032未监听

## 可能原因

- ResourceManager服务崩溃
- 容器停止运行
- 端口占用
- 配置错误
- 内存不足

## 检测方法

- 进程检查：jps | grep ResourceManager
- 端口检查：netstat -tlnp | grep 8032
- 日志关键词匹配：'Connection refused', '8032'
- Web UI检查：http://localhost:8088

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
