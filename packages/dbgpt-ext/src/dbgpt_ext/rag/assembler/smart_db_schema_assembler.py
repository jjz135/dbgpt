"""带智能注释的数据库表结构装配器"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from dbgpt.core import LLMClient, Chunk
from dbgpt.datasource.base import BaseConnector
from dbgpt.storage.vector_store.base import VectorStoreBase

from .optimized_db_schema import OptimizedDBSchemaAssembler
from .smart_comment_generator import SmartCommentGenerator
from ..chunk_manager import ChunkParameters

logger = logging.getLogger(__name__)


class SmartDBSchemaAssembler(OptimizedDBSchemaAssembler):
    """带智能注释的数据库表结构装配器
    
    继承自OptimizedDBSchemaAssembler，添加了LLM驱动的智能注释生成功能。
    """

    def __init__(
        self,
        connector: BaseConnector,
        table_vector_store_connector: VectorStoreBase,
        llm_client: LLMClient,
        field_vector_store_connector: Optional[VectorStoreBase] = None,
        chunk_parameters: Optional[ChunkParameters] = None,
        embedding_model: Optional[str] = None,
        embeddings = None,
        max_seq_length: int = 512,
        # 优化参数
        max_tables: int = 30,
        empty_table_threshold: int = 0,
        enable_table_filtering: bool = True,
        enable_smart_comments: bool = True,
        user_query: str = "",
        # 智能注释参数
        max_concurrent_llm_calls: int = 2,
        **kwargs: Any,
    ) -> None:
        """初始化带智能注释的装配器
        
        Args:
            llm_client: LLM客户端，用于生成智能注释
            max_concurrent_llm_calls: 最大并发LLM调用数
        """
        super().__init__(
            connector=connector,
            table_vector_store_connector=table_vector_store_connector,
            field_vector_store_connector=field_vector_store_connector,
            chunk_parameters=chunk_parameters,
            embedding_model=embedding_model,
            embeddings=embeddings,
            max_seq_length=max_seq_length,
            max_tables=max_tables,
            empty_table_threshold=empty_table_threshold,
            enable_table_filtering=enable_table_filtering,
            enable_smart_comments=enable_smart_comments,
            user_query=user_query,
            **kwargs
        )
        
        self._llm_client = llm_client
        self._max_concurrent_llm_calls = max_concurrent_llm_calls
        
        # 重新初始化智能注释生成器，传入LLM客户端
        if self._enable_smart_comments:
            self._comment_generator = SmartCommentGenerator(llm_client)
            
            # 检查并修复ChromaDB连接问题
            self._ensure_vector_store_ready()
            
            # 重新加载chunks，这次会包含智能注释
            logger.info("重新加载chunks以包含智能注释...")
            self._chunks = self._load_optimized_chunks()

    def _generate_optimized_chunks(self, table_names: List[str]) -> List[Chunk]:
        """生成优化的chunks，包含智能注释"""
        chunks = []
        
        # 如果启用智能注释，批量生成注释
        all_comments = {}
        if self._enable_smart_comments and self._comment_generator and self._llm_client:
            try:
                logger.info(f"开始为 {len(table_names)} 个表生成智能注释...")
                
                # 使用asyncio运行异步的注释生成
                all_comments = asyncio.run(
                    self._comment_generator.batch_generate_comments(
                        self._connector, 
                        table_names,
                        self._llm_client,
                        max_concurrent=self._max_concurrent_llm_calls
                    )
                )
                
                logger.info(f"智能注释生成完成，成功生成 {len(all_comments)} 个表的注释")
                
            except Exception as e:
                logger.warning(f"智能注释生成失败，使用默认注释: {e}")
                all_comments = {}
        
        for table_name in table_names:
            try:
                # 获取表的紧凑信息
                table_info = self._get_compact_table_info(table_name)
                
                if table_info:
                    # 获取智能注释
                    comments = all_comments.get(table_name, {})
                    
                    # 调试智能注释传递
                    logger.info(f"   表 {table_name} 智能注释传递调试:")
                    logger.info(f"   all_comments中是否有该表: {table_name in all_comments}")
                    logger.info(f"   comments类型: {type(comments)}")
                    logger.info(f"   comments内容: {comments}")
                    
                    # 创建增强的表描述（包含智能注释）
                    logger.info(f" SmartDBSchemaAssembler调用_create_enhanced_table_description: table={table_name}")
                    enhanced_content = self._create_enhanced_table_description(
                        table_name, table_info, comments
                    )
                    logger.info(f" SmartDBSchemaAssembler增强内容长度: {len(enhanced_content)}, 预览: {enhanced_content[:200]}...")
                    
                    # 创建单个紧凑的chunk（表+字段信息+智能注释合并）
                    chunk = Chunk(
                        content=enhanced_content,
                        metadata={
                            "table_name": table_name,
                            "chunk_type": "table_schema_smart",
                            "row_count": table_info.get("row_count", 0),
                            "column_count": table_info.get("column_count", 0),
                            "has_smart_comments": bool(comments.get("table_comment") or comments.get("field_comments")),
                            "smart_table_comment": comments.get("table_comment", ""),
                            "smart_field_count": len(comments.get("field_comments", {})),
                            "created_at": datetime.now().isoformat()
                        }
                    )
                    chunks.append(chunk)
                    
            except Exception as e:
                logger.warning(f"生成表 {table_name} 的智能chunk失败: {e}")
        
        return chunks

    @classmethod
    def create_with_llm(
        cls,
        connector: BaseConnector,
        table_vector_store_connector: VectorStoreBase,
        llm_client: LLMClient,
        field_vector_store_connector: Optional[VectorStoreBase] = None,
        chunk_parameters: Optional[ChunkParameters] = None,
        embedding_model: Optional[str] = None,
        embeddings = None,
        max_seq_length: int = 512,
        # 优化参数
        max_tables: Optional[int] = 30,
        empty_table_threshold: int = 0,
        enable_table_filtering: bool = True,
        enable_smart_comments: bool = True,
        user_query: str = "",
        # 智能注释参数
        max_concurrent_llm_calls: int = 2,
    ) -> "SmartDBSchemaAssembler":
        """创建带智能注释的装配器"""
        return cls(
            connector=connector,
            table_vector_store_connector=table_vector_store_connector,
            llm_client=llm_client,
            field_vector_store_connector=field_vector_store_connector,
            chunk_parameters=chunk_parameters,
            embedding_model=embedding_model,
            embeddings=embeddings,
            max_seq_length=max_seq_length,
            max_tables=max_tables,
            empty_table_threshold=empty_table_threshold,
            enable_table_filtering=enable_table_filtering,
            enable_smart_comments=enable_smart_comments,
            user_query=user_query,
            max_concurrent_llm_calls=max_concurrent_llm_calls,
        )

    def get_smart_comment_stats(self) -> Dict[str, Any]:
        """获取智能注释统计信息"""
        stats = self.get_optimization_stats()
        
        # 添加智能注释特定统计
        total_smart_comments = 0
        total_field_comments = 0
        
        for chunk in self._chunks:
            if chunk.metadata.get("has_smart_comments", False):
                total_smart_comments += 1
                total_field_comments += chunk.metadata.get("smart_field_count", 0)
        
        stats.update({
            "llm_client_available": self._llm_client is not None,
            "total_smart_table_comments": total_smart_comments,
            "total_smart_field_comments": total_field_comments,
            "max_concurrent_llm_calls": self._max_concurrent_llm_calls,
        })
        
        return stats
    
    def _ensure_vector_store_ready(self) -> None:
        """确保向量存储准备就绪，修复可能的连接问题"""
        try:
            # 检查是否是ChromaDB
            if hasattr(self._table_vector_store_connector, '_chroma_client'):
                logger.info("  检查ChromaDB连接状态...")
                
                # 尝试简单的连接测试
                chroma_client = self._table_vector_store_connector._chroma_client
                collections = chroma_client.list_collections()
                logger.info(f"ChromaDB连接正常，发现 {len(collections)} 个collections")
                
                # 检查目标collection（兼容ChromaDB v0.6.0+）
                collection_name = self._table_vector_store_connector._collection_name
                target_exists = self._check_collection_exists(chroma_client, collection_name, collections)
                
                if not target_exists:
                    logger.warning(f" 目标collection不存在: {collection_name}")
                    logger.info(" 尝试重新创建collection...")
                    
                    # 重新创建collection
                    collection_metadata = {"hnsw:space": "cosine"}
                    new_collection = chroma_client.get_or_create_collection(
                        name=collection_name,
                        embedding_function=None,
                        metadata=collection_metadata
                    )
                    
                    # 更新引用
                    self._table_vector_store_connector._collection = new_collection
                    logger.info(" Collection重新创建成功")
                
        except Exception as e:
            logger.warning(f" 向量存储连接检查失败: {e}")
            
            # 尝试使用修复工具
            try:
                from ..utils.chromadb_fix import fix_chromadb_issues
                logger.info("🔧 尝试使用ChromaDB修复工具...")
                
                fix_success = fix_chromadb_issues(self._table_vector_store_connector)
                if fix_success:
                    logger.info(" ChromaDB连接问题修复成功")
                else:
                    logger.warning(" ChromaDB连接问题修复失败")
            except Exception as fix_error:
                logger.warning(f"修复工具运行失败: {fix_error}")
    
    def persist(self, **kwargs: Any) -> List[str]:
        """持久化chunks到向量存储（增强版）"""
        # 先确保向量存储准备就绪
        self._ensure_vector_store_ready()
        
        # 调用父类的持久化方法
        return super().persist(**kwargs)
    
    def _check_collection_exists(self, chroma_client, collection_name: str, collections) -> bool:
        """检查collection是否存在（兼容ChromaDB v0.6.0+）"""
        try:
            # ChromaDB v0.6.0+ 返回的是字符串列表而不是对象列表
            if collections and isinstance(collections[0], str):
                # 新版本：collections是字符串列表
                return collection_name in collections
            else:
                # 旧版本：collections是对象列表
                return any(getattr(c, 'name', str(c)) == collection_name for c in collections)
        except Exception as e:
            logger.warning(f"检查collection存在性失败: {e}")
            
            # 回退方案：直接尝试获取collection
            try:
                chroma_client.get_collection(collection_name)
                return True
            except Exception:
                return False
