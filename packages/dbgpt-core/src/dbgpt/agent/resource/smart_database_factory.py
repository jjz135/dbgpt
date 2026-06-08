"""智能数据库资源工厂 - 用于创建和管理集成智能注释的数据库资源"""

import logging
from typing import Optional, Dict, Any

from dbgpt.core import Embeddings, LLMClient
from dbgpt.datasource.base import BaseConnector
from dbgpt.storage.vector_store.base import VectorStoreBase

from .smart_database import SmartDBResource
from dbgpt_ext.rag.assembler.smart_comment_generator import SmartCommentGenerator

logger = logging.getLogger(__name__)


class SmartDBResourceFactory:
    """智能数据库资源工厂
    
    负责创建和管理集成智能注释的数据库资源，
    简化Agent使用智能注释系统的配置过程。
    """
    
    @staticmethod
    def create_smart_db_resource(
        name: str,
        connector: BaseConnector,
        comment_vector_store: VectorStoreBase,
        embeddings: Optional[Embeddings] = None,
        llm_client: Optional[LLMClient] = None,
        auto_generate_comments: bool = False,
        use_smart_comments: bool = True,
        **kwargs
    ) -> SmartDBResource:
        """创建智能数据库资源
        
        Args:
            name: 资源名称
            connector: 数据库连接器
            comment_vector_store: 智能注释向量存储
            embeddings: 嵌入模型
            llm_client: LLM客户端（用于生成智能注释）
            auto_generate_comments: 是否自动生成智能注释
            use_smart_comments: 是否使用智能注释
            
        Returns:
            SmartDBResource实例
        """
        logger.info(f"创建智能数据库资源: {name}")
        
        # 创建SmartDBResource
        smart_db_resource = SmartDBResource.create_with_smart_comments(
            name=name,
            connector=connector,
            comment_vector_store=comment_vector_store,
            embeddings=embeddings,
            use_smart_comments=use_smart_comments,
            **kwargs
        )
        
        # 如果需要自动生成智能注释
        if auto_generate_comments and llm_client:
            try:
                logger.info("开始自动生成智能注释...")
                SmartDBResourceFactory._auto_generate_comments(
                    connector, comment_vector_store, embeddings, llm_client
                )
                logger.info("智能注释自动生成完成")
            except Exception as e:
                logger.warning(f"自动生成智能注释失败: {e}")
        
        return smart_db_resource
    
    @staticmethod
    def _auto_generate_comments(
        connector: BaseConnector,
        comment_vector_store: VectorStoreBase,
        embeddings: Embeddings,
        llm_client: LLMClient
    ):
        """自动生成智能注释"""
        import asyncio
        
        async def generate_comments():
            # 创建智能注释生成器
            generator = SmartCommentGenerator(
                llm_client=llm_client,
                vector_store=comment_vector_store,
                embeddings=embeddings
            )
            
            # 获取所有表名
            table_names = list(connector.get_table_names())
            logger.info(f"将为 {len(table_names)} 个表生成智能注释")
            
            # 批量生成并保存注释
            results = await generator.batch_generate_and_save_comments(
                connector=connector,
                table_names=table_names,
                max_concurrent=2  # 限制并发数
            )
            
            success_count = sum(1 for _, (_, chunk_ids) in results.items() if chunk_ids)
            logger.info(f"智能注释生成完成: {success_count}/{len(table_names)} 表成功")
            
            return results
        
        # 运行异步生成过程
        return asyncio.run(generate_comments())
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> SmartDBResource:
        """从配置字典创建智能数据库资源
        
        Args:
            config: 配置字典，包含以下键：
                - name: 资源名称
                - connector: 数据库连接器
                - comment_vector_store: 智能注释向量存储
                - embeddings: 嵌入模型（可选）
                - llm_client: LLM客户端（可选）
                - auto_generate_comments: 是否自动生成智能注释（默认False）
                - use_smart_comments: 是否使用智能注释（默认True）
                
        Returns:
            SmartDBResource实例
        """
        required_keys = ["name", "connector", "comment_vector_store"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"配置中缺少必需的键: {key}")
        
        return SmartDBResourceFactory.create_smart_db_resource(
            name=config["name"],
            connector=config["connector"],
            comment_vector_store=config["comment_vector_store"],
            embeddings=config.get("embeddings"),
            llm_client=config.get("llm_client"),
            auto_generate_comments=config.get("auto_generate_comments", False),
            use_smart_comments=config.get("use_smart_comments", True)
        )
    
    @staticmethod
    def enhance_existing_db_resource(
        existing_resource,
        comment_vector_store: VectorStoreBase,
        embeddings: Optional[Embeddings] = None,
        use_smart_comments: bool = True
    ) -> SmartDBResource:
        """将现有的数据库资源增强为智能数据库资源
        
        Args:
            existing_resource: 现有的数据库资源
            comment_vector_store: 智能注释向量存储
            embeddings: 嵌入模型
            use_smart_comments: 是否使用智能注释
            
        Returns:
            SmartDBResource实例
        """
        if not hasattr(existing_resource, 'connector'):
            raise ValueError("现有资源必须具有connector属性")
        
        return SmartDBResource.create_with_smart_comments(
            name=existing_resource.name,
            connector=existing_resource.connector,
            comment_vector_store=comment_vector_store,
            embeddings=embeddings,
            use_smart_comments=use_smart_comments,
            db_type=getattr(existing_resource, '_db_type', None),
            db_name=getattr(existing_resource, '_db_name', None),
            dialect=getattr(existing_resource, '_dialect', None)
        )
    
    @staticmethod
    def check_smart_comments_availability(
        comment_vector_store: VectorStoreBase
    ) -> Dict[str, Any]:
        """检查智能注释的可用性
        
        Args:
            comment_vector_store: 智能注释向量存储
            
        Returns:
            包含可用性信息的字典
        """
        try:
            # 尝试查询智能注释
            test_chunks = comment_vector_store.similar_search(
                "test", top_k=1, score_threshold=0.0
            )
            
            # 统计智能注释
            smart_comment_chunks = [
                chunk for chunk in test_chunks
                if chunk.metadata and chunk.metadata.get("source") == "smart_comment_generator"
            ]
            
            return {
                "available": True,
                "total_chunks": len(test_chunks),
                "smart_comment_chunks": len(smart_comment_chunks),
                "vector_store_accessible": True
            }
            
        except Exception as e:
            logger.warning(f"检查智能注释可用性失败: {e}")
            return {
                "available": False,
                "error": str(e),
                "vector_store_accessible": False
            }
