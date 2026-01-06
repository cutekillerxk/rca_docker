#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库检索（RAG）机制实现
从DB-GPT迁移，适配HDFS集群诊断场景
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from langchain_core.documents import Document

# LangChain 1.0.7: 使用 langchain_community 而不是 langchain
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

# 文档加载器
try:
    from langchain_community.document_loaders import (
        TextLoader,
        PyPDFLoader,
        UnstructuredMarkdownLoader,
        UnstructuredFileLoader,
    )
    DOCUMENT_LOADERS_AVAILABLE = True
except ImportError:
    DOCUMENT_LOADERS_AVAILABLE = False
    logging.warning("langchain_community.document_loaders 未安装，文档加载功能将受限")



from langchain_text_splitters import RecursiveCharacterTextSplitter
TEXT_SPLITTER_AVAILABLE = True


import numpy as np
import logging

# 设置本地模型路径（优先使用服务器本地模型）
# 默认使用 /media/hnu/LLM/hnu/LLM/ 目录下的模型
LOCAL_MODEL_BASE_DIR = "/media/hnu/LLM/hnu/LLM"
# 默认使用的嵌入模型（可根据需要修改）
# 推荐中文场景：bge-large-zh-v1.5, text2vec-base-chinese
# 推荐多语言场景：bge-m3
DEFAULT_EMBEDDING_MODEL = "Chuxin-Embedding"  #bge-large-zh-v1.5 中文嵌入模型  bge-m3 多语言嵌入模型

# 设置sentence-transformers模型缓存目录
MODEL_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
# 设置环境变量（sentence-transformers会使用这个目录）
os.environ['TRANSFORMERS_CACHE'] = MODEL_CACHE_DIR
os.environ['HF_HOME'] = MODEL_CACHE_DIR


from sentence_transformers import SentenceTransformer
SENTENCE_TRANSFORMER_AVAILABLE = True



