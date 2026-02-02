#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM批量分析模块
使用LLM分析收集的帖子，筛选真实故障场景并提取关键信息
"""

import os
import sys
import time
import html
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mutli_agent.llm_client import LLMClient

# 导入数据库模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_collection.database import FaultResearchDB


class LLMAnalyzer:
    """LLM批量分析器"""
    
    def __init__(self, db: FaultResearchDB, llm_client: LLMClient, batch_size: int = 10):
        """
        初始化分析器
        
        Args:
            db: 数据库实例
            llm_client: LLM客户端
            batch_size: 批处理大小（每次分析的帖子数）
        """
        self.db = db
        self.llm_client = llm_client
        self.batch_size = batch_size
    
    def _clean_html_content(self, content: str) -> str:
        """清理HTML内容，提取纯文本"""
        if not content:
            return ""
        
        # 移除HTML实体
        content = html.unescape(content)
        
        # 简单移除HTML标签（不完美，但够用）
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余空白
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _build_analysis_prompt(self, post: Dict[str, Any]) -> str:
        """构建分析提示词"""
        title = post.get('title', '')
        content = self._clean_html_content(post.get('content', ''))
        tags = ', '.join(post.get('tags', []))
        url = post.get('url', '')
        
        # 限制内容长度（避免token过多）
        if len(content) > 2000:
            content = content[:2000] + "..."
        
        prompt = f"""请分析以下Stack Overflow帖子，判断它是否描述了一个真实的Hadoop集群故障场景。

帖子标题: {title}
标签: {tags}
URL: {url}

帖子内容:
{content}

请按照以下JSON格式回答：
{{
    "is_real_fault": true/false,  // 是否为真实故障场景（排除理论问题、配置教程、概念性问题等）
    "fault_component": "HDFS/YARN/MapReduce/Network/Generic/Unknown",  // 故障组件
    "fault_symptoms": "简要描述故障症状",  // 故障症状
    "error_logs": "提取的错误日志或异常信息（如果有）",  // 错误日志
    "root_cause": "推测的根本原因（如果不确定可写'未知'）",  // 根本原因
    "solution": "解决方案或建议（如果有）",  // 解决方案
    "environment_info": "环境信息（Hadoop版本、部署方式等，如果有）",  // 环境信息
    "preliminary_category": "初步分类（如：namenode_down, datanode_down, disk_full等，如果不确定可写'unknown'）",  // 初步分类
    "confidence": 0.0-1.0,  // 分析的置信度
    "analysis_notes": "其他备注信息"  // 分析备注
}}

