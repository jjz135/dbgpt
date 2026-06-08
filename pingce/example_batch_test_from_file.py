"""
示例：从 CSV/Excel 文件批量导入问题进行测试

这个脚本展示了如何加载外部问题列表并进行批量测试
"""

import asyncio
import csv
import sys
import os
from typing import List

# 添加路径
DB_GPT_ROOT = r"D:\code\py\dbgpt\dbgpt"
sys.path.insert(0, DB_GPT_ROOT)

# 导入主测试器
from knowledge_qa_batch_test import KnowledgeQABatchTester, QATestCase


def load_questions_from_csv(csv_path: str) -> List[QATestCase]:
    """
    从 CSV 文件加载问题
    
    CSV 格式：
    question,ground_truth
    "问题1","标准答案1"
    "问题2","标准答案2"
    
    Args:
        csv_path: CSV 文件路径
        
    Returns:
        List[QATestCase]: 测试用例列表
    """
    test_cases = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            question = row.get('question', '').strip()
            ground_truth = row.get('ground_truth', '').strip()
            
            if question:  # 只添加非空问题
                test_cases.append(QATestCase(
                    question=question,
                    ground_truth=ground_truth if ground_truth else None
                ))
    
    print(f"✅ 从 CSV 加载了 {len(test_cases)} 个问题")
    return test_cases


def load_questions_from_excel(excel_path: str) -> List[QATestCase]:
    """
    从 Excel 文件加载问题
    
    Excel 需要包含列：question, ground_truth（可选）
    
    Args:
        excel_path: Excel 文件路径
        
    Returns:
        List[QATestCase]: 测试用例列表
    """
    try:
        import pandas as pd
        
        df = pd.read_excel(excel_path)
        test_cases = []
        
        for _, row in df.iterrows():
            question = str(row.get('question', '')).strip()
            ground_truth = str(row.get('ground_truth', '')).strip()
            
            if question and question != 'nan':
                test_cases.append(QATestCase(
                    question=question,
                    ground_truth=ground_truth if ground_truth and ground_truth != 'nan' else None
                ))
        
        print(f"✅ 从 Excel 加载了 {len(test_cases)} 个问题")
        return test_cases
        
    except ImportError:
        print("❌ 需要安装 pandas 和 openpyxl: pip install pandas openpyxl")
        raise


async def main():
    """
    主函数 - 从文件加载问题并执行批量测试
    """
    
    # ==================== 配置区域 ====================
    
    # 1. 问题文件路径（CSV 或 Excel）
    QUESTIONS_FILE = "questions_example060202.csv"  # ← 使用你准备好的 CSV 文件
    FILE_TYPE = "csv"  # 或 "excel"
    
    # 2. 知识库配置
    KNOWLEDGE_SPACE = "质量2"  # ← 修改为你的知识库名称（与 knowledge_qa_batch_test.py 中保持一致）
    MODEL_NAME = "qwen-plus"  # 可选
    
    # 3. 输出文件
    OUTPUT_EXCEL = "batch_test_results060202.xlsx"
    
    # 4. 配置文件路径（重要：需要配置 LLM 和 embedding 模型）
    # 使用通义千问配置示例
    CONFIG_FILE = os.path.join(DB_GPT_ROOT, "configs", "dbgpt-proxy-tongyi.toml")
    
    # ==================== 加载问题 ====================
    
    print("=" * 80)
    print("正在加载问题...")
    print("=" * 80)
    
    if FILE_TYPE == "csv":
        test_cases = load_questions_from_csv(QUESTIONS_FILE)
    elif FILE_TYPE == "excel":
        test_cases = load_questions_from_excel(QUESTIONS_FILE)
    else:
        raise ValueError(f"不支持的文件类型: {FILE_TYPE}")
    
    if not test_cases:
        print("❌ 没有加载到任何问题，请检查文件格式")
        return
    
    print(f"\n前 3 个问题预览:")
    for i, tc in enumerate(test_cases[:3], 1):
        print(f"  {i}. {tc.question[:60]}...")
    
    # ==================== 执行测试 ====================
    
    tester = KnowledgeQABatchTester(
        config_path=CONFIG_FILE,  # ← 使用配置文件
        knowledge_space_name=KNOWLEDGE_SPACE,
        model_name=MODEL_NAME
    )
    
    print("\n" + "=" * 80)
    print("开始批量测试...")
    print("=" * 80)
    
    results = await tester.batch_test(
        test_cases=test_cases,
        output_excel=OUTPUT_EXCEL,
        knowledge_space=KNOWLEDGE_SPACE,
        model_name=MODEL_NAME,
        concurrency=1
    )
    
    # ==================== 导出 RAGAS 数据集 ====================
    
    ragas_dataset = tester.export_to_ragas_dataset(results)
    
    print("\n" + "=" * 80)
    print("📊 测试完成总结")
    print("=" * 80)
    print(f"总问题数: {len(test_cases)}")
    print(f"成功回答: {sum(1 for r in results if not r.answer.startswith('ERROR'))}")
    print(f"失败数量: {sum(1 for r in results if r.answer.startswith('ERROR'))}")
    print(f"结果文件: {OUTPUT_EXCEL}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
