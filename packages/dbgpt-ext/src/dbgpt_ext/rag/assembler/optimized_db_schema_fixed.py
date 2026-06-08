"""数据库表结构装配器 - 解决ChromaDB并发问题"""

import logging
from typing import Any, List, Dict, Optional
import time
import threading

from dbgpt.core import Chunk, Embeddings
from dbgpt.datasource.base import BaseConnector
from dbgpt.storage.vector_store.base import VectorStoreBase

from .optimized_db_schema import OptimizedDBSchemaAssembler
from ..chunk_manager import ChunkParameters

logger = logging.getLogger(__name__)

# 全局锁，防止ChromaDB并发问题
_chroma_lock = threading.RLock()


class FixedOptimizedDBSchemaAssembler(OptimizedDBSchemaAssembler):
    """修复版的优化数据库表结构装配器
    
    主要修复：
    1. ChromaDB并发访问问题
    2. Collection创建和访问的同步问题
    3. 更好的错误处理和重试机制
    """

    def __init__(
        self,
        connector: BaseConnector,
        table_vector_store_connector: VectorStoreBase,
        field_vector_store_connector: Optional[VectorStoreBase] = None,
        chunk_parameters: Optional[ChunkParameters] = None,
        embedding_model: Optional[str] = None,
        embeddings: Optional[Embeddings] = None,
        max_seq_length: int = 512,
        # 优化参数
        max_tables: Optional[int] = None,
        empty_table_threshold: int = 0,
        enable_table_filtering: bool = True,
        enable_smart_comments: bool = True,
        user_query: str = "",
        **kwargs: Any,
    ) -> None:
        """初始化修复版装配器"""
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
        
        # 添加向量存储验证
        self._verify_vector_store()
    
    def _verify_vector_store(self) -> None:
        """验证向量存储的可用性"""
        try:
            # 检查ChromaDB连接
            if hasattr(self._table_vector_store_connector, '_chroma_client'):
                chroma_client = self._table_vector_store_connector._chroma_client
                collections = chroma_client.list_collections()
                logger.info(f"ChromaDB连接正常，现有collections: {len(collections)}")
            
            # 检查embedding模型
            if not self._embeddings:
                logger.warning(" Embedding模型未初始化，可能影响向量存储")
            else:
                # 测试embedding
                test_result = self._embeddings.embed_query("test")
                logger.info(f"Embedding模型测试通过，维度: {len(test_result)}")
                
        except Exception as e:
            logger.warning(f"向量存储验证警告: {e}")

    def persist(self, **kwargs: Any) -> List[str]:
        """持久化chunks到向量存储（修复版）"""
        if not self._chunks:
            logger.warning("没有chunks需要持久化")
            return []
        
        if not self._embeddings:
            logger.error(" Embedding模型未初始化，无法进行向量化存储")
            logger.info("  建议检查embedding模型配置")
            return []
        
        logger.info(f"开始持久化 {len(self._chunks)} 个优化chunks到向量存储")
        
        # 使用全局锁防止并发问题
        with _chroma_lock:
            return self._safe_persist_chunks()
    
    def _safe_persist_chunks(self) -> List[str]:
        """安全的持久化chunks方法"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"重试持久化 (第 {attempt + 1} 次尝试)")
                    time.sleep(retry_delay * attempt)  # 递增延迟
                
                # 验证向量存储状态
                self._ensure_vector_store_ready()
                
                # 分批处理chunks，避免一次性加载过多
                batch_size = 5  # 减小批次大小
                chunk_ids = []
                
                for i in range(0, len(self._chunks), batch_size):
                    batch_chunks = self._chunks[i:i+batch_size]
                    logger.info(f"持久化批次 {i//batch_size + 1}/{(len(self._chunks) + batch_size - 1)//batch_size}: {len(batch_chunks)} chunks")
                    
                    # 单独处理每个批次
                    batch_ids = self._persist_chunk_batch(batch_chunks)
                    chunk_ids.extend(batch_ids)
                    
                    # 批次间稍微延迟
                    time.sleep(0.1)
                
                logger.info(f" 成功持久化 {len(chunk_ids)} 个chunks")
                return chunk_ids
                
            except Exception as e:
                logger.error(f"持久化尝试 {attempt + 1} 失败: {e}")
                
                if attempt == max_retries - 1:
                    logger.error("  所有持久化尝试都失败了")
                    logger.info("  可能的解决方案:")
                    logger.info("   1. 检查ChromaDB服务状态")
                    logger.info("   2. 检查embedding模型配置")
                    logger.info("   3. 检查磁盘空间和权限")
                    logger.info("   4. 尝试重启ChromaDB服务")
                    return []
        
        return []
    
    def _ensure_vector_store_ready(self) -> None:
        """确保向量存储准备就绪"""
        try:
            # 检查ChromaDB collection状态
            if hasattr(self._table_vector_store_connector, '_collection'):
                collection = self._table_vector_store_connector._collection
                if collection is None:
                    raise ValueError("ChromaDB collection未初始化")
                
                # 尝试获取collection信息
                count = collection.count()
                logger.debug(f"ChromaDB collection当前包含 {count} 个文档")
            
        except Exception as e:
            logger.error(f"向量存储状态检查失败: {e}")
            raise
    
    def _persist_chunk_batch(self, chunks: List[Chunk]) -> List[str]:
        """持久化单个批次的chunks"""
        try:
            # 验证chunks内容
            valid_chunks = []
            for chunk in chunks:
                if chunk.content and chunk.content.strip():
                    valid_chunks.append(chunk)
                else:
                    logger.warning(f"跳过空chunk: {chunk.chunk_id}")
            
            if not valid_chunks:
                logger.warning("批次中没有有效chunks")
                return []
            
            # 使用较小的线程数和批次大小
            chunk_ids = self._table_vector_store_connector.load_document_with_limit(
                valid_chunks, 
                max_chunks_once_load=2,  # 减小批次
                max_threads=1  # 使用单线程避免并发问题
            )
            
            return chunk_ids
            
        except Exception as e:
            logger.error(f"批次持久化失败: {e}")
            
            # 尝试逐个持久化
            logger.info("尝试逐个持久化chunks...")
            chunk_ids = []
            
            for chunk in chunks:
                try:
                    single_ids = self._table_vector_store_connector.load_document_with_limit(
                        [chunk], max_chunks_once_load=1, max_threads=1
                    )
                    chunk_ids.extend(single_ids)
                except Exception as single_error:
                    logger.error(f"单个chunk持久化失败 {chunk.chunk_id}: {single_error}")
            
            return chunk_ids
    
    def get_persist_diagnostics(self) -> Dict[str, Any]:
        """获取持久化诊断信息"""
        diagnostics = {
            "chunks_count": len(self._chunks) if self._chunks else 0,
            "embeddings_available": self._embeddings is not None,
            "vector_store_type": type(self._table_vector_store_connector).__name__,
            "vector_store_available": self._table_vector_store_connector is not None
        }
        
        # ChromaDB特定诊断
        if hasattr(self._table_vector_store_connector, '_chroma_client'):
            try:
                chroma_client = self._table_vector_store_connector._chroma_client
                collections = chroma_client.list_collections()
                collection_name = self._table_vector_store_connector._collection_name
                
                diagnostics.update({
                    "chroma_client_available": True,
                    "total_collections": len(collections),
                    "target_collection_name": collection_name,
                    "collection_exists": any(c.name == collection_name for c in collections)
                })
                
                # 检查目标collection
                if diagnostics["collection_exists"]:
                    collection = self._table_vector_store_connector._collection
                    diagnostics["collection_count"] = collection.count()
                
            except Exception as e:
                diagnostics["chroma_diagnostics_error"] = str(e)
        
        return diagnostics


def create_fixed_assembler(
    connector: BaseConnector,
    table_vector_store_connector: VectorStoreBase,
    embeddings: Embeddings,
    enable_smart_comments: bool = True,
    max_tables: Optional[int] = None,
    **kwargs
) -> FixedOptimizedDBSchemaAssembler:
    """创建修复版装配器的便捷方法"""
    
    logger.info(" 创建修复版优化数据库表结构装配器")
    
    assembler = FixedOptimizedDBSchemaAssembler(
        connector=connector,
        table_vector_store_connector=table_vector_store_connector,
        embeddings=embeddings,
        enable_smart_comments=enable_smart_comments,
        max_tables=max_tables,
        **kwargs
    )
    
    # 输出诊断信息
    diagnostics = assembler.get_persist_diagnostics()
    logger.info("📊 装配器诊断信息:")
    for key, value in diagnostics.items():
        logger.info(f"   {key}: {value}")
    
    return assembler
