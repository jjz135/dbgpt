"""Protocol for the Report vis - supports mixed text analysis and visualizations."""

import json
import logging
from typing import Any, Dict, List, Optional

from ..base import Vis

logger = logging.getLogger(__name__)


def default_report_chart_type_prompt() -> str:
    """Return prompt information for the report chart types.
    
    Returns:
        str: prompt information for available chart types and report structure.
    """
    prompt = """
Available Chart Types for Report Sections:

1. response_bar_chart: **[HIGHLY RECOMMENDED for aggregations]**
   - Use when SQL contains: GROUP BY, COUNT(*), SUM(), AVG(), MAX(), MIN()
   - Perfect for: comparing values across categories, ranking data

2. response_pie_chart: **[RECOMMENDED for proportion analysis]**
   - Use when SQL contains: GROUP BY with single dimension
   - Perfect for: showing proportions, distribution percentages

3. response_line_chart:
   - Use when SQL contains: time/date fields (ORDER BY date/time)
   - Perfect for: trend analysis over time, time series data

4. response_area_chart:
   - Use for stacked time series, cumulative trends

5. response_scatter_chart:
   - Use for exploring correlations between two numeric values

6. response_table: **[USE SPARINGLY]**
   - ONLY use when: detailed records with >5 columns needed
   - Avoid for: aggregated numeric data

**Report Structure Guidelines**:
- Each report should have a clear executive summary at the beginning
- Organize content into logical sections with headers
- Alternate between text analysis and visualizations for better readability
- Provide key insights and recommendations in text sections
- Use charts to support and illustrate your analysis
"""
    return prompt.strip()


class VisReport(Vis):
    """Report Vis Protocol - supports mixed text analysis and chart visualizations."""

    def render_prompt(self) -> Optional[str]:
        """Return the prompt for the vis protocol."""
        return default_report_chart_type_prompt()

    def sync_generate_param(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate the parameters required by the vis protocol."""
        sections: Optional[List[dict]] = kwargs.get("sections", None)
        title: Optional[str] = kwargs.get("title", "分析报告")
        summary: Optional[str] = kwargs.get("summary", "")
        
        if not sections:
            raise ValueError(
                f"Parameter information is missing and {self.vis_tag()} protocol "
                "conversion cannot be performed."
            )

        processed_sections = []
        for section in sections:
            section_type = section.get("type", "text")
            processed_section = {
                "type": section_type,
                "title": section.get("title", ""),
            }
            
            if section_type == "text":
                # Text analysis section
                processed_section["content"] = section.get("content", "")
            elif section_type == "chart":
                # Chart visualization section
                processed_section["chart_type"] = section.get("chart_type", "response_table")
                processed_section["sql"] = section.get("sql", "")
                processed_section["description"] = section.get("description", "")
                
                try:
                    data = section.get("data", None)
                    err_msg = section.get("err_msg", None)
                    if data is None:
                        processed_section["err_msg"] = err_msg
                        processed_section["data"] = []
                    elif isinstance(data, list):
                        # Data is already a list (e.g., from LLM or pre-processed)
                        processed_section["data"] = data
                    elif hasattr(data, 'to_json'):
                        # Data is a DataFrame, convert to list of dicts
                        processed_section["data"] = json.loads(
                            data.to_json(orient="records", date_format="iso", date_unit="s")
                        )
                    else:
                        # Unknown type, try to use as-is
                        processed_section["data"] = data if data else []
                except Exception as e:
                    logger.exception("Report chart build failed!")
                    processed_section["data"] = []
                    processed_section["err_msg"] = str(e)
            
            processed_sections.append(processed_section)

        report_param = {
            "title": title,
            "summary": summary,
            "sections": processed_sections,
            "section_count": len(processed_sections),
            "display_strategy": "report",
            "style": "professional",
        }

        return report_param

    @classmethod
    def vis_tag(cls):
        """Vis Report tag."""
        return "vis-report"

