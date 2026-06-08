import logging
from typing import Optional, Tuple

from dbgpt.agent import Action, ActionOutput, AgentResource
from dbgpt.rag.retriever.rerank import RetrieverNameRanker

logger = logging.getLogger(__name__)


class QualityRootReasoningAction(Action[str]):
    """Action to perform root cause reasoning from problem descriptions."""

    @property
    def name(self) -> str:
        return "quality_root_reasoning"

    @property
    def description(self) -> str:
        return "Analyze the root cause of the given quality issue based on the knowledge base."

    @property
    def args(self) -> dict:
        return {
            "problem": {
                "type": "string",
                "description": "Description of the quality issue or abnormal result",
            }
        }

    async def run(
            self,
            ai_message: str,
            resource: Optional[AgentResource] = None,
            rely_action_out: Optional[ActionOutput] = None,
            need_vis_render: bool = True,
            **kwargs,
    ) -> ActionOutput:
        logger.info(f"=== Action received ai_message length: {len(ai_message)}")
        logger.info(f"=== Action received ai_message content: {ai_message}")
        problem = kwargs.get("problem") or ai_message
        if not resource:
            return ActionOutput(
                is_exe_success=False,
                content="No knowledge base resource is provided.",
            )
        try:
            # 使用 prompt 提取接口（兼容 DBResource 和 KnowledgeResource）
            resource_prompt, _ = await resource.get_prompt(lang="zh", question=problem)
            return ActionOutput(
                is_exe_success=True,
                content=resource_prompt or "未获取到有效的知识库内容或数据库内容。",
                action_input=problem,
                thoughts="Used get_prompt to retrieve context from resource.",
                observations=resource_prompt or "",
                view=ai_message
            )
        except Exception as e:
            logger.exception(f"Error in QualityRootReasoningAction: {e}")
            return ActionOutput(is_exe_success=False, content=str(e))
