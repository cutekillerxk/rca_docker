# YARN和MapReduce监控与日志检测指南

## 📋 目录
1. [监控端口和Web UI](#监控端口和web-ui)
2. [JMX监控端点](#jmx监控端点)
3. [日志文件位置和命名规则](#日志文件位置和命名规则)
4. [docker-compose.yml端口映射配置](#docker-composeyml端口映射配置)
5. [错误检测方法](#错误检测方法)

---

## 监控端口和Web UI

### YARN ResourceManager Web UI

**端口**：`8088`（容器内端口）

**访问地址**：
- 容器内：`http://localhost:8088`
- 宿主机：`http://localhost:8088`（需要端口映射）

**功能**：
- 查看集群概览（总内存、总CPU、节点数）
- 查看运行中的任务（Applications）
- 查看节点列表（Nodes）
- 查看任务历史（History）
- 查看调度器信息（Scheduler）

**是否需要端口映射**：✅ **需要**（如果要从宿主机访问）

---

### YARN NodeManager Web UI

**端口**：`8042`（容器内端口）

**访问地址**：
- 容器内：`http://localhost:8042`
- 宿主机：需要端口映射（每个节点不同）

**功能**：
- 查看节点资源使用情况
- 查看运行中的Container
- 查看节点日志

**是否需要端口映射**：⚠️ **可选**（主要用于调试，不是必须的）

---

### MapReduce历史服务器（JobHistory Server）

**端口**：`19888`（容器内端口）

**访问地址**：
- 容器内：`http://localhost:19888`
- 宿主机：`http://localhost:19888`（需要端口映射）

**功能**：
- 查看已完成的任务历史
- 查看任务详细信息（Map/Reduce进度、日志等）

**是否需要端口映射**：✅ **建议**（方便查看任务历史）

**注意**：历史服务器需要单独启动（不是自动启动的）

---

## JMX监控端点

### YARN ResourceManager JMX

**端点**：`http://localhost:8088/jmx`

**访问方式**：
- 容器内：`curl http://localhost:8088/jmx`
- 宿主机：需要通过docker exec在容器内访问

**关键指标**：
- `NumActiveNMs`：活跃的NodeManager数量
- `NumDecommissionedNMs`：已停用的NodeManager数量
- `NumLostNMs`：丢失的NodeManager数量
- `NumUnhealthyNMs`：不健康的NodeManager数量
- `AvailableMB`：可用内存（MB）
- `AllocatedMB`：已分配内存（MB）
- `PendingMB`：等待分配的内存（MB）
- `AppsSubmitted`：已提交的应用数
- `AppsRunning`：运行中的应用数
- `AppsCompleted`：已完成的应用数
- `AppsFailed`：失败的应用数
- `AppsKilled`：被终止的应用数

**示例命令**：
```bash
# 在容器内访问JMX
docker exec namenode sh -c 'su - hadoop -c "curl -s http://localhost:8088/jmx | python3 -m json.tool | head -100"'
```

---

### YARN NodeManager JMX

**端点**：`http://localhost:8042/jmx`

**访问方式**：
- 容器内：`curl http://localhost:8042/jmx`
- 宿主机：需要通过docker exec在容器内访问

**关键指标**：
- `NumActiveContainers`：活跃的Container数量
- `NumCompletedContainers`：已完成的Container数量
- `NumFailedContainers`：失败的Container数量
- `NumKilledContainers`：被终止的Container数量
- `AllocatedMB`：已分配内存（MB）
- `AllocatedVCores`：已分配CPU核心数
- `AvailableMB`：可用内存（MB）
- `AvailableVCores`：可用CPU核心数

**示例命令**：
```bash
# 在namenode容器内访问NodeManager JMX
docker exec namenode sh -c 'su - hadoop -c "curl -s http://localhost:8042/jmx | python3 -m json.tool | head -100"'

# 在datanode1容器内访问NodeManager JMX
docker exec datanode1 sh -c 'su - hadoop -c "curl -s http://localhost:8042/jmx | python3 -m json.tool | head -100"'
```

---

### MapReduce ApplicationMaster JMX

**端点**：每个任务的ApplicationMaster都有独立的JMX端点

**端口**：动态分配（通常在10000-65535之间）

**访问方式**：通过ResourceManager Web UI查看任务详情，找到ApplicationMaster的Web UI地址

**关键指标**：
- `MapsCompleted`：已完成的Map任务数
- `MapsTotal`：总Map任务数
- `ReducesCompleted`：已完成的Reduce任务数
- `ReducesTotal`：总Reduce任务数
- `MapProgress`：Map进度百分比
- `ReduceProgress`：Reduce进度百分比

---

## 日志文件位置和命名规则

### 日志目录

**位置**：`/usr/local/hadoop/logs/`（所有节点相同）

### YARN日志文件命名规则

**格式**：`yarn-hadoop-{服务名}-{hostname}.log`

**示例**：
- ResourceManager（namenode容器）：
  - `yarn-hadoop-resourcemanager-namenode.log`
  - `yarn-hadoop-resourcemanager-namenode.out`（标准输出）

- NodeManager（namenode容器）：
  - `yarn-hadoop-nodemanager-namenode.log`
  - `yarn-hadoop-nodemanager-namenode.out`

- NodeManager（datanode1容器）：
  - `yarn-hadoop-nodemanager-datanode1.log`
  - `yarn-hadoop-nodemanager-datanode1.out`

- NodeManager（datanode2容器）：
  - `yarn-hadoop-nodemanager-datanode2.log`
  - `yarn-hadoop-nodemanager-datanode2.out`

### MapReduce日志

**任务日志位置**：
- 通过YARN日志聚合：`/tmp/logs`（HDFS路径，如果启用了日志聚合）
- 通过`yarn logs`命令查看：`yarn logs -applicationId <application_id>`

**历史服务器日志**：
- `mapred-hadoop-historyserver-namenode.log`（如果启动了历史服务器）

### 查看日志命令

```bash
# 查看ResourceManager日志（最后50行）
docker exec namenode sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-resourcemanager-namenode.log"'

# 查看NodeManager日志（namenode容器）
docker exec namenode sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-namenode.log"'

# 查看NodeManager日志（datanode1容器）
docker exec datanode1 sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-datanode1.log"'

# 查看NodeManager日志（datanode2容器）
docker exec datanode2 sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-datanode2.log"'

# 查看MapReduce任务日志
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn logs -applicationId application_1234567890_0001"'
```

---

## docker-compose.yml端口映射配置

### 当前状态

**已映射的端口**：
- NameNode Web UI: `9870:9870`
- DataNode Web UI: `9864:9864`, `9865:9864`, `9866:9864`
- HDFS RPC: `9000:9000`, `8020:8020`

**未映射的端口**：
- ResourceManager Web UI: `8088` ❌
- NodeManager Web UI: `8042` ❌（每个节点）
- MapReduce历史服务器: `19888` ❌

### 需要添加的端口映射

#### 方案1：最小配置（只映射必要的端口）

**ResourceManager Web UI**（必须）：
```yaml
ports:
  - "0.0.0.0:8088:8088"   # ResourceManager Web UI
```

**MapReduce历史服务器**（建议）：
```yaml
ports:
  - "0.0.0.0:19888:19888" # MapReduce历史服务器 Web UI
```

**NodeManager Web UI**（可选，用于调试）：
```yaml
# namenode容器（也运行NodeManager，所以需要8042端口）
ports:
  - "0.0.0.0:8042:8042"   # NodeManager Web UI (namenode容器)

# datanode1容器
ports:
  - "0.0.0.0:8043:8042"   # NodeManager Web UI (datanode1容器，映射到8043避免冲突)

# datanode2容器
ports:
  - "0.0.0.0:8044:8042"   # NodeManager Web UI (datanode2容器，映射到8044避免冲突)
```

**注意**：namenode容器也会运行NodeManager（因为namenode容器同时运行DataNode和NodeManager），所以也需要8042端口映射。

#### 完整的docker-compose.yml修改示例

```yaml
services:
  namenode:
    # ... 其他配置 ...
    ports:
      - "0.0.0.0:9870:9870"   # NameNode Web UI
      - "0.0.0.0:9000:9000"   # HDFS RPC
      - "0.0.0.0:8020:8020"   # HDFS RPC (alternative)
      - "0.0.0.0:50070:50070" # NameNode Web UI (Hadoop 2.x)
      - "0.0.0.0:2225:22"     # SSH
      - "0.0.0.0:9866:9864"   # DataNode Web UI (namenode容器内)
      - "0.0.0.0:8088:8088"   # ResourceManager Web UI ⭐ 新增
      - "0.0.0.0:19888:19888" # MapReduce历史服务器 Web UI ⭐ 新增
      - "0.0.0.0:8042:8042"   # NodeManager Web UI (namenode容器) ⭐ 新增（可选）

  datanode1:
    # ... 其他配置 ...
    ports:
      - "0.0.0.0:9864:9864"   # DataNode Web UI
      - "0.0.0.0:2223:22"     # SSH
      - "0.0.0.0:8043:8042"   # NodeManager Web UI ⭐ 新增（可选）

  datanode2:
    # ... 其他配置 ...
    ports:
      - "0.0.0.0:9865:9864"   # DataNode Web UI
      - "0.0.0.0:2224:22"     # SSH
      - "0.0.0.0:8044:8042"   # NodeManager Web UI ⭐ 新增（可选）
```

### 修改后的操作步骤

1. **修改docker-compose.yml**：添加上述端口映射
2. **重启容器**：
```bash
docker-compose down
docker-compose up -d
```

**注意**：重启容器不会影响HDFS数据（因为使用了volume），但会停止所有服务，需要重新启动HDFS和YARN服务。

---

## 错误检测方法

### 方法1：检查服务进程（最基础）

```bash
# 检查ResourceManager
docker exec namenode sh -c 'su - hadoop -c "jps"'
# 应该看到：ResourceManager

# 检查NodeManager（所有节点）
docker exec namenode sh -c 'su - hadoop -c "jps"'
docker exec datanode1 sh -c 'su - hadoop -c "jps"'
docker exec datanode2 sh -c 'su - hadoop -c "jps"'
# 应该看到：NodeManager
```

### 方法2：检查Web UI（最直观）

**ResourceManager Web UI**：
- 访问：`http://localhost:8088`
- 检查：
  - 节点列表是否显示3个节点
  - 是否有错误提示
  - 任务是否能正常提交

**NodeManager Web UI**（如果映射了端口）：
- namenode容器：`http://localhost:8042`
- datanode1容器：`http://localhost:8043`
- datanode2容器：`http://localhost:8044`

### 方法3：检查日志（最详细）

**查看ResourceManager错误日志**：
```bash
docker exec namenode sh -c 'su - hadoop -c "tail -100 /usr/local/hadoop/logs/yarn-hadoop-resourcemanager-namenode.log | grep -i error"'
```

**查看NodeManager错误日志**：
```bash
# namenode容器
docker exec namenode sh -c 'su - hadoop -c "tail -100 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-namenode.log | grep -i error"'

# datanode1容器
docker exec datanode1 sh -c 'su - hadoop -c "tail -100 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-datanode1.log | grep -i error"'

# datanode2容器
docker exec datanode2 sh -c 'su - hadoop -c "tail -100 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-datanode2.log | grep -i error"'
```

### 方法4：检查JMX指标（最专业）

**检查ResourceManager JMX**：
```bash
docker exec namenode sh -c 'su - hadoop -c "curl -s http://localhost:8088/jmx | python3 -m json.tool | grep -E \"(NumActiveNMs|NumLostNMs|AppsFailed|AppsKilled)\""'
```

**检查NodeManager JMX**：
```bash
docker exec namenode sh -c 'su - hadoop -c "curl -s http://localhost:8042/jmx | python3 -m json.tool | grep -E \"(NumFailedContainers|NumKilledContainers)\""'
```

### 方法5：使用YARN命令（最方便）

**查看节点状态**：
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn node -list"'
```

**查看任务状态**：
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn application -list"'
```

**查看失败的任务**：
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn application -list -appStates FAILED"'
```

### 方法6：检查网络连接（排查连接问题）

**检查ResourceManager端口是否监听**：
```bash
docker exec namenode sh -c 'su - hadoop -c "netstat -tlnp | grep 8088"'
```

**检查NodeManager端口是否监听**：
```bash
docker exec namenode sh -c 'su - hadoop -c "netstat -tlnp | grep 8042"'
docker exec datanode1 sh -c 'su - hadoop -c "netstat -tlnp | grep 8042"'
docker exec datanode2 sh -c 'su - hadoop -c "netstat -tlnp | grep 8042"'
```

---

## 常见错误检测场景

### 场景1：ResourceManager启动失败

**检测方法**：
```bash
# 1. 检查进程
docker exec namenode sh -c 'su - hadoop -c "jps"'
# 如果没有ResourceManager，说明启动失败

# 2. 查看日志
docker exec namenode sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-resourcemanager-namenode.log"'

# 3. 检查端口
docker exec namenode sh -c 'su - hadoop -c "netstat -tlnp | grep 8088"'
```

**常见原因**：
- 端口被占用
- 配置文件错误
- 内存不足

### 场景2：NodeManager无法连接到ResourceManager

**检测方法**：
```bash
# 1. 检查ResourceManager是否运行
docker exec namenode sh -c 'su - hadoop -c "jps"'

# 2. 检查NodeManager日志
docker exec datanode1 sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-datanode1.log | grep -i error"'

# 3. 检查配置
docker exec datanode1 sh -c 'su - hadoop -c "cat /usr/local/hadoop/etc/hadoop/yarn-site.xml | grep resourcemanager.hostname"'
```

**常见原因**：
- ResourceManager未启动
- 配置的hostname错误
- 网络问题

### 场景3：任务提交失败

**检测方法**：
```bash
# 1. 检查YARN节点
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn node -list"'

# 2. 查看任务日志
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn logs -applicationId <application_id>"'

# 3. 检查ResourceManager Web UI
# 访问 http://localhost:8088，查看任务失败原因
```

**常见原因**：
- 没有可用的NodeManager
- 资源不足
- 配置错误

---

## 总结

### 必须的端口映射

| 服务 | 容器内端口 | 宿主机端口 | 是否必须 |
|------|-----------|-----------|----------|
| ResourceManager Web UI | 8088 | 8088 | ✅ 必须 |
| MapReduce历史服务器 | 19888 | 19888 | ⚠️ 建议 |

### 可选的端口映射

| 服务 | 容器内端口 | 宿主机端口 | 是否必须 | 说明 |
|------|-----------|-----------|----------|------|
| NodeManager Web UI (namenode) | 8042 | 8042 | ❌ 可选 | namenode容器也运行NodeManager |
| NodeManager Web UI (datanode1) | 8042 | 8043 | ❌ 可选 | 映射到8043避免与namenode冲突 |
| NodeManager Web UI (datanode2) | 8042 | 8044 | ❌ 可选 | 映射到8044避免冲突 |

### 日志文件位置

- **所有日志**：`/usr/local/hadoop/logs/`
- **命名规则**：`yarn-hadoop-{服务名}-{hostname}.log`
- **日志聚合**：`/tmp/logs`（HDFS路径，如果启用）

### JMX端点

- **ResourceManager JMX**：`http://localhost:8088/jmx`
- **NodeManager JMX**：`http://localhost:8042/jmx`（每个节点）
- **访问方式**：需要通过docker exec在容器内访问

### 推荐的错误检测流程

1. **快速检查**：访问ResourceManager Web UI (`http://localhost:8088`)
2. **详细检查**：查看日志文件
3. **专业检查**：查看JMX指标
4. **命令检查**：使用`yarn node -list`和`yarn application -list`

