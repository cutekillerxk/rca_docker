# YARN配置错误 故障测试用例

## 故障描述

YARN配置错误 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `yarn_config_error`
- **故障名称**: YARN配置错误
- **类别**: YARN
- **严重程度**: medium
- **经典性评分**: 4/5

## 典型症状

- NodeManager日志出现 'UnknownHostException: wrong-hostname'
- NodeManager日志出现 'Connection refused'
- ResourceManager Web UI中该NodeManager显示为离线
- yarn node -list 显示该节点为 'lost' 或 'unhealthy'
- NodeManager无法连接到ResourceManager

## 可能原因

- yarn-site.xml中yarn.resourcemanager.hostname配置错误
- 网络配置错误
- DNS解析问题
- 配置文件格式错误

## 检测方法

- 日志关键词匹配：'UnknownHostException', 'Connection refused'
- 配置文件检查：yarn-site.xml中的ResourceManager地址
- Web UI检查：ResourceManager中节点状态
- 网络检查：ping ResourceManager地址

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
