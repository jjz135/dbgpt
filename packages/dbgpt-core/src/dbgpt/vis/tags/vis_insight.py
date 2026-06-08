"""Protocol for the Insight vis."""
import json
import logging
from typing import Any, Dict, Optional

from ..base import Vis

logger = logging.getLogger(__name__)


def default_insight_chart_type_prompt() -> str:
    """Return prompt information for the insight chart types.
    
    Returns:
        str: prompt information for available chart types.
    """
    chart_types = [
        {"response_line_chart": "used to display comparative trend analysis data"},
        {
            "response_pie_chart": "suitable for scenarios such as proportion and "
            "distribution statistics"
        },
        {
            "response_table": "suitable for display with many display columns or "
            "non-numeric columns"
        },
        {
            "response_bar_chart": "suitable for comparing values across categories, "
            "ranking data, or showing frequency distributions"
        },
        {
            "response_scatter_chart": "suitable for exploring relationships between "
            "variables, detecting outliers, etc."
        },
        {
            "response_area_chart": "suitable for visualization of time series data, "
            "comparison of multiple groups of data, analysis of data change trends, "
            "etc."
        },
        {
            "response_donut_chart": "suitable for hierarchical structure representation"
            ", category proportion display and highlighting key categories, etc."
        },
        {
            "response_heatmap": "suitable for visual analysis of time series data, "
            "large-scale data sets, distribution of classified data, etc."
        },
    ]
    return "\n".join(
        f"{key}:{value}"
        for dict_item in chart_types
        for key, value in dict_item.items()
    )


class VisInsight(Vis):
    """Insight Vis Protocol."""

    def render_prompt(self) -> Optional[str]:
        """Return the prompt for the vis protocol."""
        return default_insight_chart_type_prompt()

    async def generate_param(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate the parameters required by the vis protocol."""
        charts: Optional[dict] = kwargs.get("charts", None)
        title: Optional[str] = kwargs.get("title", None)
        if not charts:
            raise ValueError(
                f"Parameter information is missing and {self.vis_tag} protocol "
                "conversion cannot be performed."
            )

        chart_items = []
        for chart in charts:
            param = {}
            sql = chart.get("sql", "")
            param["sql"] = sql
            param["type"] = chart.get("display_type", "response_table")
            param["title"] = chart.get("title", "")
            param["describe"] = chart.get("thought", "")
            try:
                df = chart.get("data", None)
                err_msg = chart.get("err_msg", None)
                if df is None:
                    param["err_msg"] = err_msg
                else:
                    param["data"] = json.loads(
                        df.to_json(orient="records", date_format="iso", date_unit="s")
                    )
            except Exception as e:
                logger.exception("insight chart build faild！")
                param["data"] = []
                param["err_msg"] = str(e)
            chart_items.append(param)

        insight_param = {
            "data": chart_items,
            "chart_count": len(chart_items),
            "title": title,
            "display_strategy": "default",
            "style": "default",
        }

        return insight_param

    @classmethod
    def vis_tag(cls):
        """Vis Insight."""
        return "vis-insight"
