"""增强的数据库资源 - 集成智能注释系统"""

import logging
from typing import Optional, Union, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from dbgpt.core import Embeddings
from dbgpt.storage.vector_store.base import VectorStoreBase
from dbgpt.util.executor_utils import blocking_func_to_async

from .database import RDBMSConnectorResource, DBParameters
from dbgpt_ext.rag.summary.rdbms_db_summary import _parse_db_summary

logger = logging.getLogger(__name__)


class SmartDBResource(RDBMSConnectorResource):
    """集成智能注释的数据库资源
    
    在原有数据库资源基础上，增加智能注释检索功能，
    使Agent能够获取包含智能注释的增强schema信息。
    """
    
    def __init__(
        self,
        name: str,
        connector=None,
        comment_vector_store: Optional[VectorStoreBase] = None,
        embeddings: Optional[Embeddings] = None,
        use_smart_comments: bool = True,
        fallback_to_original: bool = True,
        **kwargs
    ):
        """初始化智能数据库资源
        
        Args:
            name: 资源名称
            connector: 数据库连接器
            comment_vector_store: 智能注释向量存储
            embeddings: 嵌入模型
            use_smart_comments: 是否使用智能注释
            fallback_to_original: 当智能注释不可用时是否回退到原始schema
        """
        super().__init__(name=name, connector=connector, **kwargs)
        
        self._comment_vector_store = comment_vector_store
        self._embeddings = embeddings
        self._use_smart_comments = use_smart_comments
        self._fallback_to_original = fallback_to_original
        
        logger.info(f"SmartDBResource initialized: use_smart_comments={use_smart_comments}")

    def get_schema_link(
        self, db: str, question: Optional[str] = None
    ) -> Union[str, List[str]]:
        """返回增强的数据库schema信息，包含智能注释"""
        
        # 如果不使用智能注释，直接返回原始schema
        if not self._use_smart_comments or not self._comment_vector_store:
            logger.debug("使用原始schema信息（智能注释未启用或向量存储不可用）")
            return _parse_db_summary(self.connector)
        
        try:
            logger.info("开始获取增强的schema信息（包含智能注释）")
            
            # 获取原始schema
            original_schema = _parse_db_summary(self.connector)
            
            # 如果没有用户问题，返回所有表的增强信息
            if not question:
                enhanced_schema = self._enhance_all_tables_schema(original_schema)
            else:
                # 基于问题检索相关的智能注释
                enhanced_schema = self._enhance_schema_with_smart_comments(
                    original_schema, question
                )
            
            logger.info(f"成功获取增强schema信息，包含 {len(enhanced_schema)} 个表")
            return enhanced_schema
            
        except Exception as e:
            logger.warning(f"获取智能注释失败: {e}")
            
            if self._fallback_to_original:
                logger.info("回退到原始schema信息")
                return _parse_db_summary(self.connector)
            else:
                raise

    def _enhance_all_tables_schema(self, original_schema: List[str]) -> List[str]:
        """为所有表增强schema信息"""
        enhanced_schema = []
        
        for table_schema in original_schema:
            try:
                # 从schema中提取表名
                table_name = self._extract_table_name_from_schema(table_schema)
                if table_name:
                    enhanced_table_schema = self._enhance_single_table_schema(
                        table_schema, table_name
                    )
                    enhanced_schema.append(enhanced_table_schema)
                else:
                    enhanced_schema.append(table_schema)
            except Exception as e:
                logger.warning(f"增强表schema失败: {e}")
                enhanced_schema.append(table_schema)
        
        return enhanced_schema

    def _enhance_schema_with_smart_comments(
        self, original_schema: List[str], question: str
    ) -> List[str]:
        """基于用户问题检索相关智能注释并增强schema"""
        try:
            # 使用问题查询相关的智能注释
            from dbgpt.storage.vector_store.filters import MetadataFilters, MetadataFilter
            
            # 检索相关的注释chunks
            comment_chunks = self._comment_vector_store.similar_search_with_scores(
                question, top_k=10, score_threshold=0.0
            )
            
            # 按表名组织注释
            table_comments = {}
            for chunk in comment_chunks:
                metadata = chunk.metadata or {}
                table_name = metadata.get("table_name")
                if table_name:
                    if table_name not in table_comments:
                        table_comments[table_name] = {
                            "table_comment": "",
                            "field_comments": {}
                        }
                    
                    comment_type = metadata.get("type")
                    if comment_type == "table_comment":
                        # 从content中提取表注释
                        content = chunk.content or ""
                        if "表注释:" in content:
                            table_comment = content.split("表注释:")[1].split("\n")[0].strip()
                            table_comments[table_name]["table_comment"] = table_comment
                    elif comment_type == "field_comment":
                        # 从content中提取字段注释
                        field_name = metadata.get("field_name")
                        content = chunk.content or ""
                        if field_name and "字段注释:" in content:
                            field_comment = content.split("字段注释:")[1].split("\n")[0].strip()
                            table_comments[table_name]["field_comments"][field_name] = field_comment
            
            logger.info(f"从智能注释中获取到 {len(table_comments)} 个表的注释信息")
            
            # 增强原始schema
            enhanced_schema = []
            for table_schema in original_schema:
                table_name = self._extract_table_name_from_schema(table_schema)
                if table_name and table_name in table_comments:
                    enhanced_table_schema = self._apply_comments_to_schema(
                        table_schema, table_name, table_comments[table_name]
                    )
                    enhanced_schema.append(enhanced_table_schema)
                else:
                    enhanced_schema.append(table_schema)
            
            return enhanced_schema
            
        except Exception as e:
            logger.error(f"基于问题增强schema失败: {e}")
            return original_schema

    def _enhance_single_table_schema(self, table_schema: str, table_name: str) -> str:
        """为单个表增强schema信息"""
        try:
            # 查询该表的所有智能注释
            from dbgpt.storage.vector_store.filters import MetadataFilters, MetadataFilter
            
            filters = MetadataFilters(filters=[
                MetadataFilter(key="table_name", value=table_name)
            ])
            
            comment_chunks = self._comment_vector_store.similar_search(
                f"表名 {table_name}", top_k=20, filters=filters
            )
            
            # 组织注释信息
            comments = {"table_comment": "", "field_comments": {}}
            for chunk in comment_chunks:
                metadata = chunk.metadata or {}
                comment_type = metadata.get("type")
                
                if comment_type == "table_comment":
                    content = chunk.content or ""
                    if "表注释:" in content:
                        table_comment = content.split("表注释:")[1].split("\n")[0].strip()
                        comments["table_comment"] = table_comment
                elif comment_type == "field_comment":
                    field_name = metadata.get("field_name")
                    content = chunk.content or ""
                    if field_name and "字段注释:" in content:
                        field_comment = content.split("字段注释:")[1].split("\n")[0].strip()
                        comments["field_comments"][field_name] = field_comment
            
            # 应用注释到schema
            return self._apply_comments_to_schema(table_schema, table_name, comments)
            
        except Exception as e:
            logger.warning(f"为表 {table_name} 增强schema失败: {e}")
            return table_schema

    def _extract_table_name_from_schema(self, table_schema: str) -> Optional[str]:
        """从schema字符串中提取表名"""
        try:
            # 解析格式：table_name(column1, column2, ...)
            if "(" in table_schema:
                table_name = table_schema.split("(")[0].strip()
                return table_name
            return None
        except Exception:
            return None

    def _apply_comments_to_schema(
        self, table_schema: str, table_name: str, comments: Dict[str, Any]
    ) -> str:
        """将智能注释应用到表schema中"""
        try:
            table_comment = comments.get("table_comment", "")
            field_comments = comments.get("field_comments", {})
            
            # 如果没有任何注释，返回原始schema
            if not table_comment and not field_comments:
                return table_schema
            
            enhanced_schema = table_schema
            
            # 添加表注释
            if table_comment and table_comment != f"{table_name}数据表":
                # 在表名后添加表注释
                if "(" in enhanced_schema:
                    parts = enhanced_schema.split("(", 1)
                    enhanced_schema = f"{parts[0]}[{table_comment}]({parts[1]}"
            
            # 添加字段注释
            if field_comments:
                for field_name, field_comment in field_comments.items():
                    if field_comment and field_comment != f"{field_name}字段":
                        # 在字段名后添加注释
                        enhanced_schema = enhanced_schema.replace(
                            f"{field_name}",
                            f"{field_name}[{field_comment}]"
                        )
            
            logger.debug(f"表 {table_name} schema增强完成")
            return enhanced_schema
            
        except Exception as e:
            logger.warning(f"应用注释到schema失败: {e}")
            return table_schema

    @classmethod
    def create_with_smart_comments(
        cls,
        name: str,
        connector,
        comment_vector_store: VectorStoreBase,
        embeddings: Optional[Embeddings] = None,
        use_smart_comments: bool = True,
        **kwargs
    ) -> "SmartDBResource":
        """创建带智能注释的数据库资源
        
        Args:
            name: 资源名称
            connector: 数据库连接器
            comment_vector_store: 智能注释向量存储
            embeddings: 嵌入模型
            use_smart_comments: 是否使用智能注释
            
        Returns:
            SmartDBResource实例
        """
        return cls(
            name=name,
            connector=connector,
            comment_vector_store=comment_vector_store,
            embeddings=embeddings,
            use_smart_comments=use_smart_comments,
            **kwargs
        )

    def get_smart_comment_stats(self) -> Dict[str, Any]:
        """获取智能注释统计信息"""
        try:
            if not self._comment_vector_store:
                return {"smart_comments_available": False}
            
            # 查询所有智能注释
            all_comments = self._comment_vector_store.similar_search(
                "智能注释", top_k=1000, score_threshold=0.0
            )
            
            table_comments = 0
            field_comments = 0
            tables_with_comments = set()
            
            for chunk in all_comments:
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
