"""智能注释生成器 - 基于表结构和示例数据为表和字段生成注释"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal

from dbgpt.core import (
    ChatPromptTemplate,
    HumanPromptTemplate,
    LLMClient,
    ModelMessage,
    ModelRequest,
    Chunk,
    Embeddings,
)
from dbgpt.datasource.base import BaseConnector
from dbgpt.storage.vector_store.base import VectorStoreBase

logger = logging.getLogger(__name__)


class SmartCommentGenerator:
    """智能注释生成器
    
    基于表结构和示例数据，使用大模型为数据库表和字段生成有意义的注释。
    这些注释将被保存到向量数据库中，提升RAG检索的准确性。
    """

    def __init__(
        self, 
        llm_client: Optional[LLMClient] = None,
        vector_store: Optional[VectorStoreBase] = None,
        embeddings: Optional[Embeddings] = None
    ):
        """初始化智能注释生成器
        
        Args:
            llm_client: LLM客户端，如果为None则需要在调用时提供
            vector_store: 向量数据库存储，用于保存智能注释
            embeddings: 嵌入模型，用于向量化注释内容
        """
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.embeddings = embeddings
        
        # 注释生成提示词模板
        self.comment_prompt_template = ChatPromptTemplate(
            messages=[
                HumanPromptTemplate.from_template(self._get_comment_generation_prompt())
            ]
        )

    def _get_comment_generation_prompt(self) -> str:
        """获取注释生成的提示词模板"""
        return """你是一个数据库专家，需要根据表结构和示例数据为数据库表和字段生成有意义的注释。

请分析以下表的结构和示例数据：

表名: {table_name}
字段结构:
{table_structure}

示例数据:
{sample_data}

请为这个表和每个字段生成简洁、准确的中文注释。注释应该：
1. 描述表的业务用途和功能
2. 说明每个字段的含义和作用
3. 基于示例数据推断字段的业务含义
4. 保持注释简洁明了，每个注释不超过50个字符
5. 禁止对未出现的数字、分类类型进行揣测

请按以下JSON格式返回结果：
{{
    "table_comment": "表的业务用途描述",
    "field_comments": {{
        "字段名1": "字段1的业务含义",
        "字段名2": "字段2的业务含义",
        ...
    }}
}}

