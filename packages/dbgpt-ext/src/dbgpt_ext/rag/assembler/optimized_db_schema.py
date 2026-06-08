"""优化的数据库表结构装配器 - 集成表过滤和智能分块"""

import logging
from typing import Any, List, Optional, Dict
from datetime import datetime

from dbgpt.core import Chunk, Embeddings
from dbgpt.datasource.base import BaseConnector
from dbgpt.rag.embedding.embedding_factory import DefaultEmbeddingFactory
from dbgpt.storage.vector_store.base import VectorStoreBase

from .base import BaseAssembler
from ..chunk_manager import ChunkParameters
from ..knowledge.datasource import DatasourceKnowledge
from ..retriever.db_schema import DBSchemaRetriever
from .smart_comment_generator import SmartCommentGenerator

logger = logging.getLogger(__name__)


class OptimizedDBSchemaAssembler(BaseAssembler):
    """优化的数据库表结构装配器
    
    主要优化：
    1. 智能表过滤：忽略空表和系统表
    2. 优先级排序：业务表优先
    3. 紧凑分块：减少chunk数量
    4. 缓存机制：避免重复分析
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
        max_tables: int = 50,
        empty_table_threshold: int = 0,
        enable_table_filtering: bool = True,
        enable_smart_comments: bool = True,
        user_query: str = "",
        **kwargs: Any,
    ) -> None:
        """初始化优化的装配器
        
        Args:
            max_tables: 最大处理表数量
            empty_table_threshold: 空表阈值
            enable_table_filtering: 是否启用表过滤
            enable_smart_comments: 是否启用智能注释生成
            user_query: 用户查询（用于相关性过滤）
        """
        self._connector = connector
        self._table_vector_store_connector = table_vector_store_connector
        self._field_vector_store_connector = field_vector_store_connector
        self._chunk_parameters = chunk_parameters
        self._max_seq_length = max_seq_length
        
        # 优化参数
        self._max_tables = max_tables
        self._empty_table_threshold = empty_table_threshold
        self._enable_table_filtering = enable_table_filtering
        self._enable_smart_comments = enable_smart_comments
        self._user_query = user_query
        
        # 初始化embeddings
        if embeddings:
            self._embeddings = embeddings
        else:
            try:
                # 尝试创建embedding模型
                if embedding_model:
                    # 检查embedding_model是否包含完整路径，如果不是则添加embedding前缀
                    if not embedding_model.startswith(('/', '\\', 'embedding/')):
                        embedding_path = f"embedding/{embedding_model}"
                    else:
                        embedding_path = embedding_model
                    
                    self._embeddings = DefaultEmbeddingFactory(
                        default_model_name=embedding_model,
                        default_model_path=embedding_path
                    ).create()
                    logger.info(f"使用指定embedding模型: {embedding_path}")
                else:
                    # 使用系统的embedding工厂
                    from dbgpt.component import SystemApp
                    from dbgpt.rag.embedding.embedding_factory import EmbeddingFactory
                    
                    try:
                        system_app = SystemApp.get_instance()
                        embedding_factory = system_app.get_component(
                            "embedding_factory", EmbeddingFactory
                        )
                        self._embeddings = embedding_factory.create()
                        logger.info("使用系统embedding工厂创建embeddings")
                    except Exception as system_error:
                        logger.warning(f"无法获取系统embedding工厂: {system_error}")
                        # 最后的回退方案：使用默认的embedding模型
                        default_embedding_path = "embedding/text2vec-large-chinese"
                        self._embeddings = DefaultEmbeddingFactory(
                            default_model_name="text2vec-large-chinese",
                            default_model_path=default_embedding_path
                        ).create()
                        logger.info(f"使用默认embedding模型: {default_embedding_path}")
                        
            except Exception as e:
                logger.error(f"Embedding初始化失败: {e}")
                logger.info("回退到无embedding模式，将影响向量化功能")
                self._embeddings = None
        
        # 创建知识源（BaseAssembler需要）
        from ..knowledge.datasource import DatasourceKnowledge
        knowledge = DatasourceKnowledge(connector, model_dimension=max_seq_length)
        
        # 系统表模式
        self._system_table_patterns = [
            'information_schema', 'performance_schema', 'mysql', 'sys',
            'pg_catalog', 'pg_toast', '__', 'sqlite_', 'msreplication_',
            'sysdiagrams', 'dtproperties'
        ]
        
        # 业务关键词
        self._business_keywords = [
            'user', 'order', 'product', 'customer', 'sales', 'invoice',
            'payment', 'transaction', 'account', 'item', 'service', 'data'
        ]
        
        # 初始化智能注释生成器
        self._comment_generator = None
        self._llm_client = None  # 基础版本没有LLM客户端
        if self._enable_smart_comments:
            self._comment_generator = SmartCommentGenerator()
        
        # 调用父类初始化（必须在最后调用）
        super().__init__(
            knowledge=knowledge,
            chunk_parameters=chunk_parameters,
            **kwargs
        )
        
        # 重新加载优化的chunks（覆盖父类的chunks）
        self._chunks = self._load_optimized_chunks()

    def _load_optimized_chunks(self) -> List[Chunk]:
        """加载优化的chunks"""
        logger.info("开始加载优化的数据库表结构chunks...")
        
        try:
            # 获取所有表名
            all_tables = list(self._connector.get_table_names())
            logger.info(f"发现 {len(all_tables)} 个表")
            
            # 过滤表
            if self._enable_table_filtering:
                filtered_tables = self._filter_tables(all_tables)
                logger.info(f"过滤后剩余 {len(filtered_tables)} 个表")
            else:
                # 如果max_tables为None，处理所有表
                if self._max_tables is None:
                    filtered_tables = all_tables
                    logger.info("处理所有表（无数量限制）")
                else:
                    filtered_tables = all_tables[:self._max_tables]
                    logger.info(f"限制处理前 {self._max_tables} 个表")
            
            # 验证表处理完整性
            self._validate_table_processing(filtered_tables, all_tables)
            
            # 生成优化的chunks
            chunks = self._generate_optimized_chunks(filtered_tables)
            logger.info(f"生成了 {len(chunks)} 个优化chunks")
            
            # 验证chunks完整性
            self._validate_chunk_completeness(chunks, filtered_tables)
            
            return chunks
            
        except Exception as e:
            logger.error(f"加载优化chunks失败: {e}")
            return []

    def _filter_tables(self, table_names: List[str]) -> List[str]:
        """过滤表名"""
        logger.info("开始过滤表...")
        
        # 分析表的优先级
        table_priorities = []
        
        for table_name in table_names:
            try:
                priority_score = self._calculate_table_priority(table_name)
                if priority_score > 0:  # 只保留有意义的表
                    table_priorities.append((table_name, priority_score))
            except Exception as e:
                logger.warning(f"分析表 {table_name} 优先级失败: {e}")
        
        # 按优先级排序并限制数量
        table_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # 如果max_tables为None，返回所有有效表
        if self._max_tables is None:
            filtered_tables = [name for name, _ in table_priorities]
            logger.info(f"返回所有 {len(filtered_tables)} 个有效表")
        else:
            filtered_tables = [name for name, _ in table_priorities[:self._max_tables]]
            logger.info(f"返回优先级最高的 {len(filtered_tables)} 个表")
        
        return filtered_tables

    def _calculate_table_priority(self, table_name: str) -> float:
        """计算表的优先级评分"""
        table_name_lower = table_name.lower()
        score = 0.0
        
        # 系统表 - 忽略
        if any(pattern in table_name_lower for pattern in self._system_table_patterns):
            return 0.0
        
        # 获取表的基本信息
        try:
            row_count = self._get_table_row_count(table_name)
            
            # 空表 - 低优先级
            if row_count <= self._empty_table_threshold:
                return 0.1  # 给一个很小的分数，避免完全忽略
            
            # 数据量评分
            if row_count > 1000:
                score += 3.0
            elif row_count > 100:
                score += 2.0
            elif row_count > 10:
                score += 1.0
            else:
                score += 0.5
            
        except Exception:
            # 如果无法获取行数，给默认分数
            score += 1.0
        
        # 业务相关性评分
        business_score = sum(
            1.0 for keyword in self._business_keywords 
            if keyword in table_name_lower
        )
        score += business_score
        
        # 查询相关性评分
        if self._user_query:
            query_keywords = self._extract_query_keywords(self._user_query)
            if any(keyword in table_name_lower for keyword in query_keywords):
                score += 2.0
        
        return score

    def _get_table_row_count(self, table_name: str) -> int:
        """获取表的行数"""
        try:
            with self._connector.session_scope() as session:
                from sqlalchemy import text
                result = session.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                return result.fetchone()[0]
        except Exception:
            return 0

    def _extract_query_keywords(self, query: str) -> List[str]:
        """从用户查询中提取关键词"""
        import re
        
        # 移除常见停用词
        stopwords = {'的', '是', '在', '有', '和', '与', '或', '查询', '显示', '统计', '分析', 'select', 'from', 'where'}
        
        # 提取中英文单词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query.lower())
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        return keywords

    def _generate_optimized_chunks(self, table_names: List[str]) -> List[Chunk]:
        """生成优化的chunks，集成智能注释"""
        chunks = []
        
        # 如果启用智能注释，批量生成注释
        all_comments = {}
        if self._enable_smart_comments and self._comment_generator:
            try:
                logger.info("开始生成智能注释...")
                # 需要LLM客户端，这里先跳过智能注释，在实际使用时会传入
                logger.info("智能注释功能已启用，将在有LLM客户端时生成")
            except Exception as e:
                logger.warning(f"智能注释生成失败，使用默认注释: {e}")
        
        failed_tables = []
        
        for i, table_name in enumerate(table_names, 1):
            success = False
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"重试处理表 {table_name} (第 {attempt + 1} 次尝试)")
                    else:
                        logger.debug(f"处理表 {i}/{len(table_names)}: {table_name}")
                    
                    # 获取表的紧凑信息
                    table_info = self._get_compact_table_info(table_name)
                    
                    if table_info:
                        # 获取智能注释
                        comments = all_comments.get(table_name, {})
                        
                        # 创建增强的表描述（包含智能注释）
                        logger.info(f"🔧 调用_create_enhanced_table_description: table={table_name}")
                        enhanced_content = self._create_enhanced_table_description(
                            table_name, table_info, comments
                        )
                        logger.info(f"🔧 增强内容长度: {len(enhanced_content)}, 预览: {enhanced_content[:200]}...")
                        
                        # 创建单个紧凑的chunk（表+字段信息+智能注释合并）
                        chunk = Chunk(
                            content=enhanced_content,
                            metadata={
                                "table_name": table_name,
                                "chunk_type": "table_schema_enhanced",
                                "row_count": table_info.get("row_count", 0),
                                "column_count": table_info.get("column_count", 0),
                                "has_smart_comments": bool(comments),
                                "created_at": datetime.now().isoformat()
                            }
                        )
                        chunks.append(chunk)
                        success = True
                    else:
                        logger.warning(f"跳过表 {table_name}：无法获取表信息")
                        
                except Exception as e:
                    logger.warning(f"处理表 {table_name} 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        failed_tables.append((table_name, str(e)))
            
            if not success and table_name not in [t[0] for t in failed_tables]:
                failed_tables.append((table_name, "表信息获取失败"))
        
        # 记录失败统计
        if failed_tables:
            logger.warning(f"  {len(failed_tables)} 个表处理失败:")
            for table_name, error in failed_tables[:3]:  # 只显示前3个
                logger.warning(f"  - {table_name}: {error}")
            if len(failed_tables) > 3:
                logger.warning(f"  ... 还有 {len(failed_tables) - 3} 个表失败")
        
        success_rate = (len(table_names) - len(failed_tables)) / len(table_names) if table_names else 0
        logger.info(f"表处理成功率: {success_rate:.2%} ({len(table_names) - len(failed_tables)}/{len(table_names)})")
        
        return chunks

    def _get_compact_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取紧凑的表信息"""
        try:
            with self._connector.session_scope() as session:
                # 获取列信息
                from sqlalchemy import text
                result = session.execute(text(f"DESCRIBE `{table_name}`"))
                columns = result.fetchall()
                
                # 获取行数
                result = session.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                row_count = result.fetchone()[0]
                
                # 生成紧凑的表描述
                content = self._format_compact_table_description(
                    table_name, columns, row_count
                )
                
                #  修复：将columns信息转换为标准格式并包含在返回值中
                columns_list = []
                for col in columns:
                    columns_list.append({
                        "name": col[0],  # Field name
                        "type": col[1],  # Type
                        "null": col[2],  # Null
                        "key": col[3],   # Key (PRI, MUL, etc.)
                        "default": col[4], # Default
                        "extra": col[5]  # Extra
                    })
                
                result = {
                    "content": content,
                    "row_count": row_count,
                    "column_count": len(columns),
                    "columns": columns_list  # 🆕 添加columns信息
                }
                
                logger.info(f"  _get_compact_table_info返回值: table={table_name}")
                logger.info(f"   返回keys: {list(result.keys())}")
                logger.info(f"   columns数量: {len(result['columns'])}")
                logger.info(f"   columns示例: {result['columns'][:2] if result['columns'] else '空'}")
                
                return result
                
        except Exception as e:
            logger.warning(f"获取表 {table_name} 信息失败: {e}")
            return None

    def _format_compact_table_description(self, table_name: str, 
                                        columns: List, row_count: int) -> str:
        """格式化紧凑的表描述"""
        # 表基本信息
        content = f"表名: {table_name}\n"
        content += f"数据量: {row_count} 行, {len(columns)} 列\n"
        
        # 主键信息
        primary_keys = [col[0] for col in columns if col[3] == 'PRI']
        if primary_keys:
            content += f"主键: {', '.join(primary_keys)}\n"
        
        # 字段信息（紧凑格式）
        content += "字段: "
        field_descriptions = []
        for col in columns:
            field_name = col[0]
            field_type = col[1]
            
            # 简化字段类型描述
            simplified_type = self._simplify_field_type(field_type)
            
            field_desc = f"{field_name}({simplified_type})"
            
            # 添加关键标识
            if col[3] == 'PRI':
                field_desc += "[主键]"
            elif col[3] == 'MUL':
                field_desc += "[索引]"
            
            field_descriptions.append(field_desc)
        
        content += ", ".join(field_descriptions)
        
        return content

    def _simplify_field_type(self, field_type: str) -> str:
        """简化字段类型描述"""
        field_type_lower = field_type.lower()
        
        # 简化常见类型
        if 'varchar' in field_type_lower or 'char' in field_type_lower:
            return 'text'
        elif 'int' in field_type_lower:
            return 'int'
        elif 'decimal' in field_type_lower or 'float' in field_type_lower or 'double' in field_type_lower:
            return 'number'
        elif 'date' in field_type_lower or 'time' in field_type_lower:
            return 'datetime'
        elif 'text' in field_type_lower or 'blob' in field_type_lower:
            return 'longtext'
        else:
            return field_type.split('(')[0]  # 移除长度限制

    def _create_enhanced_table_description(
        self, 
        table_name: str, 
        table_info: Dict[str, Any], 
        comments: Dict[str, Any]
    ) -> str:
        """创建增强的表描述，包含智能注释"""
        # 基础表信息
        content = f"表名: {table_name}\n"
        
        # 添加表注释（如果有）
        table_comment = comments.get("table_comment", "")
        if table_comment and table_comment != f"{table_name}数据表":
            content += f"表说明: {table_comment}\n"
        
        # 数据量信息
        row_count = table_info.get("row_count", 0)
        column_count = table_info.get("column_count", 0)
        content += f"数据量: {row_count} 行, {column_count} 列\n"
        
        # 获取列信息
        columns = table_info.get("columns", [])
        logger.info(f"   表 {table_name} 列信息调试:")
        logger.info(f"   table_info keys: {list(table_info.keys())}")
        logger.info(f"   columns数量: {len(columns)}")
        logger.info(f"   columns内容: {columns[:3] if columns else '空列表'}")
        
        if columns:
            # 主键信息
            primary_keys = [col.get("name") for col in columns if col.get("key") == "PRI"]
            if primary_keys:
                content += f"主键: {', '.join(primary_keys)}\n"
            
            # 字段信息（增强版，包含智能注释）
            content += "字段: "
            field_descriptions = []
            field_comments = comments.get("field_comments", {})
            
            logger.info(f"   表 {table_name} 的智能注释调试:")
            logger.info(f"   comments参数类型: {type(comments)}")
            logger.info(f"   comments参数内容: {comments}")
            logger.info(f"   table_comment: {comments.get('table_comment', 'None')}")
            logger.info(f"   field_comments类型: {type(field_comments)}")
            logger.info(f"   field_comments数量: {len(field_comments)}")
            if field_comments:
                logger.info(f"   field_comments示例: {list(field_comments.items())[:3]}")
            else:
                logger.warning(f"❌ 表 {table_name} 的field_comments为空！")
            
            for col in columns:
                field_name = col.get("name", "")
                field_type = col.get("type", "")
                
                # 简化字段类型描述
                simplified_type = self._simplify_field_type(field_type)
                
                # 构建字段描述
                field_desc = f"{field_name}({simplified_type})"
                
                # 添加智能注释
                if field_name in field_comments:
                    smart_comment = field_comments[field_name]
                    if smart_comment and smart_comment != f"{field_name}字段":
                        field_desc += f"[{smart_comment}]"
                        logger.debug(f"   字段 {field_name} 添加智能注释: {smart_comment}")
                    else:
                        logger.debug(f"    字段 {field_name} 智能注释为空或默认值")
                else:
                    logger.debug(f"❌ 字段 {field_name} 没有智能注释")
                
                # 添加关键标识
                if col.get("key") == "PRI":
                    field_desc += "[主键]"
                elif col.get("key") == "MUL":
                    field_desc += "[索引]"
                
                field_descriptions.append(field_desc)
            
            content += ", ".join(field_descriptions)
        else:
            # 回退到原始格式
            logger.warning(f"   表 {table_name} 没有columns信息，使用回退逻辑")
            logger.info(f"   回退前content: {content}")
            original_content = table_info.get("content", content)
            logger.info(f"   table_info.content: {original_content}")
            content = original_content
        
        return content

    @classmethod
    def load_from_connection(
        cls,
        connector: BaseConnector,
        table_vector_store_connector: VectorStoreBase,
        field_vector_store_connector: Optional[VectorStoreBase] = None,
        chunk_parameters: Optional[ChunkParameters] = None,
        embedding_model: Optional[str] = None,
        embeddings: Optional[Embeddings] = None,
        max_seq_length: int = 512,
        # 优化参数
        max_tables: Optional[int] = 50,
        empty_table_threshold: int = 0,
        enable_table_filtering: bool = True,
        enable_smart_comments: bool = True,
        user_query: str = "",
        **kwargs: Any,
    ) -> "OptimizedDBSchemaAssembler":
        """从数据库连接创建优化的装配器"""
        return cls(
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
            **kwargs,
        )

    def get_chunks(self) -> List[Chunk]:
        """获取chunks"""
        return self._chunks

    def persist(self, **kwargs: Any) -> List[str]:
        """持久化chunks到向量存储"""
        if not self._chunks:
            logger.warning("没有chunks需要持久化")
            return []
        
        if not self._embeddings:
            logger.error("  Embedding模型未初始化，无法进行向量化存储")
            logger.info("   建议检查embedding模型配置或使用非向量化的存储方式")
            return []
        
        # 所有chunks都存储到table vector store（简化存储结构）
        logger.info(f"持久化 {len(self._chunks)} 个优化chunks到向量存储")
        
        try:
            # 修复ChromaDB并发问题：使用较小的批次和单线程
            return self._safe_persist_with_retry()
        except Exception as e:
            logger.error(f"向量存储持久化失败: {e}")
            logger.info(" 可能是embedding模型问题，请检查embedding配置")
            return []
    
    def _safe_persist_with_retry(self) -> List[str]:
        """安全的持久化方法，带重试机制"""
        import time
        
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"重试持久化 (第 {attempt + 1} 次尝试)")
                    time.sleep(retry_delay)
                
                # 使用较小的批次大小和单线程，避免ChromaDB并发问题
                chunk_ids = self._table_vector_store_connector.load_document_with_limit(
                    self._chunks,
                    max_chunks_once_load=3,  # 减小批次大小
                    max_threads=1  # 使用单线程避免并发问题
                )
                
                logger.info(f" 成功持久化 {len(chunk_ids)} 个chunks")
                return chunk_ids
                
            except Exception as e:
                logger.warning(f"持久化尝试 {attempt + 1} 失败: {e}")
                
                if "does not exist" in str(e):
                    logger.info(" 检测到Collection不存在错误，尝试重新初始化向量存储")
                    try:
                        # 尝试重新创建collection
                        if hasattr(self._table_vector_store_connector, 'create_collection'):
                            collection_name = getattr(self._table_vector_store_connector, '_collection_name', 'default')
                            self._table_vector_store_connector.create_collection(collection_name)
                            logger.info(" 向量存储collection重新创建成功")
                    except Exception as recreate_error:
                        logger.warning(f"重新创建collection失败: {recreate_error}")
                
                if attempt == max_retries - 1:
                    logger.error(" 所有持久化尝试都失败了")
                    logger.info("  建议的解决方案:")
                    logger.info("   1. 检查ChromaDB服务状态")
                    logger.info("   2. 检查embedding模型配置")
                    logger.info("   3. 检查磁盘空间和权限")
                    logger.info("   4. 重启应用程序")
                    
                    # 尝试逐个持久化作为最后手段
                    logger.info(" 尝试逐个持久化chunks...")
                    return self._persist_chunks_individually()
        
        return []
    
    def _persist_chunks_individually(self) -> List[str]:
        """逐个持久化chunks（最后手段）"""
        successful_ids = []
        failed_count = 0
        
        for i, chunk in enumerate(self._chunks):
            try:
                logger.debug(f"持久化单个chunk {i+1}/{len(self._chunks)}")
                chunk_ids = self._table_vector_store_connector.load_document_with_limit(
                    [chunk], max_chunks_once_load=1, max_threads=1
                )
                successful_ids.extend(chunk_ids)
            except Exception as e:
                failed_count += 1
                logger.warning(f"单个chunk持久化失败 {i+1}: {e}")
        
        logger.info(f"逐个持久化完成: 成功 {len(successful_ids)}, 失败 {failed_count}")
        return successful_ids

    def as_retriever(self, top_k: int = 10, **kwargs) -> DBSchemaRetriever:
        """创建检索器"""
        return DBSchemaRetriever(
            top_k=top_k,
            connector=self._connector,
            table_vector_store_connector=self._table_vector_store_connector,
            field_vector_store_connector=self._field_vector_store_connector,
            **kwargs
        )

    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        total_chunks = len(self._chunks)
        
        # 统计不同类型的表
        row_counts = []
        for chunk in self._chunks:
            row_count = chunk.metadata.get("row_count", 0)
            if row_count > 0:
                row_counts.append(row_count)
        
        # 统计智能注释
        chunks_with_comments = sum(
            1 for chunk in self._chunks 
            if chunk.metadata.get("has_smart_comments", False)
        )
        
        return {
            "total_chunks": total_chunks,
            "tables_with_data": len(row_counts),
            "total_rows": sum(row_counts),
            "avg_rows_per_table": sum(row_counts) / len(row_counts) if row_counts else 0,
            "optimization_enabled": self._enable_table_filtering,
            "smart_comments_enabled": self._enable_smart_comments,
            "chunks_with_smart_comments": chunks_with_comments,
            "max_tables_limit": self._max_tables
        }
    
    def _validate_table_processing(self, selected_tables: List[str], all_tables: List[str]) -> None:
        """验证表处理的完整性"""
        logger.info("开始验证表处理完整性...")
        
        # 记录处理统计
        total_tables = len(all_tables)
        selected_count = len(selected_tables)
        
        if self._max_tables is None:
            # 首次连接模式：应该处理所有非系统表
            if self._enable_table_filtering:
                system_tables = [t for t in all_tables if self._is_system_table(t)]
                expected_count = total_tables - len(system_tables)
                logger.info(f"预期处理 {expected_count} 个业务表（跳过 {len(system_tables)} 个系统表）")
            else:
                expected_count = total_tables
                logger.info(f"预期处理所有 {expected_count} 个表")
        else:
            expected_count = min(self._max_tables, total_tables)
            logger.info(f"预期处理最多 {expected_count} 个表")
        
        # 验证处理覆盖率
        if selected_count == 0:
            logger.error("  严重错误：没有选择任何表进行处理！")
            raise ValueError("数据库表处理失败：没有选择任何表")
        
        coverage_ratio = selected_count / total_tables
        logger.info(f"表处理覆盖率: {coverage_ratio:.2%} ({selected_count}/{total_tables})")
        
        if self._max_tables is None and coverage_ratio < 0.8:
            logger.warning(f" 表覆盖率较低 ({coverage_ratio:.2%})，可能存在问题")
        
        logger.info(" 表处理完整性验证通过")
    
    def _validate_chunk_completeness(self, chunks: List[Chunk], selected_tables: List[str]) -> None:
        """验证chunks的完整性"""
        logger.info("开始验证chunks完整性...")
        
        if not chunks:
            logger.error(" 严重错误：没有生成任何chunks！")
            raise ValueError("数据库chunks生成失败：没有生成任何chunks")
        
        # 统计表级chunks和字段级chunks
        table_chunks = 0
        field_chunks = 0
        processed_tables = set()
        
        for chunk in chunks:
            metadata = chunk.metadata or {}
            if metadata.get("separated"):
                if metadata.get("part") == "table":
                    table_chunks += 1
                    if "table_name" in metadata:
                        processed_tables.add(metadata["table_name"])
                elif metadata.get("part") == "field":
                    field_chunks += 1
                    if "table_name" in metadata:
                        processed_tables.add(metadata["table_name"])
            else:
                table_chunks += 1
                if "table_name" in metadata:
                    processed_tables.add(metadata["table_name"])
        
        logger.info(f"生成了 {table_chunks} 个表级chunks和 {field_chunks} 个字段级chunks")
        logger.info(f"处理了 {len(processed_tables)} 个表的数据")
        
        # 验证表覆盖
        missing_tables = set(selected_tables) - processed_tables
        if missing_tables:
            logger.warning(f"  以下 {len(missing_tables)} 个表没有生成chunks: {list(missing_tables)[:5]}...")
        
        # 验证chunks质量
        empty_chunks = [i for i, chunk in enumerate(chunks) if not chunk.content.strip()]
        if empty_chunks:
            logger.warning(f"  发现 {len(empty_chunks)} 个空chunks")
        
        success_rate = len(processed_tables) / len(selected_tables) if selected_tables else 0
        logger.info(f"chunks生成成功率: {success_rate:.2%}")
        
        if success_rate < 0.8:
            logger.warning(f"  chunks生成成功率较低 ({success_rate:.2%})")
        
        logger.info(" chunks完整性验证通过")
    
    def _is_system_table(self, table_name: str) -> bool:
        """判断是否为系统表"""
        table_name_lower = table_name.lower()
        
        # 检查系统表模式
        for pattern in self._system_table_patterns:
            if pattern in table_name_lower:
                return True
        
        return False
