"""Reporter Action Module - Generates analysis reports with text and visualizations."""

import json
import logging
from typing import Any, Dict, List, Optional

from dbgpt._private.pydantic import BaseModel, Field, model_to_dict
from dbgpt.vis.tags.vis_report import VisReport

from ...core.action.base import Action, ActionOutput
from ...resource.base import AgentResource, ResourceType
from ...resource.database import DBResource

logger = logging.getLogger(__name__)


class ReportOutput(BaseModel):
    """Complete report output model.
    
    Sections can be either text or chart type:
    - Text section: {"type": "text", "title": "optional title", "content": "markdown content"}
    - Chart section: {"type": "chart", "title": "chart title", "chart_type": "response_bar_chart", 
                      "sql": "SELECT ...", "description": "analysis"}
    """

    title: str = Field(
        ...,
        description="The main title of the analysis report.",
    )
    summary: str = Field(
        ...,
        description="Executive summary of the report (2-3 sentences) highlighting "
        "the key findings and conclusions.",
    )
    sections: List[Dict[str, Any]] = Field(
        ...,
        description="List of report sections. Each section should have 'type' field "
        "('text' or 'chart'). Text sections need 'content' field. Chart sections "
        "need 'chart_type', 'sql', and 'description' fields. 'title' is optional for both.",
    )

    def to_dict(self):
        """Convert to dict."""
        return model_to_dict(self)


class ReporterAction(Action[ReportOutput]):
    """Reporter action class for generating analysis reports."""

    def __init__(self, **kwargs):
        """Reporter action init."""
        super().__init__(**kwargs)
        self._render_protocol = VisReport()

    @property
    def resource_need(self) -> Optional[ResourceType]:
        """Return the resource type needed for the action."""
        return ResourceType.DB

    @property
    def render_protocol(self) -> Optional[VisReport]:
        """Return the render protocol."""
        return self._render_protocol

    @property
    def out_model_type(self):
        """Return the output model type."""
        return ReportOutput

    async def run(
        self,
        ai_message: str,
        resource: Optional[AgentResource] = None,
        rely_action_out: Optional[ActionOutput] = None,
        need_vis_render: bool = True,
        **kwargs,
    ) -> ActionOutput:
        """Perform the action - generate analysis report."""
        try:
            input_param = self._input_convert(ai_message, ReportOutput)
        except Exception as e:
            logger.exception(str(e))
            return ActionOutput(
                is_exe_success=False,
                content="Failed to parse the report structure from AI response.",
            )
        
        if not isinstance(input_param, ReportOutput):
            return ActionOutput(
                is_exe_success=False,
                content="Invalid report format received.",
            )
        
        report: ReportOutput = input_param
        
        try:
            db_resources: List[DBResource] = DBResource.from_resource(self.resource)
            if not db_resources:
                raise ValueError("The database resource is not found!")

            db = db_resources[0]
            if not db:
                raise ValueError("The database resource is not found!")

            # Process sections - execute SQL for chart sections
            processed_sections = []
            for section in report.sections:
                # sections is already List[Dict], so work with it directly
                section_dict = dict(section) if section else {}
                
                # Ensure type field exists, default to 'text'
                if "type" not in section_dict:
                    section_dict["type"] = "text"
                
                if section_dict.get("type") == "chart":
                    # Execute SQL and add data to chart section
                    try:
                        sql = section_dict.get("sql", "")
                        if sql:
                            sql_df = await db.query_to_df(sql)
                            section_dict["data"] = sql_df
                            
                            # Smart chart type correction based on SQL analysis and data
                            current_chart_type = section_dict.get("chart_type", "response_table")
                            corrected_chart_type = self._correct_chart_type(
                                sql, current_chart_type, sql_df, section_dict.get("title", ""), section_dict.get("description", "")
                            )
                            if corrected_chart_type != current_chart_type:
                                logger.info(
                                    f"Chart type corrected from '{current_chart_type}' to '{corrected_chart_type}' "
                                    f"for section: {section_dict.get('title', '')}"
                                )
                                section_dict["chart_type"] = corrected_chart_type
                    except Exception as e:
                        logger.warning(f"SQL execute failed: {str(e)}")
                        section_dict["err_msg"] = str(e)
                
                processed_sections.append(section_dict)

            if not self.render_protocol:
                raise ValueError("The render protocol is not initialized!")

            # Generate visualization
            view = await self.render_protocol.display(
                title=report.title,
                summary=report.summary,
                sections=processed_sections,
            )

            return ActionOutput(
                is_exe_success=True,
                content=json.dumps(report.to_dict(), ensure_ascii=False),
                view=view,
            )
        except Exception as e:
            logger.exception("Report generation failed!")
            return ActionOutput(
                is_exe_success=False, 
                content=f"Report action run failed: {str(e)}"
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
            title: Section title
            description: Section description
            
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