class SimpleEmbeddings(Embeddings):
    """简化的嵌入模型封装"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        初始化嵌入模型
        
        Args:
            model_name: 模型名称或路径
                - 如果为 None，使用 DEFAULT_EMBEDDING_MODEL
                - 如果是本地路径，直接使用
                - 如果是模型名称，先尝试本地路径，再尝试在线下载
        """
        self.model_name = model_name or DEFAULT_EMBEDDING_MODEL
        if SENTENCE_TRANSFORMER_AVAILABLE:
            try:
                # 1. 尝试使用本地模型路径
                local_model_path = os.path.join(LOCAL_MODEL_BASE_DIR, self.model_name)
                if os.path.exists(local_model_path):
                    logging.info(f"使用本地模型: {local_model_path}")
                    self.embedder = SentenceTransformer(local_model_path)
                else:
                    # 2. 尝试作为完整路径
                    if os.path.exists(self.model_name):
                        logging.info(f"使用指定路径模型: {self.model_name}")
                        self.embedder = SentenceTransformer(self.model_name)
                    else:
                        # 3. 尝试从 HuggingFace 下载（使用缓存目录）
                        logging.info(f"尝试加载模型: {self.model_name}（将从 HuggingFace 下载）")
                        self.embedder = SentenceTransformer(
                            self.model_name,
                            cache_folder=MODEL_CACHE_DIR
                        )
            except Exception as e:
                logging.warning(f"加载嵌入模型失败: {e}，使用简化版")
                self.embedder = None
        else:
            self.embedder = None
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        if self.embedder:
            embeddings = self.embedder.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # 简化版：使用简单的词频向量（实际应用中应使用真实嵌入模型）
            logging.warning("使用简化版嵌入，建议安装sentence-transformers")
            return [[0.0] * 384 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        if self.embedder:
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        else:
            logging.warning("使用简化版嵌入，建议安装sentence-transformers")
            return [0.0] * 384


class KnowledgeBase:
    """知识库管理类"""
    
    def __init__(self, kb_name: str, kb_path: Optional[str] = None):
        """
        初始化知识库
        
        Args:
            kb_name: 知识库名称（如：NameNodeExpert, DataNodeExpert）
            kb_path: 知识库存储路径（可选）
        """
        self.kb_name = kb_name
        self.kb_path = kb_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "knowledge_base",
            kb_name
        )
        os.makedirs(self.kb_path, exist_ok=True)
        
        # 初始化嵌入模型
        self.embeddings = SimpleEmbeddings()
        
        # 向量存储
        self.vector_store = None
        self._load_or_create_vector_store()
    
    def _load_or_create_vector_store(self):
        """加载或创建向量存储"""
        vector_store_path = os.path.join(self.kb_path, "vector_store")
        
        if os.path.exists(vector_store_path) and os.listdir(vector_store_path):
            try:
                self.vector_store = FAISS.load_local(
                    vector_store_path,
                    self.embeddings
                )
                logging.info(f"成功加载知识库: {self.kb_name}")
            except Exception as e:
                logging.warning(f"加载向量存储失败: {e}，将创建新的")
                self.vector_store = None
        
        if self.vector_store is None:
            # 创建空的向量存储
            self.vector_store = FAISS.from_texts(
                ["初始化"],
                self.embeddings
            )
            # 删除初始化文档
            self.vector_store.delete([self.vector_store.index_to_docstore_id[0]])
    
    def add_documents(self, documents: List[Document]):
        """
        添加文档到知识库
        
        Args:
            documents: Document列表
        """
        if not documents:
            return
        
        # 添加到向量存储
        self.vector_store.add_documents(documents)
        
        # 保存向量存储
        self.save()
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None):
        """
        添加文本到知识库
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表（可选）
        """
        if not texts:
            return
        
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        # 创建Document对象
        documents = [
            Document(page_content=text, metadata=metadata)
            for text, metadata in zip(texts, metadatas)
        ]
        
        self.add_documents(documents)
    
    def search(self, query: str, top_k: int = 3, score_threshold: float = 0.4) -> List[Tuple[Document, float]]:
        """
        搜索相关知识
        
        Args:
            query: 查询字符串
            top_k: 返回top_k个结果
            score_threshold: 相似度阈值（FAISS使用L2距离，越小越相似）
        
        Returns:
            (Document, score) 元组列表
        """
        try:
            # FAISS使用similarity_search_with_score
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            # 过滤低分结果（注意：FAISS返回的是距离，不是相似度）
            # 距离越小越相似，所以需要反转阈值判断
            filtered_results = [
                (doc, score) for doc, score in results
                if score <= (1.0 - score_threshold) * 10  # 简单的阈值转换
            ]
            
            return filtered_results
        except Exception as e:
            logging.error(f"搜索知识库失败: {e}")
            return []
    
    def save(self):
        """保存向量存储"""
        vector_store_path = os.path.join(self.kb_path, "vector_store")
        os.makedirs(vector_store_path, exist_ok=True)
        self.vector_store.save_local(vector_store_path)
        logging.info(f"知识库已保存: {self.kb_name}")


class KnowledgeBaseManager:
    """知识库管理器"""
    
    def __init__(self):
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self._init_default_knowledge_bases()
    
    def _init_default_knowledge_bases(self):
        """初始化默认知识库"""
        # HDFS集群诊断相关的知识库
        default_kbs = [
            "NameNodeExpert",
            "DataNodeExpert",
            "YARNExpert",
            "HistoryCases",  # 历史故障案例
            "HadoopDocs",    # Hadoop官方文档
        ]
        
        for kb_name in default_kbs:
            self.get_or_create_kb(kb_name)
    
    def get_or_create_kb(self, kb_name: str) -> KnowledgeBase:
        """获取或创建知识库"""
        if kb_name not in self.knowledge_bases:
            self.knowledge_bases[kb_name] = KnowledgeBase(kb_name)
        return self.knowledge_bases[kb_name]
    
    def search_knowledge(
        self,
        query: str,
        kb_name: Optional[str] = None,
        top_k: int = 3,
        score_threshold: float = 0.4
    ) -> List[Tuple[Document, float]]:
        """
        搜索知识库
        
        Args:
            query: 查询字符串
            kb_name: 知识库名称（None表示搜索所有知识库）
            top_k: 返回top_k个结果
            score_threshold: 相似度阈值
        
        Returns:
            (Document, score) 元组列表
        """
        if kb_name:
            # 搜索指定知识库
            if kb_name in self.knowledge_bases:
                return self.knowledge_bases[kb_name].search(query, top_k, score_threshold)
            else:
                logging.warning(f"知识库不存在: {kb_name}")
                return []
        else:
            # 搜索所有知识库
            all_results = []
            for kb in self.knowledge_bases.values():
                results = kb.search(query, top_k, score_threshold)
                all_results.extend(results)
            
            # 按分数排序并返回top_k
            all_results.sort(key=lambda x: x[1])
            return all_results[:top_k]
    
    def match_knowledge_base(self, expert_type: str) -> str:
        """
        根据专家类型匹配知识库名称
        
        Args:
            expert_type: 专家类型（如："namenode", "datanode"）
        
        Returns:
            知识库名称
        """
        expert_type_lower = expert_type.lower()
        
        # 匹配规则
        if "namenode" in expert_type_lower or "nn" in expert_type_lower:
            return "NameNodeExpert"
        elif "datanode" in expert_type_lower or "dn" in expert_type_lower:
            return "DataNodeExpert"
        elif "yarn" in expert_type_lower:
            return "YARNExpert"
        else:
            # 默认返回历史案例库
            return "HistoryCases"


