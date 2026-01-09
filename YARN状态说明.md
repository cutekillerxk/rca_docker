# YARN和MapReduce当前状态说明

## ✅ 已安装（软件包）

### 1. YARN软件包
- **位置**：`/usr/local/hadoop/share/hadoop/yarn/`
- **命令**：`/usr/local/hadoop/bin/yarn` ✅ 存在
- **版本**：Hadoop 3.3.6（已确认）

### 2. MapReduce软件包
- **位置**：`/usr/local/hadoop/share/hadoop/mapreduce/`
- **示例程序**：`hadoop-mapreduce-examples-3.3.6.jar` ✅ 存在

## ⚠️ 未配置（配置文件）

### 1. yarn-site.xml
- **状态**：空配置文件（只有默认注释）
- **需要**：添加ResourceManager、NodeManager等配置

### 2. mapred-site.xml
- **状态**：空配置文件
- **需要**：指定使用YARN作为MapReduce框架

## ❌ 未启动（服务）

### 当前运行的服务（jps结果）：
```
NameNode          ✅ 运行中
DataNode          ✅ 运行中
SecondaryNameNode ✅ 运行中
```

### 未运行的服务：
```
ResourceManager   ❌ 未启动
NodeManager       ❌ 未启动
```

---

## 📋 总结

| 项目 | 状态 | 说明 |
|------|------|------|
| **软件安装** | ✅ 完成 | YARN和MapReduce的jar包都在 |
| **命令可用** | ✅ 可用 | `yarn`命令可以运行 |
| **配置文件** | ❌ 未配置 | yarn-site.xml和mapred-site.xml是空的 |
| **服务运行** | ❌ 未启动 | ResourceManager和NodeManager没有运行 |

---

## 🚀 下一步操作

1. **配置YARN**：填写yarn-site.xml和mapred-site.xml
2. **启动服务**：启动ResourceManager和NodeManager
3. **验证功能**：提交一个MapReduce任务测试

---

## 💡 类比理解

就像买了一台电脑：
- ✅ **硬件已安装**（YARN和MapReduce软件包已安装）
- ⚠️ **系统未配置**（配置文件是空的，需要设置）
- ❌ **服务未启动**（ResourceManager和NodeManager没有运行）

你需要：
1. 配置系统（填写配置文件）
2. 启动服务（运行ResourceManager和NodeManager）
3. 才能使用YARN和MapReduce功能

---

## 📖 启动YARN和MapReduce的完整流程（详细操作指南）

### 第一步：配置 yarn-site.xml（在所有节点）

#### 为什么需要这一步？
YARN需要知道：
- ResourceManager运行在哪台机器
- 各个服务的端口号
- 每个节点有多少资源（内存、CPU）
- 如何与MapReduce配合工作

#### 具体操作

1. 在namenode容器中编辑配置文件：
```bash
docker exec -it namenode sh -c 'su - hadoop -c "vim /usr/local/hadoop/etc/hadoop/yarn-site.xml"'
```

参数说明：
- `docker exec -it namenode`：进入namenode容器，`-it`表示交互式（可以编辑）
- `su - hadoop`：切换到hadoop用户（`-`表示加载环境变量）
- `vim`：文本编辑器

2. 在vim中，按`i`进入插入模式，删除现有内容，粘贴以下配置：

```xml
<?xml version="1.0"?>
<configuration>
  <!-- ResourceManager配置 -->
  <property>
    <name>yarn.resourcemanager.hostname</name>
    <value>namenode</value>
    <description>ResourceManager运行在namenode容器</description>
  </property>
  
  <property>
    <name>yarn.resourcemanager.webapp.address</name>
    <value>0.0.0.0:8088</value>
    <description>ResourceManager Web UI地址</description>
  </property>
  
  <property>
    <name>yarn.resourcemanager.address</name>
    <value>namenode:8032</value>
    <description>ResourceManager RPC地址</description>
  </property>
  
  <property>
    <name>yarn.resourcemanager.scheduler.address</name>
    <value>namenode:8030</value>
    <description>ResourceManager调度器地址</description>
  </property>
  
  <property>
    <name>yarn.resourcemanager.resource-tracker.address</name>
    <value>namenode:8031</value>
    <description>ResourceManager资源追踪器地址</description>
  </property>
  
  <!-- NodeManager配置 -->
  <property>
    <name>yarn.nodemanager.aux-services</name>
    <value>mapreduce_shuffle</value>
    <description>NodeManager辅助服务，用于MapReduce Shuffle</description>
  </property>
  
  <property>
    <name>yarn.nodemanager.aux-services.mapreduce_shuffle.class</name>
    <value>org.apache.hadoop.mapred.ShuffleHandler</value>
  </property>
  
  <!-- 资源限制 -->
  <property>
    <name>yarn.nodemanager.resource.memory-mb</name>
    <value>1024</value>
    <description>每个NodeManager可用内存（MB）</description>
  </property>
  
  <property>
    <name>yarn.nodemanager.resource.cpu-vcores</name>
    <value>2</value>
    <description>每个NodeManager可用CPU核心数</description>
  </property>
  
  <property>
    <name>yarn.scheduler.maximum-allocation-mb</name>
    <value>1024</value>
    <description>单个Container最大内存（MB）</description>
  </property>
  
  <property>
    <name>yarn.scheduler.maximum-allocation-vcores</name>
    <value>2</value>
    <description>单个Container最大CPU核心数</description>
  </property>
</configuration>
```

