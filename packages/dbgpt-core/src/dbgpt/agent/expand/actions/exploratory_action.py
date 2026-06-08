"""探索性查询Action，用于在正式查询前先探索数据库表结构和样本数据。"""

import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from dbgpt._private.pydantic import BaseModel, Field

from ...core.action.base import Action, ActionOutput
from ...resource.base import AgentResource, ResourceType
from ...resource.database import DBResource

logger = logging.getLogger(__name__)


class ExploratoryInput(BaseModel):
    """探索性查询输入模型."""

    selected_tables: List[str] = Field(
        ...,
        description="从所有可用表中选择的3个用于探索的表名列表，应该选择与用户问题最相关的表"
    )
    reasoning: str = Field(
        ...,
        description="选择这些表的理由，解释为什么这些表与用户问题相关"
    )


class ExploratoryAction(Action[ExploratoryInput]):
    """探索性查询Action类。
    
    该Action用于在正式的数据科学查询之前，先让LLM从可用表中选择3个最相关的表，
    然后查询这些表的前5行数据，为后续的查询提供上下文信息。
    """

    def __init__(self, **kwargs):
        """初始化探索性查询action。"""
        super().__init__(**kwargs)

    @property
    def resource_need(self) -> Optional[ResourceType]:
        """返回Action所需的资源类型。"""
        return ResourceType.DB

    @property
    def out_model_type(self):
        """返回输出模型类型。"""
        return ExploratoryInput

    async def run(
        self,
        ai_message: str,
        resource: Optional[AgentResource] = None,
        rely_action_out: Optional[ActionOutput] = None,
        need_vis_render: bool = True,
        **kwargs,
    ) -> ActionOutput:
        """执行探索性查询。
        
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
            param: ExploratoryInput = self._input_convert(ai_message, ExploratoryInput)
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
                    # 查询表的基本信息和前5行数据
                    # 根据数据库类型选择合适的表名引用方式
                    db_type = getattr(db, 'db_type', 'mysql').lower()
                    
                    if db_type in ['mysql', 'mariadb']:
                        safe_table_name = f"`{table_name}`"
                    elif db_type in ['postgresql', 'postgres']:
                        safe_table_name = f'"{table_name}"'
                    elif db_type in ['sqlite']:
                        safe_table_name = f'"{table_name}"'
                    elif db_type in ['sqlserver', 'mssql']:
                        safe_table_name = f"[{table_name}]"
                    else:
                        # 默认尝试双引号，如果失败则不加引号
                        safe_table_name = f'"{table_name}"'
                    
                    # 根据数据库类型构建LIMIT语句
                    if db_type in ['sqlserver', 'mssql']:
                        sample_sql = f"SELECT TOP 5 * FROM {safe_table_name}"
                    elif db_type in ['oracle']:
                        sample_sql = f"SELECT * FROM {safe_table_name} WHERE ROWNUM <= 5"
                    else:
                        # MySQL, PostgreSQL, SQLite等
                        sample_sql = f"SELECT * FROM {safe_table_name} LIMIT 5"
                    
                    try:
                        columns, values = await db.query(sample_sql)
                    except Exception as quote_error:
                        # 如果带引号的查询失败，尝试不带引号的查询
                        logger.warning(f"带引号的表名查询失败，尝试不带引号: {quote_error}")
                        
                        if db_type in ['sqlserver', 'mssql']:
                            fallback_sql = f"SELECT TOP 5 * FROM {table_name}"
                        elif db_type in ['oracle']:
                            fallback_sql = f"SELECT * FROM {table_name} WHERE ROWNUM <= 5"
                        else:
                            fallback_sql = f"SELECT * FROM {table_name} LIMIT 5"
                        
                        columns, values = await db.query(fallback_sql)
                    
                    # 获取表的字段信息
                    # 将Row对象转换为可序列化的列表
                    serializable_data = []
                    if values:
                        for row in values[:5]:
                            try:
                                if hasattr(row, '_mapping'):
                                    # SQLAlchemy Row对象，转换为字典然后转为列表
                                    row_data = []
                                    for value in row._mapping.values():
                                        # 处理可能的特殊数据类型
                                        if value is None:
                                            row_data.append(None)
                                        elif isinstance(value, (str, int, float, bool)):
                                            row_data.append(value)
                                        elif isinstance(value, (datetime, date)):
                                            row_data.append(value.isoformat())
                                        elif isinstance(value, Decimal):
                                            row_data.append(float(value))
                                        else:
                                            # 其他类型转换为字符串
                                            row_data.append(str(value))
                                    serializable_data.append(row_data)
                                elif hasattr(row, '__iter__') and not isinstance(row, str):
                                    # 可迭代对象，转换为列表
                                    row_data = []
                                    for value in row:
                                        if value is None:
                                            row_data.append(None)
                                        elif isinstance(value, (str, int, float, bool)):
                                            row_data.append(value)
                                        elif isinstance(value, (datetime, date)):
                                            row_data.append(value.isoformat())
                                        elif isinstance(value, Decimal):
                                            row_data.append(float(value))
                                        else:
                                            row_data.append(str(value))
                                    serializable_data.append(row_data)
                                else:
                                    # 其他情况，转换为字符串
                                    serializable_data.append([str(row)])
                            except Exception as row_error:
                                logger.warning(f"处理行数据时出错: {row_error}, row: {row}")
                                serializable_data.append([f"数据处理错误: {str(row_error)}"])
                    
                    table_info = {
                        "table_name": table_name,
                        "columns": list(columns) if columns else [],
                        "sample_data": serializable_data,
                        "sample_count": len(values) if values else 0
                    }
                    exploration_results.append(table_info)
                    
                    logger.info(f"成功探索表 {table_name}，获取了 {len(values) if values else 0} 行样本数据")
                    
                except Exception as table_error:
                    logger.warning(f"探索表 {table_name} 时出错: {str(table_error)}")
                    # 即使某个表查询失败，也继续其他表的查询
                    table_info = {
                        "table_name": table_name,
                        "columns": [],
                        "sample_data": [],
                        "sample_count": 0,
                        "error": str(table_error)
                    }
                    exploration_results.append(table_info)
            
            # 构建结果内容
            result_content = {
                "selected_tables": selected_tables,
                "reasoning": param.reasoning,
                "exploration_results": exploration_results,
                "total_tables_explored": len(exploration_results),
                "action_type": "exploratory_query"
            }
            
            content = json.dumps(result_content, ensure_ascii=False, indent=2)
            
            return ActionOutput(
                is_exe_success=True,
                content=content,
                resource_type=self.resource_need.value,
                resource_value=db._db_name,
                action="exploratory_query",
                action_input=f"探索表: {', '.join(selected_tables)}",
                thoughts=param.reasoning,
            )
            
        except Exception as e:
            logger.exception(f"探索性查询执行失败: {str(e)}")
            return ActionOutput(
                is_exe_success=False, 
                content=f"探索性查询执行失败: {str(e)}"
            )
