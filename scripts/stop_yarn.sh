#!/bin/bash
# 停止YARN服务脚本
# 用法: ./stop_yarn.sh

set -e

echo "=========================================="
echo "停止YARN服务"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 停止ResourceManager
stop_resourcemanager() {
    echo -e "${YELLOW}停止ResourceManager (namenode)...${NC}"
    docker exec namenode sh -c 'su - hadoop -c "yarn --daemon stop resourcemanager"' || true
    sleep 1
    echo -e "${GREEN}✓ ResourceManager已停止${NC}"
}

# 停止NodeManager
stop_nodemanager() {
    local container=$1
    echo -e "${YELLOW}停止NodeManager (${container})...${NC}"
    docker exec ${container} sh -c 'su - hadoop -c "yarn --daemon stop nodemanager"' || true
    sleep 1
    echo -e "${GREEN}✓ NodeManager已停止 (${container})${NC}"
}

# 停止ResourceManager
stop_resourcemanager

# 停止所有NodeManager
stop_nodemanager namenode
stop_nodemanager datanode1
stop_nodemanager datanode2

echo ""
echo -e "${GREEN}=========================================="
echo "YARN服务已全部停止"
echo "==========================================${NC}"
echo ""

