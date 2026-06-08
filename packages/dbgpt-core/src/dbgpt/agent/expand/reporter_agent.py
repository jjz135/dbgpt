"""Reporter Agent - Generates comprehensive analysis reports with text and visualizations."""

from typing import List, Optional

from ..core.agent import AgentMessage
from ..core.base_agent import ConversableAgent
from ..core.profile import DynConfig, ProfileConfig
from ..resource.database import DBResource
from .actions.reporter_action import ReporterAction


class ReporterAgent(ConversableAgent):
    """Reporter Agent for generating analysis reports.
    
    This agent creates comprehensive analysis reports that combine:
    - Executive summaries
    - Text-based analysis and insights
    - Data visualizations (charts and tables)
    - Key findings and recommendations
    
    The reports are designed for professional presentation with
    clear structure and visual appeal.
    """

    profile: ProfileConfig = ProfileConfig(
        name=DynConfig(
            "Analyst",
            category="agent",
            key="dbgpt_agent_expand_reporter_agent_profile_name",
        ),
        role=DynConfig(
            "AnalysisReporter",
            category="agent",
            key="dbgpt_agent_expand_reporter_agent_profile_role",
        ),
        goal=DynConfig(
            "Generate comprehensive analysis reports that combine insightful text "
            "analysis with compelling data visualizations. Create professional reports "
            "that tell a complete story from the data.\n\n"
            "**CRITICAL REQUIREMENTS**:\n"
            "1. Start with an executive summary highlighting key findings\n"
            "2. Alternate between text analysis and charts for better readability\n"
            "3. Each chart MUST have meaningful business analysis\n"
            "4. Include specific metrics, comparisons, and actionable insights\n"
            "5. End with conclusions and recommendations",
            category="agent",
            key="dbgpt_agent_expand_reporter_agent_profile_goal",
        ),
        constraints=DynConfig(
            [
                "【Report Structure Guidelines】",
                
                "1. **Executive Summary** (REQUIRED):\n"
                "   - Write a 2-3 sentence summary in the 'summary' field\n"
                "   - Highlight the most important findings upfront\n"
                "   - Include key metrics and conclusions",
                
                "2. **Section Organization**:\n"
                "   - Use TEXT sections for analysis, context, and insights\n"
                "   - Use CHART sections for data visualization\n"
                "   - Alternate between text and charts for flow\n"
                "   - Each section should have a clear purpose",
                
                "3. **Text Section Content**:\n"
                "   - Write in professional, clear language\n"
                "   - Use markdown formatting (bold, bullets, etc.)\n"
                "   - Include specific numbers and percentages\n"
                "   - Provide interpretation of the data\n"
                "   - Example: '**关键发现**: 生产线PL001能耗最高达42.2kWh，超出平均值48%...'",
                
                "4. **Chart Section Rules - CRITICAL CHART TYPE SELECTION**:\n"
                "   - GROUP BY + SUM/COUNT/AVG (comparing categories) → response_bar_chart\n"
                "   - Proportion/percentage analysis (parts of whole, distribution) → response_pie_chart\n"
                "     * Example: '各车间碳排放量占比' MUST use response_pie_chart\n"
                "     * Example: '市场份额分布' MUST use response_pie_chart\n"
                "     * When you see words like '占比', '比例', '分布', 'percentage', 'proportion' → USE response_pie_chart\n"
                "   - Time series data (trends over time) → response_line_chart\n"
                "   - Detailed records (>5 columns) → response_table\n"
                "   - Always include business analysis in 'description'",
                
                "5. **Chart Types Available**: {{ display_type }}",
                
                "6. **Quality Checklist**:\n"
                "   - ✓ Has executive summary\n"
                "   - ✓ At least 3-5 sections\n"
                "   - ✓ Mix of text and charts\n"
                "   - ✓ Specific metrics cited\n"
                "   - ✓ Actionable insights included\n"
                "   - ✓ Professional tone throughout",
            ],
            category="agent",
            key="dbgpt_agent_expand_reporter_agent_profile_constraints",
        ),
        desc=DynConfig(
            "Analyzes data and generates comprehensive professional reports "
            "combining text analysis with data visualizations for clear, "
            "actionable insights.",
            category="agent",
            key="dbgpt_agent_expand_reporter_agent_profile_desc",
        ),
    )

    def __init__(self, **kwargs):
        """Create a new instance of ReporterAgent."""
        super().__init__(**kwargs)
        self._init_actions([ReporterAction])

    def _init_reply_message(
        self,
        received_message: AgentMessage,
        rely_messages: Optional[List[AgentMessage]] = None,
    ) -> AgentMessage:
        """Initialize the reply message with context."""
        reply_message = super()._init_reply_message(received_message, rely_messages)

        dbs: List[DBResource] = DBResource.from_resource(self.resource)

        if not dbs:
            raise ValueError(
                f"Resource type {self.actions[0].resource_need} is not supported."
            )
        db = dbs[0]
        reply_message.context = {
            "display_type": self.actions[0].render_prompt(),
            "dialect": db.dialect,
        }
        return reply_message

