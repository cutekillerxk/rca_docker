#!/bin/bash
# MapReduce测试脚本
# 用法: ./test_mapreduce.sh [test_name]
# test_name可选: pi, wordcount, terasort

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

TEST_NAME=${1:-pi}

echo -e "${BLUE}=========================================="
echo "MapReduce测试: ${TEST_NAME}"
echo "==========================================${NC}"
echo ""

# 检查YARN服务
check_yarn() {
    echo -e "${YELLOW}检查YARN服务状态...${NC}"
    if ! docker exec namenode sh -c 'su - hadoop -c "jps"' | grep -q ResourceManager; then
        echo -e "${RED}错误: ResourceManager未运行${NC}"
        echo "请先运行: ./scripts/start_yarn.sh"
        exit 1
    fi
    echo -e "${GREEN}✓ YARN服务正常${NC}"
}

# 测试Pi计算
test_pi() {
    local maps=$1
    local samples=$2
    echo -e "${YELLOW}运行Pi计算测试 (maps=${maps}, samples=${samples})...${NC}"
    docker exec namenode sh -c "su - hadoop -c 'yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi ${maps} ${samples}'"
}

# 测试WordCount
test_wordcount() {
    echo -e "${YELLOW}准备测试数据...${NC}"
    # 创建输入目录
    docker exec namenode sh -c 'su - hadoop -c "hdfs dfs -mkdir -p /input"'
    # 创建测试文件
    docker exec namenode sh -c 'su - hadoop -c "echo \"hello world hello hadoop\" | hdfs dfs -put - /input/test1.txt"'
    docker exec namenode sh -c 'su - hadoop -c "echo \"hadoop yarn mapreduce\" | hdfs dfs -put - /input/test2.txt"'
    
    # 删除旧输出（如果存在）
    docker exec namenode sh -c 'su - hadoop -c "hdfs dfs -rm -r -f /output" 2>/dev/null || true'
    
    echo -e "${YELLOW}运行WordCount测试...${NC}"
    docker exec namenode sh -c 'su - hadoop -c "yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar wordcount /input /output"'
    
    echo -e "${GREEN}查看结果:${NC}"
    docker exec namenode sh -c 'su - hadoop -c "hdfs dfs -cat /output/part-r-00000"'
}

# 测试TeraSort（大数据排序）
test_terasort() {
    local size=$1  # MB
    echo -e "${YELLOW}生成TeraGen数据 (${size}MB)...${NC}"
    docker exec namenode sh -c 'su - hadoop -c "hdfs dfs -rm -r -f /teragen-input /teragen-output 2>/dev/null || true"'
    
    # 生成数据 (size MB = size * 1024 * 1024 / 100 bytes per record)
    local records=$((size * 1024 * 1024 / 100))
    docker exec namenode sh -c "su - hadoop -c 'yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar teragen ${records} /teragen-input'"
    
    echo -e "${YELLOW}运行TeraSort...${NC}"
    docker exec namenode sh -c 'su - hadoop -c "yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar terasort /teragen-input /teragen-output"'
    
    echo -e "${GREEN}验证排序结果:${NC}"
    docker exec namenode sh -c 'su - hadoop -c "yarn jar /usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar teravalidate /teragen-output /teragen-validate"'
}

# 主逻辑
check_yarn

case ${TEST_NAME} in
    pi)
        test_pi 2 10
        ;;
    wordcount)
        test_wordcount
        ;;
    terasort)
        test_terasort 10  # 10MB数据
        ;;
    *)
        echo -e "${RED}未知测试: ${TEST_NAME}${NC}"
        echo "支持的测试: pi, wordcount, terasort"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=========================================="
echo "测试完成！"
echo "==========================================${NC}"
echo ""
echo "查看YARN任务: http://localhost:8088"

