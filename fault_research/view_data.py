#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查看工具
方便查看已收集的帖子数据
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_collection'))
from database import FaultResearchDB
import html


def print_post(post, show_content=False):
    """打印帖子信息"""
    print(f"\n{'='*80}")
    print(f"ID: {post['id']}")
    print(f"标题: {post['title']}")
    print(f"来源: {post['source']}")
    print(f"原始ID: {post['post_id']}")
    print(f"标签: {post.get('tags', [])}")
    print(f"作者: {post.get('author', 'Unknown')}")
    print(f"创建时间: {post.get('created_at', 'Unknown')}")
    print(f"收集时间: {post.get('collected_at', 'Unknown')}")
    print(f"分数: {post.get('score', 0)}")
    print(f"回答数: {post.get('answer_count', 0)}")
    print(f"浏览量: {post.get('view_count', 0)}")
    print(f"有被接受答案: {'是' if post.get('is_accepted') else '否'}")
    print(f"URL: {post.get('url', '')}")
    
    if show_content and post.get('content'):
        # 简单清理HTML标签（只显示前500字符）
        content = post['content']
        # 移除HTML实体
        content = html.unescape(content)
        # 简单移除HTML标签（不完美，但够用）
        import re
        content = re.sub(r'<[^>]+>', '', content)
        content = content.strip()
        
        if len(content) > 500:
            content = content[:500] + "..."
        print(f"\n内容预览:\n{content}")


def main():
    """主函数"""
    db_path = "fault_research.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    db = FaultResearchDB(db_path)
    
    print("="*80)
    print("故障研究数据库查看工具")
    print("="*80)
    
    # 统计信息
    print("\n【统计信息】")
    total = db.get_post_count()
    so_count = db.get_post_count("stackoverflow")
    csdn_count = db.get_post_count("csdn")
    
    print(f"总帖子数: {total}")
    print(f"  - Stack Overflow: {so_count}")
    print(f"  - CSDN: {csdn_count}")
    
    if total == 0:
        print("\n数据库为空，没有收集到任何帖子。")
        db.close()
        return
    
    # 交互式菜单
    while True:
        print("\n" + "="*80)
        print("【菜单】")
        print("1. 查看所有帖子列表（简要）")
        print("2. 查看所有帖子列表（详细）")
        print("3. 查看指定ID的帖子详情")
        print("4. 搜索帖子（按标题关键词）")
        print("5. 查看高分帖子（分数>=10）")
        print("6. 查看故障相关帖子（标题包含error/exception/failure等）")
        print("7. 查看有被接受答案的帖子")
        print("8. 按标签筛选")
        print("0. 退出")
        
        choice = input("\n请选择操作 (0-8): ").strip()
        
        if choice == "0":
            print("\n再见！")
            break
        
        elif choice == "1":
            print("\n【所有帖子列表（简要）】")
            posts = db.get_all_posts()
            for i, post in enumerate(posts, 1):
                tags_str = ", ".join(post.get('tags', []))
                print(f"{i:3d}. [{tags_str:20s}] {post['title'][:60]:60s} | 分数:{post.get('score', 0):3d} | 回答:{post.get('answer_count', 0):2d}")
        
        elif choice == "2":
            print("\n【所有帖子列表（详细）】")
            posts = db.get_all_posts()
            for post in posts:
                print_post(post, show_content=False)
        
        elif choice == "3":
            post_id = input("请输入帖子ID: ").strip()
            try:
                post_id = int(post_id)
                posts = db.get_all_posts()
                post = next((p for p in posts if p['id'] == post_id), None)
                if post:
                    print_post(post, show_content=True)
                else:
                    print(f"未找到ID为 {post_id} 的帖子")
            except ValueError:
                print("无效的ID")
        
        elif choice == "4":
            keyword = input("请输入搜索关键词: ").strip().lower()
            if keyword:
                posts = db.get_all_posts()
                matched = [p for p in posts if keyword in p['title'].lower() or (p.get('content', '').lower() and keyword in p['content'].lower())]
                print(f"\n找到 {len(matched)} 个匹配的帖子:")
                for i, post in enumerate(matched, 1):
                    print(f"{i:3d}. {post['title'][:70]}")
                    print(f"     URL: {post.get('url', '')}")
            else:
                print("关键词不能为空")
        
        elif choice == "5":
            print("\n【高分帖子（分数>=10）】")
            posts = db.get_all_posts()
            high_score = [p for p in posts if p.get('score', 0) >= 10]
            high_score.sort(key=lambda x: x.get('score', 0), reverse=True)
            for i, post in enumerate(high_score, 1):
                print(f"{i:3d}. 分数:{post.get('score', 0):3d} | {post['title'][:65]}")
                print(f"     URL: {post.get('url', '')}")
        
        elif choice == "6":
            print("\n【故障相关帖子】")
            posts = db.get_all_posts()
            keywords = ['error', 'exception', 'failure', 'issue', 'problem', 'corrupt', 'down', 'crash', 'timeout', 'dead', 'missing']
            fault_posts = [p for p in posts if any(kw in p['title'].lower() for kw in keywords)]
            print(f"找到 {len(fault_posts)} 个可能的故障相关帖子:")
            for i, post in enumerate(fault_posts, 1):
                print(f"{i:3d}. {post['title'][:70]}")
                print(f"     URL: {post.get('url', '')}")
        
        elif choice == "7":
            print("\n【有被接受答案的帖子】")
            posts = db.get_all_posts()
            accepted = [p for p in posts if p.get('is_accepted')]
            print(f"找到 {len(accepted)} 个有被接受答案的帖子:")
            for i, post in enumerate(accepted, 1):
                print(f"{i:3d}. {post['title'][:70]}")
                print(f"     URL: {post.get('url', '')}")
        
        elif choice == "8":
            print("\n【按标签筛选】")
            print("可用标签: hadoop, hdfs, yarn, mapreduce, apache-hadoop, apache-spark, hive, etc.")
            tag = input("请输入标签: ").strip().lower()
            if tag:
                posts = db.get_all_posts()
                matched = [p for p in posts if tag in [t.lower() for t in p.get('tags', [])]]
                print(f"\n找到 {len(matched)} 个包含标签 '{tag}' 的帖子:")
                for i, post in enumerate(matched, 1):
                    tags_str = ", ".join(post.get('tags', []))
                    print(f"{i:3d}. [{tags_str}] {post['title'][:60]}")
            else:
                print("标签不能为空")
        
        else:
            print("无效的选择，请重新输入")
    
    db.close()


if __name__ == "__main__":
    main()
