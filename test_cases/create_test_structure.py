#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试用例目录结构和模板文件

使用方法：
    python test_cases/create_test_structure.py
"""

import os
import json
from datetime import datetime

# 导入 FAULT_TYPE_LIBRARY
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cl_agent.config import FAULT_TYPE_LIBRARY

# 测试用例根目录
TEST_CASES_ROOT = os.path.dirname(os.path.abspath(__file__))


def create_directory_structure():
    """创建所有故障类型的目录结构"""
    
    # 按 category 分组
    categories = {}
    for fault_id, fault_info in FAULT_TYPE_LIBRARY.items():
        category = fault_info["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append((fault_id, fault_info))
    
    # 创建目录和模板文件
    for category, faults in categories.items():
        category_dir = os.path.join(TEST_CASES_ROOT, category)
        os.makedirs(category_dir, exist_ok=True)
        
        for fault_id, fault_info in faults:
            fault_dir = os.path.join(category_dir, fault_id)
            os.makedirs(fault_dir, exist_ok=True)
            
            # 创建 case1 目录
            case1_dir = os.path.join(fault_dir, "case1")
            os.makedirs(case1_dir, exist_ok=True)
            
            # 创建 metadata.json
            metadata = {
                "fault_type": fault_id,
                "fault_name": fault_info["fault_type"],
                "category": category,
                "severity": fault_info["severity"],
                "description": f"{fault_info['fault_type']} 测试用例",
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "待填充",
                "affected_nodes": [],
                "expected_symptoms": fault_info["symptoms"],
                "keywords": fault_info["keywords"]
            }
            
            metadata_path = os.path.join(case1_dir, "metadata.json")
            if not os.path.exists(metadata_path):
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                print(f"✅ 创建: {metadata_path}")
            
            # 创建 ground_truth.json
            ground_truth = {
                "fault_type": fault_id,
                "fault_name": fault_info["fault_type"],
                "category": category,
                "severity": fault_info["severity"],
                "confidence": 0.9,
                "affected_nodes": [],
                "symptoms": fault_info["symptoms"],
                "root_cause": {
                    "primary_cause": fault_info["possible_causes"][0] if fault_info["possible_causes"] else "未知",
                    "secondary_causes": fault_info["possible_causes"][1:] if len(fault_info["possible_causes"]) > 1 else [],
                    "evidence": []
                },
                "recommended_actions": []
            }
            
            ground_truth_path = os.path.join(case1_dir, "ground_truth.json")
            if not os.path.exists(ground_truth_path):
                with open(ground_truth_path, "w", encoding="utf-8") as f:
                    json.dump(ground_truth, f, ensure_ascii=False, indent=2)
                print(f"✅ 创建: {ground_truth_path}")
            
            # 创建 cluster_logs.txt 占位文件
            logs_path = os.path.join(case1_dir, "cluster_logs.txt")
            if not os.path.exists(logs_path):
                with open(logs_path, "w", encoding="utf-8") as f:
                    f.write(f"# {fault_info['fault_type']} 测试用例日志\n")
                    f.write(f"# 请将实际的集群日志内容粘贴到这里\n")
                    f.write(f"# 格式应与 result/cluster_logs_*.txt 相同\n\n")
                print(f"✅ 创建: {logs_path}")
            
            # 创建 README.md
            readme_path = os.path.join(fault_dir, "README.md")
            if not os.path.exists(readme_path):
                readme_content = f"""# {fault_info['fault_type']} 故障测试用例

## 故障描述

{fault_info['fault_type']} 故障的测试用例。

## 故障类型信息

- **故障类型ID**: `{fault_id}`
- **故障名称**: {fault_info['fault_type']}
- **类别**: {category.upper()}
- **严重程度**: {fault_info['severity']}
- **经典性评分**: {fault_info.get('classic_score', 'N/A')}/5

## 典型症状

"""
                for symptom in fault_info["symptoms"]:
                    readme_content += f"- {symptom}\n"
                
                readme_content += "\n## 可能原因\n\n"
                for cause in fault_info["possible_causes"]:
                    readme_content += f"- {cause}\n"
                
                readme_content += "\n## 检测方法\n\n"
                for method in fault_info["detection_methods"]:
                    readme_content += f"- {method}\n"
                
                readme_content += "\n## 测试用例\n\n"
                readme_content += "### case1: 待填充\n"
                readme_content += "- **场景**: 待描述\n"
                readme_content += "- **日志文件**: `case1/cluster_logs.txt`\n"
                readme_content += "- **元数据**: `case1/metadata.json`\n"
                readme_content += "- **标准答案**: `case1/ground_truth.json`\n"
                
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(readme_content)
                print(f"✅ 创建: {readme_path}")
    
    print("\n" + "="*70)
    print("✅ 目录结构创建完成！")
    print("="*70)
    print("\n下一步：")
    print("1. 将实际的集群日志复制到各 case1/cluster_logs.txt")
    print("2. 根据实际情况更新 metadata.json 和 ground_truth.json")
    print("3. 可以创建更多测试用例（case2, case3, ...）")


if __name__ == "__main__":
    print("="*70)
    print("创建测试用例目录结构")
    print("="*70)
    print()
    create_directory_structure()
