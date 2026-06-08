"""优化的探索性查询Action，解决大量表导致的RAG性能问题。"""

import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any

from dbgpt._private.pydantic import BaseModel, Field

from ...core.action.base import Action, ActionOutput
from ...resource.base import AgentResource, ResourceType
from ...resource.database import DBResource

logger = logging.getLogger(__name__)


class OptimizedExploratoryInput(BaseModel):
    """优化的探索性查询输入模型."""

    selected_tables: List[str] = Field(
        ...,
        description="从筛选后的相关表中选择的3个用于探索的表名列表，应该选择与用户问题最相关的表"
    )
    reasoning: str = Field(
        ...,
        description="选择这些表的理由，解释为什么这些表与用户问题相关"
    )


class OptimizedExploratoryAction(Action[OptimizedExploratoryInput]):
    """优化的探索性查询Action类。
    
    主要优化：
    1. 智能表过滤：预先过滤掉空表和系统表
    2. 相关性排序：根据用户查询对表进行相关性排序
    3. 限制表数量：只向LLM提供最相关的表，避免token溢出
    4. 缓存机制：缓存表分析结果
    """

    def __init__(self, **kwargs):
        """初始化优化的探索性查询action。"""
        super().__init__(**kwargs)
        
        # 优化参数
        self._max_tables_for_llm = 20  # 向LLM提供的最大表数量
        self._empty_table_threshold = 0
        self._cache = {}  # 简单的内存缓存
        
        # 系统表模式
        self._system_table_patterns = [
            'information_schema', 'performance_schema', 'mysql', 'sys',
            'pg_catalog', 'pg_toast', '__', 'sqlite_', 'msreplication_',
            'sysdiagrams', 'dtproperties'
        ]
        
        # 业务关键词
        self._business_keywords = [
            'user', 'order', 'product', 'customer', 'sales', 'invoice',
            'payment', 'transaction', 'account', 'item', 'service', 'data',
            '用户', '订单', '产品', '客户', '销售', '发票', '支付', '交易', '账户', '商品', '服务'
        ]

    @property
    def resource_need(self) -> Optional[ResourceType]:
        """返回Action所需的资源类型。"""
        return ResourceType.DB

    @property
    def out_model_type(self):
        """返回输出模型类型。"""
        return OptimizedExploratoryInput

    def _extract_user_question(self, ai_message: str) -> str:
        """从AI消息中提取用户问题。"""
        # 尝试从消息中提取用户问题
        import re
        
        # 查找"用户输入:"或"用户问题:"等模式
        patterns = [
            r"用户输入:\s*(.*?)(?:\n|$)",
            r"用户问题:\s*(.*?)(?:\n|$)",
            r"问题:\s*(.*?)(?:\n|$)",
            r"查询:\s*(.*?)(?:\n|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ai_message)
            if match:
                return match.group(1).strip()
        
        # 如果没有找到特定模式，返回消息的前100个字符
        return ai_message[:100]

    def _filter_and_rank_tables(self, connector, user_question: str) -> List[str]:
        """过滤和排序表，返回最相关的表。"""
        cache_key = f"{id(connector)}_{hash(user_question)}"
        
        # 检查缓存
        if cache_key in self._cache:
            logger.info("使用缓存的表过滤结果")
            return self._cache[cache_key]
        
        try:
            # 获取所有表名
            all_tables = list(connector.get_table_names())
            logger.info(f"数据库包含 {len(all_tables)} 个表，开始过滤和排序")
            
            # 分析每个表的优先级
            table_scores = []
            
            for table_name in all_tables:
                score = self._calculate_table_relevance_score(connector, table_name, user_question)
                if score > 0:  # 只保留有意义的表
                    table_scores.append((table_name, score))
            
            # 按评分排序并限制数量
            table_scores.sort(key=lambda x: x[1], reverse=True)
            relevant_tables = [name for name, _ in table_scores[:self._max_tables_for_llm]]
            
            # 缓存结果
            self._cache[cache_key] = relevant_tables
            
            logger.info(f"过滤后保留 {len(relevant_tables)} 个相关表")
            return relevant_tables
            
        except Exception as e:
            logger.warning(f"表过滤失败，使用原始方法: {e}")
            # 回退到简单截断
            all_tables = list(connector.get_table_names())
            return all_tables[:self._max_tables_for_llm]

    def _calculate_table_relevance_score(self, connector, table_name: str, user_question: str) -> float:
        """计算表的相关性评分。"""
        table_name_lower = table_name.lower()
        score = 0.0
        
        # 系统表 - 忽略
        if any(pattern in table_name_lower for pattern in self._system_table_patterns):
            return 0.0
        
        try:
            # 获取表的行数
            with connector.session_scope() as session:
                result = session.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                row_count = result.fetchone()[0]
                
                # 空表 - 低优先级
                if row_count <= self._empty_table_threshold:
                    return 0.1  # 给一个很小的分数
                
                # 数据量评分
                if row_count > 1000:
                    score += 3.0
                elif row_count > 100:
                    score += 2.0
                elif row_count > 10:
                    score += 1.0
                else:
                    score += 0.5
                    
        except Exception:
            # 如果无法获取行数，给默认分数
            score += 1.0
        
        # 业务相关性评分
        business_score = sum(
            1.0 for keyword in self._business_keywords 
            if keyword in table_name_lower
        )
        score += business_score
        
        # 查询相关性评分
        if user_question:
            query_keywords = self._extract_query_keywords(user_question)
            if any(keyword in table_name_lower for keyword in query_keywords):
                score += 2.0
        
        return score

    def _extract_query_keywords(self, query: str) -> List[str]:
        """从用户查询中提取关键词。"""
        import re
        
        # 移除常见停用词
        stopwords = {'的', '是', '在', '有', '和', '与', '或', '查询', '显示', '统计', '分析', 'select', 'from', 'where'}
        
        # 提取中英文单词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query.lower())
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        return keywords

    async def run(
        self,
        ai_message: str,
        resource: Optional[AgentResource] = None,
        rely_action_out: Optional[ActionOutput] = None,
        need_vis_render: bool = True,
        **kwargs,
    ) -> ActionOutput:
        """执行优化的探索性查询。
        
        Args:
            ai_message: AI生成的消息，包含选择的表和理由
            resource: 数据库资源
            rely_action_out: 依赖的Action输出
            need_vis_render: 是否需要可视化渲染
            **kwargs: 其他参数
            
        Returns:
            ActionOutput: 包含探索性查询结果的输出
        """
        try:
            param: OptimizedExploratoryInput = self._input_convert(ai_message, OptimizedExploratoryInput)
        except Exception as e:
            logger.exception(f"解析探索性查询参数失败: {str(e)}! \n {ai_message}")
            return ActionOutput(
                is_exe_success=False,
                content=f"解析探索性查询参数失败: {str(e)}",
            )

        try:
            if not self.resource_need:
                raise ValueError("未找到所需的资源类型！")

            db_resources: List[DBResource] = DBResource.from_resource(self.resource)
            if not db_resources:
                raise ValueError("未找到数据库资源！")

            db = db_resources[0]
            
            # 限制选择的表数量为3个
            selected_tables = param.selected_tables[:3]
            if len(selected_tables) == 0:
                raise ValueError("至少需要选择一个表进行探索")
            
            exploration_results = []
            
            # 对每个选择的表查询前5行数据
            for table_name in selected_tables:
                try:
                    logger.info(f"开始探索表: {table_name}")
                    
                    # 动态生成SQL查询
                    dialect = db.dialect
                    if dialect in ['mysql', 'postgresql']:
                        # MySQL和PostgreSQL支持LIMIT
                        limit_clause = "LIMIT 5"
                        table_quote = f"`{table_name}`"
                    elif dialect == 'sqlite':
                        limit_clause = "LIMIT 5"
                        table_quote = f'"{table_name}"'
                    elif dialect in ['mssql', 'sqlserver']:
                        # SQL Server使用TOP
                        limit_clause = "TOP 5"
                        table_quote = f"[{table_name}]"
                    elif dialect == 'oracle':
                        # Oracle使用ROWNUM
                        limit_clause = "WHERE ROWNUM <= 5"
                        table_quote = f'"{table_name}"'
                    else:
                        # 默认使用LIMIT
                        limit_clause = "LIMIT 5"
                        table_quote = f"`{table_name}`"
                    
                    # 构建查询SQL
                    if dialect == 'mssql' or dialect == 'sqlserver':
                        sql = f"SELECT {limit_clause} * FROM {table_quote}"
                    elif dialect == 'oracle':
                        sql = f"SELECT * FROM {table_quote} {limit_clause}"
                    else:
                        sql = f"SELECT * FROM {table_quote} {limit_clause}"
                    
                    logger.info(f"执行SQL: {sql}")
                    
                    # 执行查询
                    result = await db.query(sql)
                    
                    # 处理结果数据，确保JSON序列化兼容
                    processed_data = []
                    if result:
                        columns, values = result
                        for row in values:
                            processed_row = {}
                            
                            # 处理不同类型的row数据
                            if isinstance(row, (tuple, list)):
                                # 如果row是元组或列表，使用列名作为key
                                for i, value in enumerate(row):
                                    col_name = columns[i] if i < len(columns) else f"col_{i}"
                                    processed_row[col_name] = self._serialize_value(value)
                            elif hasattr(row, '_asdict'):
                                # SQLAlchemy Row对象
                                row_dict = row._asdict()
                                for key, value in row_dict.items():
                                    processed_row[key] = self._serialize_value(value)
                            elif hasattr(row, 'keys'):
                                # 字典类型或有keys方法的对象
                                for key in row.keys():
                                    processed_row[key] = self._serialize_value(row[key])
                            else:
                                # 尝试转换为字典
                                try:
                                    row_dict = dict(row)
                                    for key, value in row_dict.items():
                                        processed_row[key] = self._serialize_value(value)
                                except:
                                    # 如果都失败了，将row转换为字符串
                                    processed_row["data"] = str(row)
                            
                            processed_data.append(processed_row)
                    
                    exploration_results.append({
                        "table_name": table_name,
                        "sample_data": processed_data,
                        "row_count": len(processed_data),
                        "status": "success"
                    })
                    
                    logger.info(f"成功探索表 {table_name}，获取 {len(processed_data)} 行数据")
                    
                except Exception as table_error:
                    logger.error(f"探索表 {table_name} 时出错: {table_error}")
                    exploration_results.append({
                        "table_name": table_name,
                        "sample_data": [],
                        "row_count": 0,
                        "status": "error",
                        "error": str(table_error)
                    })
            
            # 构建完整的探索结果，包含DataScientistAgent期望的格式
            complete_result = {
                "selected_tables": selected_tables,
                "reasoning": f"基于智能评分系统选择了 {len(selected_tables)} 个最相关的表进行探索",
                "exploration_results": exploration_results,
                "total_explored_tables": len(selected_tables),
                "successful_explorations": len([r for r in exploration_results if r.get("status") == "success"])
            }
            
            result_content = json.dumps(complete_result, ensure_ascii=False, indent=2)
            
            logger.info("探索性查询完成")
            return ActionOutput(
                is_exe_success=True,
                content=result_content,
            )
            
        except Exception as e:
            logger.exception(f"执行探索性查询时发生错误: {str(e)}")
            return ActionOutput(
                is_exe_success=False,
                content=f"执行探索性查询失败: {str(e)}",
            )

    def get_filtered_table_info_for_llm(self, connector, user_question: str) -> str:
        """获取过滤后的表信息，用于提供给LLM。"""
        try:
            # 获取过滤后的相关表
            relevant_tables = self._filter_and_rank_tables(connector, user_question)
            
            if not relevant_tables:
                return "未找到相关表"
            
            # 构建紧凑的表信息描述
            table_info = f"数据库包含以下 {len(relevant_tables)} 个相关表：\n"
            
            for i, table_name in enumerate(relevant_tables, 1):
                try:
                    # 获取表的基本信息
                    with connector.session_scope() as session:
                        # 获取行数
                        result = session.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                        row_count = result.fetchone()[0]
                        
                        # 获取列数（简化版）
                        try:
                            result = session.execute(f"DESCRIBE `{table_name}`")
                            columns = result.fetchall()
                            column_count = len(columns)
                            
                            # 获取前几个列名
                            column_names = [col[0] for col in columns[:5]]
                            column_info = ", ".join(column_names)
                            if len(columns) > 5:
                                column_info += f"... (共{column_count}列)"
                            
                        except:
                            column_count = 0
                            column_info = "无法获取列信息"
                    
                    table_info += f"{i}. {table_name} ({row_count}行, {column_count}列): {column_info}\n"
                    
                except Exception as e:
                    table_info += f"{i}. {table_name} (无法获取详细信息: {e})\n"
            
            return table_info
            
        except Exception as e:
            logger.error(f"获取过滤表信息失败: {e}")
            return f"获取表信息失败: {e}"

    def _serialize_value(self, value):
        """序列化值，确保JSON兼容"""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif value is None:
            return None
        else:
            try:
                # 尝试JSON序列化测试
                json.dumps(value)
                return value
            except (TypeError, ValueError):
                # 如果不能序列化，转换为字符串
                return str(value)
