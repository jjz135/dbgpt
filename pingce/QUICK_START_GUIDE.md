# 🚀 快速开始指南 - 5分钟上手批量评测

## 第一步：准备问题列表

### 方式1：使用示例 CSV 文件

已为你创建了示例文件 `questions_example.csv`，你可以：

1. 打开这个文件
2. 按照格式添加你的 100-200 个问题
3. 保存

**CSV 格式说明：**
```csv
question,ground_truth
"问题1","标准答案1（可选）"
"问题2","标准答案2（可选）"
```

### 方式2：直接在脚本中编写

打开 `knowledge_qa_batch_test.py`，找到主函数中的 `test_cases` 部分：

```python
test_cases = [
    QATestCase(
        question="你的第一个问题...",
        ground_truth="标准答案1..."
    ),
    QATestCase(
        question="你的第二个问题...",
        ground_truth="标准答案2..."
    ),
    # ... 继续添加
]
```

---

## 第二步：修改配置

打开 `knowledge_qa_batch_test.py`，只需修改 2 个地方：

```python
# 第 1 处：知识库名称（必填）
KNOWLEDGE_SPACE = "桥梁制造工艺"  # ← 改成你的知识库名称

# 第 2 处：模型名称（可选，留空用默认）
MODEL_NAME = "qwen-plus"  # 或 None
```

---

## 第三步：运行脚本

在命令行执行：

```bash
cd D:\code\py\dbgpt\dbgpt
python knowledge_qa_batch_test.py
```

---

## 第四步：查看结果

脚本运行完成后，会生成 `knowledge_qa_batch_results.xlsx` 文件，包含：

| 列名 | 说明 |
|------|------|
| question | 你的问题 |
| answer | AI 生成的答案 |
| contexts | 检索到的知识库片段 |
| ground_truth | 标准答案（如有提供） |
| full_context | 完整的原始上下文 |

---

## 第五步：使用 RAGAS 评测

将导出的 Excel 文件用于 RAGAS 评测：

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

## ✅ 完成！

现在你已经掌握了完整的工作流程：

```
准备问题 → 修改配置 → 运行脚本 → 导出结果 → RAGAS 评测
```

---

## 💡 小贴士

### 1. 测试少量问题先验证

建议先用 3-5 个问题测试，确保配置正确后再批量运行。

### 2. 监控进度

脚本会在控制台实时显示进度：
```
进度: 1/100
[1] 处理问题: 在桥梁钢箱梁底板与斜底板单元制造...
   检索到 3 个相关文档片段
   答案长度: 523 字符
```

### 3. 防止中断丢失数据

脚本每处理 10 个问题会自动保存一次，即使中途中断也不会丢失之前的结果。

### 4. 从 CSV 批量导入

如果你有大量问题，可以使用 `example_batch_test_from_file.py`：

```bash
python example_batch_test_from_file.py
```

记得修改脚本中的文件路径和知识库名称。

---

## ❓ 遇到问题？

### 问题1：找不到模块
```bash
pip install pandas openpyxl datasets
```

### 问题2：知识库不存在
确认 `KNOWLEDGE_SPACE` 名称与 DB-GPT 中创建的完全一致。

### 问题3：API 调用失败
检查网络连接和 API 密钥配置。

---

## 📚 更多帮助

详细文档请查看：`KNOWLEDGE_QA_BATCH_TEST_README.md`

祝你评测顺利！🎉