# 全局知识库管理器实例
_kb_manager = None


def get_kb_manager() -> KnowledgeBaseManager:
    """获取全局知识库管理器"""
    global _kb_manager
    if _kb_manager is None:
        _kb_manager = KnowledgeBaseManager()
    return _kb_manager


def search_diagnosis_knowledge(
    query: str,
    expert_type: str = "all",
    top_k: int = 3,
    score_threshold: float = 0.4
) -> str:
    """
    从知识库检索诊断相关知识（工具函数，供Agent调用）
    
    Args:
        query: 查询字符串（例如："NameNode无法启动"）
        expert_type: 专家类型（"namenode", "datanode", "all"）
        top_k: 返回top_k个结果
        score_threshold: 相似度阈值
    
    Returns:
        检索到的相关知识字符串
    """
    kb_manager = get_kb_manager()
    
    # 匹配知识库
    if expert_type.lower() == "all":
        kb_name = None  # 搜索所有知识库
    else:
        kb_name = kb_manager.match_knowledge_base(expert_type)
    
    # 执行搜索
    results = kb_manager.search_knowledge(
        query=query,
        kb_name=kb_name,
        top_k=top_k,
        score_threshold=score_threshold
    )
    
    # 格式化返回
    if not results:
        return f"未找到与 '{query}' 相关的知识"
    
    knowledge_str = f"找到 {len(results)} 条相关知识：\n\n"
    for idx, (doc, score) in enumerate(results, 1):
        knowledge_str += f"[知识 {idx}] (相似度: {1-score:.2f})\n"
        if doc.metadata:
            if 'source' in doc.metadata:
                knowledge_str += f"来源: {doc.metadata['source']}\n"
            if 'desc' in doc.metadata:
                knowledge_str += f"描述: {doc.metadata['desc']}\n"
        knowledge_str += f"内容: {doc.page_content}\n\n"
    
    return knowledge_str


def search_operation_knowledge(
    query: str,
    top_k: int = 3,
    score_threshold: float = 0.4
) -> str:
    """
    从操作知识库检索Hadoop集群操作说明（工具函数，供Agent调用）
    
    Args:
        query: 查询字符串（例如："如何重启NameNode"、"查看集群状态"）
        top_k: 返回top_k个结果
        score_threshold: 相似度阈值
    
    Returns:
        检索到的操作说明字符串
    """
    kb_manager = get_kb_manager()
    
    # 确保操作知识库存在并已初始化
    if "OperationKB" not in kb_manager.knowledge_bases:
        init_operation_knowledge_base()
    
    # 搜索操作知识库
    results = kb_manager.search_knowledge(
        query=query,
        kb_name="OperationKB",
        top_k=top_k,
        score_threshold=score_threshold
    )
    
    # 格式化返回
    if not results:
        return f"未找到与 '{query}' 相关的操作说明"
    
    knowledge_str = f"找到 {len(results)} 条操作说明：\n\n"
    for idx, (doc, score) in enumerate(results, 1):
        knowledge_str += f"[操作说明 {idx}] (相似度: {1-score:.2f})\n"
        if doc.metadata:
            if 'operation_type' in doc.metadata:
                knowledge_str += f"操作类型: {doc.metadata['operation_type']}\n"
            if 'tool' in doc.metadata:
                knowledge_str += f"使用工具: {doc.metadata['tool']}\n"
        knowledge_str += f"内容: {doc.page_content}\n\n"
    
    return knowledge_str


