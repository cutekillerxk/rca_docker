#!/bin/bash
# 故障注入脚本 - 场景1: ResourceManager未启动
# 用法: ./inject_fault_scenario1.sh

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "故障注入: 场景1 - ResourceManager未启动"
echo "==========================================${NC}"
echo ""

echo -e "${YELLOW}停止ResourceManager...${NC}"
docker exec namenode sh -c 'su - hadoop -c "yarn --daemon stop resourcemanager"' || true
sleep 1

# 验证已停止
if docker exec namenode sh -c 'su - hadoop -c "jps"' | grep -q ResourceManager; then
    echo -e "${RED}错误: ResourceManager仍在运行${NC}"
    exit 1
else
    echo -e "${GREEN}✓ ResourceManager已停止${NC}"
fi

echo ""
echo -e "${YELLOW}现在可以测试故障诊断系统了${NC}"
echo "尝试提交一个MapReduce任务，应该会失败："
echo "  docker exec namenode sh -c 'su - hadoop -c \"yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 2 10\"'"
echo ""
echo -e "${BLUE}恢复服务（修复故障）:${NC}"
echo "  docker exec namenode sh -c 'su - hadoop -c \"yarn --daemon start resourcemanager\"'"
echo ""

