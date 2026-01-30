# NameNode安全模式 故障测试用例

## 故障描述

NameNode安全模式 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `namenode_safemode`
- **故障名称**: NameNode安全模式
- **类别**: HDFS
- **严重程度**: high
- **经典性评分**: 4/5

## 典型症状

- 无法执行HDFS写操作
- hdfs dfsadmin -safemode get 返回 'Safe mode is ON'
- 写操作报错：SafeModeException
- NameNode日志显示安全模式状态

## 可能原因

- 集群刚启动，正在进行数据块检查（正常，通常30秒内自动退出）
- 可用DataNode数量不足
- 数据块副本数不满足最低要求
- NameNode元数据损坏

## 检测方法

- 命令检查：hdfs dfsadmin -safemode get
- 日志关键词匹配：'Safe mode is ON'
- 写操作测试：hdfs dfs -mkdir /test

## 测试用例

### case1: 待填充
- **场景**: 待描述
- **日志文件**: `case1/cluster_logs.txt`
- **元数据**: `case1/metadata.json`
- **标准答案**: `case1/ground_truth.json`
