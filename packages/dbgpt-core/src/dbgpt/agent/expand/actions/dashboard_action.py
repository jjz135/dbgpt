"""Dashboard Action Module."""

import json
import logging
from typing import Any, List, Optional

from dbgpt._private.pydantic import BaseModel, Field, model_to_dict
from dbgpt.vis.tags.vis_dashboard import Vis, VisDashboard

from ...core.action.base import Action, ActionOutput
from ...resource.base import AgentResource, ResourceType
from ...resource.database import DBResource

logger = logging.getLogger(__name__)


class ChartItem(BaseModel):
    """Chart item model."""

    title: str = Field(
        ...,
        description="The title of the current analysis chart.",
    )
    display_type: str = Field(
        "response_table",
        description="The chart rendering method selected for SQL. If you don’t know "
        "what to output, just output 'response_table' uniformly.",
    )
    sql: str = Field(
        ..., description="Executable sql generated for the current target/problem"
    )
    thought: str = Field(..., description="Summary of thoughts to the user")

    def to_dict(self):
        """Convert to dict."""
        return model_to_dict(self)


class DashboardAction(Action[List[ChartItem]]):
    """Dashboard action class."""

    def __init__(self, **kwargs):
        """Dashboard action init."""
        super().__init__(**kwargs)
        self._render_protocol = VisDashboard()

    @property
    def resource_need(self) -> Optional[ResourceType]:
        """Return the resource type needed for the action."""
        return ResourceType.DB

    @property
    def render_protocol(self) -> Optional[Vis]:
        """Return the render protocol."""
        return self._render_protocol

    @property
    def out_model_type(self):
        """Return the output model type."""
        return List[ChartItem]

    async def run(
        self,
        ai_message: str,
        resource: Optional[AgentResource] = None,
        rely_action_out: Optional[ActionOutput] = None,
        need_vis_render: bool = True,
        **kwargs,
    ) -> ActionOutput:
        """Perform the action."""
        try:
            input_param = self._input_convert(ai_message, List[ChartItem])
        except Exception as e:
            logger.exception(str(e))
            return ActionOutput(
                is_exe_success=False,
                content="The requested correctly structured answer could not be found.",
            )
        if not isinstance(input_param, list):
            return ActionOutput(
                is_exe_success=False,
                content="The requested correctly structured answer could not be found.",
            )
        chart_items: List[ChartItem] = input_param
        try:
            db_resources: List[DBResource] = DBResource.from_resource(self.resource)
            if not db_resources:
                raise ValueError("The database resource is not found！")

            db = db_resources[0]

            if not db:
                raise ValueError("The database resource is not found！")

            chart_params = []
            for chart_item in chart_items:
                chart_dict = {}
                try:
                    sql_df = await db.query_to_df(chart_item.sql)
                    chart_dict = chart_item.to_dict()
                    # 避免默认使用气泡图；如果选择了气泡图，则回退为表格 （气泡图真的没人看的懂）
                    if chart_dict.get("display_type") == "response_bubble_chart":
                        chart_dict["display_type"] = "response_table"
                    
                    # Smart chart type correction
                    corrected_type = self._correct_chart_type(
                        chart_item.sql,
                        chart_dict.get("display_type", "response_table"),
                        sql_df,
                        chart_item.title,
                        chart_item.thought
                    )
                    if corrected_type != chart_dict.get("display_type"):
                        logger.info(
                            f"Chart type corrected from '{chart_dict['display_type']}' to '{corrected_type}' "
                            f"for: {chart_item.title}"
                        )
                        chart_dict["display_type"] = corrected_type
                    
                    chart_dict["data"] = sql_df
                except Exception as e:
                    logger.warning(f"Sql execute failed！{str(e)}")
                    chart_dict["err_msg"] = str(e)
                chart_params.append(chart_dict)
            if not self.render_protocol:
                raise ValueError("The render protocol is not initialized!")
            view = await self.render_protocol.display(charts=chart_params)
            return ActionOutput(
                is_exe_success=True,
                content=json.dumps(
                    [chart_item.to_dict() for chart_item in chart_items]
                ),
                view=view,
            )
        except Exception as e:
            logger.exception("Dashboard generate Failed！")
            return ActionOutput(
                is_exe_success=False, content=f"Dashboard action run failed!{str(e)}"
            )

    def _correct_chart_type(
        self,
        sql: str,
        current_type: str,
        data_df: Any,
        title: str = "",
        description: str = ""
    ) -> str:
        """Intelligently correct chart type based on SQL analysis and data characteristics.
        
        Args:
            sql: The SQL query
            current_type: Current chart type selected by LLM
            data_df: DataFrame with query results
            title: Chart title
            description: Chart description/thought
            
        Returns:
            Corrected chart type
        """
        import re
        
        sql_upper = sql.upper()
        title_lower = (title + " " + description).lower()
        
        # Check for proportion/percentage keywords in title/description
        proportion_keywords = [
            '占比', '比例', '分布', '百分比', 'percent', 'proportion', 
            'distribution', 'share', 'ratio'
        ]
        has_proportion_context = any(kw in title_lower for kw in proportion_keywords)
        
        # Analyze SQL structure
        has_group_by = 'GROUP BY' in sql_upper
        has_aggregation = any(agg in sql_upper for agg in ['SUM(', 'COUNT(', 'AVG(', 'MAX(', 'MIN('])
        
        # Count columns in result data
        num_columns = len(data_df.columns) if hasattr(data_df, 'columns') else 0
        num_rows = len(data_df) if hasattr(data_df, '__len__') else 0
        
        # Rule 1: If it's a proportion analysis with GROUP BY and 2 columns (category + value), use pie chart
        if has_proportion_context and has_group_by and num_columns == 2:
            if current_type != 'response_pie_chart':
                logger.info(
                    f"Detected proportion analysis with {num_columns} columns, "
                    f"recommending pie chart instead of {current_type}"
                )
                return 'response_pie_chart'
        
        # Rule 2: If SQL has GROUP BY + aggregation but no time series, prefer bar chart over table
        if has_group_by and has_aggregation and num_columns <= 3:
            # Check if it's NOT time series data
            has_time_column = any(
                col_name.lower() in ['date', 'time', 'year', 'month', 'day', 'collect_time', 'created_at']
                for col_name in (data_df.columns if hasattr(data_df, 'columns') else [])
            )
            if not has_time_column and current_type == 'response_table':
                logger.info(
                    f"Detected aggregated data without time dimension, "
                    f"recommending bar chart instead of table"
                )
                return 'response_bar_chart'
        
        # Rule 3: If it's time series data, prefer line chart
        if has_time_column and has_group_by:
            if current_type in ['response_table', 'response_bar_chart']:
                logger.info(
                    f"Detected time series data, recommending line chart"
                )
                return 'response_line_chart'
        
        # No correction needed, return current type
        return current_type
