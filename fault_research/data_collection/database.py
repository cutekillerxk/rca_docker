#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模块 - 存储从 Stack Overflow 和 CSDN 收集的故障帖子
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class FaultResearchDB:
    """故障研究数据库管理类"""
    
    def __init__(self, db_path: str = "fault_research.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # 使返回结果为字典形式
        
        cursor = self.conn.cursor()
        
        # 创建帖子表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,  -- 'stackoverflow' 或 'csdn'
                post_id TEXT NOT NULL,  -- 原始平台的帖子ID
                title TEXT NOT NULL,
                content TEXT,
                tags TEXT,  -- JSON格式的标签列表
                url TEXT NOT NULL,
                author TEXT,
                created_at TIMESTAMP,  -- 帖子创建时间
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 收集时间
                view_count INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,  -- 点赞数/分数
                answer_count INTEGER DEFAULT 0,
                is_accepted INTEGER DEFAULT 0,  -- 是否有被接受的答案
                UNIQUE(source, post_id)
            )
        """)
        
        # 创建故障分析表（后续LLM分析结果）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fault_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,  -- 关联posts表的id
                is_real_fault INTEGER,  -- 是否为真实故障场景 (0/1)
                fault_component TEXT,  -- 故障组件 (HDFS/YARN/MapReduce等)
                fault_symptoms TEXT,  -- 故障症状描述
                error_logs TEXT,  -- 提取的错误日志
                root_cause TEXT,  -- 根本原因
                solution TEXT,  -- 解决方案
                environment_info TEXT,  -- 环境信息
                preliminary_category TEXT,  -- 初步分类
                analysis_notes TEXT,  -- 分析备注
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        """)
        
        # 创建故障类型映射表（最终分类结果）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fault_type_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                fault_type TEXT,  -- 故障类型名称
                confidence REAL DEFAULT 0.0,  -- 置信度
                keywords TEXT,  -- 关键词列表（JSON格式）
                mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        """)
        
        # 创建索引以提高查询性能
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_collected_at ON posts(collected_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fault_analysis_post_id ON fault_analysis(post_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fault_type_post_id ON fault_type_mapping(post_id)")
        
        self.conn.commit()
        print(f"[Database] 数据库初始化完成: {self.db_path}")
    
    def insert_post(self, post_data: Dict[str, Any]) -> int:
        """
        插入一条帖子记录
        
        Args:
            post_data: 帖子数据字典，包含以下字段：
                - source: 来源 ('stackoverflow' 或 'csdn')
                - post_id: 原始平台ID
                - title: 标题
                - content: 内容
                - tags: 标签列表（会被转换为JSON）
                - url: URL
                - author: 作者
                - created_at: 创建时间（字符串或datetime）
                - view_count: 浏览量
                - score: 分数
                - answer_count: 答案数
                - is_accepted: 是否有被接受的答案 (0/1)
        
        Returns:
            插入记录的ID
        """
        cursor = self.conn.cursor()
        
        # 处理tags（如果是列表，转换为JSON字符串）
        tags = post_data.get("tags", [])
        if isinstance(tags, list):
            tags = json.dumps(tags)
        elif tags is None:
            tags = "[]"
        
        # 处理created_at时间
        created_at = post_data.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif created_at is None:
            created_at = None
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO posts (
                    source, post_id, title, content, tags, url, author,
                    created_at, view_count, score, answer_count, is_accepted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data.get("source"),
                str(post_data.get("post_id")),
                post_data.get("title", ""),
                post_data.get("content", ""),
                tags,
                post_data.get("url", ""),
                post_data.get("author"),
                created_at,
                post_data.get("view_count", 0),
                post_data.get("score", 0),
                post_data.get("answer_count", 0),
                post_data.get("is_accepted", 0)
            ))
            
            self.conn.commit()
            
            # 获取插入的ID
            if cursor.rowcount > 0:
                post_db_id = cursor.lastrowid
                print(f"[Database] 插入帖子成功: {post_data.get('title', '')[:50]}... (ID: {post_db_id})")
                return post_db_id
            else:
                # 如果因为UNIQUE约束未插入，查找现有记录
                cursor.execute("""
                    SELECT id FROM posts WHERE source = ? AND post_id = ?
                """, (post_data.get("source"), str(post_data.get("post_id"))))
                row = cursor.fetchone()
                if row:
                    print(f"[Database] 帖子已存在，跳过: {post_data.get('title', '')[:50]}... (ID: {row['id']})")
                    return row['id']
                return 0
        except Exception as e:
            print(f"[Database] 插入帖子失败: {e}")
            self.conn.rollback()
            return 0
    
    def get_post_count(self, source: Optional[str] = None) -> int:
        """
        获取帖子总数
        
        Args:
            source: 可选，指定来源 ('stackoverflow' 或 'csdn')
        
        Returns:
            帖子数量
        """
        cursor = self.conn.cursor()
        if source:
            cursor.execute("SELECT COUNT(*) FROM posts WHERE source = ?", (source,))
        else:
            cursor.execute("SELECT COUNT(*) FROM posts")
        return cursor.fetchone()[0]
    
    def get_all_posts(self, source: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取所有帖子
        
        Args:
            source: 可选，指定来源
            limit: 可选，限制返回数量
        
        Returns:
            帖子列表
        """
        cursor = self.conn.cursor()
        query = "SELECT * FROM posts"
        params = []
        
        if source:
            query += " WHERE source = ?"
            params.append(source)
        
        query += " ORDER BY collected_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 转换为字典列表
        posts = []
        for row in rows:
            post = dict(row)
            # 解析tags JSON
            if post.get("tags"):
                try:
                    post["tags"] = json.loads(post["tags"])
                except:
                    post["tags"] = []
            posts.append(post)
        
        return posts
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("[Database] 数据库连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


if __name__ == "__main__":
    # 测试数据库功能
    db = FaultResearchDB("test_fault_research.db")
    
    # 测试插入
    test_post = {
        "source": "stackoverflow",
        "post_id": "12345",
        "title": "Test Post",
        "content": "This is a test post content",
        "tags": ["hadoop", "hdfs"],
        "url": "https://stackoverflow.com/questions/12345",
        "author": "test_user",
        "created_at": datetime.now(),
        "view_count": 100,
        "score": 5,
        "answer_count": 2,
        "is_accepted": 1
    }
    
    post_id = db.insert_post(test_post)
    print(f"插入的帖子ID: {post_id}")
    print(f"总帖子数: {db.get_post_count()}")
    
    # 清理测试数据库
    import os
    if os.path.exists("test_fault_research.db"):
        os.remove("test_fault_research.db")
        print("测试数据库已清理")
