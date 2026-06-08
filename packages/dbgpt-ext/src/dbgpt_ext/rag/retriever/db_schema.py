"""DBSchema retriever."""

import logging
from typing import List, Optional, Dict, Any

from dbgpt._private.config import Config
from dbgpt.core import Chunk
from dbgpt.datasource.base import BaseConnector
from dbgpt.rag.retriever.base import BaseRetriever
from dbgpt.rag.retriever.rerank import DefaultRanker, Ranker
from dbgpt.storage.vector_store.base import VectorStoreBase
from dbgpt.storage.vector_store.filters import MetadataFilter, MetadataFilters
from dbgpt.util.chat_util import run_tasks
from dbgpt.util.executor_utils import blocking_func_to_async_no_executor

from ..summary.rdbms_db_summary import (
    _DEFAULT_COLUMN_SEPARATOR,
    _parse_db_summary,
    _parse_table_detail,
)

logger = logging.getLogger(__name__)

CFG = Config()


class DBSchemaRetriever(BaseRetriever):
    """DBSchema retriever."""

    def __init__(
        self,
        table_vector_store_connector: VectorStoreBase,
        field_vector_store_connector: VectorStoreBase = None,
        comment_vector_store_connector: VectorStoreBase = None,
        separator: str = "--table-field-separator--",
        column_separator: str = _DEFAULT_COLUMN_SEPARATOR,
        top_k: int = 4,
        connector: Optional[BaseConnector] = None,
        query_rewrite: bool = False,
        rerank: Optional[Ranker] = None,
        use_smart_comments: bool = True,
        **kwargs,
    ):
        """Create DBSchemaRetriever.

        Args:
            table_vector_store_connector: VectorStoreBase
                to load and retrieve table info.
            field_vector_store_connector: VectorStoreBase
                to load and retrieve field info.
            comment_vector_store_connector: VectorStoreBase
                to load and retrieve smart comments.
            separator: field/table separator
            top_k (int): top k
            connector (Optional[BaseConnector]): RDBMSConnector.
            query_rewrite (bool): query rewrite
            rerank (Ranker): rerank
            use_smart_comments (bool): whether to use smart comments for retrieval

        Examples:
            .. code-block:: python

                from dbgpt_ext.datasource.rdbms.conn_sqlite import SQLiteTempConnector
                from dbgpt_ext.rag.assembler.db_schema import DBSchemaAssembler
                from dbgpt_serve.rag.connector import VectorStoreConnector
                from dbgpt_ext.storage.vector_store.chroma_store import (
                    ChromaVectorConfig,
                )
                from dbgpt.rag.retriever.embedding import EmbeddingRetriever


                def _create_temporary_connection():
                    connect = SQLiteTempConnector.create_temporary_db()
                    connect.create_temp_tables(
                        {
                            "user": {
                                "columns": {
                                    "id": "INTEGER PRIMARY KEY",
                                    "name": "TEXT",
                                    "age": "INTEGER",
                                },
                                "data": [
                                    (1, "Tom", 10),
                                    (2, "Jerry", 16),
                                    (3, "Jack", 18),
                                    (4, "Alice", 20),
                                    (5, "Bob", 22),
                                ],
                            }
                        }
                    )
                    return connect


                connector = _create_temporary_connection()
                vector_store_config = ChromaVectorConfig(name="vector_store_name")
                embedding_model_path = "{your_embedding_model_path}"
                embedding_fn = embedding_factory.create(model_name=embedding_model_path)
                vector_connector = VectorStoreConnector.from_default(
                    "Chroma",
                    vector_store_config=vector_store_config,
                    embedding_fn=embedding_fn,
                )
                # get db struct retriever
                retriever = DBSchemaRetriever(
                    top_k=3,
                    vector_store_connector=vector_connector,
                    connector=connector,
                )
                chunks = retriever.retrieve("show columns from table")
                result = [chunk.content for chunk in chunks]
                print(f"db struct rag example results:{result}")
        """
        self._separator = separator
        self._column_separator = column_separator
        self._top_k = top_k
        self._connector = connector
        self._query_rewrite = query_rewrite
        self._table_vector_store_connector = table_vector_store_connector
        self._field_vector_store_connector = field_vector_store_connector
        self._comment_vector_store_connector = comment_vector_store_connector
        self._use_smart_comments = use_smart_comments
        self._need_embeddings = False
        if self._table_vector_store_connector:
            self._need_embeddings = True
        self._rerank = rerank or DefaultRanker(self._top_k)

    def _retrieve(
        self, query: str, filters: Optional[MetadataFilters] = None
    ) -> List[Chunk]:
        """Retrieve knowledge chunks.

        Args:
            query (str): query text
            filters: metadata filters.

        Returns:
            List[Chunk]: list of chunks
        """
        if self._need_embeddings:
            return self._similarity_search(query, filters)
        else:
            table_summaries = _parse_db_summary(self._connector)
            return [Chunk(content=table_summary) for table_summary in table_summaries]

    def _retrieve_with_score(
        self,
        query: str,
        score_threshold: float,
        filters: Optional[MetadataFilters] = None,
    ) -> List[Chunk]:
        """Retrieve knowledge chunks with score.

        Args:
            query (str): query text
            score_threshold (float): score threshold
            filters: metadata filters.

        Returns:
            List[Chunk]: list of chunks
        """
        return self._retrieve(query, filters)

    async def _aretrieve(
        self, query: str, filters: Optional[MetadataFilters] = None
    ) -> List[Chunk]:
        """Retrieve knowledge chunks.

        Args:
            query (str): query text
            filters: metadata filters.

        Returns:
            List[Chunk]: list of chunks
        """
        return await blocking_func_to_async_no_executor(
            func=self._retrieve,
            query=query,
            filters=filters,
        )

    async def _aretrieve_with_score(
        self,
        query: str,
        score_threshold: float,
        filters: Optional[MetadataFilters] = None,
    ) -> List[Chunk]:
        """Retrieve knowledge chunks with score.

        Args:
            query (str): query text
            score_threshold (float): score threshold
            filters: metadata filters.
        """
        return await self._aretrieve(query, filters)

    def _retrieve_field(self, table_chunk: Chunk, query) -> Chunk:
        metadata = table_chunk.metadata
        metadata["part"] = "field"
        filters = [MetadataFilter(key=k, value=v) for k, v in metadata.items()]
        # 使用0.0阈值确保字段检索也能正常工作
        field_chunks = self._field_vector_store_connector.similar_search_with_scores(
            query, self._top_k, 0.0, MetadataFilters(filters=filters)
        )
        field_contents = [chunk.content.strip() for chunk in field_chunks]
        table_chunk.content += (
            "\n" + self._separator + "\n" + self._column_separator.join(field_contents)
        )
        return self._deserialize_table_chunk(table_chunk)

    def _similarity_search(
        self, query, filters: Optional[MetadataFilters] = None
    ) -> List[Chunk]:
        """Similar search."""
        # 使用更低的阈值以提高召回率，特别是对于中文查询
        score_threshold = 0.0  # 改为0.0以确保能够召回相关文档
        
        logger.info(f" 开始向量检索: query='{query}', top_k={self._top_k}, threshold={score_threshold}")
        
        all_chunks = []
        
        # 首先从智能注释向量库中检索
        if self._use_smart_comments and self._comment_vector_store_connector:
            try:
                logger.info(" 从智能注释向量库中检索...")
                comment_chunks = self._comment_vector_store_connector.similar_search_with_scores(
                    query, self._top_k, score_threshold, filters
                )
                logger.info(f" 智能注释检索结果: 找到 {len(comment_chunks)} 个相关注释")
                
                # 增强注释chunks的内容，添加原始schema信息
                enhanced_comment_chunks = self._enhance_comment_chunks(comment_chunks)
                all_chunks.extend(enhanced_comment_chunks)
                
            except Exception as e:
                logger.warning(f"  智能注释检索失败: {e}")
        
        # 从表结构向量库中检索
        table_chunks = self._table_vector_store_connector.similar_search_with_scores(
            query, self._top_k, score_threshold, filters
        )
        
        logger.info(f" 表结构检索结果: 找到 {len(table_chunks)} 个相关表")
        for i, chunk in enumerate(table_chunks[:3]):  # 只显示前3个
            logger.info(f"  {i+1}. 分数: {chunk.score:.4f}, 内容长度: {len(chunk.content)}, ID: {chunk.chunk_id}")
            if chunk.content:
                preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
                logger.info(f"     内容预览: {preview}")

        # 如果向量检索没有结果，回退到直接数据库schema查询
        if not table_chunks and not all_chunks and self._connector:
            logger.warning("  向量检索无结果，回退到直接数据库schema查询")
            try:
                table_summaries = _parse_db_summary(self._connector)
                fallback_chunks = [Chunk(content=table_summary) for table_summary in table_summaries]
                logger.info(f" 回退查询成功，获得 {len(fallback_chunks)} 个表的schema信息")
                return fallback_chunks
            except Exception as e:
                logger.error(f" 回退查询也失败: {e}")

        # Find all table chunks which are not separated
        not_sep_chunks = [
            chunk for chunk in table_chunks if not chunk.metadata.get("separated")
        ]
        separated_chunks = [
            chunk for chunk in table_chunks if chunk.metadata.get("separated")
        ]

        # 处理分离的chunks
        if separated_chunks:
            # Create tasks list
            # The fields of table is too large, and it has to be separated into chunks,
            # so we need to retrieve fields of each table separately
            tasks = [
                lambda c=chunk: self._retrieve_field(c, query) for chunk in separated_chunks
            ]
            # Run tasks concurrently
            separated_result = run_tasks(tasks, concurrency_limit=3)
            all_chunks.extend(separated_result)
        
        # 添加未分离的表chunks
        all_chunks.extend([self._deserialize_table_chunk(chunk) for chunk in not_sep_chunks])
        
        # 使用reranker对结果进行重新排序
        if len(all_chunks) > self._top_k and self._rerank:
            all_chunks = self._rerank.rank(all_chunks, query)
        
        return all_chunks

    def _enhance_comment_chunks(self, comment_chunks: List[Chunk]) -> List[Chunk]:
        """增强注释chunks，添加原始schema信息
        
        Args:
            comment_chunks: 智能注释chunks
            
        Returns:
            增强后的chunks列表
        """
        enhanced_chunks = []
        
        for chunk in comment_chunks:
            try:
                table_name = chunk.metadata.get("table_name")
                if not table_name or not self._connector:
                    enhanced_chunks.append(chunk)
                    continue
                
                # 获取表的原始schema信息
                try:
                    columns = self._connector.get_columns(table_name)
                    if columns:
                        # 构建完整的表信息
                        schema_info = f"\n\n原始表结构:\nCREATE TABLE `{table_name}` (\n"
                        for col in columns:
                            col_name = col["name"]
                            col_type = str(col["type"]) if "type" in col else "UNKNOWN"
                            col_comment = col.get("comment", "")
                            schema_info += f"    `{col_name}` {col_type.upper()}"
                            if col_comment:
                                schema_info += f" COMMENT '{col_comment}'"
                            schema_info += ",\n"
                        schema_info = schema_info.rstrip(",\n") + "\n);"
                        
                        # 获取索引信息
                        try:
                            indexes = self._connector.get_indexes(table_name)
                            if indexes:
                                index_info = "\n索引信息:\n"
                                for index in indexes:
                                    if isinstance(index, tuple):
                                        index_name, _ = index
                                        index_info += f"- {index_name}\n"
                                    else:
                                        index_info += f"- {index.get('name', 'unknown')}\n"
                                schema_info += index_info
                        except Exception:
                            pass
                        
                        # 将schema信息添加到注释chunk的内容中
                        enhanced_content = chunk.content + schema_info
                        enhanced_chunk = Chunk(
                            content=enhanced_content,
                            metadata=chunk.metadata,
                            chunk_id=chunk.chunk_id,
                            score=getattr(chunk, 'score', 0.0)
                        )
                        enhanced_chunks.append(enhanced_chunk)
                    else:
                        enhanced_chunks.append(chunk)
                        
                except Exception as e:
                    logger.warning(f"获取表 {table_name} 的schema信息失败: {e}")
                    enhanced_chunks.append(chunk)
                    
            except Exception as e:
                logger.warning(f"增强注释chunk失败: {e}")
                enhanced_chunks.append(chunk)
        
        return enhanced_chunks

    def get_smart_comment_stats(self) -> Dict[str, Any]:
        """获取智能注释统计信息"""
        try:
            if not self._comment_vector_store_connector:
                return {"smart_comments_available": False}
            
            # 查询智能注释chunks
            test_chunks = self._comment_vector_store_connector.similar_search(
                "智能注释", top_k=100, score_threshold=0.0
            )
            
            table_comments = 0
            field_comments = 0
            tables_with_comments = set()
            
            for chunk in test_chunks:
                metadata = chunk.metadata or {}
                if metadata.get("source") == "smart_comment_generator":
                    table_name = metadata.get("table_name")
                    if table_name:
                        tables_with_comments.add(table_name)
                    
                    comment_type = metadata.get("type")
                    if comment_type == "table_comment":
                        table_comments += 1
                    elif comment_type == "field_comment":
                        field_comments += 1
            
            return {
                "smart_comments_available": True,
                "total_table_comments": table_comments,
                "total_field_comments": field_comments,
                "tables_with_comments": len(tables_with_comments),
                "use_smart_comments": self._use_smart_comments
            }
            
        except Exception as e:
            logger.warning(f"获取智能注释统计失败: {e}")
            return {"smart_comments_available": False, "error": str(e)}

    def _deserialize_table_chunk(self, chunk: Chunk) -> Chunk:
        """Deserialize table chunk."""
        db_summary_version = chunk.metadata.get("db_summary_version")
        if not db_summary_version:
            return chunk
        parts = chunk.content.split(self._separator)
        table_part, field_part = parts[0].strip(), parts[1].strip()
        table_detail = _parse_table_detail(table_part)
        table_name = table_detail.get("table_name")
        table_comment = table_detail.get("table_comment")
        index_keys = table_detail.get("index_keys")

        table_name = table_name.strip() if table_name else table_name
        table_comment = table_comment.strip() if table_comment else table_comment
        index_keys = index_keys.strip() if index_keys else index_keys
        if not table_name:
            return chunk

        create_statement = f"CREATE TABLE `{table_name}`\r\n(\r\n    "
        create_statement += field_part
        create_statement += "\r\n)"
        if table_comment:
            create_statement += f' COMMENT "{table_comment}"\r\n'
        if index_keys:
            create_statement += f"Index keys: {index_keys}"

        chunk.content = create_statement
        return chunk
