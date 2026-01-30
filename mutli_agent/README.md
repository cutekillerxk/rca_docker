# 多智能体框架

基于Role Token的多专家会诊系统，用于Hadoop集群故障诊断。

## 架构设计

### 核心组件

1. **BaseAgent** (`base.py`)
   - Agent抽象基类
   - 极简设计：只包含prompt构建、LLM调用、输出解析
   - 支持工具注入和Role Token

2. **LLMClient** (`llm_client.py`)
   - LLM调用封装
   - 替代LangChain，直接调用vLLM/OpenAI API
   - 支持Role Token注入

3. **FaultClassifierAgent** (`agents/classifier.py`)
   - 故障分类Agent
   - 无工具，只做分类任务
   - 输出结构化JSON

4. **ExpertAgents** (`agents/experts/`)
   - HDFS专家Agent：处理HDFS相关故障
   - 可以调用工具进行深度诊断
   - 输出对话式诊断文本

5. **DiscussionAgent** (`agents/discussion.py`)
   - 综合多个专家的诊断结果
   - 识别一致性/冲突
   - 生成最终诊断报告（JSON格式）

6. **FaultOrchestrator** (`orchestrator.py`)
   - 总协调器
   - 管理整个诊断流程：
     1. 收集全局上下文
     2. 分类
     3. 选择相关专家
     4. 并行调用专家
     5. Discussion Agent综合
     6. 返回结果

### 工具模块

- **ContextCollector** (`utils/context_collector.py`): 全局上下文收集器
- **ExpertSelector** (`utils/expert_selector.py`): 专家选择器
- **ToolAdapter** (`utils/tool_adapter.py`): 工具适配器（将LangChain工具转换为普通函数）

## 使用示例

```python
from mutli_agent import FaultOrchestrator, LLMClient

# 初始化LLM客户端
llm_client = LLMClient(model_name="qwen-8b")

# 创建协调器
orchestrator = FaultOrchestrator(llm_client, model_name="qwen-8b")

# 执行诊断
user_input = "查看集群状态，分析是否有故障"
result = orchestrator.diagnose(user_input)

# 查看结果
print("分类结果:", result["classification"])
print("专家诊断:", result["expert_diagnoses"])
print("综合讨论:", result["discussion"])
```

## 目录结构

```
mutli_agent/
├── __init__.py                 # 包初始化
├── base.py                     # BaseAgent抽象基类
├── llm_client.py              # LLM调用封装
├── schemas.py                 # 输出格式Schema定义
├── orchestrator.py            # 总协调器
├── agents/
│   ├── __init__.py
│   ├── classifier.py          # 分类Agent
│   ├── discussion.py          # Discussion Agent
│   └── experts/
│       ├── __init__.py
│       └── hdfs_expert.py    # HDFS专家Agent
└── utils/
    ├── __init__.py
    ├── context_collector.py   # 全局上下文收集器
    ├── expert_selector.py     # 专家选择器
    └── tool_adapter.py       # 工具适配器
```

## 设计特点

1. **完全可控**：每一步都是显式的，便于追踪和调试
2. **Role Token支持**：支持Role Token微调策略
3. **全局上下文注入**：解决联动错误问题
4. **多专家会诊**：并行调用多个专家，综合诊断结果
5. **工具系统集成**：复用现有工具系统，通过适配器转换

## 与现有系统的集成

- 复用 `cl_agent/tools/tools.py` 中的工具函数
- 复用 `cl_agent/config.py` 中的配置
- 复用 `cl_agent/cluster_context.py` 中的集群上下文信息
- 复用 `cl_agent/log_reader.py` 和 `cl_agent/monitor_collector.py` 的功能

## 后续扩展

- 添加更多专家Agent（YARN、MapReduce、Network等）
- 实现工具调用循环（如果需要）
- 添加缓存机制（提高性能）
- 添加异步支持（提高并发性能）