def init_operation_knowledge_base():
    """
    初始化操作知识库，包含所有Hadoop集群操作的详细说明
    """
    kb_manager = get_kb_manager()
    kb = kb_manager.get_or_create_kb("OperationKB")
    
    # 操作说明文档列表
    operations = [
        # Hadoop服务操作（单节点）
        {
            "content": """
**操作名称**：重启NameNode服务
**工具**：hadoop_auto_operation
**命令格式**：["restart", "namenode"]
**说明**：在namenode容器内重启NameNode服务（先stop再start），容器保持运行
**执行方式**：docker exec namenode + su - hadoop + hdfs --daemon stop/start namenode
**前提条件**：namenode容器必须已运行
**示例**：
- 用户说"重启NameNode" → hadoop_auto_operation(command_args=["restart", "namenode"])
- 用户说"重启名称节点" → hadoop_auto_operation(command_args=["restart", "namenode"])
""",
            "metadata": {
                "operation_type": "hadoop_service",
                "tool": "hadoop_auto_operation",
                "target": "namenode",
                "action": "restart"
            }
        },
        {
            "content": """
**操作名称**：启动NameNode服务
**工具**：hadoop_auto_operation
**命令格式**：["start", "namenode"]
**说明**：在namenode容器内启动NameNode服务，容器保持运行
**执行方式**：docker exec namenode + su - hadoop + hdfs --daemon start namenode
**前提条件**：namenode容器必须已运行
**示例**：
- 用户说"启动NameNode" → hadoop_auto_operation(command_args=["start", "namenode"])
""",
            "metadata": {
                "operation_type": "hadoop_service",
                "tool": "hadoop_auto_operation",
                "target": "namenode",
                "action": "start"
            }
        },
        {
            "content": """
**操作名称**：停止NameNode服务
**工具**：hadoop_auto_operation
**命令格式**：["stop", "namenode"]
**说明**：在namenode容器内停止NameNode服务，容器保持运行
**执行方式**：docker exec namenode + su - hadoop + hdfs --daemon stop namenode
**前提条件**：namenode容器必须已运行
**示例**：
- 用户说"停止NameNode" → hadoop_auto_operation(command_args=["stop", "namenode"])
- 用户说"关闭NameNode" → hadoop_auto_operation(command_args=["stop", "namenode"])
""",
            "metadata": {
                "operation_type": "hadoop_service",
                "tool": "hadoop_auto_operation",
                "target": "namenode",
                "action": "stop"
            }
        },
        {
            "content": """
**操作名称**：重启DataNode1服务
**工具**：hadoop_auto_operation
**命令格式**：["restart", "datanode1"]
**说明**：在datanode1容器内重启DataNode服务（先stop再start），容器保持运行
**执行方式**：docker exec datanode1 + su - hadoop + hdfs --daemon stop/start datanode
**前提条件**：datanode1容器必须已运行
**示例**：
- 用户说"重启DataNode1" → hadoop_auto_operation(command_args=["restart", "datanode1"])
- 用户说"重启数据节点1" → hadoop_auto_operation(command_args=["restart", "datanode1"])
""",
            "metadata": {
                "operation_type": "hadoop_service",
                "tool": "hadoop_auto_operation",
                "target": "datanode1",
                "action": "restart"
            }
        },
        {
            "content": """
**操作名称**：启动整个HDFS集群
**工具**：hadoop_auto_operation
**命令格式**：["start"]
**说明**：在namenode容器内执行start-dfs.sh启动整个HDFS集群，所有容器保持运行
**执行方式**：docker exec namenode + su - hadoop + start-dfs.sh
**前提条件**：namenode容器必须已运行
**示例**：
- 用户说"启动整个集群" → hadoop_auto_operation(command_args=["start"])
- 用户说"启动所有节点" → hadoop_auto_operation(command_args=["start"])
""",
            "metadata": {
                "operation_type": "hadoop_cluster",
                "tool": "hadoop_auto_operation",
                "target": "cluster",
                "action": "start"
            }
        },
        {
            "content": """
**操作名称**：停止整个HDFS集群
**工具**：hadoop_auto_operation
**命令格式**：["stop"]
**说明**：在namenode容器内执行stop-dfs.sh停止整个HDFS集群，所有容器保持运行
**执行方式**：docker exec namenode + su - hadoop + stop-dfs.sh
**前提条件**：namenode容器必须已运行
**示例**：
- 用户说"停止整个集群" → hadoop_auto_operation(command_args=["stop"])
- 用户说"关闭所有节点" → hadoop_auto_operation(command_args=["stop"])
""",
            "metadata": {
                "operation_type": "hadoop_cluster",
                "tool": "hadoop_auto_operation",
                "target": "cluster",
                "action": "stop"
            }
        },
        # Hadoop命令操作（功能点二）
        {
            "content": """
**操作名称**：查看集群状态
**工具**：execute_hadoop_command
**命令格式**：["hdfs", "dfsadmin", "-report"]
**说明**：查看HDFS集群的详细状态报告，包括节点信息、存储使用情况、数据块状态等
**执行容器**：namenode
**示例**：
- 用户说"查看集群状态" → execute_hadoop_command(command_args=["hdfs", "dfsadmin", "-report"])
- 用户说"集群状态报告" → execute_hadoop_command(command_args=["hdfs", "dfsadmin", "-report"])
""",
            "metadata": {
                "operation_type": "hadoop_command",
                "tool": "execute_hadoop_command",
                "command": "hdfs dfsadmin -report"
            }
        },
        {
            "content": """
**操作名称**：查看安全模式状态
**工具**：execute_hadoop_command
**命令格式**：["hdfs", "dfsadmin", "-safemode", "get"]
**说明**：查看HDFS是否处于安全模式
**执行容器**：namenode
**示例**：
- 用户说"查看安全模式" → execute_hadoop_command(command_args=["hdfs", "dfsadmin", "-safemode", "get"])
""",
            "metadata": {
                "operation_type": "hadoop_command",
                "tool": "execute_hadoop_command",
                "command": "hdfs dfsadmin -safemode get"
            }
        },
        {
            "content": """
**操作名称**：进入安全模式
**工具**：execute_hadoop_command
**命令格式**：["hdfs", "dfsadmin", "-safemode", "enter"]
**说明**：让HDFS进入安全模式（只读模式）
**执行容器**：namenode
**示例**：
- 用户说"进入安全模式" → execute_hadoop_command(command_args=["hdfs", "dfsadmin", "-safemode", "enter"])
""",
            "metadata": {
                "operation_type": "hadoop_command",
                "tool": "execute_hadoop_command",
                "command": "hdfs dfsadmin -safemode enter"
            }
        },
        {
            "content": """
**操作名称**：退出安全模式
**工具**：execute_hadoop_command
**命令格式**：["hdfs", "dfsadmin", "-safemode", "leave"]
**说明**：让HDFS退出安全模式
**执行容器**：namenode
**示例**：
- 用户说"退出安全模式" → execute_hadoop_command(command_args=["hdfs", "dfsadmin", "-safemode", "leave"])
""",
            "metadata": {
                "operation_type": "hadoop_command",
                "tool": "execute_hadoop_command",
                "command": "hdfs dfsadmin -safemode leave"
            }
        },
        {
            "content": """
**操作名称**：检查文件系统
**工具**：execute_hadoop_command
**命令格式**：["hdfs", "fsck", "/"]
**说明**：检查HDFS文件系统的完整性
**执行容器**：namenode
**示例**：
- 用户说"检查文件系统" → execute_hadoop_command(command_args=["hdfs", "fsck", "/"])
- 用户说"文件系统检查" → execute_hadoop_command(command_args=["hdfs", "fsck", "/"])
""",
            "metadata": {
                "operation_type": "hadoop_command",
                "tool": "execute_hadoop_command",
                "command": "hdfs fsck /"
            }
        },
        {
            "content": """
**操作名称**：查看存储使用情况
**工具**：execute_hadoop_command
**命令格式**：["hdfs", "dfs", "-df"]
**说明**：查看HDFS的存储使用情况
**执行容器**：namenode
**示例**：
- 用户说"查看存储使用" → execute_hadoop_command(command_args=["hdfs", "dfs", "-df"])
""",
            "metadata": {
                "operation_type": "hadoop_command",
                "tool": "execute_hadoop_command",
                "command": "hdfs dfs -df"
            }
        },
    ]
    
    # 将操作说明添加到知识库
    from langchain_core.documents import Document
    for op in operations:
        doc = Document(
            page_content=op["content"],
            metadata=op["metadata"]
        )
        kb.add_documents([doc])
    
    # 保存知识库
    kb.save()
    logging.info("操作知识库初始化完成")


