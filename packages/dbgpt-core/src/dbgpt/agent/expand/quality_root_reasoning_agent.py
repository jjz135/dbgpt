
"""Quality Root Reasoning Agent."""

import logging
from typing import Dict, List, Optional, Tuple

from dbgpt.agent import AgentMessage, ActionOutput, AgentResource
from dbgpt.rag.retriever.rerank import RetrieverNameRanker

from ..core.base_agent import ConversableAgent
from ..core.profile import DynConfig, ProfileConfig
from .actions.quality_root_reasoning_action import QualityRootReasoningAction

logger = logging.getLogger(__name__)


class QualityRootReasoningAgent(ConversableAgent):
    """Agent for reasoning about root causes of quality issues."""

    profile: ProfileConfig = ProfileConfig(
        name=DynConfig(
            "RootReasoner",
            category="agent",
            key="dbgpt_agent_expand_quality_root_reasoning_name",
        ),
        role=DynConfig(
            "CauseAnalyzer",
            category="agent",
            key="dbgpt_agent_expand_quality_root_reasoning_role",
        ),
        goal=DynConfig(
            "Analyze the root causes of observed anomalies or quality issues "
            "when human explicitly asks to explore the reason or cause of a problem.",
            category="agent",
            key="dbgpt_agent_expand_quality_root_reasoning_goal",
        ),
        desc=DynConfig(
            "This agent is designed for reasoning about the potential root causes of a problem. "
            "Only select this agent when the user's query requires analyzing why something went wrong, "
            "such as '为什么...','...怎么回事','分析...','....原因是什么'."
            "It leverages external knowledge base or structured data to generate grounded causal analysis."
            "This agent, whenever present, must always appear last.",
            category="agent",
            key="dbgpt_agent_expand_quality_root_reasoning_desc",
        ),
        constraints=DynConfig(
            [
                "Do not fabricate causes. Only output reasons supported by the knowledge base.",
                "If no matching cause is found, clearly state that. and say '知识库中内容有限'",
                "Always ground output to retrieved relevant text chunks. ",
                "If you do not see conflict/error/problems, say '看起来一切正常，如果您怀疑结果不正确，可以细化您的要求'",
                "Reply in one chunk, do not split chunks.",
                "Do NOT make assumptions, do not make up information/data."
            ],
            category="agent",
            key="dbgpt_agent_expand_quality_root_reasoning_constraints",
        ),
    )

    def __init__(self, **kwargs):
        """Create a new QualityRootReasoningAgent instance."""
        super().__init__(**kwargs)
        self._post_reranks = [RetrieverNameRanker(topk=5)]
        self._init_actions([QualityRootReasoningAction])

    async def act(self, message: AgentMessage, **kwargs) -> ActionOutput:
        logger.info(f"=== act method received message.content length: {len(message.content)}")
        logger.info(f"=== act method received message.content preview: {message.content[:200]}...")

        action = self.actions[0]
        result: ActionOutput = await action.run(
            ai_message=message.content,
            resource=self.resource,
            need_vis_render=True,
            **(message.context or {}),
            **kwargs,
        )

        logger.info(f"=== action result.content length: {len(result.content)}")
        logger.info(f"=== action result.content preview: {result.content[:200]}...")


        return result

    async def load_resource(self, question: str, is_retry_chat: bool = False):
        """Load relevant chunks from knowledge base resources."""
        if self.resource:
            if self.resource.is_pack:
                sub_resources = self.resource.sub_resources
                candidates_results: List = []
                resource_candidates_map = {}
                info_map = {}
                prompt_list = []
                for resource in sub_resources:
                    (
                        candidates,
                        prompt_template,
                        resource_reference,
                    ) = await resource.get_resources(question=question)
                    resource_candidates_map[resource.name] = (
                        candidates,
                        resource_reference,
                        prompt_template,
                    )
                    candidates_results.extend(candidates)
                new_candidates_map = self.post_filters(resource_candidates_map)
                for resource, (
                    candidates,
                    references,
                    prompt_template,
                ) in new_candidates_map.items():
                    content = "\n".join(
                        [f"--{i}--:" + chunk.content for i, chunk in enumerate(candidates)]
                    )
                    prompt_list.append(prompt_template.format(name=resource, content=content))
                    info_map.update(references)
                return "\n".join(prompt_list), info_map
            else:
                resource_prompt, resource_reference = await self.resource.get_prompt(
                    lang=self.language, question=question
                )
                return resource_prompt, resource_reference
        return None, None

    def _init_reply_message(
        self,
        received_message: AgentMessage,
        rely_messages: Optional[List[AgentMessage]] = None,
    ) -> AgentMessage:
        reply = super()._init_reply_message(received_message, rely_messages)
        reply.context = {
            "problem": received_message.content,
        }
        return reply

    def post_filters(self, resource_candidates_map: Optional[Dict[str, Tuple]] = None):
        """Post filters using reranker to select top candidates."""
        if resource_candidates_map:
            new_candidates_map = resource_candidates_map.copy()
            filter_hit = False
            for resource, (
                candidates,
                references,
                prompt_template,
            ) in resource_candidates_map.items():
                for rerank in self._post_reranks:
                    filter_candidates = rerank.rank(candidates)
                    new_candidates_map[resource] = [], [], prompt_template
                    if filter_candidates and len(filter_candidates) > 0:
                        new_candidates_map[resource] = (
                            filter_candidates,
                            references,
                            prompt_template,
                        )
                        filter_hit = True
                        break
            if filter_hit:
                logger.info("Post filters hit, using filtered candidate causes.")
                return new_candidates_map
        return resource_candidates_map

    async def adjust_final_message(self, is_success: bool, reply_message: AgentMessage):
        if (
            reply_message.action_report
            and reply_message.action_report.content
            and isinstance(reply_message.action_report.content, str)
        ):
            reply_message.content = reply_message.action_report.content
        return is_success, reply_message