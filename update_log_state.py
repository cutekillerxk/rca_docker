#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新日志读取器状态文件到最新值
读取所有日志文件的最新位置并更新 log_reader_state.json
"""

import sys
import os
import subprocess

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cl_agent.log_reader import (
    read_all_cluster_logs,
    load_log_reader_state,
    save_log_reader_state,
    init_docker_readers,
    docker_readers
)
from cl_agent.config import LOG_FILES_CONFIG, DEFAULT_MAX_LINES


def count_log_lines(container: str, log_file: str, log_path: str) -> int:
    """计算日志文件的行数"""
    try:
        # 构建完整路径
        if not os.path.isabs(log_file):
            full_path = os.path.join(log_path, log_file)
        else:
            full_path = log_file
        
        # 确保路径使用正斜杠
        full_path = full_path.replace('\\', '/')
        escaped_path = full_path.replace("'", "'\"'\"'")
        
        # 使用wc -l计算行数
        result = subprocess.run(
            f'docker exec {container} sh -c "wc -l \'{escaped_path}\' 2>&1"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # wc -l 输出格式: "行数 文件名"
            line_count = result.stdout.strip().split()[0]
            return int(line_count)
        else:
            return 0
    except Exception as e:
        return 0


def update_log_reader_state():
    """更新日志读取器状态到最新值"""
    print("=" * 70)
    print("更新日志读取器状态文件")
    print("=" * 70)
    
    num_log_files = len(LOG_FILES_CONFIG)
    print(f"检测到 {num_log_files} 个日志文件配置")
    
    # 加载当前状态
    last_positions, last_files = load_log_reader_state(num_log_files)
    print(f"\n当前状态:")
    print(f"  - 最后位置: {last_positions}")
    print(f"  - 最后文件: {last_files}")
    
    # 初始化Docker读取器
    print("\n初始化Docker读取器...")
    init_docker_readers()
    
    # 读取所有日志（这会更新位置）
    print("\n读取所有日志文件以获取最新位置...")
    print("（这可能需要一些时间，取决于日志文件大小）")
    
    try:
        # 为了更新到最新位置，需要读取所有内容（不限制行数）
        # 注意：这会读取从上次位置到文件末尾的所有内容，可能很大，需要一些时间
        all_logs, new_positions, new_files = read_all_cluster_logs(
            max_lines=None,  # None表示不限制行数，读取到文件末尾
            last_positions=last_positions,
            last_files=last_files
        )
        
        print(f"\n读取完成！")
        print(f"  - 新位置: {new_positions}")
        print(f"  - 新文件: {new_files}")
        
        # 保存新状态
        print("\n保存新状态到文件...")
        save_log_reader_state(new_positions, new_files)
        
        print("\n" + "=" * 70)
        print("✅ 状态文件已成功更新到最新值！")
        print("=" * 70)
        
        # 显示更新摘要（显示行数变化）
        print("\n更新摘要:")
        for i, log_config in enumerate(LOG_FILES_CONFIG):
            node_name = log_config["display_name"]
            old_pos = last_positions[i] if i < len(last_positions) else 0
            new_pos = new_positions[i] if i < len(new_positions) else 0
            old_file = last_files[i] if i < len(last_files) else None
            new_file = new_files[i] if i < len(new_files) else None
            
            print(f"  [{i+1}] {node_name}:")
            
            # 计算字节数变化
            byte_diff = new_pos - old_pos
            
            # 计算行数变化
            if log_config["type"] == "docker" and new_file:
                container = log_config.get("container")
                log_path = log_config.get("log_path", "/usr/local/hadoop/logs")
                
                # 计算新文件的总行数
                new_total_lines = count_log_lines(container, new_file, log_path)
                
                # 计算新增的行数（从旧位置到新位置）
                added_lines = 0
                if old_file == new_file and new_pos > old_pos:
                    # 同一文件，读取新增部分来计算行数
                    try:
                        container = log_config.get("container")
                        log_path = log_config.get("log_path", "/usr/local/hadoop/logs")
                        
                        # 构建完整路径
                        if not os.path.isabs(new_file):
                            full_path = os.path.join(log_path, new_file)
                        else:
                            full_path = new_file
                        full_path = full_path.replace('\\', '/')
                        escaped_path = full_path.replace("'", "'\"'\"'")
                        
                        # 使用dd命令只读取从old_pos到new_pos的字节数（精确读取新增部分）
                        # dd if=file bs=1 skip=old_pos count=byte_diff
                        result = subprocess.run(
                            f'docker exec {container} sh -c "dd if=\'{escaped_path}\' bs=1 skip={old_pos} count={byte_diff} 2>/dev/null"',
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if result.returncode == 0 and result.stdout:
                            # 计算新增部分的行数
                            added_lines = len(result.stdout.splitlines())
                        else:
                            # 如果dd失败，使用字节数估算（假设平均每行100字节）
                            added_lines = byte_diff // 100 if byte_diff > 0 else 0
                    except Exception as e:
                        # 如果读取失败，使用字节数估算（假设平均每行100字节）
                        added_lines = byte_diff // 100 if byte_diff > 0 else 0
                
                # 显示信息（同时显示字节数和行数）
                if old_file != new_file:
                    print(f"      文件: {old_file} -> {new_file}")
                    print(f"      字节: {old_pos} -> {new_pos} (增加 {byte_diff} 字节)")
                    print(f"      行数: {new_total_lines} 行")
                else:
                    print(f"      文件: {new_file}")
                    print(f"      字节: {old_pos} -> {new_pos} (增加 {byte_diff} 字节)")
                    if added_lines > 0:
                        print(f"      行数: {new_total_lines} 行 (新增 {added_lines} 行)")
                    else:
                        print(f"      行数: {new_total_lines} 行")
            else:
                # 非docker类型，只显示字节数
                print(f"      位置: {old_pos} -> {new_pos} (增加 {byte_diff} 字节)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 更新失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = update_log_reader_state()
    sys.exit(0 if success else 1)
