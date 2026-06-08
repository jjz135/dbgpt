# 📦 DB-GPT 知识库问答批量评测工具包

## 🎯 功能说明

这套工具可以**自动批量调用 DB-GPT 知识库问答接口**，无需通过前端手动操作，直接在后端脚本中完成以下工作：

✅ 自动收集 **question**（问题）  
✅ 自动收集 **context**（检索到的知识库内容）  
✅ 自动收集 **answer**（AI 生成的答案）  
✅ 导出为 Excel 格式，完美适配 **RAGAS 评测**  
✅ 支持一次性处理 100-200 个问题  
✅ 增量保存，防止中断丢失数据  

---

## 📁 文件清单

### 核心脚本

| 文件名 | 用途 | 适用场景 |
|--------|------|----------|
| `knowledge_qa_batch_test.py` | **主脚本** - 完整的批量测试工具 | 直接在代码中编写问题列表 |
| `example_batch_test_from_file.py` | **示例脚本** - 从 CSV/Excel 文件导入问题 | 有大量问题存储在文件中 |

### 示例数据

| 文件名 | 用途 |
|--------|------|
| `questions_example.csv` | CSV 格式的问题模板，包含 4 个示例问题 |

### 文档

| 文件名 | 内容 |
|--------|------|
| `QUICK_START_GUIDE.md` | **快速开始指南** - 5分钟上手教程 |
| `KNOWLEDGE_QA_BATCH_TEST_README.md` | **详细使用文档** - 完整功能说明和高级配置 |
| `README_批量评测工具.md` | 本文件 - 工具包总览 |

---

## 🚀 快速开始（3步搞定）

### 第1步：准备问题

**方式A：使用 CSV 文件（推荐）**

1. 复制 `questions_example.csv`
2. 按照格式填入你的 100-200 个问题
3. 保存为 `my_questions.csv`

**方式B：直接在代码中编写**

打开 `knowledge_qa_batch_test.py`，在 `main()` 函数中添加：

```python
test_cases = [
    QATestCase(question="问题1...", ground_truth="答案1..."),
    QATestCase(question="问题2...", ground_truth="答案2..."),
    # ... 继续添加
]
```

### 第2步：修改配置

打开 `knowledge_qa_batch_test.py`，修改这两处：

```python
KNOWLEDGE_SPACE = "桥梁制造工艺"  # ← 改成你的知识库名称
MODEL_NAME = "qwen-plus"          # ← 改成你的模型名称（或留空）
```

### 第3步：运行

```bash
cd D:\code\py\dbgpt\dbgpt
python knowledge_qa_batch_test.py
```

等待脚本运行完成，会生成 `knowledge_qa_batch_results.xlsx` 文件。

---

## 📊 输出结果说明

生成的 Excel 文件包含以下列：

| 列名 | 说明 | RAGAS 需要？ |
|------|------|:------------:|
| question | 用户提问 | ✅ 是 |
| answer | AI 生成的答案 | ✅ 是 |
| contexts | JSON 格式的上下文列表 | ✅ 是 |
| ground_truth | 标准答案（如有提供） | ✅ 是 |
| full_context | 完整的原始上下文 | ❌ 参考用 |

---

## 🔗 与 RAGAS 集成

运行完批量测试后，直接使用以下代码进行 RAGAS 评测：

```python
import pandas as pd
import json
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# 读取结果
df = pd.read_excel("knowledge_qa_batch_results.xlsx")
df['contexts'] = df['contexts'].apply(lambda x: json.loads(x))

# 创建数据集
dataset = Dataset.from_dict({
    'question': df['question'].tolist(),
    'answer': df['answer'].tolist(),
    'contexts': df['contexts'].tolist(),
    'ground_truth': df['ground_truth'].tolist()
})

# 执行评测
result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision])
print(result)
```

---

## 💡 核心优势

### 1. 完全自动化
- ❌ 不需要手动在前端逐个提问
- ❌ 不需要手动复制粘贴答案
- ✅ 脚本自动完成所有操作

### 2. 数据完整性
- 自动捕获完整的 `context`（检索到的知识库片段）
- 自动清理答案中的引用标签
- 保留原始数据和格式化数据

### 3. 容错机制
- 每处理 10 个问题自动保存一次
- 即使中途中断，已处理的数据不会丢失
- 错误的问题会记录错误信息，不影响其他问题

### 4. 灵活配置
- 支持自定义配置文件
- 支持并发处理（谨慎使用）
- 支持从文件批量导入问题

---

## 🛠️ 技术实现原理

```
┌─────────────────────────────────────────────┐
│  1. 初始化 DB-GPT 系统                       │
│     - 加载配置                               │
│     - 初始化 SystemApp                       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  2. 创建 ChatParam                           │
│     - 设置会话ID                             │
│     - 指定知识库空间                         │
│     - 指定模型                               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  3. 通过 ChatFactory 创建 ChatKnowledge      │
│     - 自动加载对应的 Prompt                  │
│     - 初始化 RAG 检索器                      │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  4. 调用 generate_input_values()             │
│     - 执行向量检索                           │
│     - 收集 context                           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  5. 调用 stream_call()                       │
│     - 流式调用 LLM                           │
│     - 收集 answer                            │
│     - 添加引用信息                           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  6. 保存结果                                 │
│     - 构建 DataFrame                         │
│     - 导出为 Excel                           │
│     - 转换为 RAGAS Dataset                   │
└─────────────────────────────────────────────┘
```

---

## 📖 详细文档

- **快速入门**：查看 `QUICK_START_GUIDE.md`
- **完整文档**：查看 `KNOWLEDGE_QA_BATCH_TEST_README.md`

---

## ❓ 常见问题

### Q1: 需要准备什么环境？

确保安装了以下 Python 包：
```bash
pip install pandas openpyxl datasets
```

### Q2: 如何知道知识库名称？

在 DB-GPT 前端界面查看知识库列表，或使用以下代码查询：

```python
from dbgpt_app.knowledge.service import KnowledgeService
service = KnowledgeService()
spaces = service.list_knowledge_spaces()
for space in spaces:
    print(space.name)
```

### Q3: 处理速度慢怎么办？

- 检查网络连接和 API 响应时间
- 适当增加并发数（修改 `concurrency` 参数）
- 减少每个问题的最大 token 数

### Q4: 可以在没有 GPU 的机器上运行吗？

✅ 可以！这个脚本只是调用 DB-GPT 的 API，不需要本地运行 LLM。

---

## 🎉 开始使用

现在你已经了解了所有信息，可以开始了：

1. 阅读 `QUICK_START_GUIDE.md`
2. 准备你的问题列表
3. 运行脚本
4. 使用 RAGAS 评测结果

祝你评测顺利！🚀

---

## 📞 技术支持

如遇到问题，请检查：
1. DB-GPT 服务是否正常运行
2. 知识库是否已正确索引
3. LLM API 密钥是否有效
4. Python 环境依赖是否齐全

更多帮助请查看详细文档或联系技术支持。
