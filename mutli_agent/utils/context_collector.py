#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局上下文收集器
收集所有节点日志、JMX监控指标、集群状态信息
"""

from typing import Dict, Any
import sys
import os

# 添加路径以导入现有模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cl_agent.log_reader import read_all_cluster_logs, load_log_reader_state, save_log_reader_state
from cl_agent.monitor_collector import collect_all_metrics
from cl_agent.config import LOG_FILES_CONFIG, DEFAULT_MAX_LINES


class ContextCollector:
    """
    全局上下文收集器
    统一收集集群的所有上下文信息
    """
    
    def __init__(self):
        """初始化上下文收集器"""
        pass
    
    def collect_all_context(self) -> Dict[str, Any]:
        """
        收集所有全局上下文
        
        Returns:
            全局上下文字典，包含：
            - logs: 所有节点日志
            - metrics: 监控指标
            - cluster_state: 集群状态
            - timestamp: 收集时间戳
        """
        from datetime import datetime
        
        context = {
            "timestamp": datetime.now().isoformat(),
            "logs": {},
            "metrics": {},
            "cluster_state": {},
        }
        
        # 1. 收集日志
        try:
            num_log_files = len(LOG_FILES_CONFIG)
            last_positions, last_files = load_log_reader_state(num_log_files)
            
            all_logs, new_positions, new_files = read_all_cluster_logs(
                max_lines=DEFAULT_MAX_LINES,
                last_positions=last_positions,
                last_files=last_files
            )
            save_log_reader_state(new_positions, new_files)
            context["logs"] = all_logs
            
            # 保存日志到 result 目录（与 cl_agent/tools/tools.py 保持一致）
            try:
                # 确定result目录路径（相对于当前文件：rca/mutli_agent/utils/context_collector.py -> rca/result）
                current_dir = os.path.dirname(os.path.abspath(__file__))  # rca/mutli_agent/utils
                mutli_agent_dir = os.path.dirname(current_dir)  # rca/mutli_agent
                rca_dir = os.path.dirname(mutli_agent_dir)  # rca
                result_dir = os.path.join(rca_dir, "result")
                
                # 确保目录存在
                os.makedirs(result_dir, exist_ok=True)
                
                # 生成带时间戳的文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"cluster_logs_{timestamp}.txt"
                file_path = os.path.join(result_dir, filename)
                
                # 构建日志内容（与 cl_agent/tools/tools.py 格式保持一致）
                result_lines = []
                result_lines.append("[集群日志分析任务]")
                result_lines.append(f"共发现 {len(all_logs)} 个节点需要分析。")
                result_lines.append("")
                
                for node_name, log_content in all_logs.items():
                    result_lines.append(f"=== {node_name} ===")
                    result_lines.append(log_content)
                    result_lines.append("")
                
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(result_lines))
                
                print(f"[ContextCollector] 集群日志已保存到: {file_path}")
            except Exception as save_error:
                print(f"[WARNING] 保存集群日志到result目录失败: {save_error}")
                # 即使保存失败，也继续执行
                
        except Exception as e:
            print(f"[WARNING] 收集日志失败: {e}")
            context["logs"] = {}
        
        # 2. 收集监控指标
        try:
            metrics = collect_all_metrics()
            context["metrics"] = metrics
        except Exception as e:
            print(f"[WARNING] 收集监控指标失败: {e}")
            context["metrics"] = {}
        
        # 3. 收集集群状态（从监控指标中提取关键状态）
        try:
            cluster_state = self._extract_cluster_state(context["metrics"])
            context["cluster_state"] = cluster_state
        except Exception as e:
            print(f"[WARNING] 提取集群状态失败: {e}")
            context["cluster_state"] = {}
        
        return context
    
    def _extract_cluster_state(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        从监控指标中提取集群状态
        
        Args:
            metrics: 监控指标字典
        
        Returns:
            集群状态字典
        """
        state = {
            "datanode_count": {
                "live": 0,
                "dead": 0,
                "total": 0,
            },
            "hdfs_status": "unknown",
            "storage": {
                "total": 0,
                "used": 0,
                "remaining": 0,
            },
        }
        
        # 从NameNode指标中提取状态
        if "namenode" in metrics and metrics["namenode"].get("status") != "error":
            nn_metrics = metrics["namenode"].get("metrics", {})
            
            # DataNode数量
            # 注意：实际字段名是 "live_datanodes" 和 "dead_datanodes"，不是 "NumLiveDataNodes"
            # 而且 value 字段可能是字符串格式（如 "3 (心跳) / 3 (JMX实时)"），应该使用 heartbeat_value 或 jmx_value
            if "live_datanodes" in nn_metrics:
                live_metric = nn_metrics["live_datanodes"]
                # 优先使用 heartbeat_value（来自NameNode心跳统计）
                if "heartbeat_value" in live_metric:
                    state["datanode_count"]["live"] = live_metric["heartbeat_value"]
                elif "jmx_value" in live_metric:
                    state["datanode_count"]["live"] = live_metric["jmx_value"]
                elif isinstance(live_metric.get("value"), (int, float)):
                    state["datanode_count"]["live"] = live_metric["value"]
                else:
                    # 如果value是字符串，尝试提取数字
                    value_str = str(live_metric.get("value", "0"))
                    import re
                    match = re.search(r'(\d+)', value_str)
                    if match:
                        state["datanode_count"]["live"] = int(match.group(1))
            
            if "dead_datanodes" in nn_metrics:
                dead_metric = nn_metrics["dead_datanodes"]
                # 优先使用 heartbeat_value
                if "heartbeat_value" in dead_metric:
                    state["datanode_count"]["dead"] = dead_metric["heartbeat_value"]
                elif "jmx_value" in dead_metric:
                    state["datanode_count"]["dead"] = dead_metric["jmx_value"]
                elif isinstance(dead_metric.get("value"), (int, float)):
                    state["datanode_count"]["dead"] = dead_metric["value"]
                else:
                    # 如果value是字符串，尝试提取数字
                    value_str = str(dead_metric.get("value", "0"))
                    import re
                    match = re.search(r'(\d+)', value_str)
                    if match:
                        state["datanode_count"]["dead"] = int(match.group(1))
            
            state["datanode_count"]["total"] = (
                state["datanode_count"]["live"] + state["datanode_count"]["dead"]
            )
            
            # HDFS状态
            if state["datanode_count"]["dead"] > 0:
                state["hdfs_status"] = "degraded"
            elif state["datanode_count"]["live"] > 0 and state["datanode_count"]["live"] == state["datanode_count"]["total"]:
                state["hdfs_status"] = "healthy"
            elif state["datanode_count"]["total"] == 0:
                state["hdfs_status"] = "unknown"
            
            # 存储信息
            # 注意：CapacityTotal、CapacityUsed、CapacityRemaining 并没有直接存储在 metrics 中
            # 实际存储的是 remaining_storage（包含 raw_value，单位是GB）
            # 如果需要总容量和已使用容量，需要从 remaining_storage 的 raw_value 反推，或者从其他指标获取
            if "remaining_storage" in nn_metrics:
                remaining_metric = nn_metrics["remaining_storage"]
                if "raw_value" in remaining_metric and remaining_metric["raw_value"] is not None:
                    # raw_value 单位是 GB，转换为字节
                    state["storage"]["remaining"] = remaining_metric["raw_value"] * (1024 ** 3)
            
            # 尝试从 storage_usage 获取存储使用率，然后反推总容量
            if "storage_usage" in nn_metrics:
                storage_usage_metric = nn_metrics["storage_usage"]
                if "raw_value" in storage_usage_metric:
                    usage_percent = storage_usage_metric["raw_value"]  # 百分比（0-100）
                    # 如果有剩余容量，可以反推总容量
                    if state["storage"]["remaining"] > 0 and usage_percent > 0:
                        # remaining = total * (1 - usage_percent / 100)
                        # total = remaining / (1 - usage_percent / 100)
                        if usage_percent < 100:
                            state["storage"]["total"] = state["storage"]["remaining"] / (1 - usage_percent / 100)
                            state["storage"]["used"] = state["storage"]["total"] - state["storage"]["remaining"]
        
        return state