# 示例：初始化知识库数据
def init_sample_knowledge():
    """初始化示例知识库数据（用于测试）"""
    kb_manager = get_kb_manager()
    
    # NameNode专家知识库
    namenode_kb = kb_manager.get_or_create_kb("NameNodeExpert")
    namenode_kb.add_texts(
        texts=[
            "NameNode无法启动的常见原因：1) 配置文件错误 2) 端口被占用 3) 磁盘空间不足",
            "NameNode启动失败时，检查hdfs-site.xml和core-site.xml配置是否正确",
            "NameNode内存溢出时，需要增加JVM堆内存大小，修改hadoop-env.sh中的HADOOP_HEAPSIZE",
        ],
        metadatas=[
            {"source": "Hadoop官方文档", "desc": "NameNode启动问题"},
            {"source": "故障案例", "desc": "配置检查"},
            {"source": "故障案例", "desc": "内存问题"},
        ]
    )
    
    # DataNode专家知识库
    datanode_kb = kb_manager.get_or_create_kb("DataNodeExpert")
    datanode_kb.add_texts(
        texts=[
            "DataNode无法连接NameNode时，检查网络连接和防火墙设置",
            "DataNode磁盘空间不足会导致数据块复制失败",
            "DataNode心跳超时可能是网络延迟或NameNode负载过高",
        ],
        metadatas=[
            {"source": "故障案例", "desc": "连接问题"},
            {"source": "故障案例", "desc": "存储问题"},
            {"source": "故障案例", "desc": "心跳问题"},
        ]
    )
    
    # 保存所有知识库
    for kb in kb_manager.knowledge_bases.values():
        kb.save()
    
    logging.info("示例知识库数据初始化完成")


