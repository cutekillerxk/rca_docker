#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档导入示例脚本
演示如何将Hadoop和Docker文档导入到知识库
"""

import logging
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from lc_agent.knowledge_base import (
    import_document_to_kb,
    import_directory_to_kb,
    get_kb_manager
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_import_single_document():
    """示例：导入单个文档"""
    print("=" * 60)
    print("示例1: 导入单个文档")
    print("=" * 60)
    
    # 示例：导入一个Hadoop文档
    # 请将路径替换为实际的文档路径
    file_path = "/path/to/your/hadoop-doc.md"
    
    if not Path(file_path).exists():
        print(f"⚠️  文件不存在: {file_path}")
        print("请修改 file_path 为实际的文档路径")
        return
    
    result = import_document_to_kb(
        file_path=file_path,
        kb_name="HadoopDocs",
        chunk_size=500,
        chunk_overlap=50,
        encoding="utf-8",
        metadata={
            "source": "Hadoop官方文档",
            "category": "HDFS",
            "version": "3.3.0"
        }
    )
    
    if result["success"]:
        print(f"✅ 成功导入文档: {result['file_name']}")
        print(f"   知识库: {result['kb_name']}")
        print(f"   文档块数: {result['total_chunks']}")
    else:
        print(f"❌ 导入失败: {result['message']}")


def example_import_directory():
    """示例：批量导入目录中的所有文档"""
    print("\n" + "=" * 60)
    print("示例2: 批量导入目录")
    print("=" * 60)
    
    # 示例：导入整个目录
    directory_path = "/path/to/hadoop-docs"
    
    if not Path(directory_path).exists():
        print(f"⚠️  目录不存在: {directory_path}")
        print("请修改 directory_path 为实际的目录路径")
        return
    
    result = import_directory_to_kb(
        directory_path=directory_path,
        kb_name="HadoopDocs",
        chunk_size=500,
        chunk_overlap=50,
        file_extensions=['.md', '.txt', '.pdf'],
        metadata={
            "source": "Hadoop官方文档",
            "version": "3.3.0"
        }
    )
    
    print(f"导入结果: {result['message']}")
    print(f"总文件数: {result['total_files']}")
    print(f"成功: {result['success_files']}")
    
    if result['failed_files']:
        print(f"失败文件: {result['failed_files']}")


def example_import_docker_docs():
    """示例：导入Docker文档"""
    print("\n" + "=" * 60)
    print("示例3: 导入Docker文档")
    print("=" * 60)
    
    # 创建Docker知识库
    kb_manager = get_kb_manager()
    docker_kb = kb_manager.get_or_create_kb("DockerDocs")
    
    # 导入Docker文档目录
    docker_docs_path = "/path/to/docker-docs/content"
    
    if not Path(docker_docs_path).exists():
        print(f"⚠️  目录不存在: {docker_docs_path}")
        print("请先克隆Docker文档:")
        print("  git clone https://github.com/docker/docs.git")
        print("  然后修改 docker_docs_path 为实际的路径")
        return
    
    result = import_directory_to_kb(
        directory_path=docker_docs_path,
        kb_name="DockerDocs",
        chunk_size=500,
        chunk_overlap=50,
        metadata={
            "source": "Docker官方文档"
        }
    )
    
    print(f"导入结果: {result['message']}")
    print(f"成功导入: {result['success_files']}/{result['total_files']} 个文件")


def example_list_knowledge_bases():
    """示例：列出所有知识库"""
    print("\n" + "=" * 60)
    print("示例4: 列出所有知识库")
    print("=" * 60)
    
    kb_manager = get_kb_manager()
    
    print(f"已创建的知识库 ({len(kb_manager.knowledge_bases)} 个):")
    for kb_name, kb in kb_manager.knowledge_bases.items():
        # 尝试获取文档数量（如果向量存储已加载）
        doc_count = "未知"
        try:
            if kb.vector_store and hasattr(kb.vector_store, 'index'):
                doc_count = kb.vector_store.index.ntotal
        except:
            pass
        
        print(f"  - {kb_name}: {doc_count} 个文档块")
        print(f"    路径: {kb.kb_path}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("知识库文档导入示例")
    print("=" * 60)
    print("\n提示:")
    print("1. 请先准备文档文件或目录")
    print("2. 修改脚本中的路径为实际路径")
    print("3. 运行相应的示例函数")
    print("\n推荐的文档来源:")
    print("- Hadoop: git clone https://github.com/apache/hadoop.git")
    print("- Docker: git clone https://github.com/docker/docs.git")
    print("\n" + "=" * 60 + "\n")
    
    # 运行示例（取消注释以运行）
    # example_import_single_document()
    # example_import_directory()
    # example_import_docker_docs()
    example_list_knowledge_bases()
    
    print("\n" + "=" * 60)
    print("提示: 取消注释上面的函数调用来运行实际导入")
    print("=" * 60)


if __name__ == "__main__":
    main()

