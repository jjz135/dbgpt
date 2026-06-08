"""Protocol for the dashboard vis."""

import json
import logging
from typing import Any, Dict, Optional

from ..base import Vis
from .vis_chart import default_chart_type_prompt

logger = logging.getLogger(__name__)


class VisDashboard(Vis):
    """Dashboard Vis Protocol."""

    def sync_generate_param(self, **kwargs) -> Optional[Dict[str, Any]]:
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
                logger.exception("dashboard chart build faild！")
                param["data"] = []
                param["err_msg"] = str(e)
            chart_items.append(param)

        dashboard_param = {
            "data": chart_items,
            "chart_count": len(chart_items),
            "title": title,
            "display_strategy": "default",
            "style": "default",
        }

        return dashboard_param

    @classmethod
    def vis_tag(cls):
        """Vis Dashboard."""
        return "vis-dashboard"

    def render_prompt(self) -> Optional[str]:
        """Return the prompt for the vis protocol."""
        return default_chart_type_prompt()
