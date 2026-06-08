"""探索性查询的提示词模板。"""

# 中文探索性查询提示词模板
EXPLORATORY_PROMPT_ZH = """
你是一位数据科学家，需要在正式分析用户问题之前，先进行探索性查询来了解数据结构。

## 任务目标
从给定的数据库表中选择3个最相关的表，用于探索性查询。这些表应该与用户的问题密切相关。

## 用户问题
{user_question}

## 可用的数据库表信息
{database_schema}

## 你的任务
1. 仔细分析用户的问题
2. 从所有可用表中选择3个最相关的表
3. 解释选择这些表的理由

## 输出格式
请严格按照以下JSON格式输出，不要包含任何其他内容：

```json
{{
    "selected_tables": ["表名1", "表名2", "表名3"],
    "reasoning": "选择这些表的详细理由，解释它们如何与用户问题相关"
}}
```

## 注意事项
- 必须选择恰好3个表（如果可用表少于3个，则选择所有可用表）
- 表名必须与提供的数据库schema中的表名完全一致
- reasoning字段应该详细解释选择逻辑
- 优先选择可能包含用户问题核心数据的表
"""

# 英文探索性查询提示词模板
EXPLORATORY_PROMPT_EN = """
You are a data scientist who needs to conduct exploratory queries before formally analyzing user questions to understand the data structure.

## Task Objective
Select 3 most relevant tables from the given database tables for exploratory queries. These tables should be closely related to the user's question.

## User Question
{user_question}

## Available Database Table Information
{database_schema}

## Your Task
1. Carefully analyze the user's question
2. Select 3 most relevant tables from all available tables
3. Explain the rationale for selecting these tables

## Output Format
Please strictly follow the JSON format below, without any other content:

```json
{{
    "selected_tables": ["table1", "table2", "table3"],
    "reasoning": "Detailed rationale for selecting these tables, explaining how they relate to the user's question"
}}
```

## Notes
- Must select exactly 3 tables (if fewer than 3 tables are available, select all available tables)
- Table names must exactly match those in the provided database schema
- The reasoning field should provide detailed explanation of the selection logic
- Prioritize tables that may contain core data for the user's question
"""

def get_exploratory_prompt(user_question: str, database_schema: str, language: str = "zh") -> str:
    """获取探索性查询的提示词。
    
    Args:
        user_question: 用户问题
        database_schema: 数据库schema信息
        language: 语言，'zh'为中文，'en'为英文
        
    Returns:
        str: 格式化的提示词
    """
    if language.lower() == "zh":
        return EXPLORATORY_PROMPT_ZH.format(
            user_question=user_question,
            database_schema=database_schema
        )
    else:
        return EXPLORATORY_PROMPT_EN.format(
            user_question=user_question,
            database_schema=database_schema
        )
