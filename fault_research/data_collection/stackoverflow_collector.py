#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stack Overflow 帖子收集器
使用 Stack Exchange API 收集 Hadoop 相关的故障帖子
"""

import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from .database import FaultResearchDB


class StackOverflowCollector:
    """Stack Overflow 帖子收集器"""
    
    BASE_URL = "https://api.stackexchange.com/2.3"
    
    # Hadoop 相关标签和关键词
    HADOOP_TAGS = [
        "hadoop",
        "hdfs",
        "yarn",
        "mapreduce",
        "apache-hadoop"
    ]
    
    SEARCH_KEYWORDS = [
        "hadoop error",
        "hadoop exception",
        "hadoop failure",
        "hdfs error",
        "hdfs exception",
        "namenode error",
        "datanode error",
        "yarn error",
        "mapreduce error",
        "hadoop issue"
    ]
    
    def __init__(self, db: FaultResearchDB, delay: float = 0.1):
        """
        初始化收集器
        
        Args:
            db: 数据库实例
            delay: API 请求之间的延迟（秒），避免触发 rate limit
        """
        self.db = db
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Hadoop-Fault-Research/1.0"
        })
    
    def search_questions(self, 
                        query: Optional[str] = None,
                        tagged: Optional[List[str]] = None,
                        pages: int = 1,
                        page_size: int = 50) -> List[Dict[str, Any]]:
        """
        搜索问题
        
        Args:
            query: 搜索关键词
            tagged: 标签列表
            pages: 要获取的页数
            page_size: 每页大小（最大100）
        
        Returns:
            问题列表
        """
        all_questions = []
        
        for page in range(1, pages + 1):
            params = {
                "order": "desc",
                "sort": "relevance",  # 按相关性排序
                "site": "stackoverflow",
                "pagesize": min(page_size, 100),  # API限制最大100
                "page": page,
                "filter": "withbody"  # 包含问题正文
            }
            
            if query:
                params["q"] = query
            
            if tagged:
                params["tagged"] = ";".join(tagged)
            
            try:
                print(f"[Collector] 正在获取第 {page} 页...")
                response = self.session.get(
                    f"{self.BASE_URL}/search/advanced",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                
                if "items" not in data:
                    print(f"[Collector] 第 {page} 页无数据")
                    break
                
                questions = data["items"]
                all_questions.extend(questions)
                
                print(f"[Collector] 第 {page} 页获取到 {len(questions)} 个问题")
                
                # 检查是否还有更多页面
                if not data.get("has_more", False):
                    print(f"[Collector] 已获取所有可用页面")
                    break
                
                # 检查 rate limit
                if "quota_remaining" in data:
                    remaining = data["quota_remaining"]
                    print(f"[Collector] API 配额剩余: {remaining}")
                    if remaining < 10:
                        print("[Collector] ⚠️  API 配额即将用完，暂停收集")
                        break
                
                # 延迟以避免触发 rate limit
                time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                print(f"[Collector] 请求失败: {e}")
                break
            except Exception as e:
                print(f"[Collector] 处理失败: {e}")
                break
        
        return all_questions
    
    def get_question_details(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        获取问题的详细信息（包括答案）
        
        Args:
            question_id: 问题ID
        
        Returns:
            问题详情字典
        """
        params = {
            "order": "desc",
            "sort": "votes",
            "site": "stackoverflow",
            "filter": "withbody"
        }
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/questions/{question_id}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                return data["items"][0]
            return None
        except Exception as e:
            print(f"[Collector] 获取问题详情失败 (ID: {question_id}): {e}")
            return None
    
    def parse_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析问题数据，转换为数据库格式
        
        Args:
            question: Stack Overflow API 返回的问题数据
        
        Returns:
            标准化的帖子数据字典
        """
        # 提取标签
        tags = question.get("tags", [])
        
        # 提取内容（HTML格式，包含在body字段中）
        content = question.get("body", "")
        
        # 提取作者信息
        owner = question.get("owner", {})
        author = owner.get("display_name", "Unknown")
        
        # 提取时间（Unix时间戳）
        created_timestamp = question.get("creation_date", 0)
        created_at = datetime.fromtimestamp(created_timestamp) if created_timestamp else None
        
        # 检查是否有被接受的答案
        is_accepted = 1 if question.get("accepted_answer_id") else 0
        
        post_data = {
            "source": "stackoverflow",
            "post_id": str(question.get("question_id", "")),
            "title": question.get("title", ""),
            "content": content,
            "tags": tags,
            "url": question.get("link", ""),
            "author": author,
            "created_at": created_at,
            "view_count": question.get("view_count", 0),
            "score": question.get("score", 0),
            "answer_count": question.get("answer_count", 0),
            "is_accepted": is_accepted
        }
        
        return post_data
    
    def collect_posts(self, target_count: int = 500) -> int:
        """
        收集指定数量的帖子
        
        Args:
            target_count: 目标收集数量
        
        Returns:
            实际收集的数量
        """
        collected_count = 0
        all_questions = []
        
        # 策略1: 使用标签搜索
        print(f"\n[Collector] ===== 开始收集 Stack Overflow 帖子 (目标: {target_count} 个) =====\n")
        print("[Collector] 策略1: 使用 Hadoop 相关标签搜索...")
        
        # 增加每个标签的页数以获取更多帖子
        pages_per_tag = max(5, target_count // (len(self.HADOOP_TAGS) * 30))
        print(f"[Collector] 每个标签将获取 {pages_per_tag} 页（每页最多30个）")
        
        for tag in self.HADOOP_TAGS:
            if len(all_questions) >= target_count * 1.5:  # 收集更多以便筛选
                break
            
            print(f"\n[Collector] 搜索标签: {tag}")
            questions = self.search_questions(tagged=[tag], pages=pages_per_tag, page_size=30)
            
            # 去重（基于question_id）
            existing_ids = {q.get("question_id") for q in all_questions}
            new_questions = [q for q in questions if q.get("question_id") not in existing_ids]
            all_questions.extend(new_questions)
            
            print(f"[Collector] 标签 '{tag}' 获取到 {len(new_questions)} 个新问题（累计: {len(all_questions)}）")
            time.sleep(self.delay * 2)  # 标签搜索之间稍长延迟
        
        # 策略2: 使用关键词搜索
        if len(all_questions) < target_count * 1.2:
            print(f"\n[Collector] 策略2: 使用关键词搜索...")
            
            # 使用更多关键词，每关键词获取更多页
            pages_per_keyword = max(3, (target_count - len(all_questions)) // (len(self.SEARCH_KEYWORDS) * 20))
            
            for keyword in self.SEARCH_KEYWORDS:
                if len(all_questions) >= target_count * 1.5:
                    break
                
                print(f"\n[Collector] 搜索关键词: {keyword}")
                questions = self.search_questions(query=keyword, pages=pages_per_keyword, page_size=30)
                
                # 去重
                existing_ids = {q.get("question_id") for q in all_questions}
                new_questions = [q for q in questions if q.get("question_id") not in existing_ids]
                all_questions.extend(new_questions)
                
                print(f"[Collector] 关键词 '{keyword}' 获取到 {len(new_questions)} 个新问题（累计: {len(all_questions)}）")
                time.sleep(self.delay * 2)
        
        # 去重并排序（按相关性/分数）
        print(f"\n[Collector] 去重后共有 {len(all_questions)} 个问题")
        
        # 按分数排序，优先收集高分问题（可能更有价值）
        all_questions.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 保存到数据库
        print(f"\n[Collector] 开始保存到数据库...")
        for question in all_questions[:target_count]:
            try:
                post_data = self.parse_question(question)
                post_id = self.db.insert_post(post_data)
                if post_id > 0:
                    collected_count += 1
                time.sleep(0.05)  # 数据库操作之间的小延迟
            except Exception as e:
                print(f"[Collector] 处理问题失败: {e}")
                continue
        
        print(f"\n[Collector] ===== 收集完成 =====\n")
        print(f"[Collector] 成功收集并保存 {collected_count} 个帖子")
        
        return collected_count


def main():
    """主函数"""
    # 创建数据库
    db = FaultResearchDB("fault_research.db")
    
    # 检查已有帖子数
    existing_count = db.get_post_count("stackoverflow")
    print(f"[Info] 数据库中已有 {existing_count} 个 Stack Overflow 帖子")
    
    # 创建收集器
    collector = StackOverflowCollector(db, delay=0.2)
    
    # 收集500个帖子（如果已有，会跳过重复的）
    target_count = 500
    collected = collector.collect_posts(target_count=target_count)
    
    # 显示统计信息
    print(f"\n[统计] 数据库中共有 {db.get_post_count()} 个帖子")
    print(f"[统计] 本次收集了 {collected} 个新帖子")
    
    # 显示最近收集的帖子
    print("\n[最近收集的帖子]")
    recent_posts = db.get_all_posts(source="stackoverflow", limit=5)
    for i, post in enumerate(recent_posts, 1):
        print(f"{i}. [{post['tags']}] {post['title'][:60]}...")
        print(f"   URL: {post['url']}")
        print(f"   分数: {post['score']}, 回答数: {post['answer_count']}, 浏览量: {post['view_count']}")
        print()
    
    db.close()


if __name__ == "__main__":
    main()
