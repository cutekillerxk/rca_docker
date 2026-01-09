#!/bin/bash
# 启动YARN服务脚本
# 用法: ./start_yarn.sh

set -e

echo "=========================================="
echo "启动YARN服务"
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查容器是否运行
check_container() {
    local container=$1
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${RED}错误: 容器 ${container} 未运行${NC}"
        exit 1
    fi
}

# 启动ResourceManager
start_resourcemanager() {
    echo -e "${YELLOW}启动ResourceManager (namenode)...${NC}"
    docker exec namenode sh -c 'su - hadoop -c "yarn --daemon start resourcemanager"' || {
        echo -e "${RED}ResourceManager启动失败${NC}"
        return 1
    }
    sleep 2
    if docker exec namenode sh -c 'su - hadoop -c "jps"' | grep -q ResourceManager; then
        echo -e "${GREEN}✓ ResourceManager启动成功${NC}"
    else
        echo -e "${RED}✗ ResourceManager启动失败，请检查日志${NC}"
        return 1
    fi
}

# 启动NodeManager
start_nodemanager() {
    local container=$1
    echo -e "${YELLOW}启动NodeManager (${container})...${NC}"
    docker exec ${container} sh -c 'su - hadoop -c "yarn --daemon start nodemanager"' || {
        echo -e "${RED}NodeManager启动失败 (${container})${NC}"
        return 1
    }
    sleep 2
    if docker exec ${container} sh -c 'su - hadoop -c "jps"' | grep -q NodeManager; then
        echo -e "${GREEN}✓ NodeManager启动成功 (${container})${NC}"
    else
        echo -e "${RED}✗ NodeManager启动失败 (${container})，请检查日志${NC}"
        return 1
    fi
}

# 检查所有容器
echo "检查容器状态..."
check_container namenode
check_container datanode1
check_container datanode2

# 启动ResourceManager
start_resourcemanager

# 启动所有NodeManager
start_nodemanager namenode
start_nodemanager datanode1
start_nodemanager datanode2

echo ""
echo -e "${GREEN}=========================================="
echo "YARN服务启动完成！"
echo "==========================================${NC}"
echo ""
echo "验证服务状态："
echo "  - ResourceManager Web UI: http://localhost:8088"
echo "  - 检查进程: docker exec namenode sh -c 'su - hadoop -c \"jps\"'"
echo "  - 检查节点: docker exec namenode sh -c 'su - hadoop -c \"yarn node -list\"'"
echo ""

