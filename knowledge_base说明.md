# Knowledge Base 函数详细讲解文档

本文档详细讲解 `knowledge_base.py` 中的两个主要函数及其所有被调用的函数，采用递归讲解方式，适合有其他语言基础但未学过 Python 的读者。

---

## 函数 1：`search_diagnosis_knowledge` - 搜索诊断知识

### 函数定义（第 329-334 行）

```python
def search_diagnosis_knowledge(
    query: str,
    expert_type: str = "all",
    top_k: int = 3,
    score_threshold: float = 0.4
) -> str:
```

**解释：**
- `def`：定义函数（类似其他语言的 `function`）
- `query: str`：参数 `query` 是字符串类型（类型提示，可选）
- `expert_type: str = "all"`：参数 `expert_type` 默认值为 `"all"`（类似其他语言的默认参数）
- `top_k: int = 3`：参数 `top_k` 默认值为 3
- `score_threshold: float = 0.4`：参数 `score_threshold` 默认值为 0.4
- `-> str`：返回字符串类型（返回类型提示）

**对比其他语言：**
```javascript
// JavaScript 类似写法
function searchDiagnosisKnowledge(query, expertType = "all", topK = 3, scoreThreshold = 0.4) {
    // ...
}
```

### 第 347 行：获取知识库管理器

```python
kb_manager = get_kb_manager()
```

**调用函数：`get_kb_manager()`（第 321-326 行）**

```python
def get_kb_manager() -> KnowledgeBaseManager:
    """获取全局知识库管理器"""
    global _kb_manager
    if _kb_manager is None:
        _kb_manager = KnowledgeBaseManager()
    return _kb_manager
```

**详细讲解：**
- `global _kb_manager`：声明使用全局变量 `_kb_manager`（Python 中修改全局变量需要 `global` 关键字）
- `if _kb_manager is None:`：如果全局变量为 `None`（未初始化）
- `_kb_manager = KnowledgeBaseManager()`：创建新的管理器实例（单例模式）
- `return _kb_manager`：返回管理器实例

**作用：** 确保整个程序只有一个知识库管理器实例（单例模式）

**对比其他语言：**
```python
# Python 单例模式
_kb_manager = None
def get_kb_manager():
    global _kb_manager
    if _kb_manager is None:
        _kb_manager = KnowledgeBaseManager()
    return _kb_manager
```
```javascript
// JavaScript 类似写法
let kbManager = null;
function getKbManager() {
    if (kbManager === null) {
        kbManager = new KnowledgeBaseManager();
    }
    return kbManager;
}
```

**`KnowledgeBaseManager.__init__()`（第 232-234 行）**

```python
def __init__(self):
    self.knowledge_bases: Dict[str, KnowledgeBase] = {}
    self._init_default_knowledge_bases()
```

**详细讲解：**
- `__init__`：Python 的构造函数（类似其他语言的构造函数）
- `self.knowledge_bases: Dict[str, KnowledgeBase] = {}`：创建空字典，键为字符串（知识库名），值为 KnowledgeBase 对象
- `self._init_default_knowledge_bases()`：调用初始化默认知识库的方法

**`_init_default_knowledge_bases()`（第 236-248 行）**

```python
def _init_default_knowledge_bases(self):
    """初始化默认知识库"""
    default_kbs = [
        "NameNodeExpert",
        "DataNodeExpert",
        "YARNExpert",
        "HistoryCases",  # 历史故障案例
        "HadoopDocs",    # Hadoop官方文档
    ]
    
    for kb_name in default_kbs:
        self.get_or_create_kb(kb_name)
```

**详细讲解：**
- `default_kbs = [...]`：定义默认知识库名称列表（Python 列表，类似数组）
- `for kb_name in default_kbs:`：遍历列表中的每个元素
- `self.get_or_create_kb(kb_name)`：为每个名称创建或获取知识库

**`get_or_create_kb()`（第 250-254 行）**

```python
def get_or_create_kb(self, kb_name: str) -> KnowledgeBase:
    """获取或创建知识库"""
    if kb_name not in self.knowledge_bases:
        self.knowledge_bases[kb_name] = KnowledgeBase(kb_name)
    return self.knowledge_bases[kb_name]
```

**详细讲解：**
- `if kb_name not in self.knowledge_bases:`：检查字典中是否已有该知识库（`not in` 是 Python 的成员运算符）
- `self.knowledge_bases[kb_name] = KnowledgeBase(kb_name)`：不存在则创建并存入字典
- `return self.knowledge_bases[kb_name]`：返回知识库对象

