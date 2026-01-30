# Agent输入信息说明

## 一、为什么Agent会判断DataNode连接不正常？

根据诊断报告中的信息："集群状态显示DataNode数量为0（存活0，离线0）"，Agent做出这个判断是基于以下**多维度信息**的综合分析：

### 1. **监控指标（Metrics）**
- **NameNode JMX指标**：
  - `NumLiveDataNodes`: 存活的DataNode数量（如果为0，说明NameNode没有检测到任何DataNode心跳）
  - `NumDeadDataNodes`: 离线的DataNode数量
  - `MissingBlocks`: 缺失的数据块数
  - `CorruptBlocks`: 损坏的数据块数
  
- **DataNode JMX指标**：
  - 如果DataNode的JMX接口无法访问，会返回`status: "error"`
  - DataNode状态：`running`（正常）或`stopped`（停止）

### 2. **集群状态（Cluster State）**
从监控指标中提取的关键状态：
```python
cluster_state = {
    "datanode_count": {
        "live": 0,    # 从NameNode的NumLiveDataNodes提取
        "dead": 0,    # 从NameNode的NumDeadDataNodes提取
        "total": 0    # live + dead
    },
    "hdfs_status": "unknown",  # 如果dead > 0则为"degraded"，如果live == total则为"healthy"
    "storage": {...}
}
```

### 3. **日志信息（Logs）**
- 从日志中可以看到很多节点显示"无新日志"，这可能表明：
  - DataNode服务未启动
  - DataNode服务启动但无日志输出
  - 日志文件不存在或无法读取

---

## 二、Agent的输入信息详解

### 2.1 分类Agent（Classifier）的输入

**输入数据结构**（`orchestrator.py:238-242`）：
```python
classification_input = {
    "logs": global_context.get("logs", {}),      # 所有节点的日志
    "metrics": global_context.get("metrics", {}), # 监控指标
    "user_query": user_input,                     # 用户查询
}
```

**实际输入内容**：

1. **logs**（来自`ContextCollector.collect_all_context()`）：
   - 通过`read_all_cluster_logs()`收集所有节点的日志
   - 格式：`{"节点名": "日志内容"}`
   - 包含的节点：NameNode、DataNode1、DataNode2、SecondaryNameNode、ResourceManager、NodeManager等
   - 日志内容：每个节点的最新日志（默认200行，可配置）

2. **metrics**（来自`collect_all_metrics()`）：
   - **NameNode指标**：
     ```python
     {
         "status": "normal" | "error",
         "timestamp": "...",
         "metrics": {
             "NumLiveDataNodes": {"name": "...", "value": 0, "status": "..."},
             "NumDeadDataNodes": {"name": "...", "value": 0, "status": "..."},
             "MissingBlocks": {...},
             "CorruptBlocks": {...},
             "safemode": {...},
             ...
         }
     }
     ```
   - **DataNode指标**（每个DataNode）：
     ```python
     {
         "status": "normal" | "error",
         "node": "datanode1",
         "metrics": {
             "datanode_status": {"value": "running" | "stopped", ...},
             "storage_usage": {...},
             ...
         }
     }
     ```
   - **ResourceManager指标**
   - **NodeManager指标**

3. **user_query**：
   - 用户的原始查询，如"查看集群状态，分析是否有故障"

**分类Agent的Prompt构建**（`classifier.py:76-125`）：
- 包含用户查询
- 包含所有节点的日志（每个节点最多2000字符，超出会截断）
- 包含监控指标（JSON格式，最多2000字符，超出会截断）
- 要求输出JSON格式的分类结果

---

### 2.2 专家Agent（Expert）的输入

**输入数据结构**（`orchestrator.py:254-261`）：
```python
expert_input = {
    "fault_type": fault_type,                              # 故障类型（来自分类Agent）
    "logs": global_context.get("logs", {}),                # 全局日志
    "metrics": global_context.get("metrics", {}),          # 全局监控指标
    "cluster_state": global_context.get("cluster_state", {}), # 集群状态（从metrics提取）
    "related_faults": classification_result.get("related_faults"), # 可能相关的故障
    "user_query": user_input,                              # 用户查询
}
```

**实际输入内容**：

1. **fault_type**：
   - 分类Agent识别的故障类型，如`"datanode_down"`

2. **logs**：
   - 与分类Agent相同的日志信息
   - 专家Agent会显示前3个节点的日志（每个节点最多1000字符）

