# 故障研究数据收集与分析系统

## 项目目标

通过收集 Stack Overflow 和 CSDN 上的真实 Hadoop 故障案例，使用 LLM 进行批量分析，重新构建基于实际数据的故障类型分类体系。

## 目录结构

```
fault_research/
├── data_collection/              # 数据收集模块
│   ├── __init__.py
│   ├── database.py               # 数据库操作
│   ├── stackoverflow_collector.py # Stack Overflow 收集器
│   └── csdn_collector.py         # CSDN 收集器（待实现）
├── data_analysis/                # 数据分析模块
│   ├── __init__.py
│   ├── llm_analyzer.py           # LLM批量分析
│   ├── pattern_extractor.py     # 模式提取（待实现）
│   └── cluster_analyzer.py      # 聚类分析（待实现）
├── statistics/                   # 统计分析模块
│   ├── frequency_analyzer.py    # 频率统计（待实现）
│   └── visualization.py         # 可视化（待实现）
├── fault_library_builder/        # 故障类型库构建模块
│   └── rebuild_fault_types.py   # 重构故障类型库（待实现）
├── fault_research.db            # SQLite 数据库文件
├── view_data.py                 # 数据库查看工具
└── README.md                    # 本文件
```

## 数据库结构

### posts 表
存储从各个平台收集的原始帖子数据：
- `id`: 自增主键
- `source`: 来源平台（'stackoverflow' 或 'csdn'）
- `post_id`: 原始平台的帖子ID
- `title`: 标题
- `content`: 内容（HTML格式）
- `tags`: 标签（JSON格式）
- `url`: 帖子URL
- `author`: 作者
- `created_at`: 帖子创建时间
- `collected_at`: 收集时间
- `view_count`: 浏览量
- `score`: 分数/点赞数
- `answer_count`: 回答数
- `is_accepted`: 是否有被接受的答案

### fault_analysis 表
存储LLM分析结果：
- `post_id`: 关联的帖子ID
- `is_real_fault`: 是否为真实故障场景 (0/1)
- `fault_component`: 故障组件 (HDFS/YARN/MapReduce等)
- `fault_symptoms`: 故障症状描述
- `error_logs`: 提取的错误日志
- `root_cause`: 根本原因
- `solution`: 解决方案
- `environment_info`: 环境信息
- `preliminary_category`: 初步分类
- `analysis_notes`: 分析备注
- `analyzed_at`: 分析时间

### fault_type_mapping 表（待使用）
存储最终故障类型映射：
- `post_id`: 关联的帖子ID
- `fault_type`: 故障类型名称
- `confidence`: 置信度
- `keywords`: 关键词列表

## 使用方法

### 阶段一：数据收集

#### 1. 收集 Stack Overflow 帖子

```bash
cd fault_research
python3 data_collection/stackoverflow_collector.py
```

这会：
- 使用 Hadoop 相关标签搜索（hadoop, hdfs, mapreduce等）
- 使用关键词搜索（hadoop error, hdfs exception等）
- 自动去重
- 按分数排序，优先收集高质量帖子
- 保存到 `fault_research.db` 数据库

#### 2. 查看收集的帖子

```bash
python3 view_data.py
```

这会启动一个交互式菜单，可以：
- 查看所有帖子列表（简要/详细）
- 查看指定ID的帖子详情
- 搜索帖子（按标题关键词）
- 查看高分帖子
- 查看故障相关帖子
- 按标签筛选

### 阶段二：LLM批量分析

#### 使用LLM分析帖子

```bash
# 分析所有帖子（使用默认模型 qwen-8b）
python3 data_analysis/llm_analyzer.py

# 指定模型
python3 data_analysis/llm_analyzer.py --model gpt-4o

# 限制分析数量（测试用）
python3 data_analysis/llm_analyzer.py --limit 10

# 指定来源
python3 data_analysis/llm_analyzer.py --source stackoverflow

# 调整分析间隔（避免API限制）
python3 data_analysis/llm_analyzer.py --delay 2.0
```

分析器会：
1. 读取数据库中的帖子
2. 使用LLM判断是否为真实故障场景
3. 提取故障症状、错误日志、根本原因、解决方案等
4. 进行初步分类
5. 保存分析结果到 `fault_analysis` 表

#### 查看分析结果

```python
from data_collection.database import FaultResearchDB

db = FaultResearchDB("fault_research.db")
cursor = db.conn.cursor()

# 查看真实故障场景
cursor.execute("""
    SELECT p.title, a.fault_component, a.preliminary_category
    FROM posts p
    JOIN fault_analysis a ON p.id = a.post_id
    WHERE a.is_real_fault = 1
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"{row[0]} - {row[1]} - {row[2]}")

db.close()
```

## 当前状态

### 已完成
- ✅ 数据库模块（`data_collection/database.py`）
- ✅ Stack Overflow 收集器（`data_collection/stackoverflow_collector.py`）
- ✅ 已收集 500 个 Stack Overflow 帖子
- ✅ LLM批量分析模块（`data_analysis/llm_analyzer.py`）
- ✅ 数据库查看工具（`view_data.py`）

### 待实现
- ⏳ CSDN 收集器（`data_collection/csdn_collector.py`）
- ⏳ 模式提取模块（`data_analysis/pattern_extractor.py`）
- ⏳ 聚类分析模块（`data_analysis/cluster_analyzer.py`）
- ⏳ 频率统计模块（`statistics/frequency_analyzer.py`）
- ⏳ 可视化模块（`statistics/visualization.py`）
- ⏳ 故障类型库重构模块（`fault_library_builder/rebuild_fault_types.py`）

## 注意事项

1. **API 限制**：
   - Stack Overflow API 有 rate limit（每30秒300个请求），代码已内置延迟处理
   - LLM API 也有 rate limit，建议设置适当的 `--delay` 参数

2. **数据质量**：
   - 收集的帖子可能包含非故障场景（如配置问题、使用教程等）
   - LLM分析器会自动筛选，只保留真实故障场景

3. **数据库文件**：
   - `fault_research.db` 会随着收集和分析自动增长
   - 建议定期备份

4. **LLM模型选择**：
   - `qwen-8b`: 本地模型，免费但可能分析质量较低
   - `gpt-4o`: 需要API密钥，分析质量高但成本较高
   - `deepseek-r1`: 需要API密钥，性价比高

## 下一步计划

1. **阶段三**：模式提取和聚类分析，识别相似故障模式
2. **阶段四**：统计分析，评估故障频率和严重性
3. **阶段五**：基于统计结果重构故障类型库

## 快速开始示例

```bash
# 1. 收集数据（如果还没有）
cd fault_research
python3 data_collection/stackoverflow_collector.py

# 2. 查看收集的数据
python3 view_data.py

# 3. 使用LLM分析（先测试10个）
python3 data_analysis/llm_analyzer.py --limit 10 --delay 1.0

# 4. 如果测试成功，分析全部
python3 data_analysis/llm_analyzer.py --delay 1.0
```