3. 保存并退出：按`Esc`，然后输入`:wq`回车

#### 配置项说明

| 配置项 | 值 | 作用 |
|--------|-----|------|
| `yarn.resourcemanager.hostname` | `namenode` | 告诉所有节点，ResourceManager在namenode容器 |
| `yarn.resourcemanager.webapp.address` | `0.0.0.0:8088` | Web UI地址，`0.0.0.0`表示监听所有网卡，`8088`是端口 |
| `yarn.resourcemanager.address` | `namenode:8032` | RPC地址，用于客户端提交任务 |
| `yarn.resourcemanager.scheduler.address` | `namenode:8030` | 调度器地址，用于任务调度 |
| `yarn.resourcemanager.resource-tracker.address` | `namenode:8031` | 资源追踪器地址，NodeManager通过此地址汇报资源 |
| `yarn.nodemanager.aux-services` | `mapreduce_shuffle` | 告诉NodeManager要启动shuffle服务（MapReduce需要） |
| `yarn.nodemanager.resource.memory-mb` | `1024` | 每个NodeManager可用内存（MB），根据容器实际内存调整 |
| `yarn.nodemanager.resource.cpu-vcores` | `2` | 每个NodeManager可用CPU核心数 |
| `yarn.scheduler.maximum-allocation-mb` | `1024` | 单个Container最大内存，不能超过NodeManager的内存 |
| `yarn.scheduler.maximum-allocation-vcores` | `2` | 单个Container最大CPU核心数 |

4. 将相同配置复制到其他节点：
```bash
# 复制到 datanode1
docker exec -it datanode1 sh -c 'su - hadoop -c "vim /usr/local/hadoop/etc/hadoop/yarn-site.xml"'
# （粘贴相同内容）

# 复制到 datanode2
docker exec -it datanode2 sh -c 'su - hadoop -c "vim /usr/local/hadoop/etc/hadoop/yarn-site.xml"'
# （粘贴相同内容）
```

为什么所有节点都要配置？
- NodeManager需要知道ResourceManager的地址
- 所有节点使用相同的配置，保证一致性

---

### 第二步：配置 mapred-site.xml（在所有节点）

#### 为什么需要这一步？
告诉MapReduce使用YARN作为资源管理框架（而不是旧的MapReduce v1）。

#### 具体操作

1. 在namenode容器中编辑：
```bash
docker exec -it namenode sh -c 'su - hadoop -c "vim /usr/local/hadoop/etc/hadoop/mapred-site.xml"'
```

2. 粘贴以下内容：
```xml
<?xml version="1.0"?>
<configuration>
  <!-- 使用YARN作为MapReduce框架 -->
  <property>
    <name>mapreduce.framework.name</name>
    <value>yarn</value>
    <description>使用YARN运行MapReduce任务</description>
  </property>
  
  <!-- MapReduce历史服务器（可选，用于查看历史任务） -->
  <property>
    <name>mapreduce.jobhistory.address</name>
    <value>namenode:10020</value>
    <description>MapReduce历史服务器地址</description>
  </property>
  
  <property>
    <name>mapreduce.jobhistory.webapp.address</name>
    <value>namenode:19888</value>
    <description>MapReduce历史服务器Web UI地址</description>
  </property>
</configuration>
```

3. 保存并退出：`Esc`，然后`:wq`

#### 配置项说明

| 配置项 | 值 | 作用 |
|--------|-----|------|
| `mapreduce.framework.name` | `yarn` | 使用YARN运行MapReduce（而不是旧的MapReduce v1） |
| `mapreduce.jobhistory.address` | `namenode:10020` | 历史服务器地址（可选，用于查看已完成任务） |
| `mapreduce.jobhistory.webapp.address` | `namenode:19888` | 历史服务器Web UI（可选） |

4. 将相同配置复制到 datanode1 和 datanode2（同上）

---

### 第三步：启动 ResourceManager（在namenode容器）

#### 为什么需要这一步？
ResourceManager是YARN的核心，负责：
- 接收任务提交请求
- 分配资源给任务
- 调度任务执行

#### 具体操作

```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn --daemon start resourcemanager"'
```

参数说明：
- `docker exec namenode`：在namenode容器中执行命令
- `su - hadoop`：切换到hadoop用户
- `source ... hadoop-env.sh`：加载Hadoop环境变量（设置PATH等）
- `/usr/local/hadoop/bin/yarn`：yarn命令的完整路径
- `--daemon`：以后台守护进程方式运行
- `start resourcemanager`：启动ResourceManager服务

#### 验证是否启动成功

```bash
docker exec namenode sh -c 'su - hadoop -c "jps"'
```

应该看到`ResourceManager`进程。

如果没看到，查看日志：
```bash
docker exec namenode sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-resourcemanager-namenode.log"'
```

