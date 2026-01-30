#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控数据采集模块
从 JMX API 获取关键监控参数
（独立模块，不依赖其他文件）
"""

import requests
import os
import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# ==================== JMX API 配置 ====================
# Docker环境：通过 docker exec 在容器内访问 JMX（因为 JMX 只监听容器内部网络）
# 容器名称和端口映射
# 注意：URL 使用 127.0.0.1 而不是 localhost，因为 Windows 环境下 localhost 可能解析为 IPv6 (::1)
# 而 Docker 端口映射通常只监听 IPv4，导致连接失败
JMX_CONFIG = {
    "namenode": {
        "container": "namenode",
        "port": 9870,
        "url": "http://127.0.0.1:9870/jmx"  # 使用 127.0.0.1 避免 IPv6 解析问题
    },
    "datanode1": {
        "container": "datanode1",
        "port": 9864,
        "url": "http://127.0.0.1:9864/jmx"  # 使用 127.0.0.1 避免 IPv6 解析问题
    },
    "datanode2": {
        "container": "datanode2",
        "port": 9864,  # 容器内端口是 9864（主机端口映射是 9865:9864）
        "url": "http://127.0.0.1:9865/jmx"  # 主机访问使用 9865，但容器内访问使用 9864，使用 127.0.0.1 避免 IPv6 解析问题
    },
    "datanode-namenode": {
        "container": "namenode",
        "port": 9864,  # 容器内端口是 9864（主机端口映射是 9866:9864）
        "url": "http://127.0.0.1:9866/jmx"  # 主机访问使用 9866，容器内端口是 9864，使用 127.0.0.1 避免 IPv6 解析问题
    },
    "resourcemanager": {
        "container": "namenode",
        "port": 8088,  # ResourceManager在namenode容器，容器内端口8088
        "url": "http://127.0.0.1:8088/jmx"  # 主机端口也是8088
    },
    "nodemanager-namenode": {
        "container": "namenode",
        "port": 8042,  # NodeManager在namenode容器，容器内端口8042
        "url": "http://127.0.0.1:8042/jmx"  # 主机端口也是8042
    },
    "nodemanager-datanode1": {
        "container": "datanode1",
        "port": 8042,  # NodeManager在datanode1容器，容器内端口8042
        "url": "http://127.0.0.1:8043/jmx"  # 主机端口映射是8043:8042
    },
    "nodemanager-datanode2": {
        "container": "datanode2",
        "port": 8042,  # NodeManager在datanode2容器，容器内端口8042
        "url": "http://127.0.0.1:8044/jmx"  # 主机端口映射是8044:8042
    }
}

# 兼容旧配置（用于 URL 到容器的映射）
# 使用 127.0.0.1 而不是 localhost，避免 Windows 环境下 IPv6 解析问题
NAMENODE = "http://127.0.0.1:9870/jmx"
DATANODES = [
    "http://127.0.0.1:9864/jmx",  # datanode1
    "http://127.0.0.1:9865/jmx",  # datanode2
    "http://127.0.0.1:9866/jmx",  # datanode-namenode (namenode容器中的DataNode)
]

# YARN ResourceManager JMX URL
RESOURCEMANAGER = "http://127.0.0.1:8088/jmx"

# YARN NodeManager JMX URLs（按节点顺序）
NODEMANAGERS = [
    "http://127.0.0.1:8042/jmx",  # nodemanager-namenode (namenode容器中的NodeManager)
    "http://127.0.0.1:8043/jmx",  # nodemanager-datanode1
    "http://127.0.0.1:8044/jmx",  # nodemanager-datanode2
]


def fetch_jmx_via_docker(container: str, port: int) -> tuple[Optional[Dict], Optional[str]]:
    """
    通过 docker exec 在容器内访问 JMX API
    
    Args:
        container: 容器名称
        port: JMX 端口
    
    Returns:
        (数据字典, 错误信息)，如果成功返回 (data, None)，失败返回 (None, error_msg)
    """
    url = f"http://localhost:{port}/jmx"
    
    try:
        # 通过 docker exec 在容器内执行 curl 命令访问 JMX
        cmd = f'docker exec {container} sh -c "curl -s -m 30 {url} 2>&1"'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=35
        )
        
        if result.returncode != 0:
            # curl 返回码说明：7=无法连接, 28=超时, 其他=其他错误
            curl_error_codes = {
                7: "无法连接到服务器（可能端口错误或服务未启动）",
                28: "连接超时",
                6: "无法解析主机名",
                22: "HTTP 错误响应"
            }
            error_hint = curl_error_codes.get(result.returncode, f"curl 错误码 {result.returncode}")
            
            error_output = result.stderr if result.stderr else result.stdout
            error_msg = (
                f"Docker exec 执行失败 (容器: {container}, 端口: {port})\n"
                f"返回码: {result.returncode} ({error_hint})\n"
                f"命令: docker exec {container} sh -c \"curl -s -m 30 {url}\"\n"
                f"错误输出: {error_output[:500] if error_output else '(无输出)'}\n"
                f"建议：检查容器内端口 {port} 是否监听，服务是否运行"
            )
            return None, error_msg
        
        # 检查响应内容
        if not result.stdout or not result.stdout.strip():
            error_msg = f"JMX 响应为空 (容器: {container}, 端口: {port})"
            return None, error_msg
        
        # 尝试解析 JSON
        try:
            data = json.loads(result.stdout)
            return data, None
        except json.JSONDecodeError as e:
            # JSON 解析失败，返回原始内容的前500字符用于调试
            content_preview = result.stdout[:500] if result.stdout else "(空响应)"
            error_msg = (
                f"JSON解析失败 (容器: {container}, 端口: {port})\n"
                f"错误详情: {str(e)}\n"
                f"响应预览: {content_preview}"
            )
            return None, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = (
            f"访问 JMX 超时 (容器: {container}, 端口: {port})\n"
            f"可能原因：服务响应过慢或容器无响应"
        )
        return None, error_msg
    except Exception as e:
        error_msg = (
            f"访问 JMX 失败 (容器: {container}, 端口: {port})\n"
            f"错误详情: {str(e)}"
        )
        import traceback
        logging.error(f"JMX请求异常: {traceback.format_exc()}")
        return None, error_msg


def get_container_by_url(url: str) -> Optional[tuple[str, int]]:
    """
    根据 URL 获取容器名称和容器内端口
    
    Args:
        url: JMX API URL（支持 127.0.0.1，也兼容 localhost）
        注意：URL 中的端口是主机端口，需要映射到容器内端口
    
    Returns:
        (容器名称, 容器内端口) 元组，如果找不到返回 None
    """
    import re
    # 提取 URL 中的端口号（主机端口）
    port_match = re.search(r':(\d+)/jmx', url)
    if not port_match:
        return None
    
    host_port = int(port_match.group(1))
    
    # 主机端口到容器的映射（主机端口 -> 容器名）
    # 注意：datanode2 的主机端口是 9865，但容器内端口是 9864
    # datanode-namenode 的主机端口是 9866，但容器内端口是 9864
    host_port_to_container = {
        9870: "namenode",          # 主机 9870 -> namenode 容器内 9870
        9864: "datanode1",         # 主机 9864 -> datanode1 容器内 9864
        9865: "datanode2",         # 主机 9865 -> datanode2 容器内 9864
        9866: "datanode-namenode", # 主机 9866 -> namenode 容器内 9864 (namenode容器中的DataNode)
        8088: "resourcemanager",  # 主机 8088 -> namenode 容器内 8088 (ResourceManager)
        8042: "nodemanager-namenode",  # 主机 8042 -> namenode 容器内 8042 (NodeManager)
        8043: "nodemanager-datanode1", # 主机 8043 -> datanode1 容器内 8042 (NodeManager)
        8044: "nodemanager-datanode2", # 主机 8044 -> datanode2 容器内 8042 (NodeManager)
    }
    
    container_name = host_port_to_container.get(host_port)
    if container_name:
        # 获取容器内端口
        config = JMX_CONFIG.get(container_name)
        if config:
            return config["container"], config["port"]
    
    return None


def fetch_jmx(url: str) -> tuple[Optional[Dict], Optional[str]]:
    """
    获取JMX监控数据（通过 docker exec 在容器内访问）
    
    注意：由于 JMX 服务只监听容器内部网络，无法从主机直接访问，
    因此使用 docker exec 在容器内访问 JMX API。
    
    Args:
        url: JMX API URL（用于识别容器和端口）
    
    Returns:
        (数据字典, 错误信息)，如果成功返回 (data, None)，失败返回 (None, error_msg)
    """
    # 根据 URL 获取容器名称和端口
    container_info = get_container_by_url(url)
    
    if container_info:
        container, port = container_info
        # 使用 docker exec 方式访问
        return fetch_jmx_via_docker(container, port)
    
    # 如果无法识别容器，尝试直接 HTTP 访问（向后兼容）

    logging.warning(f"无法识别容器，尝试直接 HTTP 访问: {url}")
    
    
    # 如果使用 localhost，尝试替换为 127.0.0.1（某些环境下 localhost 解析可能有问题）
    # 注意：Windows 环境下，localhost 可能被代理拦截，优先使用 127.0.0.1
    alternative_url = None
    if 'localhost' in url:
        alternative_url = url.replace('localhost', '127.0.0.1')
        # 在 Windows 下，优先使用 127.0.0.1
        if os.name == 'nt':  # Windows
            url, alternative_url = alternative_url, url  # 交换，优先使用 127.0.0.1
    
    # 创建 Session 以复用连接
    session = requests.Session()
    
    # 配置连接池
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=1,
        pool_maxsize=1,
        max_retries=0  # 不重试
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # 添加请求头，模拟浏览器请求
    # 注意：使用 Connection: close 避免连接复用问题
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'identity',  # 不使用压缩，避免解压问题
        'Connection': 'close',  # 关闭连接复用，避免连接被提前关闭
        'Cache-Control': 'no-cache'
    }
    
    try:
        # 使用 session 发送请求
        # 禁用代理：Windows 系统可能自动配置代理，导致 localhost 请求失败
        # 增加超时时间，避免连接被过早关闭
        r = session.get(
            url, 
            headers=headers, 
            timeout=(10, 30),  # (连接超时10秒, 读取超时30秒) - 增加超时时间
            allow_redirects=True,
            stream=False,  # 不使用流式传输
            proxies={'http': None, 'https': None},  # 禁用代理，避免 localhost 请求被代理拦截
            verify=False  # 如果是HTTPS，不验证证书
        )
        
        logging.debug(f"JMX请求 {url} 返回状态码: {r.status_code}")
        
        # 检查状态码
        if r.status_code == 502:
            error_msg = (
                f"HTTP 502 Bad Gateway: {url}\n"
                f"可能原因：\n"
                f"1. NameNode/DataNode 服务正在启动中，JMX 服务尚未就绪\n"
                f"2. 服务负载过高，暂时无法响应\n"
                f"3. 网络连接问题\n"
                f"建议：检查容器日志确认服务状态"
            )
            return None, error_msg
        
        if r.status_code != 200:
            error_msg = f"HTTP错误: {url} 返回状态码 {r.status_code}"
            return None, error_msg
        
        # 状态码为 200，尝试解析JSON
        try:
            # 检查响应内容类型
            content_type = r.headers.get('Content-Type', '')
            if 'json' not in content_type.lower() and 'text' not in content_type.lower():
                logging.warning(f"JMX响应 Content-Type: {content_type}")
            
            data = r.json()
            session.close()
            return data, None
        except ValueError as e:
            # JSON解析失败，返回原始内容的前500字符用于调试
            content_preview = r.text[:500] if r.text else "(空响应)"
            error_msg = (
                f"JSON解析失败: {url} 返回的不是有效的JSON格式\n"
                f"错误详情: {str(e)}\n"
                f"响应预览: {content_preview}"
            )
            return None, error_msg
            
    except requests.exceptions.ConnectionError as e:
        # 如果是连接错误且还有备用URL，尝试使用备用URL（只尝试一次）
        if alternative_url:
            logging.info(f"尝试使用备用URL: {alternative_url}")
            try:
                r = session.get(
                    alternative_url,
                    headers=headers,
                    timeout=(5, 15),
                    allow_redirects=True,
                    stream=False,
                    proxies={'http': None, 'https': None}  # 禁用代理
                )
                if r.status_code == 200:
                    try:
                        data = r.json()
                        logging.info(f"使用备用URL成功: {alternative_url}")
                        session.close()
                        return data, None
                    except ValueError:
                        pass
            except Exception:
                pass
        
        # 提取端口号用于诊断
        import re
        port_match = re.search(r':(\d+)', url)
        port = port_match.group(1) if port_match else "未知"
        
        error_msg = (
            f"连接失败: 无法连接到 {url}\n"
            f"可能原因：\n"
            f"1. 服务未启动或已停止（检查容器内进程：docker exec <container> jps）\n"
            f"2. 端口映射配置错误（检查：docker ps 查看端口映射）\n"
            f"3. 防火墙阻止连接（端口 {port} 可能被阻止）\n"
            f"4. 服务正在启动中（JMX服务可能尚未就绪）\n"
            f"5. Windows代理设置问题（localhost可能被代理拦截）\n"
            f"\n诊断建议：\n"
            f"- 检查容器状态：docker ps\n"
            f"- 检查容器内进程：docker exec <container> jps\n"
            f"- 检查端口监听：docker exec <container> netstat -tlnp | grep {port}\n"
            f"- 检查容器日志：docker logs <container>\n"
            f"\n错误详情: {str(e)}"
        )
        session.close()
        return None, error_msg
        
    except requests.exceptions.Timeout as e:
        error_msg = (
            f"连接超时: {url} 响应超时（超过15秒）\n"
            f"可能原因：服务负载过高或网络延迟\n"
            f"错误详情: {str(e)}"
        )
        session.close()
        return None, error_msg
        
    except requests.exceptions.HTTPError as e:
        # 获取状态码
        status_code = "unknown"
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
        
        # 对于 502 错误，提供更详细的说明
        if status_code == 502:
            error_msg = (
                f"HTTP 502 Bad Gateway: {url}\n"
                f"可能原因：\n"
                f"1. NameNode/DataNode 服务正在启动中，JMX 服务尚未就绪\n"
                f"2. 服务负载过高，暂时无法响应\n"
                f"3. 网络连接问题\n"
                f"建议：检查容器日志确认服务状态"
            )
        else:
            error_msg = f"HTTP错误: {url} 返回 {status_code}，服务可能异常 - {str(e)}"
        session.close()
        return None, error_msg
        
    except Exception as e:
        error_msg = f"未知错误: {url} - {str(e)}"
        import traceback
        logging.error(f"JMX请求异常: {traceback.format_exc()}")
        session.close()
        return None, error_msg
        
    finally:
        # 确保响应被关闭
        try:
            if 'r' in locals() and hasattr(r, 'close'):
                r.close()
        except:
            pass


def extract_jmx_value(beans: List[Dict], bean_name: str, field_name: str, default=None):
    """
    从 JMX beans 中提取指定字段的值
    
    Args:
        beans: JMX beans 列表
        bean_name: Bean 名称，如 "Hadoop:service=NameNode,name=NameNodeStatus"
        field_name: 字段名称，如 "State"
        default: 默认值
    
    Returns:
        字段值，如果找不到返回 default
    """
    for bean in beans:
        if bean.get("name") == bean_name:
            return bean.get(field_name, default)
    return default


def get_namenode_metrics() -> Dict[str, Any]:
    """
    获取 NameNode 的关键指标
    
    Returns:
        包含 NameNode 指标的字典
    """
    metrics_data, error = fetch_jmx(NAMENODE)
    
    if error or not metrics_data:
        return {
            "status": "error",
            "error": error or "无法获取数据",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    beans = metrics_data.get("beans", [])
    
    # 提取关键指标
    result = {
        "status": "normal",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {}
    }
    
    # 1. NameNode 状态
    nn_status_bean = "Hadoop:service=NameNode,name=NameNodeStatus"
    state = extract_jmx_value(beans, nn_status_bean, "State", "unknown")
    result["metrics"]["namenode_status"] = {
        "name": "NameNode 状态",
        "value": state,
        "status": "normal" if state in ["active", "standby"] else "abnormal"
    }
    
    # 2. 安全模式状态
    fs_bean = "Hadoop:service=NameNode,name=FSNamesystemState"
    safemode = extract_jmx_value(beans, fs_bean, "Safemode", False)
    result["metrics"]["safemode"] = {
        "name": "安全模式状态",
        "value": "开启" if safemode else "关闭",
        "status": "normal" if not safemode else "abnormal"
    }
    
    # 3. 损坏的数据块数
    corrupt_blocks = extract_jmx_value(beans, fs_bean, "CorruptBlocks", 0)
    result["metrics"]["corrupt_blocks"] = {
        "name": "损坏的数据块数",
        "value": corrupt_blocks,
        "status": "normal" if corrupt_blocks == 0 else "abnormal"
    }
    
    # 4. 缺失的数据块数
    missing_blocks = extract_jmx_value(beans, fs_bean, "MissingBlocks", 0)
    result["metrics"]["missing_blocks"] = {
        "name": "缺失的数据块数",
        "value": missing_blocks,
        "status": "normal" if missing_blocks == 0 else "abnormal"
    }
    
    # 5. 存储使用率
    percent_used = extract_jmx_value(beans, fs_bean, "PercentUsed", 0.0)
    result["metrics"]["storage_usage"] = {
        "name": "NameNode 存储使用率",
        "value": f"{percent_used:.2f}%",
        "raw_value": percent_used,
        "status": "normal" if percent_used < 90 else "abnormal"
    }
    
    # 6. 活跃 DataNode 数量（心跳统计）
    live_datanodes = extract_jmx_value(beans, fs_bean, "NumLiveDataNodes", 0)
    result["metrics"]["live_datanodes"] = {
        "name": "活跃 DataNode 数量",
        "value": live_datanodes,
        "status": "normal" if live_datanodes >= 3 else "abnormal",  # 当前集群有 3 个 DataNode（namenode容器1个 + datanode1 + datanode2）
        "heartbeat_value": live_datanodes
    }
    
    # 7. 死掉的 DataNode 数量（心跳统计）
    dead_datanodes = extract_jmx_value(beans, fs_bean, "NumDeadDataNodes", 0)
    result["metrics"]["dead_datanodes"] = {
        "name": "死掉的 DataNode 数量",
        "value": dead_datanodes,
        "status": "normal" if dead_datanodes == 0 else "abnormal",
        "heartbeat_value": dead_datanodes
    }
    
    # 8. 复制不足的数据块数
    under_replicated_blocks = extract_jmx_value(beans, fs_bean, "UnderReplicatedBlocks", 0)
    result["metrics"]["under_replicated_blocks"] = {
        "name": "复制不足的数据块数",
        "value": under_replicated_blocks,
        "status": "normal" if under_replicated_blocks == 0 else "abnormal"
    }
    
    # 9. 总数据块数
    total_blocks = extract_jmx_value(beans, fs_bean, "TotalBlocks", 0)
    result["metrics"]["total_blocks"] = {
        "name": "总数据块数",
        "value": total_blocks,
        "status": "normal"
    }
    
    # 10. 剩余存储空间
    remaining_gb = extract_jmx_value(beans, fs_bean, "RemainingGB", None)
    if remaining_gb is None:
        capacity_total = extract_jmx_value(beans, fs_bean, "CapacityTotal", 0)
        capacity_used = extract_jmx_value(beans, fs_bean, "CapacityUsed", 0)
        if capacity_total > 0:
            remaining = capacity_total - capacity_used
            remaining_gb = remaining / (1024 ** 3)
        else:
            remaining_gb = 0
    
    result["metrics"]["remaining_storage"] = {
        "name": "剩余存储空间",
        "value": f"{remaining_gb:.2f} GB" if remaining_gb else "未知",
        "raw_value": remaining_gb,
        "status": "normal" if (remaining_gb is None or remaining_gb > 0) else "abnormal"
    }
    
    # 11. 堆内存使用率
    memory_bean = "java.lang:type=Memory"
    memory_info = next((bean for bean in beans if bean.get("name") == memory_bean), None)
    
    if memory_info:
        heap_memory_usage = memory_info.get("HeapMemoryUsage", {})
        if isinstance(heap_memory_usage, dict):
            used = heap_memory_usage.get("used", 0)
            max_mem = heap_memory_usage.get("max", 1)
            if max_mem > 0:
                heap_usage_percent = (used / max_mem) * 100
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": f"{heap_usage_percent:.2f}%",
                    "raw_value": heap_usage_percent,
                    "status": "normal" if heap_usage_percent < 85 else "abnormal"
                }
            else:
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": "未知",
                    "status": "normal"
                }
        else:
            result["metrics"]["heap_memory_usage"] = {
                "name": "堆内存使用率",
                "value": "无法获取",
                "status": "normal"
            }
    else:
        result["metrics"]["heap_memory_usage"] = {
            "name": "堆内存使用率",
            "value": "无法获取",
            "status": "normal"
        }
    
    # 12. 文件数量
    files_total = extract_jmx_value(beans, fs_bean, "FilesTotal", 0)
    result["metrics"]["files_total"] = {
        "name": "文件数量",
        "value": files_total,
        "status": "normal"
    }
    
    return result


def get_datanode_metrics(datanode_url: str, node_name: str) -> Dict[str, Any]:
    """
    获取指定 DataNode 的关键指标
    
    Args:
        datanode_url: DataNode JMX URL
        node_name: 节点名称，如 "datanode1", "datanode2"
    
    Returns:
        包含 DataNode 指标的字典
    """
    metrics_data, error = fetch_jmx(datanode_url)
    
    if error or not metrics_data:
        return {
            "status": "error",
            "error": error or "无法获取数据",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "node": node_name
        }
    
    beans = metrics_data.get("beans", [])
    
    result = {
        "status": "normal",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node": node_name,
        "metrics": {}
    }
    
    # 1. DataNode 状态
    dn_info_bean = "Hadoop:service=DataNode,name=DataNodeInfo"
    dn_info = next((bean for bean in beans if bean.get("name") == dn_info_bean), None)
    
    if dn_info:
        version = dn_info.get("Version")
        rpc_port = dn_info.get("RpcPort")
        
        if (version and str(version).strip()) or (rpc_port is not None and rpc_port != 0):
            state = "running"
        else:
            state = "unknown"
    else:
        state = "stopped"
    
    result["metrics"]["datanode_status"] = {
        "name": "状态",
        "value": state,
        "status": "normal" if state == "running" else "abnormal"
    }
    
    # 2. 存储使用率
    fs_bean = "Hadoop:service=DataNode,name=FSDatasetState"
    percent_used = extract_jmx_value(beans, fs_bean, "PercentUsed", 0.0)
    result["metrics"]["storage_usage"] = {
        "name": "存储使用率",
        "value": f"{percent_used:.2f}%",
        "raw_value": percent_used,
        "status": "normal" if percent_used < 90 else "abnormal"
    }
    
    # 3. 复制不足的数据块数
    under_replicated_blocks = extract_jmx_value(beans, fs_bean, "UnderReplicatedBlocks", 0)
    result["metrics"]["under_replicated_blocks"] = {
        "name": "复制不足的数据块数",
        "value": under_replicated_blocks,
        "status": "normal" if under_replicated_blocks == 0 else "abnormal"
    }
    
    # 4. 本地数据块数
    num_blocks = extract_jmx_value(beans, fs_bean, "NumBlocks", 0)
    result["metrics"]["num_blocks"] = {
        "name": "本地数据块数",
        "value": num_blocks,
        "status": "normal"
    }
    
    # 5. 剩余存储空间
    remaining_gb = extract_jmx_value(beans, fs_bean, "RemainingGB", None)
    if remaining_gb is None:
        capacity = extract_jmx_value(beans, fs_bean, "Capacity", 0)
        dfs_used = extract_jmx_value(beans, fs_bean, "DfsUsed", 0)
        if capacity > 0:
            remaining = capacity - dfs_used
            remaining_gb = remaining / (1024 ** 3)
        else:
            remaining_gb = 0
    
    result["metrics"]["remaining_storage"] = {
        "name": "剩余存储空间",
        "value": f"{remaining_gb:.2f} GB" if remaining_gb else "未知",
        "raw_value": remaining_gb,
        "status": "normal" if (remaining_gb is None or remaining_gb > 0) else "abnormal"
    }
    
    # 6. 堆内存使用率
    memory_bean = "java.lang:type=Memory"
    memory_info = next((bean for bean in beans if bean.get("name") == memory_bean), None)
    
    if memory_info:
        heap_memory_usage = memory_info.get("HeapMemoryUsage", {})
        if isinstance(heap_memory_usage, dict):
            used = heap_memory_usage.get("used", 0)
            max_mem = heap_memory_usage.get("max", 1)
            if max_mem > 0:
                heap_usage_percent = (used / max_mem) * 100
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": f"{heap_usage_percent:.2f}%",
                    "raw_value": heap_usage_percent,
                    "status": "normal" if heap_usage_percent < 85 else "abnormal"
                }
            else:
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": "未知",
                    "status": "normal"
                }
        else:
            result["metrics"]["heap_memory_usage"] = {
                "name": "堆内存使用率",
                "value": "无法获取",
                "status": "normal"
            }
    else:
        result["metrics"]["heap_memory_usage"] = {
            "name": "堆内存使用率",
            "value": "无法获取",
            "status": "normal"
        }
    
    # 7. 已用存储容量（MB）
    dfs_used = extract_jmx_value(beans, fs_bean, "DfsUsed", 0)
    dfs_used_mb = dfs_used / (1024 ** 2)
    result["metrics"]["dfs_used_mb"] = {
        "name": "已用存储容量",
        "value": f"{dfs_used_mb:.2f} MB",
        "raw_value": dfs_used_mb,
        "status": "normal"
    }
    
    return result


def get_resourcemanager_metrics() -> Dict[str, Any]:
    """
    获取 ResourceManager 的关键指标
    
    Returns:
        包含 ResourceManager 指标的字典
    """
    metrics_data, error = fetch_jmx(RESOURCEMANAGER)
    
    if error or not metrics_data:
        return {
            "status": "error",
            "error": error or "无法获取数据",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    beans = metrics_data.get("beans", [])
    
    result = {
        "status": "normal",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {}
    }
    
    # 1. ResourceManager 状态（通过检查Bean是否存在和ClusterMetrics来判断）
    rm_bean = "Hadoop:service=ResourceManager,name=ResourceManager"
    rm_exists = any(bean.get("name") == rm_bean for bean in beans)
    cluster_bean = "Hadoop:service=ResourceManager,name=ClusterMetrics"
    num_active_nms = extract_jmx_value(beans, cluster_bean, "NumActiveNMs", 0)
    
    if rm_exists and num_active_nms > 0:
        state = "active"
    elif rm_exists:
        state = "running"
    else:
        state = "stopped"
    
    result["metrics"]["resourcemanager_status"] = {
        "name": "ResourceManager 状态",
        "value": state,
        "status": "normal" if state in ["active", "running"] else "abnormal"
    }
    
    # 2. 集群指标（从ClusterMetrics Bean获取）
    cluster_bean = "Hadoop:service=ResourceManager,name=ClusterMetrics"
    
    # 活跃NodeManager数量
    num_active_nms = extract_jmx_value(beans, cluster_bean, "NumActiveNMs", 0)
    result["metrics"]["active_nodemanagers"] = {
        "name": "活跃 NodeManager 数量",
        "value": num_active_nms,
        "status": "normal" if num_active_nms >= 3 else "abnormal"  # 期望3个
    }
    
    # 丢失的NodeManager数量
    num_lost_nms = extract_jmx_value(beans, cluster_bean, "NumLostNMs", 0)
    result["metrics"]["lost_nodemanagers"] = {
        "name": "丢失的 NodeManager 数量",
        "value": num_lost_nms,
        "status": "normal" if num_lost_nms == 0 else "abnormal"
    }
    
    # 不健康的NodeManager数量
    num_unhealthy_nms = extract_jmx_value(beans, cluster_bean, "NumUnhealthyNMs", 0)
    result["metrics"]["unhealthy_nodemanagers"] = {
        "name": "不健康的 NodeManager 数量",
        "value": num_unhealthy_nms,
        "status": "normal" if num_unhealthy_nms == 0 else "abnormal"
    }
    
    # 集群总内存（使用CapabilityMB）
    capability_mb = extract_jmx_value(beans, cluster_bean, "CapabilityMB", 0)
    result["metrics"]["total_memory_mb"] = {
        "name": "集群总内存",
        "value": f"{capability_mb} MB ({capability_mb/1024:.2f} GB)" if capability_mb > 0 else "0 MB",
        "raw_value": capability_mb,
        "status": "normal"
    }
    
    # 已使用内存（使用UtilizedMB）
    utilized_mb = extract_jmx_value(beans, cluster_bean, "UtilizedMB", 0)
    result["metrics"]["utilized_memory_mb"] = {
        "name": "已使用内存",
        "value": f"{utilized_mb} MB ({utilized_mb/1024:.2f} GB)" if utilized_mb > 0 else "0 MB",
        "raw_value": utilized_mb,
        "status": "normal"
    }
    
    # 可用内存（计算：总容量 - 已使用）
    if capability_mb > 0:
        available_mb = capability_mb - utilized_mb
        result["metrics"]["available_memory_mb"] = {
            "name": "可用内存",
            "value": f"{available_mb} MB ({available_mb/1024:.2f} GB)" if available_mb > 0 else "0 MB",
            "raw_value": available_mb,
            "status": "normal"
        }
        
        # 内存使用率（计算得出）
        memory_usage_percent = (utilized_mb / capability_mb) * 100
        result["metrics"]["memory_usage_percent"] = {
            "name": "内存使用率",
            "value": f"{memory_usage_percent:.2f}%",
            "raw_value": memory_usage_percent,
            "status": "normal" if memory_usage_percent < 85 else "abnormal"  # 阈值85%
        }
    
    # 集群总CPU核心数（使用CapabilityVirtualCores）
    capability_vcores = extract_jmx_value(beans, cluster_bean, "CapabilityVirtualCores", 0)
    result["metrics"]["total_vcores"] = {
        "name": "集群总CPU核心数",
        "value": capability_vcores,
        "status": "normal"
    }
    
    # 已使用CPU核心数（使用UtilizedVirtualCores）
    utilized_vcores = extract_jmx_value(beans, cluster_bean, "UtilizedVirtualCores", 0)
    result["metrics"]["utilized_vcores"] = {
        "name": "已使用CPU核心数",
        "value": utilized_vcores,
        "status": "normal"
    }
    
    # CPU使用率（计算得出）
    if capability_vcores > 0:
        cpu_usage_percent = (utilized_vcores / capability_vcores) * 100
        result["metrics"]["cpu_usage_percent"] = {
            "name": "CPU使用率",
            "value": f"{cpu_usage_percent:.2f}%",
            "raw_value": cpu_usage_percent,
            "status": "normal" if cpu_usage_percent < 85 else "abnormal"  # 阈值85%
        }
    
    # 3. 应用统计（从QueueMetrics Bean获取，通常使用root队列）
    queue_bean = "Hadoop:service=ResourceManager,name=QueueMetrics,q0=root"
    
    # 运行中的应用数量
    apps_running = extract_jmx_value(beans, queue_bean, "AppsRunning", 0)
    result["metrics"]["apps_running"] = {
        "name": "运行中的应用数量",
        "value": apps_running,
        "status": "normal"
    }
    
    # 已提交应用数量
    apps_submitted = extract_jmx_value(beans, queue_bean, "AppsSubmitted", 0)
    result["metrics"]["apps_submitted"] = {
        "name": "已提交应用数量",
        "value": apps_submitted,
        "status": "normal"
    }
    
    # 已完成应用数量
    apps_completed = extract_jmx_value(beans, queue_bean, "AppsCompleted", 0)
    result["metrics"]["apps_completed"] = {
        "name": "已完成应用数量",
        "value": apps_completed,
        "status": "normal"
    }
    
    # 失败应用数量
    apps_failed = extract_jmx_value(beans, queue_bean, "AppsFailed", 0)
    result["metrics"]["apps_failed"] = {
        "name": "失败应用数量",
        "value": apps_failed,
        "status": "normal" if apps_failed == 0 else "abnormal"
    }
    
    # 被终止应用数量
    apps_killed = extract_jmx_value(beans, queue_bean, "AppsKilled", 0)
    result["metrics"]["apps_killed"] = {
        "name": "被终止应用数量",
        "value": apps_killed,
        "status": "normal"
    }
    
    # 4. 堆内存使用率
    memory_bean = "java.lang:type=Memory"
    memory_info = next((bean for bean in beans if bean.get("name") == memory_bean), None)
    
    if memory_info:
        heap_memory_usage = memory_info.get("HeapMemoryUsage", {})
        if isinstance(heap_memory_usage, dict):
            used = heap_memory_usage.get("used", 0)
            max_mem = heap_memory_usage.get("max", 1)
            if max_mem > 0:
                heap_usage_percent = (used / max_mem) * 100
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": f"{heap_usage_percent:.2f}%",
                    "raw_value": heap_usage_percent,
                    "status": "normal" if heap_usage_percent < 85 else "abnormal"
                }
            else:
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": "未知",
                    "status": "normal"
                }
        else:
            result["metrics"]["heap_memory_usage"] = {
                "name": "堆内存使用率",
                "value": "无法获取",
                "status": "normal"
            }
    else:
        result["metrics"]["heap_memory_usage"] = {
            "name": "堆内存使用率",
            "value": "无法获取",
            "status": "normal"
        }
    
    return result


def get_nodemanager_metrics(nodemanager_url: str, node_name: str) -> Dict[str, Any]:
    """
    获取指定 NodeManager 的关键指标
    
    Args:
        nodemanager_url: NodeManager JMX URL
        node_name: 节点名称，如 "nodemanager-namenode", "nodemanager-datanode1"
    
    Returns:
        包含 NodeManager 指标的字典
    """
    metrics_data, error = fetch_jmx(nodemanager_url)
    
    if error or not metrics_data:
        return {
            "status": "error",
            "error": error or "无法获取数据",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "node": node_name
        }
    
    beans = metrics_data.get("beans", [])
    
    result = {
        "status": "normal",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node": node_name,
        "metrics": {}
    }
    
    # 1. NodeManager 状态（通过检查NodeManagerMetrics Bean是否存在）
    nm_metrics_bean = "Hadoop:service=NodeManager,name=NodeManagerMetrics"
    nm_metrics = next((bean for bean in beans if bean.get("name") == nm_metrics_bean), None)
    
    if nm_metrics:
        state = "running"
    else:
        state = "stopped"
    
    result["metrics"]["nodemanager_status"] = {
        "name": "NodeManager 状态",
        "value": state,
        "status": "normal" if state == "running" else "abnormal"
    }
    
    if not nm_metrics:
        return result  # 如果NodeManager未运行，只返回状态
    
    # 2. 活跃Container数量（使用ContainersRunning）
    containers_running = extract_jmx_value(beans, nm_metrics_bean, "ContainersRunning", 0)
    result["metrics"]["active_containers"] = {
        "name": "活跃 Container 数量",
        "value": containers_running,
        "status": "normal"
    }
    
    # 3. 已完成Container数量（使用ContainersCompleted）
    containers_completed = extract_jmx_value(beans, nm_metrics_bean, "ContainersCompleted", 0)
    result["metrics"]["completed_containers"] = {
        "name": "已完成 Container 数量",
        "value": containers_completed,
        "status": "normal"
    }
    
    # 4. 失败Container数量（使用ContainersFailed）
    containers_failed = extract_jmx_value(beans, nm_metrics_bean, "ContainersFailed", 0)
    result["metrics"]["failed_containers"] = {
        "name": "失败 Container 数量",
        "value": containers_failed,
        "status": "normal" if containers_failed == 0 else "abnormal"
    }
    
    # 5. 被终止Container数量（使用ContainersKilled）
    containers_killed = extract_jmx_value(beans, nm_metrics_bean, "ContainersKilled", 0)
    result["metrics"]["killed_containers"] = {
        "name": "被终止 Container 数量",
        "value": containers_killed,
        "status": "normal"
    }
    
    # 6. 已分配Container数量
    allocated_containers = extract_jmx_value(beans, nm_metrics_bean, "AllocatedContainers", 0)
    result["metrics"]["allocated_containers"] = {
        "name": "已分配 Container 数量",
        "value": allocated_containers,
        "status": "normal"
    }
    
    # 7. 已使用内存（从ContainerUsedMemGB计算，单位GB转MB）
    container_used_mem_gb = extract_jmx_value(beans, nm_metrics_bean, "ContainerUsedMemGB", 0.0)
    container_used_mb = container_used_mem_gb * 1024
    result["metrics"]["used_memory_mb"] = {
        "name": "已使用内存",
        "value": f"{container_used_mb:.2f} MB ({container_used_mem_gb:.2f} GB)" if container_used_mb > 0 else "0 MB",
        "raw_value": container_used_mb,
        "status": "normal"
    }
    
    # 8. 已分配CPU核心数（使用AllocatedVCores）
    allocated_vcores = extract_jmx_value(beans, nm_metrics_bean, "AllocatedVCores", 0)
    result["metrics"]["allocated_vcores"] = {
        "name": "已分配CPU核心数",
        "value": allocated_vcores,
        "status": "normal"
    }
    
    # 9. 可用CPU核心数（使用AvailableVCores）
    available_vcores = extract_jmx_value(beans, nm_metrics_bean, "AvailableVCores", 0)
    result["metrics"]["available_vcores"] = {
        "name": "可用CPU核心数",
        "value": available_vcores,
        "status": "normal"
    }
    
    # 10. 总CPU核心数（计算：已分配 + 可用）
    total_vcores = allocated_vcores + available_vcores
    if total_vcores > 0:
        result["metrics"]["total_vcores"] = {
            "name": "总CPU核心数",
            "value": total_vcores,
            "status": "normal"
        }
        
        # CPU使用率
        cpu_usage_percent = (allocated_vcores / total_vcores) * 100
        result["metrics"]["cpu_usage_percent"] = {
            "name": "CPU使用率",
            "value": f"{cpu_usage_percent:.2f}%",
            "raw_value": cpu_usage_percent,
            "status": "normal" if cpu_usage_percent < 85 else "abnormal"  # 阈值85%
        }
    
    # 注意：NodeManager的内存指标（AllocatedMB/AvailableMB）可能在其他Bean中
    # 如果找不到，使用ContainerUsedMemGB作为已使用内存的参考
    
    # 12. 堆内存使用率
    memory_bean = "java.lang:type=Memory"
    memory_info = next((bean for bean in beans if bean.get("name") == memory_bean), None)
    
    if memory_info:
        heap_memory_usage = memory_info.get("HeapMemoryUsage", {})
        if isinstance(heap_memory_usage, dict):
            used = heap_memory_usage.get("used", 0)
            max_mem = heap_memory_usage.get("max", 1)
            if max_mem > 0:
                heap_usage_percent = (used / max_mem) * 100
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": f"{heap_usage_percent:.2f}%",
                    "raw_value": heap_usage_percent,
                    "status": "normal" if heap_usage_percent < 85 else "abnormal"
                }
            else:
                result["metrics"]["heap_memory_usage"] = {
                    "name": "堆内存使用率",
                    "value": "未知",
                    "status": "normal"
                }
        else:
            result["metrics"]["heap_memory_usage"] = {
                "name": "堆内存使用率",
                "value": "无法获取",
                "status": "normal"
            }
    else:
        result["metrics"]["heap_memory_usage"] = {
            "name": "堆内存使用率",
            "value": "无法获取",
            "status": "normal"
        }
    
    return result


def collect_all_metrics() -> Dict[str, Any]:
    """
    采集所有关键监控指标
    
    Returns:
        包含所有监控数据的字典
    """
    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "namenode": {},
        "datanodes": {},
        "resourcemanager": {},
        "nodemanagers": {}
    }
    
    # 获取 NameNode 指标
    result["namenode"] = get_namenode_metrics()
    
    # 获取所有 DataNode 指标，并统计实际连接数量
    # 注意：实际有3个DataNode：
    # 1. namenode容器中的datanode（通过主机端口9866访问，容器内端口9864）
    # 2. datanode1容器中的datanode（通过主机端口9864访问）
    # 3. datanode2容器中的datanode（通过主机端口9865访问）
    # 现在所有3个DataNode都有独立的JMX端口，可以单独监控
    node_names = ["datanode1", "datanode2", "datanode-namenode"]
    connected_count = 0
    disconnected_count = 0
    
    for i, dn_url in enumerate(DATANODES):
        node_name = node_names[i] if i < len(node_names) else f"datanode{i+1}"
        dn_result = get_datanode_metrics(dn_url, node_name)
        result["datanodes"][node_name] = dn_result
        
        if (dn_result.get("status") != "error" and 
            dn_result.get("metrics", {}).get("datanode_status", {}).get("value") == "running"):
            connected_count += 1
        else:
            disconnected_count += 1
    
    # 更新 NameNode 指标中的活跃和死掉的 DataNode 数量
    # 注意：heartbeat_value来自NameNode的JMX，显示所有3个DataNode的心跳状态
    # connected_count是实际通过JMX访问到的DataNode数量（应该是3个：datanode1、datanode2和datanode-namenode）
    if result["namenode"].get("status") != "error":
        if "live_datanodes" in result["namenode"].get("metrics", {}):
            heartbeat_value = result["namenode"]["metrics"]["live_datanodes"].get("heartbeat_value", 0)
            result["namenode"]["metrics"]["live_datanodes"]["value"] = f"{heartbeat_value} (心跳) / {connected_count} (JMX实时)"
            result["namenode"]["metrics"]["live_datanodes"]["jmx_value"] = connected_count
            result["namenode"]["metrics"]["live_datanodes"]["status"] = "normal" if heartbeat_value >= 3 else "abnormal"  # 应该有3个DataNode
        
        if "dead_datanodes" in result["namenode"].get("metrics", {}):
            heartbeat_value = result["namenode"]["metrics"]["dead_datanodes"].get("heartbeat_value", 0)
            result["namenode"]["metrics"]["dead_datanodes"]["value"] = f"{heartbeat_value} (心跳) / {disconnected_count} (JMX实时)"
            result["namenode"]["metrics"]["dead_datanodes"]["jmx_value"] = disconnected_count
            result["namenode"]["metrics"]["dead_datanodes"]["status"] = "normal" if disconnected_count == 0 else "abnormal"
    
    # 获取 ResourceManager 指标（如果未启动，返回错误状态但不影响其他指标）
    result["resourcemanager"] = get_resourcemanager_metrics()
    
    # 获取所有 NodeManager 指标
    # 注意：实际有3个NodeManager：
    # 1. namenode容器中的NodeManager（通过主机端口8042访问，容器内端口8042）
    # 2. datanode1容器中的NodeManager（通过主机端口8043访问，容器内端口8042）
    # 3. datanode2容器中的NodeManager（通过主机端口8044访问，容器内端口8042）
    nm_node_names = ["nodemanager-namenode", "nodemanager-datanode1", "nodemanager-datanode2"]
    
    for i, nm_url in enumerate(NODEMANAGERS):
        node_name = nm_node_names[i] if i < len(nm_node_names) else f"nodemanager{i+1}"
        nm_result = get_nodemanager_metrics(nm_url, node_name)
        result["nodemanagers"][node_name] = nm_result
    
    return result


def format_metrics_for_display(metrics_data: Dict[str, Any]) -> str:
    """
    格式化监控数据为 HTML 显示（紧凑版）
    
    Args:
        metrics_data: collect_all_metrics() 返回的数据
    
    Returns:
        HTML 格式的字符串
    """
    html = "<div style='font-family: Arial, sans-serif; font-size: 13px;'>"
    
    # 使用可滚动容器，限制最大高度
    html += "<div style='max-height: 500px; overflow-y: auto; border: 1px solid #ddd; border-radius: 5px; padding: 10px;'>"
    
    # NameNode 指标（紧凑版）
    html += "<h4 style='color: #2c3e50; margin: 5px 0; font-size: 14px; border-bottom: 1px solid #3498db; padding-bottom: 3px;'>NameNode</h4>"
    html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 12px;'>"
    
    if metrics_data["namenode"].get("status") == "error":
        html += f"<tr><td colspan='3' style='color: red; padding: 5px; font-size: 11px;'>❌ {metrics_data['namenode'].get('error', '未知错误')}</td></tr>"
    else:
        for key, metric in metrics_data["namenode"].get("metrics", {}).items():
            status_icon = "✅" if metric["status"] == "normal" else "⚠️"
            status_color = "#27ae60" if metric["status"] == "normal" else "#e74c3c"
            html += f"""
            <tr style='border-bottom: 1px solid #f0f0f0;'>
                <td style='padding: 4px 6px; font-weight: bold; width: 40%;'>{metric['name']}</td>
                <td style='padding: 4px 6px; width: 35%;'>{metric['value']}</td>
                <td style='padding: 4px 6px; color: {status_color}; width: 25%; font-size: 11px;'>{status_icon}</td>
            </tr>
            """
    
    html += "</table>"
    
    # ResourceManager 指标（紧凑版）
    html += "<h4 style='color: #2c3e50; margin: 10px 0 5px 0; font-size: 14px; border-bottom: 1px solid #3498db; padding-bottom: 3px;'>ResourceManager</h4>"
    html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 12px;'>"
    
    if metrics_data.get("resourcemanager", {}).get("status") == "error":
        html += f"<tr><td colspan='3' style='color: red; padding: 5px; font-size: 11px;'>❌ {metrics_data.get('resourcemanager', {}).get('error', '未知错误')}</td></tr>"
    else:
        # 按重要性排序显示ResourceManager指标
        rm_metrics = metrics_data.get("resourcemanager", {}).get("metrics", {})
        # 定义重要性顺序
        rm_priority_order = [
            "resourcemanager_status",
            "active_nodemanagers",
            "lost_nodemanagers",
            "unhealthy_nodemanagers",
            "apps_running",
            "apps_failed",
            "memory_usage_percent",
            "cpu_usage_percent",
            "total_memory_mb",
            "utilized_memory_mb",
            "available_memory_mb",
            "total_vcores",
            "utilized_vcores",
            "apps_submitted",
            "apps_completed",
            "apps_killed",
            "heap_memory_usage"
        ]
        
        # 按优先级显示
        displayed_keys = set()
        for key in rm_priority_order:
            if key in rm_metrics:
                metric = rm_metrics[key]
                status_icon = "✅" if metric["status"] == "normal" else "⚠️"
                status_color = "#27ae60" if metric["status"] == "normal" else "#e74c3c"
                html += f"""
                <tr style='border-bottom: 1px solid #f0f0f0;'>
                    <td style='padding: 4px 6px; font-weight: bold; width: 40%;'>{metric['name']}</td>
                    <td style='padding: 4px 6px; width: 35%;'>{metric['value']}</td>
                    <td style='padding: 4px 6px; color: {status_color}; width: 25%; font-size: 11px;'>{status_icon}</td>
                </tr>
                """
                displayed_keys.add(key)
        
        # 显示剩余的指标（如果有）
        for key, metric in rm_metrics.items():
            if key not in displayed_keys:
                status_icon = "✅" if metric["status"] == "normal" else "⚠️"
                status_color = "#27ae60" if metric["status"] == "normal" else "#e74c3c"
                html += f"""
                <tr style='border-bottom: 1px solid #f0f0f0;'>
                    <td style='padding: 4px 6px; font-weight: bold; width: 40%;'>{metric['name']}</td>
                    <td style='padding: 4px 6px; width: 35%;'>{metric['value']}</td>
                    <td style='padding: 4px 6px; color: {status_color}; width: 25%; font-size: 11px;'>{status_icon}</td>
                </tr>
                """
    
    html += "</table>"
    
    # DataNode 和 NodeManager 指标（合并显示，按节点分组）
    html += "<h4 style='color: #2c3e50; margin: 10px 0 5px 0; font-size: 14px; border-bottom: 1px solid #3498db; padding-bottom: 3px;'>DataNodes & NodeManagers</h4>"
    
    # 节点映射：DataNode名称 -> NodeManager名称
    node_mapping = {
        "datanode1": "nodemanager-datanode1",
        "datanode2": "nodemanager-datanode2",
        "datanode-namenode": "nodemanager-namenode"
    }
    
    for dn_name in ["datanode1", "datanode2", "datanode-namenode"]:
        # 显示DataNode信息
        dn_data = metrics_data["datanodes"].get(dn_name, {})
        nm_name = node_mapping.get(dn_name, "")
        nm_data = metrics_data["nodemanagers"].get(nm_name, {})
        
        html += f"<div style='margin-bottom: 10px;'><strong style='color: #34495e; font-size: 12px;'>{dn_name}</strong></div>"
        
        # DataNode指标
        html += "<div style='margin-left: 10px; margin-bottom: 5px;'><em style='color: #7f8c8d; font-size: 11px;'>DataNode:</em></div>"
        html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 12px; margin-left: 10px;'>"
        
        if dn_data.get("status") == "error":
            html += f"<tr><td colspan='3' style='color: red; padding: 5px; font-size: 11px;'>❌ {dn_data.get('error', '未知错误')}</td></tr>"
        else:
            # 按重要性排序DataNode指标
            dn_metrics = dn_data.get("metrics", {})
            dn_priority_order = [
                "datanode_status",
                "storage_usage",
                "remaining_storage",
                "under_replicated_blocks",
                "num_blocks",
                "dfs_used_mb",
                "heap_memory_usage"
            ]
            
            displayed_dn_keys = set()
            for key in dn_priority_order:
                if key in dn_metrics:
                    metric = dn_metrics[key]
                    status_icon = "✅" if metric["status"] == "normal" else "⚠️"
                    status_color = "#27ae60" if metric["status"] == "normal" else "#e74c3c"
                    html += f"""
                    <tr style='border-bottom: 1px solid #f0f0f0;'>
                        <td style='padding: 4px 6px; font-weight: bold; width: 40%;'>{metric['name']}</td>
                        <td style='padding: 4px 6px; width: 35%;'>{metric['value']}</td>
                        <td style='padding: 4px 6px; color: {status_color}; width: 25%; font-size: 11px;'>{status_icon}</td>
                    </tr>
                    """
                    displayed_dn_keys.add(key)
            
            # 显示剩余的DataNode指标
            for key, metric in dn_metrics.items():
                if key not in displayed_dn_keys:
                    status_icon = "✅" if metric["status"] == "normal" else "⚠️"
                    status_color = "#27ae60" if metric["status"] == "normal" else "#e74c3c"
                    html += f"""
                    <tr style='border-bottom: 1px solid #f0f0f0;'>
                        <td style='padding: 4px 6px; font-weight: bold; width: 40%;'>{metric['name']}</td>
                        <td style='padding: 4px 6px; width: 35%;'>{metric['value']}</td>
                        <td style='padding: 4px 6px; color: {status_color}; width: 25%; font-size: 11px;'>{status_icon}</td>
                    </tr>
                    """
        
        html += "</table>"
        
        # NodeManager指标
        html += "<div style='margin-left: 10px; margin-bottom: 5px;'><em style='color: #7f8c8d; font-size: 11px;'>NodeManager:</em></div>"
        html += "<table style='width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 12px; margin-left: 10px;'>"
        
        if nm_data.get("status") == "error":
            html += f"<tr><td colspan='3' style='color: red; padding: 5px; font-size: 11px;'>❌ {nm_data.get('error', '未知错误')}</td></tr>"
        else:
            # 按重要性排序NodeManager指标
            nm_metrics = nm_data.get("metrics", {})
            nm_priority_order = [
                "nodemanager_status",
                "active_containers",
                "failed_containers",
                "cpu_usage_percent",
                "used_memory_mb",
                "allocated_vcores",
                "available_vcores",
                "total_vcores",
                "allocated_containers",
                "completed_containers",
                "killed_containers",
                "heap_memory_usage"
            ]
            
            displayed_nm_keys = set()
            for key in nm_priority_order:
                if key in nm_metrics:
                    metric = nm_metrics[key]
                    status_icon = "✅" if metric["status"] == "normal" else "⚠️"
                    status_color = "#27ae60" if metric["status"] == "normal" else "#e74c3c"
                    html += f"""
                    <tr style='border-bottom: 1px solid #f0f0f0;'>
                        <td style='padding: 4px 6px; font-weight: bold; width: 40%;'>{metric['name']}</td>
                        <td style='padding: 4px 6px; width: 35%;'>{metric['value']}</td>
                        <td style='padding: 4px 6px; color: {status_color}; width: 25%; font-size: 11px;'>{status_icon}</td>
                    </tr>
                    """
                    displayed_nm_keys.add(key)
            
            # 显示剩余的NodeManager指标
            for key, metric in nm_metrics.items():
                if key not in displayed_nm_keys:
                    status_icon = "✅" if metric["status"] == "normal" else "⚠️"
                    status_color = "#27ae60" if metric["status"] == "normal" else "#e74c3c"
                    html += f"""
                    <tr style='border-bottom: 1px solid #f0f0f0;'>
                        <td style='padding: 4px 6px; font-weight: bold; width: 40%;'>{metric['name']}</td>
                        <td style='padding: 4px 6px; width: 35%;'>{metric['value']}</td>
                        <td style='padding: 4px 6px; color: {status_color}; width: 25%; font-size: 11px;'>{status_icon}</td>
                    </tr>
                    """
        
        html += "</table>"
    
    html += "</div>"  # 结束滚动容器
    
    html += f"<p style='color: #7f8c8d; font-size: 11px; margin-top: 8px; text-align: right;'>更新: {metrics_data['timestamp']}</p>"
    html += "</div>"
    
    return html

