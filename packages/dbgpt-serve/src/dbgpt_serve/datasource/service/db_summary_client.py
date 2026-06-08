"""DBSummaryClient class."""

import logging
import traceback
from typing import Tuple

from dbgpt.component import SystemApp
from dbgpt.core import Embeddings
from dbgpt.rag.embedding.embedding_factory import EmbeddingFactory
from dbgpt.rag.text_splitter.text_splitter import RDBTextSplitter
from dbgpt.storage.vector_store.base import VectorStoreBase
from dbgpt_ext.rag import ChunkParameters
from dbgpt_ext.rag.summary.gdbms_db_summary import GdbmsSummary
from dbgpt_ext.rag.summary.rdbms_db_summary import RdbmsSummary
from dbgpt_serve.datasource.manages import ConnectorManager
from dbgpt_serve.rag.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class DBSummaryClient:
    """The client for DBSummary.

    DB Summary client, provide db_summary_embedding(put db profile and table profile
    summary into vector store), get_similar_tables method(get user query related tables
    info)

    Args:
        system_app (SystemApp): Main System Application class that manages the
            lifecycle and registration of components..
    """

    def __init__(self, system_app: SystemApp):
        """Create a new DBSummaryClient."""
        self.system_app = system_app

        self.app_config = self.system_app.config.configs.get("app_config")
        self.storage_config = self.app_config.rag.storage

    @property
    def embeddings(self) -> Embeddings:
        """Get the embeddings."""
        embedding_factory: EmbeddingFactory = self.system_app.get_component(
            "embedding_factory", component_type=EmbeddingFactory
        )
        return embedding_factory.create()

    def db_summary_embedding(self, dbname, db_type):
        """Put db profile and table profile summary into vector store."""
        try:
            db_summary_client = self.create_summary_client(dbname, db_type)

            self.init_db_profile(db_summary_client, dbname)

            logger.info("db summary embedding success")
        except Exception as e:
            message = traceback.format_exc()
            logger.warning(
                f"{dbname}, {db_type} summary error!{str(e)}, detail: {message}"
            )
            raise

    def get_db_summary(self, dbname, query, topk):
        """Get user query related tables info."""
        logger.info(f" DBSummaryClient.get_db_summary 被调用: dbname={dbname}, query={query}, topk={topk}")
        
        from dbgpt_ext.rag.retriever.db_schema import DBSchemaRetriever

        try:
            table_vector_connector, field_vector_connector = (
                self._get_vector_connector_by_db(dbname)
            )
            
            logger.info(f" 获取向量连接器成功: table_vector_connector={table_vector_connector is not None}, field_vector_connector={field_vector_connector is not None}")
            
            # 添加智能注释向量存储连接器
            # 智能注释存储在table_vector_connector中，所以将其作为comment_vector_store_connector
            logger.info(" 创建DBSchemaRetriever，启用智能注释支持")
            retriever = DBSchemaRetriever(
                top_k=topk,
                table_vector_store_connector=table_vector_connector,
                field_vector_store_connector=field_vector_connector,
                comment_vector_store_connector=table_vector_connector,  # 🆕 添加智能注释支持
                separator="--table-field-separator--",
                use_smart_comments=True,  #  启用智能注释
            )

            logger.info(f" 开始检索，查询: {query}")
            table_docs = retriever.retrieve(query)
            logger.info(f" 检索到 {len(table_docs)} 个文档")
            
            #  转换智能注释格式为Agent期望的简洁格式
            ans = []
            for i, doc in enumerate(table_docs):
                logger.info(f" 文档 {i+1} 原始内容: {doc.content[:300]}...")
                converted_format = self._convert_smart_comment_to_agent_format(doc.content)
                logger.info(f" 文档 {i+1} 转换后: {converted_format[:300]}...")
                ans.append(converted_format)
            
            logger.info(f" DBSummaryClient 成功返回 {len(ans)} 个表结构")
            return ans
            
        except Exception as e:
            logger.error(f" DBSummaryClient.get_db_summary 失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise

    def _convert_smart_comment_to_agent_format(self, smart_content: str) -> str:
        """
        将智能注释格式转换为Agent期望的简洁格式
        
        输入格式: 
        表名: material_condition
        表说明: 物料状态管理表，用于记录物料的收发存状态信息
        数据量: 11 行, 2 列
        字段: cRdCode(longtext)[收发类别编码], cRdName(longtext)[收发类别名称]
        
        输出格式:
        material_condition(cRdCode[收发类别编码],cRdName[收发类别名称])
        """
        try:
            import re
            
            # 检查是否是智能注释格式
            if not ("表名:" in smart_content and "字段:" in smart_content):
                # 不是智能注释格式，直接返回
                return smart_content
            
            # 提取表名
            lines = smart_content.split('\n')
            table_name = None
            fields_line = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('表名:'):
                    table_name = line.split(':', 1)[1].strip()
                elif line.startswith('字段:'):
                    fields_line = line.split(':', 1)[1].strip()
            
            if not table_name:
                logger.warning("无法提取表名，返回原内容")
                return smart_content
            
            if not fields_line:
                return f"{table_name}()"
            
            # 解析字段：处理两种格式
            # 格式1: field_name(type)[comment] - 有智能注释
            # 格式2: field_name(type) - 没有智能注释
            
            logger.info(f" 解析字段行: {fields_line}")
            
            # 先尝试匹配有智能注释的格式
            field_pattern_with_comment = r'(\w+)\([^)]+\)\[([^\]]+)\]'
            field_matches_with_comment = re.findall(field_pattern_with_comment, fields_line)
            
            # 再尝试匹配没有智能注释的格式
            field_pattern_no_comment = r'(\w+)\([^)]+\)'
            field_matches_no_comment = re.findall(field_pattern_no_comment, fields_line)
            
            formatted_fields = []
            
            # 优先使用有智能注释的匹配
            if field_matches_with_comment:
                logger.info(f" 发现 {len(field_matches_with_comment)} 个带智能注释的字段")
                for field_name, comment in field_matches_with_comment:
                    formatted_fields.append(f"{field_name}[{comment}]")
            elif field_matches_no_comment:
                logger.info(f"发现 {len(field_matches_no_comment)} 个字段，但没有智能注释")
                #  修复：从完整匹配中提取字段名
                formatted_fields = []
                for field_match in field_matches_no_comment:
                    # field_match 是类似 'cRdCode(longtext)' 的字符串
                    # 提取括号前的字段名
                    field_name = field_match.split('(')[0]
                    formatted_fields.append(field_name)
            else:
                # 回退方案：简单提取字段名
                logger.warning("字段解析失败，使用回退方案")
                # 按逗号分割，然后提取字段名
                field_parts = fields_line.split(',')
                for part in field_parts[:20]:  # 限制数量
                    part = part.strip()
                    # 提取字段名（括号前的部分）
                    match = re.match(r'^(\w+)', part)
                    if match:
                        formatted_fields.append(match.group(1))
            
            # 构建最终格式
            if formatted_fields:
                fields_part = ",".join(formatted_fields)
                result = f"{table_name}({fields_part})"
            else:
                result = f"{table_name}(...)"
            
            logger.info(f" 转换智能注释: {table_name} -> {len(formatted_fields)}个字段")
            return result
            
        except Exception as e:
            logger.warning(f"转换智能注释格式失败: {e}")
            # 回退方案
            if "表名:" in smart_content:
                try:
                    lines = smart_content.split('\n')
                    for line in lines:
                        if line.strip().startswith('表名:'):
                            table_name = line.split(':', 1)[1].strip()
                            return f"{table_name}(...)"
                except:
                    pass
            
            return smart_content

    def init_db_summary(self):
        """Initialize db summary profile."""
        local_db_manager = ConnectorManager.get_instance(self.system_app)
        db_mange = local_db_manager
        dbs = db_mange.get_db_list()
        for item in dbs:
            try:
                self.db_summary_embedding(item["db_name"], item["db_type"])
            except Exception as e:
                message = traceback.format_exc()
                logger.warning(
                    f"{item['db_name']}, {item['db_type']} summary error!{str(e)}, "
                    f"detail: {message}"
                )

    def init_db_profile(self, db_summary_client, dbname, user_query: str = ""):
        """Initialize db summary profile.

        Args:
        db_summary_client(DBSummaryClient): DB Summary Client
        dbname(str): dbname
        user_query(str): user query for table filtering optimization
        """
        vector_store_name = dbname + "_profile"

        table_vector_connector, field_vector_connector = (
            self._get_vector_connector_by_db(dbname)
        )
        
        # 检查是否启用优化模式
        # 暂时默认启用优化，未来可以通过配置控制
        enable_optimization = True
        logger.info(f"RAG优化模式: {'启用' if enable_optimization else '禁用'}")
        
        if not table_vector_connector.vector_name_exists():
            if enable_optimization:
                # 检查是否启用智能注释
                enable_smart_comments = True  # 默认启用智能注释
                
                if enable_smart_comments:
                    # 使用带智能注释的装配器
                    from dbgpt_ext.rag.assembler.smart_db_schema_assembler import SmartDBSchemaAssembler
                    from dbgpt_ext.rag.summary.rdbms_db_summary import _DEFAULT_COLUMN_SEPARATOR
                    
                    # 获取LLM客户端
                    try:
                        from dbgpt.model.cluster.client import DefaultLLMClient
                        from dbgpt.component import ComponentType
                        from dbgpt.model.cluster.worker.manager import WorkerManagerFactory
                        
                        worker_manager = self.system_app.get_component(
                            ComponentType.WORKER_MANAGER_FACTORY, WorkerManagerFactory
                        ).create()
                        llm_client = DefaultLLMClient(worker_manager, auto_convert_message=True)
                        
                        logger.info("成功获取LLM客户端，将使用智能注释功能")
                        
                        chunk_parameters = ChunkParameters(
                            text_splitter=RDBTextSplitter(
                                column_separator=_DEFAULT_COLUMN_SEPARATOR,
                                separator="--table-field-separator--",
                            )
                        )
                        
                        # 首次连接必须处理所有表 - 移除表数量限制
                        max_tables = None  # 不限制表数量，确保处理所有表
                        empty_table_threshold = 0  # 默认空表阈值
                        
                        logger.info("使用智能注释的数据库装配器，将处理数据库中的所有表")
                        
                        db_assembler = SmartDBSchemaAssembler.create_with_llm(
                            connector=db_summary_client.db,
                            table_vector_store_connector=table_vector_connector,
                            llm_client=llm_client,
                            field_vector_store_connector=field_vector_connector,
                            chunk_parameters=chunk_parameters,
                            max_seq_length=self.app_config.service.web.embedding_model_max_seq_len,
                            max_tables=max_tables,
                            empty_table_threshold=empty_table_threshold,
                            enable_table_filtering=True,
                            enable_smart_comments=True,
                            user_query=user_query,
                            max_concurrent_llm_calls=2,  # 限制并发调用
                        )
                        
                        # 记录智能注释统计
                        stats = db_assembler.get_smart_comment_stats()
                        logger.info(f"智能注释装配器统计: {stats}")
                        
                    except Exception as llm_error:
                        logger.warning(f"无法获取LLM客户端，回退到优化装配器: {llm_error}")
                        enable_smart_comments = False
                
                if not enable_smart_comments:
                    # 使用优化的装配器（无智能注释）
                    from dbgpt_ext.rag.assembler.optimized_db_schema import OptimizedDBSchemaAssembler
                    
                    chunk_parameters = ChunkParameters(
                        text_splitter=RDBTextSplitter(
                            column_separator=_DEFAULT_COLUMN_SEPARATOR,
                            separator="--table-field-separator--",
                        )
                    )
                    
                    # 首次连接必须处理所有表 - 移除表数量限制
                    max_tables = None  # 不限制表数量，确保处理所有表
                    empty_table_threshold = 0  # 默认空表阈值
                    
                    logger.info("使用优化的数据库装配器，将处理数据库中的所有表")
                    
                    db_assembler = OptimizedDBSchemaAssembler.load_from_connection(
                        connector=db_summary_client.db,
                        table_vector_store_connector=table_vector_connector,
                        field_vector_store_connector=field_vector_connector,
                        chunk_parameters=chunk_parameters,
                        max_seq_length=self.app_config.service.web.embedding_model_max_seq_len,
                        max_tables=max_tables,
                        empty_table_threshold=empty_table_threshold,
                        enable_table_filtering=True,
                        enable_smart_comments=False,
                        user_query=user_query,
                    )
                    
                    # 记录优化统计
                    stats = db_assembler.get_optimization_stats()
                    logger.info(f"数据库装配优化统计: {stats}")
                
            else:
                # 使用原始装配器
                from dbgpt_ext.rag.assembler.db_schema import DBSchemaAssembler
                from dbgpt_ext.rag.summary.rdbms_db_summary import _DEFAULT_COLUMN_SEPARATOR

                chunk_parameters = ChunkParameters(
                    text_splitter=RDBTextSplitter(
                        column_separator=_DEFAULT_COLUMN_SEPARATOR,
                        separator="--table-field-separator--",
                    )
                )
                
                logger.info("使用原始的数据库装配器")
                
                db_assembler = DBSchemaAssembler.load_from_connection(
                    connector=db_summary_client.db,
                    table_vector_store_connector=table_vector_connector,
                    field_vector_store_connector=field_vector_connector,
                    chunk_parameters=chunk_parameters,
                    max_seq_length=self.app_config.service.web.embedding_model_max_seq_len,
                )

            # 详细记录处理结果
            chunks = db_assembler.get_chunks()
            if len(chunks) > 0:
                logger.info(f"开始持久化 {len(chunks)} 个chunks到向量数据库...")
                
                # 记录处理统计
                stats = db_assembler.get_optimization_stats() if hasattr(db_assembler, 'get_optimization_stats') else {}
                for key, value in stats.items():
                    logger.info(f"  {key}: {value}")
                
                # 持久化chunks
                try:
                    chunk_ids = db_assembler.persist()
                    if chunk_ids:
                        logger.info(f"成功持久化 {len(chunk_ids)} 个chunks到向量数据库")
                        logger.info(f"数据库 {dbname} 的表结构和字段信息已完整保存")
                    else:
                        logger.warning(" 没有chunks被持久化，可能是embedding模型问题")
                        logger.info("系统将继续运行，但向量检索功能可能受影响")
                except Exception as persist_error:
                    logger.error(f"持久化chunks失败: {persist_error}")
                    logger.info("建议检查embedding模型配置和向量数据库连接")
                    # 不再抛出异常，允许系统继续运行
                    pass
            else:
                logger.error(" 严重错误：没有chunks需要持久化！数据库处理可能失败")
                raise ValueError(f"数据库 {dbname} 处理失败：没有生成任何chunks")
        else:
            logger.info(f"Vector store name {vector_store_name} exist")
        logger.info("initialize db summary profile success...")

    def delete_db_profile(self, dbname):
        """Delete db profile."""
        table_vector_store_name = dbname + "_profile"
        field_vector_store_name = dbname + "_profile_field"

        table_vector_connector, field_vector_connector = (
            self._get_vector_connector_by_db(dbname)
        )

        table_vector_connector.delete_vector_name(table_vector_store_name)
        field_vector_connector.delete_vector_name(field_vector_store_name)
        logger.info(f"delete db profile {dbname} success")

    @staticmethod
    def create_summary_client(dbname: str, db_type: str):
        """
        Create a summary client based on the database type.

        Args:
            dbname (str): The name of the database.
            db_type (str): The type of the database.
        """
        if "graph" in db_type:
            return GdbmsSummary(dbname, db_type)
        else:
            return RdbmsSummary(dbname, db_type)

    def _get_vector_connector_by_db(
        self, dbname
    ) -> Tuple[VectorStoreBase, VectorStoreBase]:
        vector_store_name = dbname + "_profile"
        storage_manager = StorageManager.get_instance(self.system_app)
        table_vector_store = storage_manager.create_vector_store(
            index_name=vector_store_name
        )
        field_vector_store_name = dbname + "_profile_field"
        field_vector_store = storage_manager.create_vector_store(
            index_name=field_vector_store_name
        )
        return table_vector_store, field_vector_store