**作用：** 如果知识库不存在则创建，存在则直接返回（懒加载模式）

### 第 350-353 行：匹配知识库

```python
if expert_type.lower() == "all":
    kb_name = None  # 搜索所有知识库
else:
    kb_name = kb_manager.match_knowledge_base(expert_type)
```

**解释：**
- `.lower()`：将字符串转为小写（如 `"ALL"` → `"all"`）
- `==`：判断相等
- `None`：表示"空/无值"（类似其他语言的 `null`）
- `if-else`：条件判断

**执行流程：**
1. 如果 `expert_type` 是 `"all"`，设置 `kb_name = None`（搜索所有知识库）
2. 否则，调用 `match_knowledge_base` 匹配对应的知识库名称

**调用函数：`match_knowledge_base()`（第 293-314 行）**

```python
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
```

**详细讲解：**
- `expert_type_lower = expert_type.lower()`：将字符串转为小写
- `"namenode" in expert_type_lower`：检查字符串中是否包含子串（`in` 运算符）
- `or`：逻辑或运算符
- `elif`：else if 的缩写
- `return "NameNodeExpert"`：返回匹配的知识库名称

**执行流程示例：**
```python
expert_type = "NameNode" 
→ expert_type_lower = "namenode"
→ "namenode" in "namenode" → True
→ 返回 "NameNodeExpert"
```

### 第 356-361 行：执行搜索

```python
results = kb_manager.search_knowledge(
    query=query,
    kb_name=kb_name,
    top_k=top_k,
    score_threshold=score_threshold
)
```

**解释：**
- 调用 `search_knowledge` 方法进行搜索
- `query=query`：命名参数传递（参数名=变量值）
- `results` 存储搜索结果（列表）

**对比其他语言：**
```python
# Python 命名参数
search_knowledge(query=query, kb_name=kb_name, top_k=top_k)
```
```javascript
// JavaScript 类似写法
searchKnowledge({query: query, kbName: kbName, topK: topK})
```

**调用函数：`search_knowledge()`（第 256-291 行）**

```python
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
```

**详细讲解：**
- `if kb_name:`：如果指定了知识库名称（Python 中 `None` 被视为 `False`）
  - `if kb_name in self.knowledge_bases:`：检查字典中是否存在该知识库
  - `return self.knowledge_bases[kb_name].search(...)`：调用该知识库的搜索方法
- `else:`：搜索所有知识库
  - `all_results = []`：初始化结果列表
  - `for kb in self.knowledge_bases.values():`：遍历所有知识库（`.values()` 获取字典的所有值）
  - `all_results.extend(results)`：将结果合并到列表（`extend` 是添加多个元素，`append` 是添加单个元素）
  - `all_results.sort(key=lambda x: x[1])`：按分数排序（`lambda` 是匿名函数，`x[1]` 是元组的第二个元素，即分数）
  - `return all_results[:top_k]`：返回前 top_k 个结果（列表切片）

**`lambda` 表达式：**
```python
# lambda x: x[1] 等价于：
def get_score(item):
    return item[1]
all_results.sort(key=get_score)
```

**调用函数：`kb.search()`（第 193-219 行）**

```python
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
```

**详细讲解：**
- `try-except`：异常处理（类似其他语言的 try-catch）
- `self.vector_store.similarity_search_with_score(query, k=top_k)`：调用 FAISS 的相似度搜索，返回文档和分数
- **列表推导式**：`[(doc, score) for doc, score in results if score <= ...]`
  - 遍历 `results`，过滤满足条件的项
  - `if score <= (1.0 - score_threshold) * 10`：阈值转换（距离越小越相似）
- `except Exception as e:`：捕获所有异常
- `logging.error(...)`：记录错误日志
- `return []`：返回空列表

**列表推导式对比：**
```python
# 列表推导式
filtered_results = [(doc, score) for doc, score in results if score <= threshold]

# 等价于传统写法
filtered_results = []
for doc, score in results:
    if score <= threshold:
        filtered_results.append((doc, score))
```

### 第 364-377 行：格式化返回结果

```python
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
```

**详细讲解：**
- `if not results:`：如果结果为空（Python 中空列表被视为 `False`）
- `f"找到 {len(results)} 条相关知识：\n\n"`：格式化字符串（f-string）
- `for idx, (doc, score) in enumerate(results, 1):`：遍历结果，`enumerate` 从 1 开始计数
- `f"[知识 {idx}] (相似度: {1-score:.2f})\n"`：格式化相似度（两位小数）
- `if doc.metadata:`：检查元数据是否存在
- `if 'source' in doc.metadata:`：检查字典中是否有 'source' 键
- `doc.metadata['source']`：获取字典中 'source' 的值
- `doc.page_content`：获取文档内容
- `return knowledge_str`：返回格式化后的字符串

