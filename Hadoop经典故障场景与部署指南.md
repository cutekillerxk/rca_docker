# Hadoop经典故障场景与部署指南

## 📋 目录
1. [Hadoop组件详解（必读）](#hadoop组件详解必读)
2. [故障场景总览](#故障场景总览)
3. [部署准备](#部署准备)
4. [详细场景与部署指导](#详细场景与部署指导)

---

## Hadoop组件详解（必读）

> 💡 **本节用通俗易懂的语言解释Hadoop各组件的功能，即使你完全不了解Hadoop也能看懂。**

### 🎯 Hadoop是什么？

想象一下，你有一个**超大的文件**（比如1TB），你的电脑存不下，怎么办？

**传统方法**：买更大的硬盘 ❌（贵且有限）

**Hadoop方法**：把文件**切分成很多小块**，分别存到**多台电脑**上，需要时再**拼回来** ✅

这就是**分布式存储**的核心思想。

---

### 📦 组件1：HDFS（Hadoop分布式文件系统）

#### 用生活例子理解

**HDFS就像一个大型图书馆系统**：

- **NameNode（名称节点）** = **图书管理员**
  - 记住每本书（文件）放在哪个书架（DataNode）上
  - 记住每本书的名字、大小、位置
  - **不存实际的书**，只存"目录索引"
  
- **DataNode（数据节点）** = **实际的书架**
  - 真正存放书（数据）的地方
  - 每个书架（DataNode）存一部分书
  - 定期向管理员（NameNode）汇报："我这里有这些书"
  
- **SecondaryNameNode（辅助名称节点）** = **副管理员**
  - 帮助NameNode整理目录，减轻负担
  - 定期备份NameNode的"目录索引"

#### 技术细节

| 组件 | 作用 | 类比 |
|------|------|------|
| **NameNode** | 存储文件系统的元数据（文件名、目录结构、文件块位置） | 图书馆的目录卡片系统 |
| **DataNode** | 存储实际的数据块 | 图书馆的书架 |
| **SecondaryNameNode** | 定期合并NameNode的编辑日志，生成新的镜像文件 | 整理目录的助手 |

#### 为什么需要HDFS？

1. **大文件存储**：单个文件可以超过单机硬盘容量
2. **容错性**：每个数据块有多个副本（默认3个），一个DataNode坏了，数据还在
3. **高吞吐量**：多台机器并行读写，速度快

---

### ⚙️ 组件2：YARN（资源管理器）

#### 用生活例子理解

**YARN就像一个工厂的调度系统**：

- **ResourceManager（资源管理器）** = **工厂厂长**
  - 知道工厂有多少工人（CPU）、多少材料（内存）
  - 决定哪个任务分配给哪个车间（NodeManager）
  - 只有一个，管理整个工厂
  
- **NodeManager（节点管理器）** = **车间主任**
  - 管理自己车间的工人和材料
  - 向厂长汇报："我这里有2个工人，4GB材料可用"
  - 每个节点（机器）都有一个
  
- **Container（容器）** = **工作台**
  - 分配给具体任务的资源（CPU + 内存）
  - 任务在这个"工作台"上运行
  - 任务完成后，"工作台"回收给其他任务用

#### 技术细节

| 组件 | 作用 | 类比 |
|------|------|------|
| **ResourceManager** | 管理整个集群的资源（CPU、内存），决定任务分配给哪个节点 | 工厂厂长 |
| **NodeManager** | 管理单个节点的资源，向ResourceManager汇报，执行任务 | 车间主任 |
| **Container** | 分配给任务的资源单位（如：2核CPU + 4GB内存） | 工作台 |

#### 为什么需要YARN？

1. **资源管理**：多个人同时提交任务，YARN公平分配资源
2. **任务调度**：决定哪个任务先运行，哪个任务等待
3. **资源隔离**：每个任务有独立的资源，不会互相干扰

---

### 🔄 组件3：MapReduce（计算框架）

#### 用生活例子理解

**MapReduce就像统计全校学生成绩的过程**：

**场景**：统计每个班级的平均分

**传统方法**（一个人做）：
1. 拿到所有学生的成绩单
2. 一个一个看，累加每个班的分数
3. 计算平均值
4. **太慢了！** ❌

**MapReduce方法**（多人并行）：
1. **Map阶段（映射）**：
   - 把任务分给多个老师
   - 老师A统计1-3班，老师B统计4-6班，老师C统计7-9班
   - **并行处理**，速度快 ✅
   
2. **Shuffle阶段（洗牌）**：
   - 把相同班级的成绩收集到一起
   - 比如：所有"1班"的成绩放在一起
   
3. **Reduce阶段（归约）**：
   - 每个老师计算自己负责班级的平均分
   - 老师A计算1班平均分，老师B计算2班平均分...
   - **并行计算**，速度快 ✅

#### 技术细节

| 阶段 | 作用 | 输入 | 输出 |
|------|------|------|------|
| **Map** | 将输入数据切分成小块，并行处理，生成键值对 | 原始数据 | (key, value) 对 |
| **Shuffle** | 将相同key的数据收集到一起，发送给同一个Reducer | Map输出 | 按key分组的数据 |
| **Reduce** | 对每个key的所有value进行聚合计算（求和、平均等） | 分组后的数据 | 最终结果 |

#### 经典例子：WordCount（词频统计）

**任务**：统计一篇文章中每个单词出现的次数

**输入**：
```
hello world
hello hadoop
world mapreduce
```

**Map阶段**（并行处理）：
```
Map任务1: "hello world" → (hello, 1), (world, 1)
Map任务2: "hello hadoop" → (hello, 1), (hadoop, 1)
Map任务3: "world mapreduce" → (world, 1), (mapreduce, 1)
```

**Shuffle阶段**（按key分组）：
```
hello → [1, 1]
world → [1, 1]
hadoop → [1]
mapreduce → [1]
```

**Reduce阶段**（求和）：
```
hello → 2
world → 2
hadoop → 1
mapreduce → 1
```

#### 为什么需要MapReduce？

1. **并行计算**：大数据分成小块，多台机器同时处理
2. **容错性**：某个任务失败，自动重新执行
3. **简单编程模型**：只需写Map和Reduce函数，框架处理分布式细节

---

### 🔗 组件之间的关系

#### 完整的数据处理流程

```
用户提交任务
    ↓
YARN ResourceManager 接收任务
    ↓
YARN ResourceManager 分配资源（Container）
    ↓
YARN NodeManager 启动 Container
    ↓
MapReduce ApplicationMaster 启动
    ↓
MapReduce 从 HDFS 读取数据
    ↓
MapReduce 执行 Map 阶段
    ↓
MapReduce 执行 Shuffle 阶段
    ↓
MapReduce 执行 Reduce 阶段
    ↓
MapReduce 将结果写回 HDFS
    ↓
任务完成
```

#### 用生活例子理解整个流程

**场景**：分析100GB的日志文件，统计每个IP的访问次数

1. **用户提交任务** → "我要分析日志"
2. **YARN ResourceManager** → "好的，我给你分配资源"
3. **YARN NodeManager** → "我这里有资源，可以运行任务"
4. **MapReduce ApplicationMaster** → "我来协调整个任务"
5. **从HDFS读取数据** → "从分布式存储读取100GB日志"
6. **Map阶段** → "100个Map任务并行处理，每个处理1GB"
7. **Shuffle阶段** → "把相同IP的访问记录收集到一起"
8. **Reduce阶段** → "统计每个IP的访问次数"
9. **写回HDFS** → "把结果保存到分布式存储"
10. **任务完成** → "分析完成！"

---

### 📊 组件对比总结

| 组件 | 主要功能 | 类比 | 是否必须 |
|------|---------|------|----------|
| **HDFS** | 分布式存储 | 图书馆系统 | ✅ 必须（存储数据） |
| **YARN** | 资源管理 | 工厂调度系统 | ✅ 必须（运行任务） |
| **MapReduce** | 计算框架 | 统计流程 | ⚠️ 可选（可以用Spark等替代） |

---

### 🎓 学习路径建议

1. **先理解HDFS**：数据怎么存、怎么取
2. **再理解YARN**：任务怎么分配资源、怎么运行
3. **最后理解MapReduce**：任务具体怎么计算
4. **实践**：运行一个简单的WordCount任务，观察整个过程

---

### 🔍 常见问题解答

#### Q1: HDFS和普通文件系统有什么区别？

**普通文件系统**（如Windows的C盘）：
- 文件存在一台电脑上
- 这台电脑坏了，文件就丢了
- 文件太大（比如1TB），单机存不下

**HDFS**：
- 文件切分成很多块，存在多台电脑上
- 每块有多个副本，一台电脑坏了，数据还在
- 可以存储超大文件（PB级别）

#### Q2: YARN和操作系统有什么区别？

**操作系统**（如Linux）：
- 管理单台电脑的资源（CPU、内存）
- 决定哪个程序先运行

**YARN**：
- 管理**多台电脑**的资源（整个集群）
- 决定哪个任务在哪台电脑上运行
- 可以动态分配资源，用完回收

#### Q3: MapReduce和普通程序有什么区别？

**普通程序**：
- 在一台电脑上运行
- 数据太大时，处理很慢
- 电脑坏了，程序就停了

**MapReduce**：
- 在多台电脑上**并行**运行
- 数据分成小块，多台电脑同时处理，速度快
- 某台电脑坏了，任务自动在其他电脑上重新运行

#### Q4: 为什么需要这么多组件？不能简化吗？

**简化版本**（单机）：
- 一台电脑存数据、运行任务
- **问题**：数据太大存不下，处理太慢

**Hadoop版本**（分布式）：
- **HDFS**：多台电脑存数据（解决存储问题）
- **YARN**：多台电脑运行任务（解决资源管理问题）
- **MapReduce**：多台电脑并行计算（解决计算问题）

**结论**：每个组件解决不同的问题，缺一不可。

---

### 📝 记忆口诀

- **HDFS** = **存数据**（分布式存储）
- **YARN** = **管资源**（资源管理）
- **MapReduce** = **算数据**（并行计算）

**完整流程**：
```
数据存HDFS → YARN分配资源 → MapReduce计算 → 结果存HDFS
```

---

## 故障场景总览

### 综合排序（经典性 + 部署难度）

| 排名 | 故障场景 | 经典性 | 部署难度 | 综合评分 | 组件 |
|------|---------|--------|----------|----------|------|
| 1 | **YARN ResourceManager未启动** | ⭐⭐⭐⭐⭐ | ⭐ | 9.5 | YARN |
| 2 | **MapReduce任务因内存不足失败** | ⭐⭐⭐⭐⭐ | ⭐⭐ | 9.0 | YARN/MapReduce |
| 3 | **NodeManager未启动导致任务无法分配** | ⭐⭐⭐⭐ | ⭐ | 8.5 | YARN |
| 4 | **YARN配置错误（ResourceManager地址错误）** | ⭐⭐⭐⭐ | ⭐⭐ | 8.0 | YARN |
| 5 | **MapReduce任务因磁盘空间不足失败** | ⭐⭐⭐⭐ | ⭐⭐⭐ | 7.5 | HDFS/YARN |
| 6 | **Container启动失败（端口冲突）** | ⭐⭐⭐ | ⭐⭐ | 7.0 | YARN |
| 7 | **MapReduce任务因网络超时失败** | ⭐⭐⭐ | ⭐⭐⭐ | 6.5 | YARN/Network |
| 8 | **YARN队列资源不足** | ⭐⭐⭐ | ⭐⭐⭐ | 6.0 | YARN |
| 9 | **MapReduce Shuffle阶段失败** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 6.0 | MapReduce |
| 10 | **NodeManager磁盘空间不足** | ⭐⭐⭐ | ⭐⭐⭐ | 5.5 | YARN/HDFS |
| 11 | **MapReduce任务因权限问题失败** | ⭐⭐⭐ | ⭐⭐⭐⭐ | 5.0 | HDFS/YARN |
| 12 | **YARN ApplicationMaster启动失败** | ⭐⭐⭐ | ⭐⭐⭐⭐ | 4.5 | YARN |
| 13 | **MapReduce任务因数据倾斜失败** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 4.0 | MapReduce |
| 14 | **YARN Timeline Server故障** | ⭐⭐ | ⭐⭐⭐ | 3.5 | YARN |
| 15 | **MapReduce任务因代码错误失败** | ⭐⭐ | ⭐⭐⭐⭐⭐ | 2.5 | MapReduce |

**说明**：
- **经典性**：该故障在生产环境中出现的频率和重要性
- **部署难度**：1=最简单（配置即可），5=最复杂（需要复杂脚本或大量数据）
- **综合评分**：经典性 × 2 - 部署难度（优先经典且易部署的场景）

---

## 部署准备

### 第一步：启动YARN服务

#### 1.1 检查现有配置

**重要**：经过验证，你的集群**尚未配置YARN**。`yarn-site.xml` 和 `mapred-site.xml` 都是空配置文件。

因此，我们需要：
1. **先配置YARN**（修改配置文件）
2. **再启动YARN服务**

#### 1.2 YARN架构简介

**YARN (Yet Another Resource Negotiator)** 是Hadoop 2.0+的资源管理框架：

- **ResourceManager (RM)**：资源管理器，负责整个集群的资源分配
  - 运行在NameNode容器（`namenode`）
  - Web UI端口：8088
  - RPC端口：8032
  
- **NodeManager (NM)**：节点管理器，负责单个节点的资源管理
  - 运行在每个DataNode容器（`datanode1`, `datanode2`, `namenode`）
  - Web UI端口：8042
  - 向ResourceManager汇报资源使用情况

- **ApplicationMaster (AM)**：应用主控，负责单个应用的任务调度
  - 由ResourceManager启动
  - 运行在某个NodeManager上

#### 1.3 启动YARN服务

```bash
# 在namenode容器中启动ResourceManager
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon start resourcemanager"'

# 在所有节点启动NodeManager
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon start nodemanager"'
docker exec datanode1 sh -c 'su - hadoop -c "yarn --daemon start nodemanager"'
docker exec datanode2 sh -c 'su - hadoop -c "yarn --daemon start nodemanager"'
```

#### 1.4 验证YARN启动

```bash
# 检查ResourceManager进程
docker exec namenode sh -c 'su - hadoop -c "jps"'
# 应该看到：ResourceManager

# 检查NodeManager进程
docker exec datanode1 sh -c 'su - hadoop -c "jps"'
# 应该看到：NodeManager

# 访问ResourceManager Web UI
# http://localhost:8088
```

---

## 详细场景与部署指导

### 场景1：YARN ResourceManager未启动 ⭐⭐⭐⭐⭐ (最简单)

#### 故障描述
用户提交MapReduce任务时，任务无法提交，报错"Connection refused"或"ResourceManager is not available"。

#### 经典性：⭐⭐⭐⭐⭐
- 最常见的YARN故障
- 任何MapReduce任务都需要ResourceManager

#### 部署难度：⭐
- 只需停止ResourceManager服务

#### 故障注入步骤

```bash
# 1. 停止ResourceManager
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon stop resourcemanager"'

# 2. 验证已停止
docker exec namenode sh -c 'su - hadoop -c "jps"'
# 不应该看到ResourceManager

# 3. 提交一个简单的MapReduce任务（会失败）
docker exec namenode sh -c 'su - hadoop -c "yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 2 10"'
```

#### 预期错误信息
```
Exception in thread "main" java.net.ConnectException: Call From namenode/192.168.80.2 to namenode:8032 failed on connection exception
```

#### 诊断要点
- 检查ResourceManager进程是否存在（`jps`）
- 检查ResourceManager日志：`/usr/local/hadoop/logs/yarn-hadoop-resourcemanager-namenode.log`
- 检查端口8032是否监听：`netstat -tlnp | grep 8032`

#### 修复方法
```bash
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon start resourcemanager"'
```

---

### 场景2：MapReduce任务因内存不足失败 ⭐⭐⭐⭐⭐

#### 故障描述
MapReduce任务运行时，Container因内存不足被YARN杀死，任务失败。

#### 经典性：⭐⭐⭐⭐⭐
- 生产环境最常见的任务失败原因
- 资源分配不当导致

#### 部署难度：⭐⭐
- 需要配置较小的内存限制，然后提交需要更多内存的任务

#### 故障注入步骤

```bash
# 1. 修改yarn-site.xml，限制Container最大内存为128MB（很小）
docker exec namenode sh -c 'su - hadoop -c "cat >> /usr/local/hadoop/etc/hadoop/yarn-site.xml << EOF
  <property>
    <name>yarn.scheduler.maximum-allocation-mb</name>
    <value>128</value>
  </property>
  <property>
    <name>yarn.nodemanager.resource.memory-mb</name>
    <value>128</value>
  </property>
EOF"'

# 2. 重启ResourceManager和NodeManager
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon stop resourcemanager && yarn --daemon start resourcemanager"'
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"'
docker exec datanode1 sh -c 'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"'
docker exec datanode2 sh -c 'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"'

# 3. 提交一个需要较多内存的任务（会失败）
docker exec namenode sh -c 'su - hadoop -c "yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /input /output"'
```

#### 预期错误信息
```
Container killed on request. Exit code is 143
Container exited with a non-zero exit code 143
```

#### 诊断要点
- 查看YARN Web UI：http://localhost:8088，查看任务失败原因
- 检查NodeManager日志：`/usr/local/hadoop/logs/yarn-hadoop-nodemanager-*.log`
- 查看任务日志：`yarn logs -applicationId <application_id>`

#### 修复方法
```bash
# 恢复合理的内存配置（例如512MB或1GB）
docker exec namenode sh -c 'su - hadoop -c "sed -i \"/yarn.scheduler.maximum-allocation-mb/d\" /usr/local/hadoop/etc/hadoop/yarn-site.xml"'
docker exec namenode sh -c 'su - hadoop -c "sed -i \"/yarn.nodemanager.resource.memory-mb/d\" /usr/local/hadoop/etc/hadoop/yarn-site.xml"'
# 重启服务
```

---

### 场景3：NodeManager未启动导致任务无法分配 ⭐⭐⭐⭐

#### 故障描述
ResourceManager运行正常，但所有NodeManager都未启动，导致无法分配Container，任务一直处于ACCEPTED状态。

#### 经典性：⭐⭐⭐⭐
- 常见于集群重启后忘记启动NodeManager

#### 部署难度：⭐
- 只需停止NodeManager

#### 故障注入步骤

```bash
# 1. 停止所有NodeManager
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon stop nodemanager"'
docker exec datanode1 sh -c 'su - hadoop -c "yarn --daemon stop nodemanager"'
docker exec datanode2 sh -c 'su - hadoop -c "yarn --daemon stop nodemanager"'

# 2. 验证已停止
docker exec namenode sh -c 'su - hadoop -c "jps"'
# 不应该看到NodeManager

# 3. 提交任务（会一直等待）
docker exec namenode sh -c 'su - hadoop -c "yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 2 10"'
```

#### 预期错误信息
- 任务状态一直为"ACCEPTED"，不会进入"RUNNING"
- ResourceManager Web UI显示"0 active nodes"

#### 诊断要点
- 检查NodeManager进程：`jps | grep NodeManager`
- 检查ResourceManager Web UI：http://localhost:8088/cluster/nodes
- 查看ResourceManager日志

#### 修复方法
```bash
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon start nodemanager"'
docker exec datanode1 sh -c 'su - hadoop -c "yarn --daemon start nodemanager"'
docker exec datanode2 sh -c 'su - hadoop -c "yarn --daemon start nodemanager"'
```

---

### 场景4：YARN配置错误（ResourceManager地址错误） ⭐⭐⭐⭐

#### 故障描述
NodeManager配置的ResourceManager地址错误，导致NodeManager无法连接到ResourceManager。

#### 经典性：⭐⭐⭐⭐
- 配置错误是常见问题

#### 部署难度：⭐⭐
- 需要修改配置文件

#### 故障注入步骤

```bash
# 1. 修改yarn-site.xml，将ResourceManager地址改为错误的
docker exec datanode1 sh -c 'su - hadoop -c "sed -i \"s/<value>namenode<\/value>/<value>wrong-hostname<\/value>/\" /usr/local/hadoop/etc/hadoop/yarn-site.xml"'

# 2. 重启NodeManager
docker exec datanode1 sh -c 'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"'

# 3. 等待几秒，检查NodeManager日志
docker exec datanode1 sh -c 'su - hadoop -c "tail -20 /usr/local/hadoop/logs/yarn-hadoop-nodemanager-datanode1.log"'
```

#### 预期错误信息
```
java.net.UnknownHostException: wrong-hostname
或
java.net.ConnectException: Connection refused
```

#### 诊断要点
- 检查NodeManager日志中的连接错误
- 检查yarn-site.xml中的`yarn.resourcemanager.hostname`配置
- 检查ResourceManager Web UI，看该节点是否在线

#### 修复方法
```bash
# 恢复正确的配置
docker exec datanode1 sh -c 'su - hadoop -c "sed -i \"s/<value>wrong-hostname<\/value>/<value>namenode<\/value>/\" /usr/local/hadoop/etc/hadoop/yarn-site.xml"'
docker exec datanode1 sh -c 'su - hadoop -c "yarn --daemon stop nodemanager && yarn --daemon start nodemanager"'
```

---

### 场景5：MapReduce任务因磁盘空间不足失败 ⭐⭐⭐⭐

#### 故障描述
MapReduce任务运行时，中间结果或最终输出写入HDFS时，因磁盘空间不足失败。

#### 经典性：⭐⭐⭐⭐
- 生产环境常见问题

#### 部署难度：⭐⭐⭐
- 需要限制磁盘空间或填充磁盘

#### 故障注入步骤

```bash
# 方法1：填充DataNode磁盘（简单但危险）
# 在datanode1上创建大文件占满磁盘
docker exec datanode1 sh -c 'dd if=/dev/zero of=/tmp/fill_disk bs=1M count=1000 2>/dev/null || true'

# 方法2：修改HDFS配置，降低可用空间阈值（更安全）
# 在namenode上修改hdfs-site.xml
docker exec namenode sh -c 'su - hadoop -c "cat >> /usr/local/hadoop/etc/hadoop/hdfs-site.xml << EOF
  <property>
    <name>dfs.datanode.du.reserved</name>
    <value>107374182400</value>
  </property>
EOF"'
# 重启DataNode
docker exec namenode sh -c 'su - hadoop -c "hdfs --daemon stop datanode && hdfs --daemon start datanode"'

# 3. 提交一个会产生大量输出的任务
docker exec namenode sh -c 'su - hadoop -c "hdfs dfs -mkdir -p /input && echo \"test data\" | hdfs dfs -put - /input/test.txt"'
docker exec namenode sh -c 'su - hadoop -c "yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /input /output"'
```

#### 预期错误信息
```
java.io.IOException: No space left on device
```

#### 诊断要点
- 检查DataNode磁盘使用情况：`df -h`
- 检查HDFS使用情况：`hdfs dfsadmin -report`
- 查看DataNode日志

#### 修复方法
```bash
# 清理临时文件
docker exec datanode1 sh -c 'rm -f /tmp/fill_disk'
# 或恢复配置
```

---

### 场景6-15：其他故障场景

由于篇幅限制，其他场景的详细指导将在后续补充。以下是简要说明：

**场景6：Container启动失败（端口冲突）**
- 修改yarn-site.xml，设置NodeManager使用的端口与已占用端口冲突

**场景7：MapReduce任务因网络超时失败**
- 修改yarn-site.xml，设置极短的网络超时时间

**场景8：YARN队列资源不足**
- 配置YARN队列，限制队列资源，提交超过限制的任务

**场景9：MapReduce Shuffle阶段失败**
- 修改mapred-site.xml，配置错误的Shuffle服务

**场景10：NodeManager磁盘空间不足**
- 类似场景5，但针对NodeManager本地目录

**场景11：MapReduce任务因权限问题失败**
- 修改HDFS目录权限，使任务无法写入

**场景12：YARN ApplicationMaster启动失败**
- 配置错误导致AM无法启动

**场景13：MapReduce任务因数据倾斜失败**
- 准备倾斜数据，提交任务

**场景14：YARN Timeline Server故障**
- Timeline Server未启动或配置错误

**场景15：MapReduce任务因代码错误失败**
- 编写有bug的MapReduce程序

---

## 下一步行动

### 推荐顺序

1. **立即开始**：场景1（ResourceManager未启动）- 最简单，验证YARN基础功能
2. **第二优先级**：场景2（内存不足）- 经典且实用
3. **第三优先级**：场景3（NodeManager未启动）- 完善YARN诊断能力
4. **后续扩展**：根据你的需求，逐步添加其他场景

### 需要我帮你做什么？

1. **生成完整的YARN启动脚本**：一键启动/停止YARN服务
2. **生成故障注入脚本**：自动化注入上述故障
3. **扩展诊断系统**：添加YARN相关的诊断工具和知识库
4. **准备测试数据**：为MapReduce任务准备输入数据

告诉我你想从哪个场景开始，我会提供详细的步骤指导！