# ==================== 文档导入功能 ====================

def load_document(file_path: str, encoding: str = "utf-8") -> List[Document]:
    """
    加载文档文件，支持多种格式
    
    Args:
        file_path: 文件路径
        encoding: 文件编码（默认utf-8）
    
    Returns:
        Document列表
    
    Supported formats:
        - .txt, .md, .markdown: 文本文件
        - .pdf: PDF文件
        - 其他格式: 尝试使用UnstructuredFileLoader
    """
    if not DOCUMENT_LOADERS_AVAILABLE:
        raise ImportError("需要安装 langchain_community: pip install langchain-community")
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    suffix = file_path.suffix.lower()
    
    try:
        if suffix in ['.txt']:
            loader = TextLoader(str(file_path), encoding=encoding)
        elif suffix in ['.md', '.markdown']:
            try:
                loader = UnstructuredMarkdownLoader(str(file_path))
            except:
                # 如果UnstructuredMarkdownLoader失败，使用TextLoader
                loader = TextLoader(str(file_path), encoding=encoding)
        elif suffix == '.pdf':
            loader = PyPDFLoader(str(file_path))
        else:
            # 尝试使用通用加载器
            try:
                loader = UnstructuredFileLoader(str(file_path))
            except:
                # 最后尝试作为文本文件加载
                loader = TextLoader(str(file_path), encoding=encoding)
        
        documents = loader.load()
        logging.info(f"成功加载文档: {file_path}，共 {len(documents)} 页/段")
        return documents
    
    except Exception as e:
        logging.error(f"加载文档失败 {file_path}: {e}")
        raise


def split_documents(
    documents: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: Optional[List[str]] = None
) -> List[Document]:
    """
    将文档分割成较小的块
    
    Args:
        documents: Document列表
        chunk_size: 每个块的最大字符数
        chunk_overlap: 相邻块之间的重叠字符数
        separators: 分割符列表（默认：["\n\n", "\n", "。", "！", "？", " ", ""]）
    
    Returns:
        分割后的Document列表
    """
    if not TEXT_SPLITTER_AVAILABLE or RecursiveCharacterTextSplitter is None:
        logging.warning("文本分割器未安装，返回原始文档。请安装: pip install langchain")
        return documents
    
    if separators is None:
        # 中文友好的分割符
        separators = ["\n\n", "\n", "。", "！", "？", ". ", " ", ""]
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators
    )
    
    split_docs = text_splitter.split_documents(documents)
    logging.info(f"文档分割完成: {len(documents)} 个文档 -> {len(split_docs)} 个块")
    return split_docs


