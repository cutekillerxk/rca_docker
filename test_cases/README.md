# 测试用例目录结构说明

## 目录结构

```
test_cases/
├── hdfs/                          # HDFS 相关故障
│   ├── datanode_down/             # DataNode下线
│   │   ├── case1/
│   │   │   ├── cluster_logs.txt   # 集群日志（Dataset的input）
│   │   │   └── return.txt         # Agent诊断结果（Dataset的output）
│   │   ├── case2/
│   │   │   ├── cluster_logs.txt
│   │   │   └── return.txt
│   │   └── README.md              # 该故障类型的说明
│   ├── namenode_safemode/         # NameNode安全模式
│   │   └── case1/
│   │       ├── cluster_logs.txt
│   │       └── return.txt
│   └── cluster_id_mismatch/        # 集群ID不匹配
│       └── case1/
│           ├── cluster_logs.txt
│           └── return.txt
├── yarn/                          # YARN 相关故障
│   ├── resourcemanager_down/      # ResourceManager下线
│   │   └── case1/
│   │       ├── cluster_logs.txt
│   │       └── return.txt
│   ├── nodemanager_down/          # NodeManager下线
│   │   └── case1/
│   │       ├── cluster_logs.txt
│   │       └── return.txt
│   └── yarn_config_error/        # YARN配置错误
│       └── case1/
│           ├── cluster_logs.txt
│           └── return.txt
└── mapreduce/                     # MapReduce 相关故障
    ├── mapreduce_memory_insufficient/  # MapReduce任务内存不足
    │   └── case1/
    │       ├── cluster_logs.txt
    │       └── return.txt
    ├── mapreduce_disk_insufficient/   # MapReduce任务磁盘空间不足
    │   └── case1/
    │       ├── cluster_logs.txt
    │       └── return.txt
    ├── mapreduce_shuffle_failed/     # MapReduce Shuffle阶段失败
    │   └── case1/
    │       ├── cluster_logs.txt
    │       └── return.txt
    └── mapreduce_task_timeout/       # MapReduce任务超时
        └── case1/
            ├── cluster_logs.txt
            └── return.txt
```

## 文件说明

### 1. cluster_logs.txt
- **内容**：完整的集群日志，格式与 `get_cluster_logs()` 工具返回的格式一致
- **来源**：从实际故障场景中收集（手动复现）
- **格式**：包含 `[集群日志分析任务]` 头部、节点日志（`=== 节点名 ===`）、思考检查点等
- **用途**：
  - 作为 Agent 的输入，测试故障诊断能力
  - 对应 Dataset 中的 `input` 字段

### 2. return.txt
- **内容**：Agent 的诊断结果，对话风格的文本
- **来源**：Agent 对 `cluster_logs.txt` 进行诊断后的输出
- **格式**：符合 System Prompt 的输出要求，包含：
  - 整体状态
  - 诊断摘要
  - 故障详情（故障名称、置信度、受影响节点、症状、根本原因、证据、修复步骤）
- **用途**：
  - 记录 Agent 的诊断结果
  - 对应 Dataset 中的 `output` 字段

## 与 Dataset 的关系

test_cases 中的文件可以直接用于生成 Dataset 样本：

```json
{
  "instruction": "[System Prompt，从 cluster_context.py 获取]",
  "input": "[cluster_logs.txt 的内容]",
  "output": "[return.txt 的内容]"
}
```

**优势**：
- 结构简洁，只保留必要文件
- 直接对应 Dataset 格式，便于数据转换
- 故障类型信息可以从目录路径获取（如：`hdfs/datanode_down`）

## 命名规范

1. **目录名**：使用 `FAULT_TYPE_LIBRARY` 中的 key（如 `datanode_down`）
2. **测试用例目录**：`case1`, `case2`, `case3`, ... 或使用描述性名称
3. **日志文件**：统一命名为 `cluster_logs.txt`
4. **诊断结果文件**：统一命名为 `return.txt`

## 使用场景

1. **故障诊断测试**：使用 `cluster_logs.txt` 作为输入，测试 Agent 的诊断能力
2. **数据集生成**：结合 System Prompt，生成 Dataset 格式的训练样本
3. **回归测试**：确保系统更新后仍能正确识别已知故障
4. **文档示例**：作为故障诊断的示例和参考

## 数据流转

```
故障复现 → 收集日志 → Agent诊断 → 保存结果
    ↓           ↓           ↓          ↓
cluster_logs.txt  →  Agent  →  return.txt  →  Dataset样本
```

1. **故障复现**：手动注入故障（参考 `故障复现方案.md`）
2. **收集日志**：收集故障时的集群日志，保存为 `cluster_logs.txt`
3. **Agent诊断**：使用 Agent 对日志进行诊断，保存结果为 `return.txt`
4. **生成Dataset**：结合 System Prompt，生成 Dataset 格式的 JSON 文件