---

## 函数 2：`init_sample_knowledge` - 初始化示例知识库

### 函数定义（第 381-382 行）

```python
def init_sample_knowledge():
    """初始化示例知识库数据（用于测试）"""
```

**解释：**
- 无参数函数
- `"""..."""`：文档字符串（docstring），用于说明函数用途

### 第 383 行：获取知识库管理器

```python
kb_manager = get_kb_manager()
```

**（已在函数 1 中讲解）**

### 第 386 行：创建或获取 NameNode 知识库

```python
namenode_kb = kb_manager.get_or_create_kb("NameNodeExpert")
```

**调用函数：`get_or_create_kb()`（第 250-254 行）**

**（已在函数 1 中讲解）**

**调用函数：`KnowledgeBase.__init__()`（第 108-129 行）**

```python
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
```

**详细讲解：**
- `self.kb_name = kb_name`：保存知识库名称
- `self.kb_path = kb_path or os.path.join(...)`：如果 `kb_path` 为 `None`，使用默认路径
  - `os.path.dirname(__file__)`：当前文件所在目录
  - `os.path.dirname(os.path.dirname(__file__))`：上一级目录
  - `os.path.join(...)`：拼接路径（跨平台兼容）
- `os.makedirs(self.kb_path, exist_ok=True)`：创建目录（`exist_ok=True` 表示目录已存在时不报错）
- `self.embeddings = SimpleEmbeddings()`：创建嵌入模型对象
- `self.vector_store = None`：初始化向量存储为 None
- `self._load_or_create_vector_store()`：加载或创建向量存储

**`SimpleEmbeddings.__init__()`（第 49-83 行）**

```python
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
```

**详细讲解：**
- `self.model_name = model_name or DEFAULT_EMBEDDING_MODEL`：如果 `model_name` 为 `None`，使用默认模型
- `if SENTENCE_TRANSFORMER_AVAILABLE:`：检查 sentence-transformers 是否可用
- `os.path.join(LOCAL_MODEL_BASE_DIR, self.model_name)`：拼接本地模型路径
- `if os.path.exists(local_model_path):`：检查路径是否存在
- `SentenceTransformer(local_model_path)`：加载本地模型
- `except Exception as e:`：捕获异常
- `self.embedder = None`：失败时设为 None

**`_load_or_create_vector_store()`（第 131-153 行）**

```python
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
```

**详细讲解：**
- `os.path.join(self.kb_path, "vector_store")`：拼接向量存储路径
- `os.path.exists(vector_store_path) and os.listdir(vector_store_path)`：检查路径存在且非空
- `FAISS.load_local(...)`：从本地加载 FAISS 向量存储
- `FAISS.from_texts(["初始化"], self.embeddings)`：创建新的向量存储
- `self.vector_store.delete([...])`：删除初始化文档

### 第 387-398 行：添加文本到知识库

```python
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
```

**解释：**
- `add_texts(...)`：调用方法添加文本
- `texts=[...]`：列表参数，包含多个字符串
- `metadatas=[...]`：列表参数，每个元素是一个字典

**Python 列表和字典：**
```python
# 列表（类似数组）
texts = ["文本1", "文本2", "文本3"]

# 字典（类似对象/Map）
metadata = {"source": "Hadoop文档", "desc": "启动问题"}
```

**对比其他语言：**
```python
# Python
texts = ["文本1", "文本2"]
metadata = {"key": "value"}
```
```javascript
// JavaScript
const texts = ["文本1", "文本2"];
const metadata = {key: "value"};
```

**参数对应关系：**
- `texts[0]` 对应 `metadatas[0]`
- `texts[1]` 对应 `metadatas[1]`
- `texts[2]` 对应 `metadatas[2]`

**调用函数：`add_texts()`（第 171-191 行）**

```python
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
```

**详细讲解：**
- `if not texts:`：如果文本列表为空，直接返回
- `if metadatas is None:`：如果元数据为 None
- `metadatas = [{}] * len(texts)`：创建与文本数量相同的空字典列表
- `zip(texts, metadatas)`：将两个列表配对（返回元组迭代器）
- **列表推导式**：`[Document(...) for text, metadata in zip(...)]`
- `self.add_documents(documents)`：调用添加文档的方法

