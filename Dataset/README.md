# 故障诊断数据集

## 数据集说明

本数据集用于微调Hadoop集群故障诊断Agent，采用Instruction-Following格式。

## 数据格式

每个样本包含三个字段：

```json
{
  "instruction": "System Prompt内容，包含集群环境、命令格式、工作流程、故障类型标准库等",
  "input": "集群日志内容，格式与get_cluster_logs()工具返回的格式一致",
  "output": "对话风格的诊断结果，格式符合System Prompt要求"
}
```

## 数据集组成

### 正例（有故障）- 已创建示例
- ✅ `cluster_id_mismatch_001.json` - 集群ID不匹配故障
- ✅ `datanode_down_001.json` - DataNode下线故障
- ✅ `namenode_safemode_001.json` - NameNode安全模式故障
- ✅ `resourcemanager_down_001.json` - ResourceManager下线故障
- ✅ `nodemanager_down_001.json` - NodeManager下线故障
- ✅ `yarn_config_error_001.json` - YARN配置错误故障
- ✅ `mapreduce_memory_insufficient_001.json` - MapReduce任务内存不足故障
- ✅ `mapreduce_disk_insufficient_001.json` - MapReduce任务磁盘空间不足故障
- ⏳ `mapreduce_shuffle_failed_*.json` - MapReduce Shuffle阶段失败故障（待创建）
- ⏳ `mapreduce_task_timeout_*.json` - MapReduce任务超时故障（待创建）

### 负例（正常/无故障）- 已创建示例
- ✅ `normal_001.json` - 集群正常运行的情况

### 困难样本 - 已创建示例
- ✅ `hard_case_001.json` - 多故障叠加（DataNode下线 + NameNode安全模式）

## 标注规范

1. **输入格式**：必须匹配`get_cluster_logs()`工具的实际输出格式
   - 包含`[集群日志分析任务]`头部
   - 包含节点日志（`=== 节点名 ===`）
   - 包含思考检查点（`[思考点N]`）
   - 包含汇总提示（`[汇总提示]`）

2. **输出格式**：必须符合System Prompt要求
   - 对话风格的文本
   - 包含：整体状态、诊断摘要、故障详情
   - 故障详情包含：故障名称、置信度、受影响节点、症状、根本原因、证据、修复步骤

3. **故障类型**：必须从FAULT_TYPE_LIBRARY中选择
   - 只能使用10个标准故障类型
   - 不能使用自定义类型（除非是"custom"）

4. **置信度标注**：
   - 高置信度（>0.8）：症状明显、关键词匹配度高
   - 中置信度（0.5-0.8）：症状存在但不够明显
   - 低置信度（<0.5）：症状模糊、需要进一步检查

## 使用方式

1. **数据收集**：从`test_cases/`、`result/`、`return/`目录收集实际日志
2. **数据标注**：按照标注规范创建样本
3. **数据验证**：检查格式是否符合要求
4. **微调训练**：使用Instruction-Following格式进行微调

## 数据集规模目标

- 总样本量：150-200个
- 训练集（70%）：105-140个
- 验证集（15%）：22-30个
- 测试集（15%）：22-30个
