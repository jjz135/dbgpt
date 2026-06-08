"""智能注释知识源 - 用于包装数据库表和字段的智能注释"""

from typing import Any, Dict, List, Optional, Union

from dbgpt.core import Document
from dbgpt.rag.knowledge.base import (
    ChunkStrategy,
    DocumentType,
    Knowledge,
    KnowledgeType,
)


class SmartCommentKnowledge(Knowledge):
    """智能注释知识源
    
    用于包装数据库表和字段的智能注释，将其转换为可以存储在向量数据库中的文档。
    这些注释由SmartCommentGenerator生成，包含表的业务含义和字段的语义信息。
    """

    def __init__(
        self,
        table_comments: Dict[str, Dict[str, Any]],
        knowledge_type: Optional[KnowledgeType] = KnowledgeType.DOCUMENT,
        metadata: Optional[Dict[str, Union[str, List[str]]]] = None,
        **kwargs: Any,
    ) -> None:
        """创建智能注释知识源
        
        Args:
            table_comments: 表注释数据，格式为 {table_name: {"table_comment": str, "field_comments": dict}}
            knowledge_type: 知识类型
            metadata: 元数据
        """
        self._table_comments = table_comments
        super().__init__(knowledge_type=knowledge_type, metadata=metadata, **kwargs)

    def _load(self) -> List[Document]:
        """从注释数据加载文档"""
        docs = []
        
        for table_name, comments in self._table_comments.items():
            table_comment = comments.get("table_comment", f"{table_name}数据表")
            field_comments = comments.get("field_comments", {})
            
            # 创建表注释文档
            table_content = f"表名: {table_name}\n表注释: {table_comment}"
            if field_comments:
                field_names = list(field_comments.keys())
                table_content += f"\n包含字段: {', '.join(field_names)}"
            
            table_metadata = {
                "source": "smart_comment",
                "table_name": table_name,
                "type": "table_comment",
                "comment_type": "ai_generated"
            }
            if self._metadata:
                table_metadata.update(self._metadata)
            
            docs.append(Document(content=table_content, metadata=table_metadata))
            
            # 为每个字段创建单独的文档
            for field_name, field_comment in field_comments.items():
                field_content = f"表名: {table_name}\n字段名: {field_name}\n字段注释: {field_comment}"
                
                field_metadata = {
                    "source": "smart_comment",
                    "table_name": table_name,
                    "field_name": field_name,
                    "type": "field_comment",
                    "comment_type": "ai_generated"
                }
                if self._metadata:
                    field_metadata.update(self._metadata)
                
                docs.append(Document(content=field_content, metadata=field_metadata))
        
        return docs

    @classmethod
    def support_chunk_strategy(cls) -> List[ChunkStrategy]:
        """返回支持的分块策略"""
        return [
            ChunkStrategy.CHUNK_BY_SIZE,
            ChunkStrategy.CHUNK_BY_SEPARATOR,
        ]

    @classmethod
    def type(cls) -> KnowledgeType:
        """返回知识类型"""
        return KnowledgeType.DOCUMENT

    @classmethod
    def document_type(cls) -> DocumentType:
        """返回文档类型"""
        return DocumentType.DATASOURCE

    @classmethod
    def default_chunk_strategy(cls) -> ChunkStrategy:
        """返回默认分块策略"""
        return ChunkStrategy.CHUNK_BY_SIZE

    def add_table_comments(self, table_name: str, comments: Dict[str, Any]) -> None:
        """添加表注释
        
        Args:
            table_name: 表名
            comments: 注释数据，包含table_comment和field_comments
        """
        self._table_comments[table_name] = comments

    def get_table_comments(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取指定表的注释
        
        Args:
            table_name: 表名
            
        Returns:
            表的注释数据，如果不存在则返回None
        """
        return self._table_comments.get(table_name)

    def get_all_tables(self) -> List[str]:
        """获取所有包含注释的表名"""
        return list(self._table_comments.keys())

    def remove_table_comments(self, table_name: str) -> bool:
        """删除指定表的注释
        
        Args:
            table_name: 表名
            
        Returns:
            是否成功删除
        """
        if table_name in self._table_comments:
            del self._table_comments[table_name]
            return True
        return False