def import_document_to_kb(
    file_path: str,
    kb_name: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    encoding: str = "utf-8",
    metadata: Optional[Dict] = None
) -> Dict[str, any]:
    """
    将文档导入到指定知识库
    
    Args:
        file_path: 文档文件路径
        kb_name: 知识库名称
        chunk_size: 文本块大小
        chunk_overlap: 文本块重叠大小
        encoding: 文件编码
        metadata: 额外的元数据（会添加到所有文档块）
    
    Returns:
        导入结果字典，包含：
        - success: 是否成功
        - kb_name: 知识库名称
        - file_name: 文件名
        - total_chunks: 总块数
        - message: 消息
    """
    try:
        # 1. 加载文档
        documents = load_document(file_path, encoding=encoding)
        
        # 2. 添加元数据
        if metadata:
            for doc in documents:
                if doc.metadata:
                    doc.metadata.update(metadata)
                else:
                    doc.metadata = metadata.copy()
        
        # 添加文件来源信息
        file_name = Path(file_path).name
        for doc in documents:
            if not doc.metadata:
                doc.metadata = {}
            doc.metadata['source'] = doc.metadata.get('source', file_name)
            doc.metadata['file_path'] = str(file_path)
        
        # 3. 分割文档
        split_docs = split_documents(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # 4. 添加到知识库
        kb_manager = get_kb_manager()
        kb = kb_manager.get_or_create_kb(kb_name)
        kb.add_documents(split_docs)
        
        logging.info(f"成功导入文档到知识库 {kb_name}: {file_name} ({len(split_docs)} 个块)")
        
        return {
            "success": True,
            "kb_name": kb_name,
            "file_name": file_name,
            "total_chunks": len(split_docs),
            "message": f"成功导入 {len(split_docs)} 个文档块"
        }
    
    except Exception as e:
        error_msg = f"导入文档失败: {str(e)}"
        logging.error(error_msg)
        return {
            "success": False,
            "kb_name": kb_name,
            "file_name": Path(file_path).name if file_path else "unknown",
            "total_chunks": 0,
            "message": error_msg
        }


def import_directory_to_kb(
    directory_path: str,
    kb_name: str,
    chunk_size: int = 500, 
    chunk_overlap: int = 50,
    encoding: str = "utf-8",
    file_extensions: Optional[List[str]] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, any]:
    """
    将目录中的所有文档导入到知识库
    
    Args:
        directory_path: 目录路径
        kb_name: 知识库名称
        chunk_size: 文本块大小
        chunk_overlap: 文本块重叠大小
        encoding: 文件编码
        file_extensions: 支持的文件扩展名列表（默认：['.txt', '.md', '.markdown', '.pdf']）
        metadata: 额外的元数据
    
    Returns:
        导入结果字典，包含：
        - success: 是否全部成功
        - total_files: 总文件数
        - success_files: 成功文件数
        - failed_files: 失败文件列表
        - results: 每个文件的导入结果
    """
    if file_extensions is None:
        file_extensions = ['.txt', '.md', '.markdown', '.pdf']
    
    directory_path = Path(directory_path)
    if not directory_path.exists() or not directory_path.is_dir():
        return {
            "success": False,
            "total_files": 0,
            "success_files": 0,
            "failed_files": [],
            "results": [],
            "message": f"目录不存在或不是目录: {directory_path}"
        }
    
    # 查找所有支持的文件
    files = []
    for ext in file_extensions:
        files.extend(directory_path.glob(f"*{ext}"))
        files.extend(directory_path.rglob(f"*{ext}"))  # 递归搜索
    
    files = list(set(files))  # 去重
    
    if not files:
        return {
            "success": False,
            "total_files": 0,
            "success_files": 0,
            "failed_files": [],
            "results": [],
            "message": f"目录中没有找到支持的文件: {file_extensions}"
        }
    
    results = []
    success_count = 0
    failed_files = []
    
    for file_path in files:
        result = import_document_to_kb(
            str(file_path),
            kb_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding=encoding,
            metadata=metadata
        )
        results.append(result)
        
        if result["success"]:
            success_count += 1
        else:
            failed_files.append(result["file_name"])
    
    return {
        "success": len(failed_files) == 0,
        "total_files": len(files),
        "success_files": success_count,
        "failed_files": failed_files,
        "results": results,
        "message": f"导入完成: {success_count}/{len(files)} 个文件成功"
    }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 初始化示例数据
    init_sample_knowledge()
    
    # 测试搜索
    result = search_diagnosis_knowledge("NameNode无法启动", expert_type="namenode")
    print(result)