注意：
1. 只将明确的故障场景标记为 is_real_fault=true
2. 如果帖子只是询问概念、配置方法、使用教程等，应标记为 is_real_fault=false
3. 尽量提取具体的错误日志和异常信息
4. 如果不确定某些字段，可以写"未知"或"不确定"
"""
        return prompt
    
    def analyze_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        分析单个帖子
        
        Args:
            post: 帖子数据字典
        
        Returns:
            分析结果字典，如果分析失败返回None
        """
        try:
            prompt = self._build_analysis_prompt(post)
            
            # 调用LLM
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt="你是一个专业的Hadoop集群故障分析专家，擅长从技术帖子中识别真实的故障场景。",
                temperature=0.1  # 低温度以保证一致性
            )
            
            # 解析JSON响应
            analysis_result = self._parse_llm_response(response)
            
            if analysis_result:
                # 保存到数据库
                self._save_analysis(post['id'], analysis_result)
                return analysis_result
            else:
                print(f"[Analyzer] 帖子 {post['id']} 分析结果解析失败")
                return None
                
        except Exception as e:
            print(f"[Analyzer] 分析帖子 {post.get('id', 'unknown')} 时出错: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM响应，提取JSON"""
        import json
        try:
            # 尝试直接解析JSON
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # 尝试从markdown代码块中提取
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 尝试提取第一个JSON对象
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            print(f"[Analyzer] 无法从响应中提取JSON: {response[:200]}")
            return None
            
        except Exception as e:
            print(f"[Analyzer] 解析响应失败: {e}")
            print(f"[Analyzer] 原始响应: {response[:500]}")
            return None
    
    def _save_analysis(self, post_id: int, analysis: Dict[str, Any]):
        """保存分析结果到数据库"""
        cursor = self.db.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO fault_analysis (
                    post_id, is_real_fault, fault_component, fault_symptoms,
                    error_logs, root_cause, solution, environment_info,
                    preliminary_category, analysis_notes, analyzed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_id,
                1 if analysis.get('is_real_fault') else 0,
                analysis.get('fault_component', 'Unknown'),
                analysis.get('fault_symptoms', ''),
                analysis.get('error_logs', ''),
                analysis.get('root_cause', ''),
                analysis.get('solution', ''),
                analysis.get('environment_info', ''),
                analysis.get('preliminary_category', 'unknown'),
                analysis.get('analysis_notes', ''),
                datetime.now().isoformat()
            ))
            
            self.db.conn.commit()
            print(f"[Analyzer] 已保存分析结果 (post_id: {post_id})")
            
        except Exception as e:
            print(f"[Analyzer] 保存分析结果失败: {e}")
            self.db.conn.rollback()
    
    def analyze_all_posts(
        self,
        source: Optional[str] = None,
        limit: Optional[int] = None,
        delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        批量分析所有帖子
        
        Args:
            source: 可选，指定来源（'stackoverflow' 或 'csdn'）
            limit: 可选，限制分析数量
            delay: 每次分析之间的延迟（秒）
        
        Returns:
            统计信息字典
        """
        print(f"\n[Analyzer] ===== 开始批量分析帖子 =====\n")
        
        # 获取待分析的帖子
        posts = self.db.get_all_posts(source=source, limit=limit)
        
        if not posts:
            print("[Analyzer] 没有找到待分析的帖子")
            return {"total": 0, "analyzed": 0, "failed": 0}
        
        print(f"[Analyzer] 找到 {len(posts)} 个帖子待分析")
        
        # 检查哪些已经分析过
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT post_id FROM fault_analysis")
        analyzed_post_ids = {row[0] for row in cursor.fetchall()}
        
        # 过滤出未分析的帖子
        unanalyzed_posts = [p for p in posts if p['id'] not in analyzed_post_ids]
        
        if not unanalyzed_posts:
            print("[Analyzer] 所有帖子都已分析过")
            return {"total": len(posts), "analyzed": len(posts), "failed": 0}
        
        print(f"[Analyzer] 其中 {len(unanalyzed_posts)} 个未分析，将开始分析...\n")
        
        # 批量分析
        analyzed_count = 0
        failed_count = 0
        
        for i, post in enumerate(unanalyzed_posts, 1):
            print(f"[Analyzer] [{i}/{len(unanalyzed_posts)}] 分析帖子: {post['title'][:60]}...")
            
            result = self.analyze_post(post)
            
            if result:
                analyzed_count += 1
                if result.get('is_real_fault'):
                    print(f"  ✓ 识别为真实故障场景 ({result.get('fault_component', 'Unknown')})")
                else:
                    print(f"  - 非故障场景")
            else:
                failed_count += 1
                print(f"  ✗ 分析失败")
            
            # 延迟以避免API限制
            if i < len(unanalyzed_posts):
                time.sleep(delay)
        
        print(f"\n[Analyzer] ===== 分析完成 =====\n")
        print(f"[Analyzer] 总计: {len(posts)} 个帖子")
        print(f"[Analyzer] 已分析: {analyzed_count} 个")
        print(f"[Analyzer] 失败: {failed_count} 个")
        
        return {
            "total": len(posts),
            "analyzed": analyzed_count,
            "failed": failed_count
        }
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        cursor = self.db.conn.cursor()
        
        # 总分析数
        cursor.execute("SELECT COUNT(*) FROM fault_analysis")
        total_analyzed = cursor.fetchone()[0]
        
        # 真实故障数
        cursor.execute("SELECT COUNT(*) FROM fault_analysis WHERE is_real_fault = 1")
        real_faults = cursor.fetchone()[0]
        
        # 按组件统计
        cursor.execute("""
            SELECT fault_component, COUNT(*) as count
            FROM fault_analysis
            WHERE is_real_fault = 1
            GROUP BY fault_component
            ORDER BY count DESC
        """)
        component_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按初步分类统计
        cursor.execute("""
            SELECT preliminary_category, COUNT(*) as count
            FROM fault_analysis
            WHERE is_real_fault = 1
            GROUP BY preliminary_category
            ORDER BY count DESC
        """)
        category_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_analyzed": total_analyzed,
            "real_faults": real_faults,
            "non_faults": total_analyzed - real_faults,
            "component_stats": component_stats,
            "category_stats": category_stats
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM批量分析帖子")
    parser.add_argument("--db", default="fault_research.db", help="数据库文件路径")
    parser.add_argument("--model", default="qwen-8b", help="LLM模型名称")
    parser.add_argument("--limit", type=int, help="限制分析数量")
    parser.add_argument("--delay", type=float, default=1.0, help="分析间隔（秒）")
    parser.add_argument("--source", choices=["stackoverflow", "csdn"], help="指定来源")
    
    args = parser.parse_args()
    
    # 初始化数据库
    db = FaultResearchDB(args.db)
    
    # 初始化LLM客户端
    llm_client = LLMClient(model_name=args.model)
    
    # 创建分析器
    analyzer = LLMAnalyzer(db, llm_client)
    
    # 开始分析
    stats = analyzer.analyze_all_posts(
        source=args.source,
        limit=args.limit,
        delay=args.delay
    )
    
    # 显示统计信息
    print("\n" + "="*80)
    print("【分析统计】")
    analysis_stats = analyzer.get_analysis_statistics()
    print(f"总分析数: {analysis_stats['total_analyzed']}")
    print(f"真实故障: {analysis_stats['real_faults']}")
    print(f"非故障场景: {analysis_stats['non_faults']}")
    print(f"\n按组件统计:")
    for component, count in analysis_stats['component_stats'].items():
        print(f"  {component}: {count}")
    print(f"\n按分类统计:")
    for category, count in list(analysis_stats['category_stats'].items())[:10]:
        print(f"  {category}: {count}")
    
    db.close()


if __name__ == "__main__":
    main()