3. **metrics**：
   - 与分类Agent相同的监控指标
   - 专家Agent会提取关键指标显示，如：
     - NameNode的`NumLiveDataNodes`、`NumDeadDataNodes`、`MissingBlocks`、`CorruptBlocks`

4. **cluster_state**（从metrics中提取，`context_collector.py:120-134`）：
   ```python
   {
       "datanode_count": {
           "live": 0,      # 从NameNode的NumLiveDataNodes提取
           "dead": 0,      # 从NameNode的NumDeadDataNodes提取
           "total": 0      # live + dead
       },
       "hdfs_status": "unknown",  # "healthy" | "degraded" | "unknown"
       "storage": {
           "total": 0,
           "used": 0,
           "remaining": 0
       }
   }
   ```

5. **related_faults**：
   - 分类Agent识别出的可能相关的故障类型列表

6. **user_query**：
   - 用户的原始查询

**专家Agent的Prompt构建**（以HDFS专家为例，`hdfs_expert.py:93-185`）：
- 故障类型和详细信息
- 用户查询
- 全局日志上下文（前3个节点，每个最多1000字符）
- 关键监控指标（NameNode的关键指标）
- 集群状态（DataNode数量、HDFS状态）
- 可能相关的故障
- 工具调用结果（如果有）

---

## 三、数据收集流程

### 3.1 全局上下文收集（`ContextCollector.collect_all_context()`）

**步骤1：收集日志**（`context_collector.py:49-100`）
- 调用`read_all_cluster_logs()`读取所有节点日志
- 保存日志读取状态
- **同时保存日志到`result`目录**（新增功能）

**步骤2：收集监控指标**（`context_collector.py:102-108`）
- 调用`collect_all_metrics()`收集所有监控指标
- 包括：NameNode、DataNode、ResourceManager、NodeManager的JMX指标

**步骤3：提取集群状态**（`context_collector.py:110-116`）
- 从监控指标中提取关键状态信息
- 计算DataNode数量、HDFS状态等

**返回的全局上下文**：
```python
{
    "timestamp": "2026-01-29T19:46:09",
    "logs": {
        "NameNode": "...",
        "DataNode1": "...",
        "DataNode2": "...",
        ...
    },
    "metrics": {
        "namenode": {...},
        "datanodes": {
            "datanode1": {...},
            "datanode2": {...},
            "datanode-namenode": {...}
        },
        "resourcemanager": {...},
        "nodemanagers": {...}
    },
    "cluster_state": {
        "datanode_count": {"live": 0, "dead": 0, "total": 0},
        "hdfs_status": "unknown",
        "storage": {...}
    }
}
```

---

## 四、为什么判断DataNode连接不正常？

基于上述输入信息，Agent会综合以下证据做出判断：

### 证据1：监控指标显示DataNode数量为0
- NameNode的`NumLiveDataNodes = 0`：说明NameNode没有收到任何DataNode的心跳
- NameNode的`NumDeadDataNodes = 0`：说明NameNode也没有记录任何死掉的DataNode
- **结论**：NameNode完全没有检测到DataNode的存在

### 证据2：集群状态显示异常
- `datanode_count.live = 0`
- `datanode_count.dead = 0`
- `datanode_count.total = 0`
- `hdfs_status = "unknown"`
- **结论**：集群状态异常，没有DataNode连接

### 证据3：日志显示"无新日志"
- DataNode1、DataNode2的日志显示"无新日志"
- 可能原因：
  - DataNode服务未启动
  - DataNode服务启动但无日志输出
  - 日志文件不存在

### 证据4：DataNode JMX可能无法访问
- 如果DataNode的JMX接口无法访问，`metrics.datanodes[datanode1].status = "error"`
- 说明DataNode服务可能未运行或无法连接

---

## 五、总结

Agent判断DataNode连接不正常是基于**多维度信息**的综合分析：

1. ✅ **监控指标**：NameNode的JMX显示DataNode数量为0
2. ✅ **集群状态**：从监控指标提取的状态显示异常
3. ✅ **日志信息**：DataNode日志显示"无新日志"
4. ✅ **JMX连接**：DataNode的JMX接口可能无法访问

这些信息都是通过`ContextCollector`统一收集，然后分别传递给分类Agent和专家Agent进行分析的。Agent不是仅基于日志，而是基于**日志+监控指标+集群状态**的综合信息进行判断。