**`zip()` 函数：**
```python
texts = ["文本1", "文本2"]
metadatas = [{"source": "来源1"}, {"source": "来源2"}]
list(zip(texts, metadatas))
# 结果：[("文本1", {"source": "来源1"}), ("文本2", {"source": "来源2"})]
```

**调用函数：`add_documents()`（第 155-169 行）**

```python
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
```

**详细讲解：**
- `if not documents:`：如果文档列表为空，返回
- `self.vector_store.add_documents(documents)`：将文档添加到 FAISS 向量存储
- `self.save()`：保存向量存储到磁盘

**调用函数：`save()`（第 221-226 行）**

```python
def save(self):
    """保存向量存储"""
    vector_store_path = os.path.join(self.kb_path, "vector_store")
    os.makedirs(vector_store_path, exist_ok=True)
    self.vector_store.save_local(vector_store_path)
    logging.info(f"知识库已保存: {self.kb_name}")
```

**详细讲解：**
- `os.path.join(self.kb_path, "vector_store")`：拼接保存路径
- `os.makedirs(vector_store_path, exist_ok=True)`：创建目录（`exist_ok=True` 表示已存在时不报错）
- `self.vector_store.save_local(vector_store_path)`：保存 FAISS 向量存储到本地
- `logging.info(...)`：记录日志

**调用函数：`logging.info()`**

```python
logging.info(f"知识库已保存: {self.kb_name}")
```

**详细讲解：**
- `logging`：Python 标准日志模块
- `logging.info(...)`：记录信息级别日志
- `f"..."`：格式化字符串

### 第 416-417 行：保存所有知识库

```python
for kb in kb_manager.knowledge_bases.values():
    kb.save()
```

**详细讲解：**
- `kb_manager.knowledge_bases.values()`：获取所有知识库对象（字典的 `.values()` 方法）
- `for kb in ...:`：遍历每个知识库
- `kb.save()`：保存知识库（已在上面讲解）

### 第 419 行：记录日志

```python
logging.info("示例知识库数据初始化完成")
```

**（已在上面讲解）**

---

## 总结：两个函数的关系

```
init_sample_knowledge()  →  创建知识库并添加数据
         ↓
    （数据已保存）
         ↓
search_diagnosis_knowledge()  →  从知识库中搜索数据
```

**工作流程：**
1. 先调用 `init_sample_knowledge()` 初始化数据
2. 再调用 `search_diagnosis_knowledge()` 搜索数据

**类比理解：**
- `init_sample_knowledge`：像图书馆管理员，把书（知识）放到书架上
- `search_diagnosis_knowledge`：像读者，从书架上找书（搜索知识）

---

## 完整调用关系图

```
search_diagnosis_knowledge()
├── get_kb_manager()
│   └── KnowledgeBaseManager.__init__()
│       └── _init_default_knowledge_bases()
│           └── get_or_create_kb()
│               └── KnowledgeBase.__init__()
│                   ├── SimpleEmbeddings.__init__()
│                   └── _load_or_create_vector_store()
├── match_knowledge_base()
└── search_knowledge()
    └── kb.search()
        └── vector_store.similarity_search_with_score()  # FAISS库方法

init_sample_knowledge()
├── get_kb_manager()  # 同上
├── get_or_create_kb()  # 同上
├── add_texts()
│   └── add_documents()
│       └── save()
│           └── logging.info()
└── logging.info()
```

---

## Python 语法要点总结

### 1. 类型提示
```python
def function(param: str) -> int:
    return len(param)
```

### 2. 默认参数
```python
def function(param: str = "default"):
    pass
```

### 3. 列表推导式
```python
# 简洁写法
result = [x * 2 for x in range(5) if x > 2]

# 等价于
result = []
for x in range(5):
    if x > 2:
        result.append(x * 2)
```

### 4. 字典操作
```python
# 检查键是否存在
if 'key' in dictionary:
    value = dictionary['key']

# 获取值（不存在返回默认值）
value = dictionary.get('key', 'default')
```

### 5. f-string 格式化
```python
name = "张三"
age = 25
message = f"我叫{name}，今年{age}岁"
```

### 6. 异常处理
```python
try:
    # 可能出错的代码
    result = risky_operation()
except Exception as e:
    # 处理异常
    logging.error(f"错误: {e}")
```

### 7. 单例模式
```python
_instance = None

def get_instance():
    global _instance
    if _instance is None:
        _instance = SomeClass()
    return _instance
```

---

**文档生成时间：** 2025-12-29  
**适用对象：** 有其他语言基础但未学过 Python 的开发者  
**讲解方式：** 递归讲解（讲解函数时，同时讲解所有被调用的函数）