---

### 第四步：启动 NodeManager（在所有节点）

#### 为什么需要这一步？
NodeManager负责：
- 管理单个节点的资源（CPU、内存）
- 向ResourceManager汇报资源
- 启动和管理Container（任务运行环境）

#### 具体操作

在namenode容器中启动：
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn --daemon start nodemanager"'
```

在datanode1容器中启动：
```bash
docker exec datanode1 sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn --daemon start nodemanager"'
```

在datanode2容器中启动：
```bash
docker exec datanode2 sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn --daemon start nodemanager"'
```

参数说明：
- `start nodemanager`：启动NodeManager服务
- 其他参数同上

#### 验证是否启动成功

在每个容器中检查：
```bash
# namenode
docker exec namenode sh -c 'su - hadoop -c "jps"'
# 应该看到：NodeManager

# datanode1
docker exec datanode1 sh -c 'su - hadoop -c "jps"'
# 应该看到：NodeManager

# datanode2
docker exec datanode2 sh -c 'su - hadoop -c "jps"'
# 应该看到：NodeManager
```

---

### 第五步：验证YARN集群状态

#### 方法1：查看节点列表

```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn node -list"'
```

参数说明：
- `yarn node -list`：列出所有注册到ResourceManager的NodeManager节点

预期输出：应该看到3个节点（namenode、datanode1、datanode2）

#### 方法2：访问Web UI

在浏览器打开：`http://localhost:8088`

应该看到：
- 集群概览
- 节点列表（3个节点）
- 运行中的任务

#### 方法3：查看集群信息

```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn top"'
```

参数说明：
- `yarn top`：类似Linux的top，实时显示集群资源使用情况

---

### 第六步：测试MapReduce任务

#### 为什么需要这一步？
验证YARN和MapReduce是否正常工作。

#### 测试1：Pi计算（最简单）

```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 2 10"'
```

参数说明：
- `yarn jar`：通过YARN运行jar包
- `/usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar`：MapReduce示例程序路径
- `pi`：计算Pi的程序
- `2`：Map任务数量
- `10`：每个Map任务的采样点数

预期结果：输出Pi的近似值（如3.14...）

#### 测试2：WordCount（经典示例）

1. 准备测试数据：
```bash
# 创建输入目录
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/hdfs dfs -mkdir -p /input"'

# 创建测试文件
docker exec namenode sh -c 'su - hadoop -c "echo \"hello world hello hadoop\" | /usr/local/hadoop/bin/hdfs dfs -put - /input/test1.txt"'
docker exec namenode sh -c 'su - hadoop -c "echo \"hadoop yarn mapreduce\" | /usr/local/hadoop/bin/hdfs dfs -put - /input/test2.txt"'
```

参数说明：
- `hdfs dfs -mkdir -p /input`：在HDFS创建目录，`-p`表示如果父目录不存在则创建
- `hdfs dfs -put - /input/test1.txt`：将标准输入（`-`）的内容上传到HDFS

2. 运行WordCount：
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /input /output"'
```

参数说明：
- `wordcount`：词频统计程序
- `/input`：输入目录（HDFS路径）
- `/output`：输出目录（HDFS路径，不能已存在）

3. 查看结果：
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/hdfs dfs -cat /output/part-r-00000"'
```

参数说明：
- `hdfs dfs -cat`：查看HDFS文件内容
- `/output/part-r-00000`：WordCount的输出文件（Reduce阶段的输出）

预期结果：每个单词及其出现次数，例如：
```
hadoop	2
hello	2
mapreduce	1
world	1
yarn	1
```

---

## 常见问题排查

### 问题1：ResourceManager启动失败

可能原因：
1. 端口被占用
2. 配置文件错误

排查方法：
```bash
# 查看日志
docker exec namenode sh -c 'su - hadoop -c "tail -50 /usr/local/hadoop/logs/yarn-hadoop-resourcemanager-namenode.log"'
```

### 问题2：NodeManager无法连接到ResourceManager

可能原因：
1. ResourceManager未启动
2. `yarn.resourcemanager.hostname`配置错误
3. 网络问题

排查方法：
```bash
# 检查ResourceManager是否运行
docker exec namenode sh -c 'su - hadoop -c "jps"'

# 检查配置
docker exec datanode1 sh -c 'su - hadoop -c "cat /usr/local/hadoop/etc/hadoop/yarn-site.xml | grep resourcemanager.hostname"'
```

### 问题3：任务提交失败

可能原因：
1. YARN服务未启动
2. 资源不足

排查方法：
```bash
# 检查YARN节点
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn node -list"'

# 查看任务日志
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && /usr/local/hadoop/bin/yarn logs -applicationId <application_id>"'
```

---

## 总结

完整流程：
1. 配置`yarn-site.xml`（所有节点）
2. 配置`mapred-site.xml`（所有节点）
3. 启动ResourceManager（namenode）
4. 启动NodeManager（所有节点）
5. 验证集群状态
6. 测试MapReduce任务

每一步的作用和参数都在上面详细说明了。按照这个流程操作即可。如果遇到问题，告诉我具体在哪一步出错。