只返回JSON格式的结果，不要包含其他内容。"""

    async def generate_table_comments(
        self, 
        connector: BaseConnector, 
        table_name: str,
        llm_client: Optional[LLMClient] = None
    ) -> Dict[str, Any]:
        """为指定表生成智能注释
        
        Args:
            connector: 数据库连接器
            table_name: 表名
            llm_client: LLM客户端
            
        Returns:
            包含表注释和字段注释的字典
        """
        client = llm_client or self.llm_client
        if not client:
            raise ValueError("LLM client is required")
        
        try:
            logger.info(f"开始为表 {table_name} 生成智能注释")
            
            # 获取表结构
            table_structure = await self._get_table_structure(connector, table_name)
            if not table_structure:
                logger.warning(f"无法获取表 {table_name} 的结构")
                return self._get_default_comments(table_name, [])
            
            # 获取示例数据
            sample_data = await self._get_sample_data(connector, table_name, limit=3)
            
            # 格式化数据用于LLM
            formatted_structure = self._format_table_structure(table_structure)
            formatted_sample = self._format_sample_data(sample_data)
            
            # 调用LLM生成注释
            comments = await self._call_llm_for_comments(
                client, table_name, formatted_structure, formatted_sample
            )
            
            logger.info(f"成功为表 {table_name} 生成智能注释")
            return comments
            
        except Exception as e:
            logger.error(f"为表 {table_name} 生成注释失败: {e}")
            # 返回默认注释
            return self._get_default_comments(table_name, table_structure or [])

    async def _get_table_structure(self, connector: BaseConnector, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        try:
            with connector.session_scope() as session:
                # 获取列信息
                from sqlalchemy import text
                result = session.execute(text(f"DESCRIBE `{table_name}`"))
                columns = result.fetchall()
                
                structure = []
                for col in columns:
                    structure.append({
                        "field": col[0],
                        "type": col[1],
                        "null": col[2],
                        "key": col[3],
                        "default": col[4],
                        "extra": col[5] if len(col) > 5 else ""
                    })
                
                return structure
                
        except Exception as e:
            logger.warning(f"获取表 {table_name} 结构失败: {e}")
            return []

    async def _get_sample_data(self, connector: BaseConnector, table_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """获取表的示例数据"""
        try:
            # 动态生成SQL查询
            dialect = getattr(connector, 'dialect', 'mysql')
            
            if dialect in ['mysql', 'postgresql']:
                limit_clause = f"LIMIT {limit}"
                table_quote = f"`{table_name}`"
            elif dialect == 'sqlite':
                limit_clause = f"LIMIT {limit}"
                table_quote = f'"{table_name}"'
            elif dialect in ['mssql', 'sqlserver']:
                limit_clause = f"TOP {limit}"
                table_quote = f"[{table_name}]"
            elif dialect == 'oracle':
                limit_clause = f"WHERE ROWNUM <= {limit}"
                table_quote = f'"{table_name}"'
            else:
                limit_clause = f"LIMIT {limit}"
                table_quote = f"`{table_name}`"
            
            # 构建查询SQL
            if dialect == 'mssql' or dialect == 'sqlserver':
                sql = f"SELECT {limit_clause} * FROM {table_quote}"
            elif dialect == 'oracle':
                sql = f"SELECT * FROM {table_quote} {limit_clause}"
            else:
                sql = f"SELECT * FROM {table_quote} {limit_clause}"
            
            with connector.session_scope() as session:
                from sqlalchemy import text
                result = session.execute(text(sql))
                rows = result.fetchall()
                
                # 处理数据，确保JSON序列化兼容
                sample_data = []
                for row in rows:
                    processed_row = {}
                    
                    # 将SQLAlchemy Row对象转换为字典
                    if hasattr(row, '_asdict'):
                        row_dict = row._asdict()
                    elif hasattr(row, 'keys'):
                        row_dict = {key: row[key] for key in row.keys()}
                    else:
                        row_dict = dict(row)
                    
                    # 处理不能JSON序列化的数据类型
                    for key, value in row_dict.items():
                        if isinstance(value, (datetime, date)):
                            processed_row[key] = value.isoformat()
                        elif isinstance(value, Decimal):
                            processed_row[key] = float(value)
                        elif value is None:
                            processed_row[key] = None
                        else:
                            try:
                                json.dumps(value)  # 测试是否可以JSON序列化
                                processed_row[key] = value
                            except (TypeError, ValueError):
                                processed_row[key] = str(value)
                    
                    sample_data.append(processed_row)
                
                return sample_data
                
        except Exception as e:
            logger.warning(f"获取表 {table_name} 示例数据失败: {e}")
            return []

    def _format_table_structure(self, structure: List[Dict[str, Any]]) -> str:
        """格式化表结构为可读文本"""
        if not structure:
            return "无法获取表结构"
        
        formatted_lines = []
        for col in structure:
            line_parts = []
            line_parts.append(f"字段名: {col['field']}")
            line_parts.append(f"类型: {col['type']}")
            
            if col.get('null') == 'NO':
                line_parts.append("NOT NULL")
            
            if col.get('key') == 'PRI':
                line_parts.append("主键")
            elif col.get('key') == 'MUL':
                line_parts.append("索引")
            elif col.get('key') == 'UNI':
                line_parts.append("唯一索引")
            
            if col.get('default') is not None:
                line_parts.append(f"默认值: {col['default']}")
            
            if col.get('extra'):
                line_parts.append(f"额外: {col['extra']}")
            
            formatted_lines.append(" | ".join(line_parts))
        
        return "\n".join(formatted_lines)

    def _format_sample_data(self, sample_data: List[Dict[str, Any]]) -> str:
        """格式化示例数据为可读文本"""
        if not sample_data:
            return "无示例数据"
        
        try:
            return json.dumps(sample_data, ensure_ascii=False, indent=2)
        except Exception:
            return "示例数据格式化失败"

    async def _call_llm_for_comments(
        self, 
        llm_client: LLMClient, 
        table_name: str, 
        table_structure: str, 
        sample_data: str
    ) -> Dict[str, Any]:
        """调用LLM生成注释"""
        try:
            # 准备提示词参数
            prompt_kwargs = {
                "table_name": table_name,
                "table_structure": table_structure,
                "sample_data": sample_data
            }
            
            # 格式化提示词
            messages = self.comment_prompt_template.format_messages(**prompt_kwargs)
            model_messages = ModelMessage.from_base_messages(messages)
            
            # 构建请求 - 使用通用模型名称或从LLM客户端获取
            model_name = getattr(llm_client, 'model_name', None) or "qwen-plus"
            model_request = ModelRequest.build_request(
                model=model_name,
                messages=model_messages,
                temperature=0.1,  # 低温度确保输出稳定
                max_new_tokens=5000  # 🔧 增加token限制以支持大表的智能注释
            )
            
            # 调用LLM
            model_output = await llm_client.generate(model_request)
            
            if not model_output.success:
                raise ValueError(f"LLM调用失败: {model_output.text}")
            
            # 解析LLM输出
            response_text = model_output.text.strip()
            
            # 尝试解析JSON
            try:
                comments = json.loads(response_text)
                
                # 验证返回格式
                if not isinstance(comments, dict):
                    raise ValueError("LLM返回格式不正确")
                
                if "table_comment" not in comments:
                    comments["table_comment"] = f"{table_name}表"
                
                if "field_comments" not in comments:
                    comments["field_comments"] = {}
                
                return comments
                
            except json.JSONDecodeError as e:
                logger.warning(f"解析LLM JSON输出失败: {e}, 原始输出: {response_text}")
                # 尝试从文本中提取有用信息
                return self._parse_text_response(response_text, table_name)
                
        except Exception as e:
            logger.error(f"调用LLM生成注释失败: {e}")
            raise

    def _parse_text_response(self, response_text: str, table_name: str) -> Dict[str, Any]:
        """从文本响应中解析注释信息"""
        # 简单的文本解析逻辑
        comments = {
            "table_comment": f"{table_name}数据表",
            "field_comments": {}
        }
        
        # 尝试从文本中提取表注释
        if "表" in response_text and "用于" in response_text:
            lines = response_text.split('\n')
            for line in lines:
                if "表" in line and ("用于" in line or "存储" in line or "记录" in line):
                    comments["table_comment"] = line.strip()[:50]
                    break
        
        return comments

    def _get_default_comments(self, table_name: str, structure: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取默认注释"""
        comments = {
            "table_comment": f"{table_name}数据表",
            "field_comments": {}
        }
        
        # 为每个字段生成简单的默认注释
        for col in structure:
            field_name = col.get('field', '')
            field_type = col.get('type', '')
            
            # 基于字段名和类型生成简单注释
            if 'id' in field_name.lower():
                comments["field_comments"][field_name] = "标识符"
            elif 'name' in field_name.lower():
                comments["field_comments"][field_name] = "名称"
            elif 'time' in field_name.lower() or 'date' in field_name.lower():
                comments["field_comments"][field_name] = "时间"
            elif 'status' in field_name.lower():
                comments["field_comments"][field_name] = "状态"
            elif 'type' in field_name.lower():
                comments["field_comments"][field_name] = "类型"
            elif 'code' in field_name.lower():
                comments["field_comments"][field_name] = "编码"
            elif 'amount' in field_name.lower() or 'money' in field_name.lower():
                comments["field_comments"][field_name] = "金额"
            elif 'count' in field_name.lower() or 'num' in field_name.lower():
                comments["field_comments"][field_name] = "数量"
            else:
                # 基于数据类型生成默认注释
                if 'int' in field_type.lower():
                    comments["field_comments"][field_name] = "整数字段"
                elif 'varchar' in field_type.lower() or 'char' in field_type.lower():
                    comments["field_comments"][field_name] = "文本字段"
                elif 'decimal' in field_type.lower() or 'float' in field_type.lower():
                    comments["field_comments"][field_name] = "数值字段"
                elif 'date' in field_type.lower() or 'time' in field_type.lower():
                    comments["field_comments"][field_name] = "日期时间字段"
                else:
                    comments["field_comments"][field_name] = f"{field_name}字段"
        
        return comments

    async def batch_generate_comments(
        self, 
        connector: BaseConnector, 
        table_names: List[str],
        llm_client: Optional[LLMClient] = None,
        max_concurrent: int = 3
    ) -> Dict[str, Dict[str, Any]]:
        """批量生成表注释
        
        Args:
            connector: 数据库连接器
            table_names: 表名列表
            llm_client: LLM客户端
            max_concurrent: 最大并发数
            
        Returns:
            表名到注释的映射
        """
        import asyncio
        
        client = llm_client or self.llm_client
        if not client:
            raise ValueError("LLM client is required")
        
        logger.info(f"开始批量生成 {len(table_names)} 个表的注释")
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(table_name: str) -> Tuple[str, Dict[str, Any]]:
            async with semaphore:
                comments = await self.generate_table_comments(connector, table_name, client)
                return table_name, comments
        
        # 并发生成注释
        tasks = [generate_with_semaphore(table_name) for table_name in table_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        all_comments = {}
        success_count = 0
        
        for i, result in enumerate(results):
            table_name = table_names[i]
            
            if isinstance(result, Exception):
                logger.error(f"生成表 {table_name} 注释失败: {result}")
                # 使用默认注释
                all_comments[table_name] = self._get_default_comments(table_name, [])
            else:
                table_name, comments = result
                all_comments[table_name] = comments
                success_count += 1
        
        logger.info(f"批量注释生成完成: {success_count}/{len(table_names)} 成功")
        return all_comments

    async def save_comments_to_vector_store(
        self,
        table_name: str,
        comments: Dict[str, Any],
        connector: BaseConnector,
        vector_store: Optional[VectorStoreBase] = None,
        embeddings: Optional[Embeddings] = None
    ) -> List[str]:
        """将智能注释保存到向量数据库
        
        Args:
            table_name: 表名
            comments: 包含表注释和字段注释的字典
            connector: 数据库连接器
            vector_store: 向量数据库存储
            embeddings: 嵌入模型
            
        Returns:
            保存的chunk ID列表
        """
        store = vector_store or self.vector_store
        embed_model = embeddings or self.embeddings
        
        if not store:
            raise ValueError("Vector store is required for saving comments")
        
        if not embed_model:
            raise ValueError("Embeddings model is required for saving comments")
        
        try:
            logger.info(f"开始保存表 {table_name} 的智能注释到向量数据库")
            
            chunks = []
            
            # 创建表注释的chunk
            table_comment = comments.get("table_comment", f"{table_name}数据表")
            table_content = f"表名: {table_name}\n表注释: {table_comment}"
            
            # 获取表的基本信息用于增强内容
            try:
                table_structure = await self._get_table_structure(connector, table_name)
                if table_structure:
                    field_names = [col['field'] for col in table_structure]
                    table_content += f"\n包含字段: {', '.join(field_names)}"
            except Exception as e:
                logger.warning(f"获取表 {table_name} 结构信息失败: {e}")
            
            table_chunk = Chunk(
                content=table_content,
                metadata={
                    "table_name": table_name,
                    "type": "table_comment",
                    "source": "smart_comment_generator",
                    "comment_type": "ai_generated"
                }
            )
            chunks.append(table_chunk)
            
            # 创建字段注释的chunks
            field_comments = comments.get("field_comments", {})
            for field_name, field_comment in field_comments.items():
                field_content = f"表名: {table_name}\n字段名: {field_name}\n字段注释: {field_comment}"
                
                # 尝试获取字段的详细信息
                try:
                    if table_structure:
                        field_info = next((col for col in table_structure if col['field'] == field_name), None)
                        if field_info:
                            field_content += f"\n字段类型: {field_info['type']}"
                            if field_info.get('key') == 'PRI':
                                field_content += "\n主键字段"
                            elif field_info.get('key'):
                                field_content += f"\n索引类型: {field_info['key']}"
                except Exception as e:
                    logger.warning(f"获取字段 {field_name} 详细信息失败: {e}")
                
                field_chunk = Chunk(
                    content=field_content,
                    metadata={
                        "table_name": table_name,
                        "field_name": field_name,
                        "type": "field_comment",
                        "source": "smart_comment_generator",
                        "comment_type": "ai_generated"
                    }
                )
                chunks.append(field_chunk)
            
            # 保存到向量数据库
            chunk_ids = store.load_document_with_limit(chunks)
            
            logger.info(f"成功保存表 {table_name} 的 {len(chunks)} 个智能注释到向量数据库")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"保存表 {table_name} 智能注释到向量数据库失败: {e}")
            raise

    async def generate_and_save_table_comments(
        self,
        connector: BaseConnector,
        table_name: str,
        llm_client: Optional[LLMClient] = None,
        vector_store: Optional[VectorStoreBase] = None,
        embeddings: Optional[Embeddings] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """生成并保存表的智能注释
        
        Args:
            connector: 数据库连接器
            table_name: 表名
            llm_client: LLM客户端
            vector_store: 向量数据库存储
            embeddings: 嵌入模型
            
        Returns:
            包含注释内容和保存的chunk ID列表的元组
        """
        # 生成注释
        comments = await self.generate_table_comments(connector, table_name, llm_client)
        
        # 保存到向量数据库
        chunk_ids = await self.save_comments_to_vector_store(
            table_name, comments, connector, vector_store, embeddings
        )
        
        return comments, chunk_ids

    async def batch_generate_and_save_comments(
        self,
        connector: BaseConnector,
        table_names: List[str],
        llm_client: Optional[LLMClient] = None,
        vector_store: Optional[VectorStoreBase] = None,
        embeddings: Optional[Embeddings] = None,
        max_concurrent: int = 3
    ) -> Dict[str, Tuple[Dict[str, Any], List[str]]]:
        """批量生成并保存表注释
        
        Args:
            connector: 数据库连接器
            table_names: 表名列表
            llm_client: LLM客户端
            vector_store: 向量数据库存储
            embeddings: 嵌入模型
            max_concurrent: 最大并发数
            
        Returns:
            表名到(注释内容, chunk ID列表)的映射
        """
        import asyncio
        
        client = llm_client or self.llm_client
        store = vector_store or self.vector_store
        embed_model = embeddings or self.embeddings
        
        if not client:
            raise ValueError("LLM client is required")
        if not store:
            raise ValueError("Vector store is required")
        if not embed_model:
            raise ValueError("Embeddings model is required")
        
        logger.info(f"开始批量生成并保存 {len(table_names)} 个表的注释")
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_and_save_with_semaphore(table_name: str) -> Tuple[str, Tuple[Dict[str, Any], List[str]]]:
            async with semaphore:
                comments, chunk_ids = await self.generate_and_save_table_comments(
                    connector, table_name, client, store, embed_model
                )
                return table_name, (comments, chunk_ids)
        
        # 并发生成并保存注释
        tasks = [generate_and_save_with_semaphore(table_name) for table_name in table_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        all_results = {}
        success_count = 0
        
        for i, result in enumerate(results):
            table_name = table_names[i]
            
            if isinstance(result, Exception):
                logger.error(f"生成并保存表 {table_name} 注释失败: {result}")
                # 使用默认注释
                default_comments = self._get_default_comments(table_name, [])
                try:
                    chunk_ids = await self.save_comments_to_vector_store(
                        table_name, default_comments, connector, store, embed_model
                    )
                    all_results[table_name] = (default_comments, chunk_ids)
                except Exception as save_error:
                    logger.error(f"保存表 {table_name} 默认注释失败: {save_error}")
                    all_results[table_name] = (default_comments, [])
            else:
                table_name, (comments, chunk_ids) = result
                all_results[table_name] = (comments, chunk_ids)
                success_count += 1
        
        logger.info(f"批量注释生成并保存完成: {success_count}/{len(table_names)} 成功")
        return all_results
