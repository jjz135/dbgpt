"""Data Scientist Agent."""

import json
import logging
from typing import List, Optional, Tuple

from ..core.agent import AgentMessage
from ..core.base_agent import ConversableAgent
from ..core.profile import DynConfig, ProfileConfig
from ..resource.database import DBResource
from .actions.chart_action import ChartAction
from .actions.exploratory_action import ExploratoryAction
from .actions.optimized_exploratory_action import OptimizedExploratoryAction
from .prompts.exploratory_prompt import get_exploratory_prompt

logger = logging.getLogger(__name__)


class DataScientistAgent(ConversableAgent):
    """Data Scientist Agent."""

    profile: ProfileConfig = ProfileConfig(
        name=DynConfig(
            "Edgar",
            category="agent",
            key="dbgpt_agent_expand_dashboard_assistant_agent_profile_name",
        ),
        role=DynConfig(
            "DataScientist",
            category="agent",
            key="dbgpt_agent_expand_dashboard_assistant_agent_profile_role",
        ),
        goal=DynConfig(
            "Use one correct {{dialect}} SQL to analyze and resolve user "
            "input targets based on the data structure information of the "
            "database given in the resource.",
            category="agent",
            key="dbgpt_agent_expand_dashboard_assistant_agent_profile_goal",
        ),
        constraints=DynConfig(
            [
                "Please ensure that the output is in the required format. "
                "Please ensure that each analysis ONLY outputs 1 analysis "
                "result SQL, including as much analysis target content as possible.",
                "Please always use 'Select ... AS ...', and provide 中文简称 after AS,"
                "for example: 'Select quantity AS 数量 from DB;'",
                "If user mentioned an ID/Serial number/part number/code，"
                "check previous chat result for information.",
                "Please ensure that only using the content you are provided.",
                "If there is a recent message record, pay attention to refer to "
                "the answers and execution results inside when analyzing, "
                "and do not generate the same wrong answer.Please check carefully "
                "to make sure the correct SQL is generated. Please strictly adhere "
                "to the data structure definition given. The use of non-existing "
                "fields is prohibited. Be careful not to confuse fields from "
                "different tables, and you can perform multi-table related queries.",
                "If the data and fields that need to be analyzed in the target are in "
                "different tables, it is recommended to use multi-table correlation "
                "queries first, and pay attention to the correlation between multiple "
                "table structures.",
                "It is prohibited to construct data yourself as query conditions. "
                "Only the data values given by the famous songs in the input can "
                "be used as query conditions.",
                "If a general question is asked, for example:'is everything normal?',"
                "or 'how's the warehouse?',consider summarize data in a corporate level."
                "Do not use columns that has NULL or None value in your following steps."
                "If add/sum doesn't work(for example, string type data), use count.",
                "Some fields may be intentionally null. If your current logic returns no results, "
                "it's recommended to check other similar fields that also reflect the intended query semantics."
                "Please select an appropriate one from the supported display methods "
                "for data display. If no suitable display type is found, "
                "use 'response_table' as default value. Supported display types: \n"
                "{{ display_type }}",
            ],
            category="agent",
            key="dbgpt_agent_expand_dashboard_assistant_agent_profile_constraints",
        ),
        desc=DynConfig(
            "Use database resources to conduct data analysis, analyze SQL, and provide "
            "recommended rendering methods.",
            category="agent",
            key="dbgpt_agent_expand_dashboard_assistant_agent_profile_desc",
        ),
    )

    max_retry_count: int = 9
    language: str = "zh"

    def __init__(self, enable_rag_optimization: bool = True, **kwargs):
        """Create a new DataScientistAgent instance.
        
        Args:
            enable_rag_optimization: 是否启用RAG优化（默认启用）
        """
        super().__init__(**kwargs)
        self._init_actions([ChartAction])
        
        # 选择使用优化或原始的探索性Action
        if enable_rag_optimization:
            logger.info("启用RAG优化模式")
            self._exploratory_action = OptimizedExploratoryAction()
        else:
            logger.info("使用原始RAG模式")
            self._exploratory_action = ExploratoryAction()
        
        self._exploration_completed = False
        self._exploration_context = ""
        self._last_error_message = ""  # 记录上一次的错误消息，避免重复
        self._rag_optimization_enabled = enable_rag_optimization

    def _init_reply_message(
        self,
        received_message: AgentMessage,
        rely_messages: Optional[List[AgentMessage]] = None,
    ) -> AgentMessage:
        reply_message = super()._init_reply_message(received_message, rely_messages)
        reply_message.context = {
            "display_type": self.actions[0].render_prompt(),
            "dialect": self.database.dialect,
        }
        return reply_message

    @property
    def database(self) -> DBResource:
        """Get the database resource."""
        dbs: List[DBResource] = DBResource.from_resource(self.resource)
        if not dbs:
            raise ValueError(
                f"Resource type {self.actions[0].resource_need} is not supported."
            )
        return dbs[0]

    async def correctness_check(
        self, message: AgentMessage
    ) -> Tuple[bool, Optional[str]]:
        """Verify whether the current execution results meet the target expectations."""
        action_out = message.action_report
        if action_out is None:
            error_msg = f"No executable analysis SQL is generated,{message.content}."
            # 避免重复相同的错误消息
            if error_msg == self._last_error_message:
                return False, "重复错误，请尝试不同的解决方案"
            self._last_error_message = error_msg
            return False, error_msg

        if not action_out.is_exe_success:
            error_msg = f"Please check your answer, {action_out.content}."
            # 避免重复相同的错误消息
            if error_msg == self._last_error_message:
                return False, "重复错误，请尝试不同的解决方案"
            self._last_error_message = error_msg
            return False, error_msg
        action_reply_obj = json.loads(action_out.content)
        sql = action_reply_obj.get("sql", None)
        if not sql:
            return (
                False,
                "Please check your answer, the sql information that needs to be "
                "generated is not found.",
            )
        try:
            if not action_out.resource_value:
                return (
                    False,
                    "Please check your answer, the data resource information is not "
                    "found.",
                )

            columns, values = await self.database.query(
                sql=sql,
                db=action_out.resource_value,
            )

            # if not values or len(values) <= 0:
            #     return (
            #         False,
            #         "Please check your answer, the current SQL cannot find the data to "
            #         "determine whether filtered field values or inappropriate filter "
            #         "conditions are used.",
            #     )
            # else:
            #     logger.info(
            #         f"reply check success! There are {len(values)} rows of data"
            #     )
            #     return True, None

            retry_count = message.context.get("retry_count", 0)
            if values is None:
                return (
                    False,
                    "SQL execution returned None, please confirm if the table or query is valid.",
                )

            if isinstance(values, list):
                if len(values) == 0:
                    # 情况1：结果为空行
                    if retry_count + 1 >= self.max_retry_count:
                        logger.info(f"Max retry count reached ({retry_count}). No results returned.")
                        return True, "查询执行成功但无结果，可能原因：SQL过滤条件不正确或数据不存在"
                    elif retry_count < 3:
                        logger.info("SQL executed successfully but returned 0 rows")
                        return False, "查询执行成功但无结果，可能原因：SQL过滤条件不正确或数据确实为空。"
                    else:
                        logger.info("SQL executed successfully but returned 0 rows")
                        return False, "查询执行成功但无结果，可能原因：SQL过滤条件不正确或数据确实为空，同时请考虑使用其它字段或过滤条件或表。"
                else:
                    # 情况2：结果非空，检查是否全为null
                    # 处理SQLAlchemy Row对象和普通的list/ “tuple”
                    # 处理方式原因：当数据库返回null时，values为 [(None,)]
                    # 其中 (None,) 的数据类型看起来是tuple，但其实不是tuple 而是 type: <class 'sqlalchemy.engine.row.Row'>
                    all_none = all(
                        row is None or (
                                hasattr(row, '__iter__') and
                                all(v is None for v in row)
                        )
                        for row in values
                    )

                    if all_none:
                        logger.info(f"SQL executed successfully but all {len(values)} rows contain only NULL values")
                        return False, "查询执行成功但所有字段值均为NULL，SQL过滤条件不正确，请使用其它字段/过滤条件/表。"
                    else:
                        logger.info(f"Reply check success! There are {len(values)} rows of data")
                        logger.info(f"Reply values are: {values}")
                        return True, None

            # fallback分支：非 list 类型异常
            return (
                False,
                f"SQL execution returned unexpected data type: {type(values).__name__}.",
            )

        except Exception as e:
            logger.exception(f"DataScientist check exception！{str(e)}")
            return (
                False,
                f"SQL execution error, please re-read the historical information to "
                f"fix this SQL. The error message is as follows:{str(e)}",
            )

    async def thinking(
        self,
        messages: List[AgentMessage],
        sender = None,
        prompt: Optional[str] = None,
    ):
        """重写thinking方法以实现两阶段的数据分析流程。
        
        第一阶段：探索性查询 - 选择相关表并获取样本数据
        第二阶段：正式查询 - 基于探索结果生成SQL查询的思考
        """
        logger.info(f"DataScientist开始思考，探索完成状态: {self._exploration_completed}")
        
        # 如果还没有进行探索性查询，先执行第一阶段
        if not self._exploration_completed:
            logger.info("开始执行第一阶段：探索性查询")
            
            # 获取用户问题 - 只取最新的用户问题，避免历史重复
            user_question = ""
            if messages:
                for msg in reversed(messages):
                    if msg.role == "user" or msg.role == "human":
                        user_question = msg.content or ""
                        # 确保获取的是原始问题，而不是包含历史记录的长消息
                        if "最近消息记录:" not in user_question:
                            break
            
            # 获取数据库schema信息
            db_schema_info = ""
            try:
                db_prompt, _ = await self.database.get_prompt(
                    lang=self.language,
                    question=user_question
                )
                db_schema_info = db_prompt
            except Exception as e:
                logger.warning(f"获取数据库schema信息失败: {e}")
                db_schema_info = "无法获取数据库schema信息"
            
            # 构建探索性查询的prompt - 使用干净的prompt，不包含历史错误
            exploratory_prompt = get_exploratory_prompt(
                user_question=user_question,
                database_schema=db_schema_info,
                language=self.language
            )
            
            # 调用父类的thinking方法来让LLM进行表选择 - 使用干净的消息
            clean_message = AgentMessage(content=exploratory_prompt, role="system")
            llm_reply, model_name = await super().thinking(
                messages=[clean_message],
                sender=sender,
                prompt=exploratory_prompt
            )
            
            # 执行探索性查询Action
            exploratory_action = self._exploratory_action
            try:
                # 设置exploratory action的resource
                exploratory_action.resource = self.resource
                exploratory_result = await exploratory_action.run(
                    ai_message=llm_reply or "",
                    resource=None,
                    rely_action_out=None,
                )
                
                if exploratory_result.is_exe_success:
                    # 解析探索结果并构建上下文
                    exploration_data = json.loads(exploratory_result.content)
                    self._exploration_context = self._format_exploration_context(exploration_data)
                    self._exploration_completed = True
                    logger.info("第一阶段探索性查询完成")
                    
                    # 立即进入第二阶段：正式SQL查询思考
                    logger.info("立即进入第二阶段：正式SQL查询思考")
                    
                    # 验证和调整planner任务
                    task_validation_result = self._validate_and_adjust_task(user_question, exploration_data)
                    
                    # 构建增强的内容用于最终SQL生成
                    enhanced_content = f"""
用户问题: {user_question}

探索性查询结果:
{self._exploration_context}

{task_validation_result}

请基于以上探索结果和任务验证信息，生成合适的SQL查询和图表展示方案。请确保：
1. 优先使用任务验证推荐的字段和表
2. 参考样本数据来理解数据格式和数据质量
3. 避免使用包含大量null值的字段作为主要分析维度
4. 生成正确的SQL语法
5. 选择合适的图表类型
"""
                    
                    # 为第二阶段的LLM创建简洁的消息列表
                    system_messages = [msg for msg in messages if msg.role == "system"]
                    final_messages_for_llm = system_messages + [AgentMessage(content=enhanced_content, role="user")]
                    
                    # 调用父类的thinking进行最终SQL分析
                    return await super().thinking(final_messages_for_llm, sender, enhanced_content)
                else:
                    logger.error("探索性查询失败")
                    return f"探索性查询失败：{exploratory_result.content}", model_name
                    
            except Exception as e:
                logger.error(f"执行探索性查询时出错: {e}")
                return f"探索性查询执行失败：{str(e)}", model_name
        
        else:
            # 这个分支理论上不应该被执行到，因为探索完成后会立即进入第二阶段
            logger.warning("意外进入第二阶段分支，exploration_completed=True但未正确处理")
            return await super().thinking(messages, sender, prompt)

    def _format_exploration_context(self, exploration_data: dict) -> str:
        """格式化探索性查询的结果为可读的上下文信息。"""
        context_parts = []
        
        # 添加选择的表和理由
        selected_tables = exploration_data.get("selected_tables", [])
        reasoning = exploration_data.get("reasoning", "")
        context_parts.append(f"选择的表: {', '.join(selected_tables)}")
        context_parts.append(f"选择理由: {reasoning}")
        
        # 添加每个表的详细信息
        exploration_results = exploration_data.get("exploration_results", [])
        for table_info in exploration_results:
            table_name = table_info.get("table_name", "")
            columns = table_info.get("columns", [])
            sample_data = table_info.get("sample_data", [])
            sample_count = table_info.get("sample_count", 0)
            
            context_parts.append(f"\n表 {table_name}:")
            context_parts.append(f"  字段: {', '.join(columns)}")
            context_parts.append(f"  样本数据行数: {sample_count}")
            
            if sample_data and len(sample_data) > 0:
                context_parts.append("  样本数据:")
                for i, row in enumerate(sample_data[:3]):  # 只显示前3行
                    context_parts.append(f"    行{i+1}: {row}")
                    
            if table_info.get("error"):
                context_parts.append(f"  错误: {table_info['error']}")
        
        return "\n".join(context_parts)

    def _validate_and_adjust_task(self, user_question: str, exploration_data: dict) -> str:
        """验证和调整planner任务，检查字段有效性并推荐替代方案。"""
        logger.info("开始验证planner任务的字段有效性")
        
        # 提取任务中提到的字段名和表名
        mentioned_fields = self._extract_mentioned_fields(user_question)
        mentioned_tables = self._extract_mentioned_tables(user_question)
        
        # 分析探索结果，获取字段质量信息
        field_quality_analysis = self._analyze_field_quality(exploration_data)
        
        # 验证提到的字段是否存在且有效
        validation_results = []
        recommendations = []
        
        # 验证字段
        for field in mentioned_fields:
            field_status = self._validate_field(field, field_quality_analysis)
            validation_results.append(field_status)
            
            if not field_status["is_valid"]:
                # 寻找替代字段
                alternative = self._find_alternative_field(field, field_quality_analysis, user_question)
                if alternative:
                    recommendations.append(f"字段 '{field}' {field_status['reason']}，推荐使用 '{alternative['field']}' 替代（{alternative['reason']}）")
                else:
                    recommendations.append(f"字段 '{field}' {field_status['reason']}，未找到合适的替代字段")
        
        # 验证表名
        for table in mentioned_tables:
            table_status = self._validate_table(table, exploration_data)
            if not table_status["is_valid"]:
                alternative_table = self._find_alternative_table(table, exploration_data)
                if alternative_table:
                    recommendations.append(f"表 '{table}' 不存在，推荐使用 '{alternative_table}' 替代")
        
        # 主动推荐高质量字段
        quality_recommendations = self._recommend_quality_fields(field_quality_analysis, user_question)
        recommendations.extend(quality_recommendations)
        
        # 构建验证结果报告
        if validation_results or recommendations:
            result_parts = ["任务验证和调整建议:"]
            
            if any(not vr["is_valid"] for vr in validation_results):
                result_parts.append("\n【字段验证问题】")
                for vr in validation_results:
                    if not vr["is_valid"]:
                        result_parts.append(f"- {vr['field']}: {vr['reason']}")
            
            if recommendations:
                result_parts.append("\n【推荐调整方案】")
                for rec in recommendations:
                    result_parts.append(f"- {rec}")
            
            return "\n".join(result_parts)
        else:
            return "任务验证通过，所有提到的字段和表都有效且数据质量良好。"

    def _extract_mentioned_fields(self, user_question: str) -> list:
        """从用户问题中提取提到的字段名。"""
        import re
        
        # 常见的字段名模式
        patterns = [
            r'按\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*分组',
            r'按\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*汇总',
            r'统计\s*([a-zA-Z_][a-zA-Z0-9_]*)',
            r'查看\s*([a-zA-Z_][a-zA-Z0-9_]*)',
            r'显示\s*([a-zA-Z_][a-zA-Z0-9_]*)',
            r'字段\s*([a-zA-Z_][a-zA-Z0-9_]*)',
            r'`([a-zA-Z_][a-zA-Z0-9_]*)`',  # 反引号包围的字段
            r'"([a-zA-Z_][a-zA-Z0-9_]*)"',  # 双引号包围的字段
        ]
        
        mentioned_fields = set()
        for pattern in patterns:
            matches = re.findall(pattern, user_question, re.IGNORECASE)
            mentioned_fields.update(matches)
        
        return list(mentioned_fields)

    def _extract_mentioned_tables(self, user_question: str) -> list:
        """从用户问题中提取提到的表名。"""
        import re
        
        patterns = [
            r'表\s*([a-zA-Z_][a-zA-Z0-9_]*)',
            r'从\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*表',
            r'`([a-zA-Z_][a-zA-Z0-9_]*)`',  # 反引号包围的表名
        ]
        
        mentioned_tables = set()
        for pattern in patterns:
            matches = re.findall(pattern, user_question, re.IGNORECASE)
            mentioned_tables.update(matches)
        
        return list(mentioned_tables)

    def _analyze_field_quality(self, exploration_data: dict) -> dict:
        """分析探索结果中各字段的数据质量。"""
        field_quality = {}
        
        exploration_results = exploration_data.get("exploration_results", [])
        for table_info in exploration_results:
            table_name = table_info.get("table_name", "")
            columns = table_info.get("columns", [])
            sample_data = table_info.get("sample_data", [])
            
            for col_idx, column in enumerate(columns):
                field_key = f"{table_name}.{column}"
                
                # 分析该字段的数据质量
                null_count = 0
                total_count = len(sample_data)
                non_null_values = []
                
                for row in sample_data:
                    if col_idx < len(row):
                        value = row[col_idx]
                        if value is None or value == '' or str(value).lower() in ['null', 'none', 'nan']:
                            null_count += 1
                        else:
                            non_null_values.append(value)
                
                null_percentage = (null_count / total_count * 100) if total_count > 0 else 100
                
                field_quality[field_key] = {
                    "table": table_name,
                    "column": column,
                    "null_count": null_count,
                    "total_count": total_count,
                    "null_percentage": null_percentage,
                    "non_null_values": non_null_values,
                    "unique_values": list(set(str(v) for v in non_null_values)),
                    "data_type": self._infer_data_type(non_null_values)
                }
        
        return field_quality

    def _infer_data_type(self, values: list) -> str:
        """推断字段的数据类型。"""
        if not values:
            return "unknown"
        
        # 检查是否为数字类型
        numeric_count = 0
        date_count = 0
        
        for value in values[:5]:  # 只检查前5个值
            str_value = str(value)
            
            # 检查数字
            try:
                float(str_value)
                numeric_count += 1
                continue
            except ValueError:
                pass
            
            # 检查日期
            if any(date_pattern in str_value for date_pattern in ['-', '/', ':']):
                date_count += 1
        
        if numeric_count > len(values) * 0.8:
            return "numeric"
        elif date_count > len(values) * 0.5:
            return "datetime"
        else:
            return "text"

    def _validate_field(self, field: str, field_quality: dict) -> dict:
        """验证单个字段的有效性。"""
        # 寻找匹配的字段（可能在不同表中）
        matching_fields = []
        for field_key, quality_info in field_quality.items():
            if field.lower() in quality_info["column"].lower() or quality_info["column"].lower() in field.lower():
                matching_fields.append((field_key, quality_info))
        
        if not matching_fields:
            return {
                "field": field,
                "is_valid": False,
                "reason": "字段不存在于任何探索的表中"
            }
        
        # 选择最佳匹配（null值最少的）
        best_match = min(matching_fields, key=lambda x: x[1]["null_percentage"])
        _, quality_info = best_match
        
        # 检查数据质量
        if quality_info["null_percentage"] > 80:
            return {
                "field": field,
                "is_valid": False,
                "reason": f"字段包含过多null值 ({quality_info['null_percentage']:.1f}%)"
            }
        elif quality_info["null_percentage"] > 50:
            return {
                "field": field,
                "is_valid": True,
                "reason": f"字段有效但包含较多null值 ({quality_info['null_percentage']:.1f}%)，建议谨慎使用"
            }
        else:
            return {
                "field": field,
                "is_valid": True,
                "reason": f"字段有效，数据质量良好 (null值: {quality_info['null_percentage']:.1f}%)"
            }

    def _find_alternative_field(self, original_field: str, field_quality: dict, user_question: str) -> dict:
        """为无效字段寻找替代方案。"""
        # 分析用户问题的意图
        intent = self._analyze_user_intent(user_question)
        
        # 根据意图和数据质量寻找最佳替代字段
        candidates = []
        
        for field_key, quality_info in field_quality.items():
            # 跳过高null值字段
            if quality_info["null_percentage"] > 50:
                continue
            
            # 根据意图评分
            score = 0
            column_name = quality_info["column"].lower()
            
            # 语义相似性评分
            if any(keyword in column_name for keyword in intent.get("keywords", [])):
                score += 10
            
            # 数据类型匹配评分
            if intent.get("expected_type") == quality_info["data_type"]:
                score += 5
            
            # 数据质量评分
            score += (100 - quality_info["null_percentage"]) / 10
            
            # 唯一值数量评分（适合分组的字段）
            if intent.get("needs_grouping", False):
                unique_count = len(quality_info["unique_values"])
                if 2 <= unique_count <= 20:  # 适合分组的唯一值数量
                    score += 5
            
            candidates.append({
                "field": quality_info["column"],
                "table": quality_info["table"],
                "score": score,
                "null_percentage": quality_info["null_percentage"]
            })
        
        if candidates:
            best_candidate = max(candidates, key=lambda x: x["score"])
            return {
                "field": f"{best_candidate['table']}.{best_candidate['field']}",
                "reason": f"数据质量更好 (null值: {best_candidate['null_percentage']:.1f}%)"
            }
        
        return None

    def _analyze_user_intent(self, user_question: str) -> dict:
        """分析用户问题的意图。"""
        intent = {
            "keywords": [],
            "expected_type": "text",
            "needs_grouping": False,
            "needs_aggregation": False
        }
        
        question_lower = user_question.lower()
        
        # 检查分组需求
        if any(keyword in question_lower for keyword in ['分组', '按', '汇总', '统计']):
            intent["needs_grouping"] = True
            intent["keywords"].extend(['name', 'type', 'category', 'status'])
        
        # 检查聚合需求
        if any(keyword in question_lower for keyword in ['数量', '总数', '计数', '求和']):
            intent["needs_aggregation"] = True
            intent["expected_type"] = "numeric"
            intent["keywords"].extend(['count', 'quantity', 'amount', 'num'])
        
        # 检查时间相关
        if any(keyword in question_lower for keyword in ['时间', '日期', '月份', '年份']):
            intent["expected_type"] = "datetime"
            intent["keywords"].extend(['date', 'time', 'month', 'year'])
        
        return intent

    def _validate_table(self, table: str, exploration_data: dict) -> dict:
        """验证表名是否存在。"""
        exploration_results = exploration_data.get("exploration_results", [])
        existing_tables = [result.get("table_name", "") for result in exploration_results]
        
        if table in existing_tables:
            return {"is_valid": True, "reason": "表存在"}
        else:
            return {"is_valid": False, "reason": "表不存在于探索结果中"}

    def _find_alternative_table(self, original_table: str, exploration_data: dict) -> str:
        """为不存在的表寻找替代方案。"""
        exploration_results = exploration_data.get("exploration_results", [])
        existing_tables = [result.get("table_name", "") for result in exploration_results]
        
        # 简单的字符串相似性匹配
        for table in existing_tables:
            if original_table.lower() in table.lower() or table.lower() in original_table.lower():
                return table
        
        # 如果没有相似的，返回第一个表作为默认选择
        return existing_tables[0] if existing_tables else None

    def _recommend_quality_fields(self, field_quality: dict, user_question: str) -> list:
        """推荐高质量的字段用于分析。"""
        recommendations = []
        intent = self._analyze_user_intent(user_question)
        
        # 寻找适合分组的字段
        if intent.get("needs_grouping", False):
            grouping_candidates = []
            for field_key, quality_info in field_quality.items():
                if (quality_info["null_percentage"] < 20 and 
                    len(quality_info["unique_values"]) <= 10 and 
                    len(quality_info["unique_values"]) >= 2):
                    grouping_candidates.append((field_key, quality_info))
            
            if grouping_candidates:
                best_grouping = min(grouping_candidates, key=lambda x: x[1]["null_percentage"])
                recommendations.append(f"推荐用于分组的字段: {best_grouping[0]} (null值: {best_grouping[1]['null_percentage']:.1f}%)")
        
        # 寻找适合聚合的数值字段
        if intent.get("needs_aggregation", False):
            numeric_candidates = []
            for field_key, quality_info in field_quality.items():
                if (quality_info["data_type"] == "numeric" and 
                    quality_info["null_percentage"] < 30):
                    numeric_candidates.append((field_key, quality_info))
            
            if numeric_candidates:
                best_numeric = min(numeric_candidates, key=lambda x: x[1]["null_percentage"])
                recommendations.append(f"推荐用于数值聚合的字段: {best_numeric[0]} (null值: {best_numeric[1]['null_percentage']:.1f}%)")
        
        return recommendations

    async def load_resource(self, question: str, is_retry_chat: bool = False):
        """Load the resource for the current agent."""
        if is_retry_chat:
            return ("", None)
        else:
            return await super().load_resource(question, is_retry_chat)

