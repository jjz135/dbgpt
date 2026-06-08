"""增强的数据库资源 - 将智能注释融入表结构并存储到向量数据库"""

import logging
from typing import Optional, Union, List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

from dbgpt.core import LLMClient, Embeddings
from dbgpt.storage.vector_store.base import VectorStoreBase
from dbgpt.util.executor_utils import blocking_func_to_async

from .database import RDBMSConnectorResource, DBParameters
from dbgpt_ext.rag.assembler.smart_db_schema_assembler import SmartDBSchemaAssembler
from dbgpt_ext.rag.chunk_manager import ChunkParameters

logger = logging.getLogger(__name__)


class EnhancedDBResource(RDBMSConnectorResource):
    """增强的数据库资源
    
    关键功能：
    1. 使用SmartDBSchemaAssembler生成包含智能注释的表结构chunks
    2. 将这些chunks存储到向量数据库中
    3. Agent获取schema时，直接从向量数据库检索包含智能注释的表结构
    
    这样确保了智能注释真正与表结构融合并被Agent使用。
    """
    
    def __init__(
        self,
        name: str,
        connector=None,
        llm_client: Optional[LLMClient] = None,
        table_vector_store: Optional[VectorStoreBase] = None,
        embeddings: Optional[Embeddings] = None,
        use_smart_comments: bool = True,
        auto_generate_on_init: bool = False,
        max_tables: int = 30,
        **kwargs
    ):
        """初始化增强数据库资源
        
        Args:
            name: 资源名称
            connector: 数据库连接器
            llm_client: LLM客户端，用于生成智能注释
            table_vector_store: 表结构向量存储
            embeddings: 嵌入模型
            use_smart_comments: 是否使用智能注释
            auto_generate_on_init: 是否在初始化时自动生成智能注释
            max_tables: 最大处理表数
        """
        super().__init__(name=name, connector=connector, **kwargs)
        
        self._llm_client = llm_client
        self._table_vector_store = table_vector_store
        self._embeddings = embeddings
        self._use_smart_comments = use_smart_comments
        self._max_tables = max_tables
        
        # 创建智能表结构装配器
        self._schema_assembler = None
        if self._use_smart_comments and self._llm_client and self._table_vector_store:
            try:
                self._schema_assembler = SmartDBSchemaAssembler.create_with_llm(
                    connector=self.connector,
                    table_vector_store_connector=self._table_vector_store,
                    llm_client=self._llm_client,
                    embeddings=self._embeddings,
                    max_tables=self._max_tables,
                    enable_smart_comments=True
                )
                
                logger.info(" 智能表结构装配器创建成功")
                
                # 如果需要，自动生成智能注释
                if auto_generate_on_init:
                    self._generate_and_store_smart_schema()
                    
            except Exception as e:
                logger.warning(f"️ 智能表结构装配器创建失败: {e}")
                self._schema_assembler = None

    def _generate_and_store_smart_schema(self):
        """生成并存储包含智能注释的表结构到向量数据库"""
        if not self._schema_assembler:
            logger.warning("智能表结构装配器不可用")
            return
        
        try:
            logger.info(" 开始生成并存储包含智能注释的表结构...")
            
            # 持久化到向量数据库
            chunk_ids = self._schema_assembler.persist()
            
            logger.info(f" 成功存储 {len(chunk_ids)} 个包含智能注释的表结构chunks到向量数据库")
            
            # 获取统计信息
            stats = self._schema_assembler.get_smart_comment_stats()
            logger.info(f" 智能注释统计: {stats}")
            
            return chunk_ids
            
        except Exception as e:
            logger.error(f" 生成并存储智能表结构失败: {e}")
            raise

    def get_schema_link(
        self, db: str, question: Optional[str] = None
    ) -> Union[str, List[str]]:
        """返回增强的数据库schema信息
        
        关键：这里不再调用原始的_parse_db_summary，
        而是从向量数据库中检索包含智能注释的表结构chunks
        """
        
        # 如果智能注释不可用，回退到原始方法
        if not self._use_smart_comments or not self._schema_assembler:
            logger.debug("使用原始schema信息（智能注释不可用）")
            from dbgpt_ext.rag.summary.rdbms_db_summary import _parse_db_summary
            return _parse_db_summary(self.connector)
        
        try:
            logger.info(" 从向量数据库检索包含智能注释的表结构...")
            
            # 使用装配器的检索器获取相关的表结构chunks
            retriever = self._schema_assembler.as_retriever(top_k=self._max_tables)
            
            if question:
                # 基于问题检索相关表结构
                relevant_chunks = retriever.retrieve_with_scores(question, score_threshold=0.0)
                logger.info(f" 基于问题 '{question}' 检索到 {len(relevant_chunks)} 个相关表结构")
            else:
                # 检索所有表结构
                relevant_chunks = retriever.retrieve_with_scores("数据库表结构", score_threshold=0.0)
                logger.info(f" 检索到 {len(relevant_chunks)} 个表结构")
            
            # 提取表结构内容
            enhanced_schemas = []
            for chunk in relevant_chunks:
                if chunk.content:
                    enhanced_schemas.append(chunk.content.strip())
            
            if enhanced_schemas:
                logger.info(f" 成功获取 {len(enhanced_schemas)} 个包含智能注释的表结构")
                return enhanced_schemas
            else:
                logger.warning(" 未获取到表结构信息，回退到原始schema")
                from dbgpt_ext.rag.summary.rdbms_db_summary import _parse_db_summary
                return _parse_db_summary(self.connector)
                
        except Exception as e:
            logger.warning(f"️ 从向量数据库检索表结构失败: {e}")
            # 回退到原始schema
            from dbgpt_ext.rag.summary.rdbms_db_summary import _parse_db_summary
            return _parse_db_summary(self.connector)

    async def regenerate_smart_schema(self, table_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """重新生成智能注释和表结构
        
        Args:
            table_names: 要处理的表名列表，为None时处理所有表
            
        Returns:
            操作结果统计
        """
        if not self._schema_assembler:
            raise ValueError("智能表结构装配器不可用")
        
        try:
            logger.info(" 开始重新生成智能注释和表结构...")
            
            # 如果指定了表名，需要重新创建装配器
            if table_names:
                # 创建新的装配器，只处理指定的表
                filtered_assembler = SmartDBSchemaAssembler.create_with_llm(
                    connector=self.connector,
                    table_vector_store_connector=self._table_vector_store,
                    llm_client=self._llm_client,
                    embeddings=self._embeddings,
                    max_tables=len(table_names),
                    enable_smart_comments=True
                )
                
                # 手动设置要处理的表名
                filtered_assembler._chunks = filtered_assembler._generate_optimized_chunks(table_names)
                chunk_ids = filtered_assembler.persist()
            else:
                # 重新生成所有表的智能注释
                self._schema_assembler = SmartDBSchemaAssembler.create_with_llm(
                    connector=self.connector,
                    table_vector_store_connector=self._table_vector_store,
                    llm_client=self._llm_client,
                    embeddings=self._embeddings,
                    max_tables=self._max_tables,
                    enable_smart_comments=True
                )
                chunk_ids = self._schema_assembler.persist()
            
            # 获取统计信息
            stats = self._schema_assembler.get_smart_comment_stats()
            
            result = {
                "success": True,
                "processed_tables": len(table_names) if table_names else stats.get("total_tables", 0),
                "stored_chunks": len(chunk_ids),
                "stats": stats
            }
            
            logger.info(f" 智能注释和表结构重新生成完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f" 重新生成智能注释和表结构失败: {e}")
            return {"success": False, "error": str(e)}

    def get_smart_schema_stats(self) -> Dict[str, Any]:
        """获取智能表结构统计信息"""
        try:
            if not self._schema_assembler:
                return {"smart_schema_available": False}
            
            stats = self._schema_assembler.get_smart_comment_stats()
            stats["smart_schema_available"] = True
            stats["use_smart_comments"] = self._use_smart_comments
            stats["llm_client_available"] = self._llm_client is not None
            stats["vector_store_available"] = self._table_vector_store is not None
            
            return stats
            
        except Exception as e:
            logger.warning(f"获取智能表结构统计失败: {e}")
            return {"smart_schema_available": False, "error": str(e)}

    @classmethod
    def create_enhanced_db_resource(
        cls,
        name: str,
        connector,
        llm_client: LLMClient,
        table_vector_store: VectorStoreBase,
        embeddings: Optional[Embeddings] = None,
        use_smart_comments: bool = True,
        auto_generate_on_init: bool = True,
        max_tables: int = 30,
        **kwargs
    ) -> "EnhancedDBResource":
        """创建增强数据库资源的便捷方法
        
        Args:
            name: 资源名称
            connector: 数据库连接器
            llm_client: LLM客户端
            table_vector_store: 表结构向量存储
            embeddings: 嵌入模型
            use_smart_comments: 是否使用智能注释
            auto_generate_on_init: 是否在初始化时自动生成
            max_tables: 最大处理表数
            
        Returns:
            EnhancedDBResource实例
        """
        return cls(
            name=name,
            connector=connector,
            llm_client=llm_client,
            table_vector_store=table_vector_store,
            embeddings=embeddings,
            use_smart_comments=use_smart_comments,
            auto_generate_on_init=auto_generate_on_init,
            max_tables=max_tables,
            **kwargs
        )

    def __str__(self) -> str:
        """字符串表示"""
        return f"EnhancedDBResource(name={self.name}, smart_comments={self._use_smart_comments})"
