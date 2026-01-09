#!/bin/bash
# 集群配置信息查询脚本
# 用于收集集群的真实配置信息

echo "======================================================================"
echo "                  Hadoop 集群配置信息查询                              "
echo "======================================================================"
echo ""

echo "========== 1. 容器状态 =========="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep -E "namenode|datanode|NAMES"
echo ""

echo "========== 2. Java版本和路径 =========="
echo "Java版本:"
docker exec namenode sh -c 'su - hadoop -c "java -version"' 2>&1
echo ""
echo "JAVA_HOME:"
docker exec namenode sh -c 'su - hadoop -c "echo \$JAVA_HOME"'
echo ""

echo "========== 3. Hadoop版本 =========="
docker exec namenode sh -c 'su - hadoop -c "hadoop version"' 2>&1 | head -5
echo ""

echo "========== 4. Hadoop环境变量 =========="
echo "HADOOP_HOME:"
docker exec namenode sh -c 'su - hadoop -c "echo \$HADOOP_HOME"'
echo "HADOOP_CONF_DIR:"
docker exec namenode sh -c 'su - hadoop -c "echo \$HADOOP_CONF_DIR"'
echo ""

echo "========== 5. core-site.xml 关键配置 =========="
docker exec namenode sh -c 'cat /usr/local/hadoop/etc/hadoop/core-site.xml' 2>/dev/null
echo ""

echo "========== 6. hdfs-site.xml 关键配置 =========="
docker exec namenode sh -c 'cat /usr/local/hadoop/etc/hadoop/hdfs-site.xml' 2>/dev/null
echo ""

echo "========== 7. workers 文件 =========="
docker exec namenode sh -c 'cat /usr/local/hadoop/etc/hadoop/workers' 2>/dev/null
echo ""

echo "========== 8. YARN配置检查 =========="
echo "yarn-site.xml:"
docker exec namenode sh -c 'cat /usr/local/hadoop/etc/hadoop/yarn-site.xml 2>/dev/null || echo "文件不存在或为空"'
echo ""
echo "YARN进程:"
docker exec namenode sh -c 'su - hadoop -c "jps"' 2>/dev/null | grep -E "ResourceManager|NodeManager" || echo "没有YARN进程运行"
echo ""

echo "========== 9. 各节点Java进程 =========="
echo "--- namenode容器 ---"
docker exec namenode sh -c 'su - hadoop -c "jps"' 2>/dev/null
echo ""
echo "--- datanode1容器 ---"
docker exec datanode1 sh -c 'su - hadoop -c "jps"' 2>/dev/null
echo ""
echo "--- datanode2容器 ---"
docker exec datanode2 sh -c 'su - hadoop -c "jps"' 2>/dev/null
echo ""

echo "========== 10. HDFS集群报告 =========="
docker exec namenode sh -c 'su - hadoop -c "hdfs dfsadmin -report"' 2>/dev/null
echo ""

echo "========== 11. 关键HDFS配置参数 =========="
echo "fs.defaultFS:"
docker exec namenode sh -c 'su - hadoop -c "hdfs getconf -confKey fs.defaultFS"' 2>/dev/null
echo ""
echo "dfs.replication:"
docker exec namenode sh -c 'su - hadoop -c "hdfs getconf -confKey dfs.replication"' 2>/dev/null
echo ""
echo "dfs.blocksize:"
docker exec namenode sh -c 'su - hadoop -c "hdfs getconf -confKey dfs.blocksize"' 2>/dev/null
echo ""
echo "dfs.namenode.name.dir:"
docker exec namenode sh -c 'su - hadoop -c "hdfs getconf -confKey dfs.namenode.name.dir"' 2>/dev/null
echo ""
echo "dfs.datanode.data.dir:"
docker exec namenode sh -c 'su - hadoop -c "hdfs getconf -confKey dfs.datanode.data.dir"' 2>/dev/null
echo ""
echo "dfs.heartbeat.interval:"
docker exec namenode sh -c 'su - hadoop -c "hdfs getconf -confKey dfs.heartbeat.interval"' 2>/dev/null
echo ""

echo "========== 12. Docker网络 =========="
docker network ls | grep -E "hadoop|NETWORK"
echo ""

echo "========== 13. 日志文件列表 =========="
docker exec namenode sh -c 'ls -la /usr/local/hadoop/logs/*.log 2>/dev/null | head -10' || echo "无日志文件"
echo ""

echo "========== 14. HDFS数据目录结构 =========="
docker exec namenode sh -c 'ls -la /usr/local/hadoop/hdfs/ 2>/dev/null' || echo "目录不存在"
echo ""

echo "======================================================================"
echo "                        查询完成                                       "
echo "======================================================================"

