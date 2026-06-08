"""智能注释组装器 - 管理智能注释的向量化存储和检索"""

import logging
from typing import Any, Dict, List, Optional

from dbgpt.core import Chunk, Embeddings
from dbgpt.datasource.base import BaseConnector
from dbgpt.rag.embedding.embedding_factory import DefaultEmbeddingFactory
from dbgpt.storage.vector_store.base import VectorStoreBase

from ..assembler.base import BaseAssembler
from ..chunk_manager import ChunkParameters
from ..knowledge.smart_comment import SmartCommentKnowledge
from ..retriever.db_schema import DBSchemaRetriever

logger = logging.getLogger(__name__)


class SmartCommentAssembler(BaseAssembler):
    """智能注释组装器
    
    用于管理数据库表和字段智能注释的向量化存储。
    支持将AI生成的表注释和字段注释存储到向量数据库中，
    以便在数据科学查询时提供更准确的语义信息。
    
    Example:
        .. code-block:: python

            from dbgpt_ext.rag.assembler.smart_comment_assembler import SmartCommentAssembler
            from dbgpt.storage.vector_store.chroma_store import ChromaVectorConfig
            
            # 准备注释数据
            table_comments = {
                "users": {
                    "table_comment": "用户信息表",
                    "field_comments": {
                        "id": "用户唯一标识",
                        "name": "用户姓名",
                        "email": "用户邮箱地址"
                    }
                }
            }
            
            # 创建组装器
            assembler = SmartCommentAssembler.load_from_comments(
                table_comments=table_comments,
                vector_store_connector=vector_store,
                embedding_model="text-embedding-3-small"
            )
            
            # 持久化到向量数据库
            chunk_ids = assembler.persist()
            
            # 创建检索器
            retriever = assembler.as_retriever(top_k=3)
    """

    def __init__(
        self,
        table_comments: Dict[str, Dict[str, Any]],
        vector_store_connector: VectorStoreBase,
        connector: Optional[BaseConnector] = None,
        chunk_parameters: Optional[ChunkParameters] = None,
        embedding_model: Optional[str] = None,
        embeddings: Optional[Embeddings] = None,
        **kwargs: Any,
    ) -> None:
        """初始化智能注释组装器
        
        Args:
            table_comments: 表注释数据
            vector_store_connector: 向量存储连接器
            connector: 数据库连接器（可选，用于获取额外的表结构信息）
            chunk_parameters: 分块参数
            embedding_model: 嵌入模型名称
            embeddings: 嵌入模型实例
        """
        self._connector = connector
        self._vector_store_connector = vector_store_connector
        self._embedding_model = embedding_model
        
        if self._embedding_model and not embeddings:
            embeddings = DefaultEmbeddingFactory(
                default_model_name=self._embedding_model
            ).create(self._embedding_model)

        knowledge = SmartCommentKnowledge(
            table_comments=table_comments,
            metadata={"source": "smart_comment_assembler"}
        )
        
        super().__init__(
            knowledge=knowledge,
            chunk_parameters=chunk_parameters,
            **kwargs,
        )

    @classmethod
    def load_from_comments(
        cls,
        table_comments: Dict[str, Dict[str, Any]],
        vector_store_connector: VectorStoreBase,
        connector: Optional[BaseConnector] = None,
        chunk_parameters: Optional[ChunkParameters] = None,
        embedding_model: Optional[str] = None,
        embeddings: Optional[Embeddings] = None,
    ) -> "SmartCommentAssembler":
        """从注释数据创建组装器
        
        Args:
            table_comments: 表注释数据
            vector_store_connector: 向量存储连接器
            connector: 数据库连接器
            chunk_parameters: 分块参数
            embedding_model: 嵌入模型名称
            embeddings: 嵌入模型实例
            
        Returns:
            SmartCommentAssembler实例
        """
        return cls(
            table_comments=table_comments,
            vector_store_connector=vector_store_connector,
            connector=connector,
            chunk_parameters=chunk_parameters,
            embedding_model=embedding_model,
            embeddings=embeddings,
        )

    def get_chunks(self) -> List[Chunk]:
        """返回所有chunks"""
        return self._chunks

    def persist(self, **kwargs: Any) -> List[str]:
        """将智能注释chunks持久化到向量存储
        
        Returns:
            保存的chunk ID列表
        """
        try:
            logger.info(f"开始持久化 {len(self._chunks)} 个智能注释chunks到向量数据库")
            
            # 保存到向量数据库
            chunk_ids = self._vector_store_connector.load_document_with_limit(self._chunks)
            
            logger.info(f"成功持久化 {len(chunk_ids)} 个智能注释chunks")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"持久化智能注释chunks失败: {e}")
            raise

    def _extract_info(self, chunks) -> List[Chunk]:
        """提取信息（基类要求的方法）"""
        return []

    def as_retriever(self, top_k: int = 4, **kwargs) -> DBSchemaRetriever:
        """创建支持智能注释的检索器
        
        Args:
            top_k: 返回的top-k结果数量
            
        Returns:
            DBSchemaRetriever实例
        """
        return DBSchemaRetriever(
            top_k=top_k,
            connector=self._connector,
            table_vector_store_connector=self._vector_store_connector,
            **kwargs
        )

    def add_table_comments(self, table_name: str, comments: Dict[str, Any]) -> None:
        """添加新的表注释
        
        Args:
            table_name: 表名
            comments: 注释数据
        """
        if isinstance(self._knowledge, SmartCommentKnowledge):
            self._knowledge.add_table_comments(table_name, comments)
            # 重新加载知识以更新chunks
            self.load_knowledge(self._knowledge)

    def remove_table_comments(self, table_name: str) -> bool:
        """删除表注释
        
        Args:
            table_name: 表名
            
        Returns:
            是否成功删除
        """
        if isinstance(self._knowledge, SmartCommentKnowledge):
            success = self._knowledge.remove_table_comments(table_name)
            if success:
                # 重新加载知识以更新chunks
                self.load_knowledge(self._knowledge)
            return success
        return False

    def get_table_comments(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取指定表的注释
        
        Args:
            table_name: 表名
            
        Returns:
            表的注释数据
        """
        if isinstance(self._knowledge, SmartCommentKnowledge):
            return self._knowledge.get_table_comments(table_name)
        return None

    def get_all_tables(self) -> List[str]:
        """获取所有包含注释的表名"""
        if isinstance(self._knowledge, SmartCommentKnowledge):
            return self._knowledge.get_all_tables()
        return []

    def update_from_generator_results(
        self, 
        generator_results: Dict[str, Dict[str, Any]]
    ) -> None:
        """从SmartCommentGenerator的结果更新注释数据
        
        Args:
            generator_results: SmartCommentGenerator.batch_generate_comments()的结果
        """
        logger.info(f"从生成器结果更新 {len(generator_results)} 个表的注释")
        
        # 更新知识源
        if isinstance(self._knowledge, SmartCommentKnowledge):
            for table_name, comments in generator_results.items():
                self._knowledge.add_table_comments(table_name, comments)
        
        # 重新加载知识以更新chunks
        self.load_knowledge(self._knowledge)
        
        logger.info("智能注释数据更新完成")
