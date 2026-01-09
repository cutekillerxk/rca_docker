# 容器中Hadoop的PATH环境变量说明

## 📋 当前状态

### 默认PATH（未加载Hadoop配置）
```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
```
**问题**：不包含Hadoop的bin和sbin目录，无法直接使用`hadoop`、`yarn`、`hdfs`命令。

---

### 完整PATH（加载Hadoop配置后）
```bash
source /usr/local/hadoop/etc/hadoop/hadoop-env.sh
```
**结果**：
```
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/usr/local/hadoop/bin:/usr/local/hadoop/sbin
```

**新增的路径**：
- `/usr/local/hadoop/bin` - Hadoop用户命令（hadoop, hdfs, yarn, mapred）
- `/usr/local/hadoop/sbin` - Hadoop管理命令（start-dfs.sh, stop-dfs.sh等）

---

## 🔍 环境变量配置位置

### 1. hadoop-env.sh（主要配置）
**位置**：`/usr/local/hadoop/etc/hadoop/hadoop-env.sh`

**内容**：
```bash
export HADOOP_HOME=/usr/local/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
```

### 2. .bashrc（用户配置）
**位置**：`/home/hadoop/.bashrc`

**内容**：
```bash
export HADOOP_HOME=/usr/local/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
```

---

## ⚠️ 重要发现

### 问题：环境变量不会自动加载

当你使用 `docker exec` 执行命令时：
```bash
docker exec namenode sh -c 'su - hadoop -c "hadoop version"'
```

**结果**：命令找不到，因为：
1. `su - hadoop` 会加载 `.bashrc`，但可能在某些情况下不生效
2. `hadoop-env.sh` 需要手动 `source` 才能生效

### 解决方案

#### 方法1：显式source hadoop-env.sh（推荐）
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && hadoop version"'
```

#### 方法2：使用完整路径
```bash
docker exec namenode sh -c 'su - hadoop -c "/usr/local/hadoop/bin/hadoop version"'
```

#### 方法3：在命令前设置环境变量
```bash
docker exec namenode sh -c 'su - hadoop -c "export PATH=\$PATH:/usr/local/hadoop/bin:/usr/local/hadoop/sbin && hadoop version"'
```

---

## 📊 命令位置

### bin目录（用户命令）
```
/usr/local/hadoop/bin/
├── hadoop      # Hadoop通用命令
├── hdfs        # HDFS命令
├── yarn        # YARN命令
├── mapred      # MapReduce命令
└── ...
```

### sbin目录（管理命令）
```
/usr/local/hadoop/sbin/
├── start-dfs.sh      # 启动HDFS
├── stop-dfs.sh       # 停止HDFS
├── start-yarn.sh     # 启动YARN
├── stop-yarn.sh      # 停止YARN
└── ...
```

---

## 💡 建议

### 在脚本中使用

**推荐方式**（在start_yarn.sh等脚本中）：
```bash
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && yarn --daemon start resourcemanager"'
```

**或者使用完整路径**：
```bash
docker exec namenode sh -c 'su - hadoop -c "/usr/local/hadoop/bin/yarn --daemon start resourcemanager"'
```

---

## 🔧 验证命令

```bash
# 检查默认PATH
docker exec namenode sh -c 'su - hadoop -c "echo \$PATH"'

# 检查加载Hadoop配置后的PATH
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && echo \$PATH"'

# 检查命令位置
docker exec namenode sh -c 'su - hadoop -c "source /usr/local/hadoop/etc/hadoop/hadoop-env.sh && which hadoop && which yarn && which hdfs"'
```

---

## 📝 总结

| 项目 | 值 |
|------|-----|
| **HADOOP_HOME** | `/usr/local/hadoop` |
| **默认PATH** | 不包含Hadoop目录 |
| **完整PATH** | `...:/usr/local/hadoop/bin:/usr/local/hadoop/sbin` |
| **配置位置** | `/usr/local/hadoop/etc/hadoop/hadoop-env.sh` |
| **需要手动加载** | ✅ 是（需要source） |

