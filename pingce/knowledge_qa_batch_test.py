"""
DB-GPT 知识库问答自动化评测脚本

功能：
1. 批量调用知识库问答接口
2. 自动收集 question、context、answer
3. 导出为 Excel 格式，适配 RAGAS 评测

使用方法：
    python knowledge_qa_batch_test.py
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd
from datasets import Dataset

# =====================================================================
# 1. 配置路径 - 根据你的实际项目路径调整
# =====================================================================
DB_GPT_ROOT = r"D:\code\py\dbgpt\dbgpt"
sys.path.insert(0, DB_GPT_ROOT)
sys.path.insert(0, os.path.join(DB_GPT_ROOT, "packages", "dbgpt-app", "src"))
sys.path.insert(0, os.path.join(DB_GPT_ROOT, "packages", "dbgpt-core", "src"))
sys.path.insert(0, os.path.join(DB_GPT_ROOT, "packages", "dbgpt-serve", "src"))
sys.path.insert(0, os.path.join(DB_GPT_ROOT, "packages", "dbgpt-ext", "src"))

# =====================================================================
# 2. 导入 DB-GPT 核心组件
# =====================================================================
from dbgpt.component import SystemApp
from dbgpt_app.config import ApplicationConfig
from dbgpt_app.dbgpt_server import initialize_app
from dbgpt_app.scene.base_chat import ChatParam
from dbgpt_app.scene.chat_factory import ChatFactory
from dbgpt_app.scene.base import ChatScene

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class QATestCase:
    """问答测试用例"""
    question: str
    ground_truth: Optional[str] = None  # 可选的标准答案


@dataclass
class QAResult:
    """问答结果"""
    question: str
    answer: str
    context: str  # 检索到的知识库内容
    contexts: List[str]  # 分割后的上下文列表（适配 RAGAS）
    ground_truth: Optional[str] = None


class KnowledgeQABatchTester:
    """知识库问答批量测试器"""

    def __init__(
        self,
        config_path: str = None,
        knowledge_space_name: str = None,
        model_name: str = None,
        chat_session_id_prefix: str = "batch_test_"
    ):
        """
        初始化测试器
        
        Args:
            config_path: DB-GPT 配置文件路径（toml格式）
            knowledge_space_name: 知识库空间名称
            model_name: LLM 模型名称
            chat_session_id_prefix: 会话ID前缀
        """
        self.config_path = config_path
        self.knowledge_space_name = knowledge_space_name
        self.model_name = model_name
        self.chat_session_id_prefix = chat_session_id_prefix
        self.system_app: Optional[SystemApp] = None
        self.test_counter = 0

    async def initialize_system(self):
        """初始化 DB-GPT 系统（简化版，仅初始化必要组件）"""
        logger.info("=" * 80)
        logger.info("正在初始化 DB-GPT 系统...")
        logger.info("=" * 80)

        # 加载配置
        if self.config_path and os.path.exists(self.config_path):
            logger.info(f"使用配置文件: {self.config_path}")
            # 使用 dbgpt_server 中的 load_config 函数
            from dbgpt_app.dbgpt_server import load_config
            config = load_config(self.config_path)
        else:
            logger.info("使用默认配置")
            config = ApplicationConfig()
            # 修复日志级别配置问题
            if hasattr(config, 'log') and hasattr(config.log, 'level'):
                log_level = config.log.level
                # 如果日志级别是环境变量占位符，设置为默认值
                if isinstance(log_level, str) and log_level.startswith('${env:'):
                    config.log.level = "INFO"
                    logger.info("使用默认日志级别: INFO")
            
            # 确保 vector_store 配置有默认值
            if hasattr(config, 'rag') and config.rag:
                if not hasattr(config.rag, 'vector_store_config') or not config.rag.vector_store_config:
                    from dbgpt_ext.storage.vector_store.chroma_store import ChromaVectorConfig
                    config.rag.vector_store_config = ChromaVectorConfig(
                        persist_path=os.path.join(DB_GPT_ROOT, "pilot", "data")
                    )
                    logger.info("已设置默认 Chroma 向量存储配置")
        
        # 手动初始化必要的组件，避免调用 initialize_app
        from fastapi import FastAPI
        app = FastAPI()
        self.system_app = SystemApp(app)
        
        # 重要：将 config 注册到 system_app 中，供 ChatFactory 使用
        self.system_app.config.configs["app_config"] = config
        
        # 关键：先调用 server_init 初始化数据库（这是标准流程）
        from dbgpt_app.base import server_init
        server_init(config, self.system_app)
        logger.info("✅ 数据库管理器已初始化")
        
        # 注册 Worker Manager Factory（ChatKnowledge 需要）
        from dbgpt.model.cluster.worker.manager import (
            _DefaultWorkerManagerFactory,
            LocalWorkerManager,
            worker_manager,
        )
        
        # 初始化 LocalWorkerManager 并设置到全局 worker_manager
        local_worker_mgr = LocalWorkerManager()
        worker_manager.worker_manager = local_worker_mgr
        
        # 正确方式：传递 worker_manager 实例作为参数
        self.system_app.register(_DefaultWorkerManagerFactory, worker_manager)
        logger.info("已注册 Worker Manager Factory")
        
        # 初始化核心组件（RAG、Embedding Factory等）
        from dbgpt_app.component_configs import initialize_components
        initialize_components(config, self.system_app)
        logger.info("✅ 核心组件已初始化（包括 Embedding Factory）")
        
        # 关键：启动本地 embedding worker（配置文件中使用的是本地 HF 模型）
        from dbgpt.model.cluster.worker.manager import (
            _start_local_embedding_worker,
            _start_local_worker,
            ModelWorkerParameters,
        )
        
        # 从配置中获取 embedding 模型配置
        if config.models and config.models.embeddings:
            for embedding_config in config.models.embeddings:
                if embedding_config.name == "text2vec-large-chinese":
                    logger.info(f"正在启动本地 embedding worker: {embedding_config.name}")
                    logger.info(f"   模型路径: {getattr(embedding_config, 'path', 'N/A')}")
                    
                    # 直接使用配置文件中的配置对象
                    # _start_local_embedding_worker 会处理所有参数
                    _start_local_embedding_worker(
                        worker_manager=worker_manager,
                        deploy_model_params=embedding_config,
                    )
                    logger.info(f"✅ 本地 embedding worker 已注册: {embedding_config.name}")
                    break
        
        # 关键：启动 LLM worker（用于调用远程模型如 qwen-plus）
        if config.models and config.models.llms:
            for llm_config in config.models.llms:
                logger.info(f"正在注册 LLM worker: {llm_config.name}")
                logger.info(f"   提供商: {getattr(llm_config, 'provider', 'N/A')}")
                
                # 创建默认的 worker 参数
                llm_worker_params = ModelWorkerParameters(
                    worker_type="llm",
                )
                
                # 注册 LLM worker
                _start_local_worker(
                    worker_manager=worker_manager,
                    worker_params=llm_worker_params,
                    deploy_model_params=llm_config,
                )
                logger.info(f"✅ LLM worker 已注册: {llm_config.name}")
        
        # 重要：在异步上下文中，需要手动启动 LocalWorkerManager
        # 直接调用 start() 并等待完成，确保 worker 完全初始化
        import asyncio
        await local_worker_mgr.start()
        logger.info("✅ LocalWorkerManager 启动完成")
        
        # 触发初始化和后置处理
        self.system_app.on_init()
        
        # 执行数据库迁移，创建必要的表（知识库元数据表等）
        logger.info("正在执行数据库迁移...")
        try:
            from dbgpt_app.base import _migration_db_storage
            web_config = config.service.web
            # 对于批量测试场景，禁用 Alembic 升级检查，直接创建表结构
            _migration_db_storage(web_config.database, disable_alembic_upgrade=True)
            logger.info("✅ 数据库表结构创建完成")
        except Exception as e:
            logger.error(f"❌ 数据库迁移失败: {e}")
            raise
        
        self.system_app.after_init()

        logger.info("DB-GPT 系统初始化完成！")
        logger.info("=" * 80)

    async def ask_question(
        self,
        question: str,
        knowledge_space: str = None,
        model_name: str = None,
        chat_session_id: str = None
    ) -> QAResult:
        """
        向知识库提问并获取答案
        
        Args:
            question: 问题文本
            knowledge_space: 知识库空间名称（覆盖构造函数参数）
            model_name: 模型名称（覆盖构造函数参数）
            chat_session_id: 会话ID
            
        Returns:
            QAResult: 包含 question, answer, context 的结果对象
        """
        self.test_counter += 1
        
        # 使用传入参数或默认参数
        space_name = knowledge_space or self.knowledge_space_name
        llm_model = model_name or self.model_name
        session_id = chat_session_id or f"{self.chat_session_id_prefix}{self.test_counter}"

        if not space_name:
            raise ValueError("必须指定 knowledge_space_name 参数")

        logger.info(f"\n[{self.test_counter}] 处理问题: {question[:50]}...")

        try:
            # 创建 ChatParam
            chat_param = ChatParam(
                chat_session_id=session_id,
                current_user_input=question,
                model_name=llm_model,
                select_param=space_name,
                chat_mode=ChatScene.ChatKnowledge,
                user_name="batch_tester",
                sys_code="batch_test",
                app_code=ChatScene.ChatKnowledge.value(),
                message_version="v2"
            )

            # 通过工厂创建 ChatKnowledge 实例
            chat_knowledge = ChatFactory.get_implementation(
                chat_mode=ChatScene.ChatKnowledge.value(),
                system_app=self.system_app,
                chat_param=chat_param
            )

            # 收集 context（在 generate_input_values 中检索）
            input_values = await chat_knowledge.generate_input_values()
            context_text = input_values.get("context", "")
            
            # 将 context 拆分为列表（适配 RAGAS 格式）
            # context 是用 "\n".join 连接的，这里尝试按段落分割
            contexts_list = [ctx.strip() for ctx in context_text.split("\n\n") if ctx.strip()]
            if not contexts_list:
                contexts_list = [context_text] if context_text else []

            logger.info(f"   检索到 {len(contexts_list)} 个相关文档片段")

            # 流式调用获取答案
            answer_parts = []
            async for response in chat_knowledge.stream_call(text_output=True, incremental=True):
                if isinstance(response, str):
                    answer_parts.append(response)
                elif hasattr(response, 'text'):
                    answer_parts.append(response.text)

            full_answer = "".join(answer_parts)
            
            # 清理答案中的引用标记（可选）
            # 如果需要保留引用，可以注释掉下面这行
            clean_answer = self._clean_reference_tags(full_answer)

            logger.info(f"   答案长度: {len(clean_answer)} 字符")

            return QAResult(
                question=question,
                answer=clean_answer,
                context=context_text,
                contexts=contexts_list,
                ground_truth=None  # 可以在外部设置
            )

        except Exception as e:
            logger.error(f"   ❌ 处理失败: {str(e)}", exc_info=True)
            return QAResult(
                question=question,
                answer=f"ERROR: {str(e)}",
                context="",
                contexts=[],
                ground_truth=None
            )

    @staticmethod
    def _clean_reference_tags(text: str) -> str:
        """
        清理答案末尾的知识库引用标签
        
        Args:
            text: 原始答案文本
            
        Returns:
            str: 清理后的文本
        """
        # 查找 <references> 标签并移除
        if "<references" in text:
            ref_start = text.find("<references")
            if ref_start != -1:
                text = text[:ref_start].rstrip()
        return text

    async def batch_test(
        self,
        test_cases: List[QATestCase],
        output_excel: str = "knowledge_qa_results.xlsx",
        knowledge_space: str = None,
        model_name: str = None,
        concurrency: int = 1  # 并发数，建议保持为1避免速率限制
    ) -> List[QAResult]:
        """
        批量测试
        
        Args:
            test_cases: 测试用例列表
            output_excel: 输出 Excel 文件路径
            knowledge_space: 知识库空间名称
            model_name: 模型名称
            concurrency: 并发数
            
        Returns:
            List[QAResult]: 所有测试结果
        """
        if not self.system_app:
            await self.initialize_system()

        logger.info(f"\n开始批量测试，共 {len(test_cases)} 个问题")
        logger.info(f"知识库: {knowledge_space or self.knowledge_space_name}")
        logger.info(f"模型: {model_name or self.model_name}")
        logger.info("=" * 80)

        results = []
        
        # 顺序执行（推荐）
        if concurrency == 1:
            for i, test_case in enumerate(test_cases, 1):
                logger.info(f"\n进度: {i}/{len(test_cases)}")
                result = await self.ask_question(
                    question=test_case.question,
                    knowledge_space=knowledge_space,
                    model_name=model_name
                )
                result.ground_truth = test_case.ground_truth
                results.append(result)
                
                # 每10个问题保存一次（防止中断丢失数据）
                if i % 10 == 0:
                    self._save_intermediate_results(results, output_excel)
                    logger.info(f"   💾 已保存中间结果到: {output_excel}")
        else:
            # 并发执行（谨慎使用）
            semaphore = asyncio.Semaphore(concurrency)
            
            async def limited_ask(tc: QATestCase) -> QAResult:
                async with semaphore:
                    return await self.ask_question(
                        question=tc.question,
                        knowledge_space=knowledge_space,
                        model_name=model_name
                    )
            
            tasks = [limited_ask(tc) for tc in test_cases]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (test_case, result) in enumerate(zip(test_cases, raw_results)):
                if isinstance(result, Exception):
                    logger.error(f"问题 {i+1} 处理失败: {result}")
                    result = QAResult(
                        question=test_case.question,
                        answer=f"ERROR: {str(result)}",
                        context="",
                        contexts=[],
                        ground_truth=test_case.ground_truth
                    )
                else:
                    result.ground_truth = test_case.ground_truth
                results.append(result)

        # 保存最终结果
        self._save_results_to_excel(results, output_excel)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ 批量测试完成！共处理 {len(results)} 个问题")
        logger.info(f"📊 结果已保存到: {output_excel}")
        logger.info("=" * 80)

        return results

    @staticmethod
    def _save_intermediate_results(results: List[QAResult], output_path: str):
        """保存中间结果（增量保存）"""
        KnowledgeQABatchTester._save_results_to_excel(results, output_path)

    @staticmethod
    def _save_results_to_excel(results: List[QAResult], output_path: str):
        """
        将结果保存为 Excel 文件（适配 RAGAS 格式）
        
        Args:
            results: 测试结果列表
            output_path: 输出文件路径
        """
        if not results:
            logger.warning("没有结果可保存")
            return

        # 构建 DataFrame（适配 RAGAS 格式）
        data = {
            "question": [r.question for r in results],
            "answer": [r.answer for r in results],
            "contexts": [json.dumps(r.contexts, ensure_ascii=False) for r in results],
            "ground_truth": [r.ground_truth or "" for r in results],
            # 额外保存完整 context 供参考
            "full_context": [r.context for r in results],
        }

        df = pd.DataFrame(data)

        # 保存到 Excel
        try:
            df.to_excel(output_path, index=False, engine='openpyxl')
            logger.info(f"💾 已保存 {len(results)} 条结果到: {output_path}")
        except Exception as e:
            logger.error(f"保存 Excel 失败: {e}")
            # 降级为 CSV
            csv_path = output_path.replace(".xlsx", ".csv")
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"💾 已降级保存为 CSV: {csv_path}")

    def export_to_ragas_dataset(self, results: List[QAResult]) -> Dataset:
        """
        将结果转换为 RAGAS 数据集格式
        
        Args:
            results: 测试结果列表
            
        Returns:
            Dataset: RAGAS 兼容的数据集
        """
        test_data = {
            "question": [r.question for r in results],
            "answer": [r.answer for r in results],
            "contexts": [r.contexts for r in results],
            "ground_truth": [r.ground_truth or "" for r in results],
        }

        dataset = Dataset.from_dict(test_data)
        logger.info(f"✅ 已创建 RAGAS 数据集，包含 {len(dataset)} 条样本")
        return dataset


# =====================================================================
# 主函数 - 使用示例
# =====================================================================
async def main():
    """
    主函数 - 配置你的测试参数并运行
    """
    
    # ==================== 配置区域 ====================
    
    # 1. DB-GPT 配置文件路径（可选，不使用则用默认配置）
    CONFIG_PATH = None  # 例如: r"D:\code\py\dbgpt\dbgpt\configs\dbgpt-proxy-siliconflow.toml"
    
    # 2. 知识库空间名称（必填！）
    KNOWLEDGE_SPACE = "质量2"  # ← 修改为你的知识库名称
    
    # 3. LLM 模型名称（可选）
    MODEL_NAME = "qwen-plus"  # 例如: "qwen-plus", "gpt-4", 留空则用默认模型
    
    # 4. 输出文件路径
    OUTPUT_EXCEL = "knowledge_qa_batch_results.xlsx"
    
    # 5. 测试用例列表
    test_cases = [
        QATestCase(
            question="在桥梁钢箱梁底板与斜底板单元制造及总拼工序中，若巡检发现定位焊及码板点焊损伤母材、定位焊参数不符，且斜底板拼接时出现最大达25mm的超大间隙及焊缝角变形修整不及时等问题，应如何进行缺陷原因分析、现场整改及后续工艺控制？",
            ground_truth="进入控制面板工艺参数设置，将一级注塑压力参数调低 5%-10%，并检查压力比例阀。"
        ),
        QATestCase(
            question="2026年企业能耗双控指标是什么？",
            ground_truth="全年综合能耗同比降低3.5%，碳排放总量控制在1.2万吨以内。"
        ),
        # 添加更多问题...
        # QATestCase(question="你的问题...", ground_truth="标准答案..."),
    ]
    
    # ==================== 执行测试 ====================
    
    tester = KnowledgeQABatchTester(
        config_path=CONFIG_PATH,
        knowledge_space_name=KNOWLEDGE_SPACE,
        model_name=MODEL_NAME
    )
    
    # 执行批量测试
    results = await tester.batch_test(
        test_cases=test_cases,
        output_excel=OUTPUT_EXCEL,
        knowledge_space=KNOWLEDGE_SPACE,
        model_name=MODEL_NAME,
        concurrency=1  # 建议保持为1
    )
    
    # 导出为 RAGAS 数据集（可选）
    ragas_dataset = tester.export_to_ragas_dataset(results)
    print("\nRAGAS 数据集预览:")
    print(ragas_dataset)
    
    return results


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
