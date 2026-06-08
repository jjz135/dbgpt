# DB-GPT 知识库问答批量评测脚本使用指南

## 📋 功能概述

这个脚本可以自动批量调用 DB-GPT 的知识库问答功能，并收集以下数据：
- **question**: 用户提问
- **answer**: LLM 生成的答案
- **context**: 从知识库检索到的相关文档内容
- **contexts**: 分割后的上下文列表（适配 RAGAS 格式）
- **ground_truth**: 标准答案（可选，用于评测）

最终导出为 Excel 文件，可直接用于 RAGAS 评测。

---

## 🚀 快速开始

### 1. 安装依赖

确保已安装以下 Python 包：

```bash
pip install pandas openpyxl datasets
```

### 2. 配置脚本

打开 `knowledge_qa_batch_test.py`，修改主函数中的配置：

```python
async def main():
    # 1. DB-GPT 配置文件路径（可选）
    CONFIG_PATH = None  # 或使用你的 toml 配置文件路径
    
    # 2. 知识库空间名称（必填！）
    KNOWLEDGE_SPACE = "桥梁制造工艺"  # ← 修改为你的知识库名称
    
    # 3. LLM 模型名称（可选）
    MODEL_NAME = "qwen-plus"  # 或留空使用默认模型
    
    # 4. 输出文件路径
    OUTPUT_EXCEL = "knowledge_qa_batch_results.xlsx"
    
    # 5. 准备测试问题列表
    test_cases = [
        QATestCase(
            question="你的第一个问题...",
            ground_truth="标准答案1..."  # 可选
        ),
        QATestCase(
            question="你的第二个问题...",
            ground_truth="标准答案2..."
        ),
        # ... 添加更多问题
    ]
```

### 3. 运行脚本

```bash
cd D:\code\py\dbgpt\dbgpt
python knowledge_qa_batch_test.py
```

---

## 📊 输出文件格式

脚本会生成一个 Excel 文件，包含以下列：

| 列名 | 说明 | 用途 |
|------|------|------|
| question | 用户提问 | RAGAS 输入 |
| answer | LLM 生成的答案 | RAGAS 输入 |
| contexts | JSON 格式的上下文列表 | RAGAS 输入 |
| ground_truth | 标准答案（如有） | RAGAS 输入 |
| full_context | 完整的原始上下文 | 参考用 |

---

## 🔗 与 RAGAS 集成

运行完批量测试后，你可以直接使用导出的数据进行 RAGAS 评测：

```python
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# 1. 读取 Excel 文件
df = pd.read_excel("knowledge_qa_batch_results.xlsx")

# 2. 解析 contexts 列（JSON 字符串转列表）
import json
df['contexts'] = df['contexts'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)

# 3. 创建 Dataset
dataset = Dataset.from_dict({
    'question': df['question'].tolist(),
    'answer': df['answer'].tolist(),
    'contexts': df['contexts'].tolist(),
    'ground_truth': df['ground_truth'].tolist()
})

# 4. 执行 RAGAS 评测
result = evaluate(
    dataset=dataset,
    metrics=[
        context_precision,
        faithfulness,
        answer_relevancy
    ]
)

print(result)
```

---

## ⚙️ 高级配置

### 使用自定义配置文件

如果你有自己的 DB-GPT 配置文件（toml 格式），可以指定路径：

```python
CONFIG_PATH = r"/dbgpt/configs/dbgpt-proxy-siliconflow.toml"
```

### 并发控制

默认情况下，脚本顺序处理问题（concurrency=1）。如果你的 API 支持高并发，可以调整：

```python
results = await tester.batch_test(
    test_cases=test_cases,
    concurrency=3  # 同时处理3个问题
)
```

**注意**：并发数过高可能触发 API 速率限制，建议从 1 开始测试。

### 增量保存

脚本每处理 10 个问题会自动保存一次中间结果，防止意外中断丢失数据。你可以在代码中修改这个阈值：

```python
if i % 10 == 0:  # 改为 5 或其他数值
    self._save_intermediate_results(results, output_excel)
```

---

## 🐛 常见问题

### Q1: 提示找不到模块 `dbgpt`

**解决方案**：确保脚本中的路径配置正确：

```python
DB_GPT_ROOT = r"D:\code\py\dbgpt\dbgpt"  # 修改为你的实际路径
```

### Q2: 提示知识库空间不存在

**解决方案**：
1. 确认知识库已在 DB-GPT 中创建
2. 检查 `KNOWLEDGE_SPACE` 名称是否完全匹配（区分大小写）

### Q3: 答案中包含 `<references>` 标签

这是正常的，脚本会自动清理这些标签。如果你想保留引用信息，可以注释掉 `_clean_reference_tags` 的调用：

```python
# clean_answer = self._clean_reference_tags(full_answer)
clean_answer = full_answer  # 保留原始答案
```

### Q4: 处理速度太慢

**优化建议**：
1. 检查网络连接和 API 响应时间
2. 适当增加并发数（谨慎使用）
3. 减少每个问题的最大 token 数（在配置文件中调整）

---

## 📝 示例：批量导入 100+ 问题

如果你有大量问题，可以从文件导入：

```python
import csv

def load_questions_from_csv(csv_path: str) -> List[QATestCase]:
    """从 CSV 文件加载问题"""
    test_cases = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append(QATestCase(
                question=row['question'],
                ground_truth=row.get('ground_truth', '')
            ))
    return test_cases

# 在主函数中使用
test_cases = load_questions_from_csv("questions.csv")
```

CSV 文件格式示例：

```csv
question,ground_truth
"问题1...","标准答案1..."
"问题2...","标准答案2..."
```

---

## 🎯 完整工作流程

```
1. 准备问题列表 (100-200个问题)
         ↓
2. 运行批量测试脚本
         ↓
3. 自动收集 question, context, answer
         ↓
4. 导出为 Excel 文件
         ↓
5. 使用 RAGAS 进行质量评测
         ↓
6. 分析评测结果，优化知识库
```

---

## 📞 技术支持

如遇到问题，请检查：
1. DB-GPT 服务是否正常运行
2. 知识库是否已正确索引
3. LLM API 密钥是否有效
4. Python 环境依赖是否齐全

祝评测顺利！🎉
