"""增强数据库资源工厂 - 简化创建和管理包含智能注释的数据库资源"""

import asyncio
import logging
from typing import Optional, Dict, Any, List

from dbgpt.core import LLMClient, Embeddings
from dbgpt.datasource.base import BaseConnector
from dbgpt.storage.vector_store.base import VectorStoreBase

from .enhanced_database import EnhancedDBResource
from dbgpt_ext.rag.assembler.smart_comment_generator import SmartCommentGenerator

logger = logging.getLogger(__name__)


class EnhancedDBResourceFactory:
    """增强数据库资源工厂
    
    负责创建和管理将智能注释融入表结构并存储到向量数据库的数据库资源，
    确保Agent能够获取包含业务语义的完整表结构信息。
    """
    
    @staticmethod
    def create_enhanced_db_resource(
        name: str,
        connector: BaseConnector,
        llm_client: LLMClient,
        table_vector_store: VectorStoreBase,
        embeddings: Optional[Embeddings] = None,
        use_smart_comments: bool = True,
        auto_generate_on_init: bool = True,
        max_tables: int = 30,
        **kwargs
    ) -> EnhancedDBResource:
        """创建增强数据库资源
        
        Args:
            name: 资源名称
            connector: 数据库连接器
            llm_client: LLM客户端，用于生成智能注释
            table_vector_store: 表结构向量存储
            embeddings: 嵌入模型
            use_smart_comments: 是否使用智能注释
            auto_generate_on_init: 是否在初始化时自动生成智能注释
            max_tables: 最大处理表数
            
        Returns:
            EnhancedDBResource实例
        """
        logger.info(f" 创建增强数据库资源: {name}")
        logger.info(f"   - 智能注释: {'启用' if use_smart_comments else '禁用'}")
        logger.info(f"   - 自动生成: {'是' if auto_generate_on_init else '否'}")
        logger.info(f"   - 最大表数: {max_tables}")
        
        # 创建增强数据库资源
        enhanced_resource = EnhancedDBResource.create_enhanced_db_resource(
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
        
        logger.info(f" 增强数据库资源创建完成: {enhanced_resource}")
        return enhanced_resource
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> EnhancedDBResource:
        """从配置字典创建增强数据库资源
        
        Args:
            config: 配置字典，包含以下键：
                - name: 资源名称
                - connector: 数据库连接器
                - llm_client: LLM客户端
                - table_vector_store: 表结构向量存储
                - embeddings: 嵌入模型（可选）
                - use_smart_comments: 是否使用智能注释（默认True）
                - auto_generate_on_init: 是否自动生成智能注释（默认True）
                - max_tables: 最大处理表数（默认30）
                
        Returns:
            EnhancedDBResource实例
        """
        required_keys = ["name", "connector", "llm_client", "table_vector_store"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"配置中缺少必需的键: {key}")
        
        return EnhancedDBResourceFactory.create_enhanced_db_resource(
            name=config["name"],
            connector=config["connector"],
            llm_client=config["llm_client"],
            table_vector_store=config["table_vector_store"],
            embeddings=config.get("embeddings"),
            use_smart_comments=config.get("use_smart_comments", True),
            auto_generate_on_init=config.get("auto_generate_on_init", True),
            max_tables=config.get("max_tables", 30)
        )
    
    @staticmethod
    async def batch_generate_smart_comments(
        connector: BaseConnector,
        llm_client: LLMClient,
        comment_vector_store: VectorStoreBase,
        embeddings: Embeddings,
        table_names: Optional[List[str]] = None,
        max_concurrent: int = 2
    ) -> Dict[str, Any]:
        """批量生成智能注释（独立于表结构存储）
        
        这个方法用于预先生成智能注释，存储在独立的向量数据库中。
        然后可以通过EnhancedDBResource将这些注释融入表结构。
        
        Args:
            connector: 数据库连接器
            llm_client: LLM客户端
            comment_vector_store: 智能注释向量存储
            embeddings: 嵌入模型
            table_names: 要处理的表名列表，为None时处理所有表
            max_concurrent: 最大并发数
            
        Returns:
            生成结果统计
        """
        logger.info(" 开始批量生成智能注释...")
        
        # 创建智能注释生成器
        generator = SmartCommentGenerator(
            llm_client=llm_client,
            vector_store=comment_vector_store,
            embeddings=embeddings
        )
        
        # 获取要处理的表名
        if table_names is None:
            table_names = list(connector.get_table_names())
        
        logger.info(f" 将为 {len(table_names)} 个表生成智能注释")
        
        # 批量生成并保存智能注释
        results = await generator.batch_generate_and_save_comments(
            connector=connector,
            table_names=table_names,
            max_concurrent=max_concurrent
        )
        
        # 统计结果
        success_count = sum(1 for _, (_, chunk_ids) in results.items() if chunk_ids)
        total_chunks = sum(len(chunk_ids) for _, (_, chunk_ids) in results.items())
        
        stats = {
            "processed_tables": len(table_names),
            "successful_tables": success_count,
            "total_comment_chunks": total_chunks,
            "table_details": {}
        }
        
        # 收集详细统计
        for table_name, (comments, chunk_ids) in results.items():
            field_comments = comments.get("field_comments", {})
            stats["table_details"][table_name] = {
                "table_comment": comments.get("table_comment", ""),
                "field_count": len(field_comments),
                "chunk_count": len(chunk_ids)
            }
        
        logger.info(f" 智能注释批量生成完成: {success_count}/{len(table_names)} 表成功")
        logger.info(f" 总计生成 {total_chunks} 个智能注释chunks")
        
        return stats
    
    @staticmethod
    def upgrade_existing_db_resource(
        existing_resource,
        llm_client: LLMClient,
        table_vector_store: VectorStoreBase,
        embeddings: Optional[Embeddings] = None,
        use_smart_comments: bool = True,
        auto_generate_on_init: bool = True,
        max_tables: int = 30
    ) -> EnhancedDBResource:
        """将现有的数据库资源升级为增强数据库资源
        
        Args:
            existing_resource: 现有的数据库资源
            llm_client: LLM客户端
            table_vector_store: 表结构向量存储
            embeddings: 嵌入模型
            use_smart_comments: 是否使用智能注释
            auto_generate_on_init: 是否自动生成智能注释
            max_tables: 最大处理表数
            
        Returns:
            EnhancedDBResource实例
        """
        if not hasattr(existing_resource, 'connector'):
            raise ValueError("现有资源必须具有connector属性")
        
        logger.info(f"⬆ 升级现有数据库资源: {existing_resource.name}")
        
        enhanced_resource = EnhancedDBResource.create_enhanced_db_resource(
            name=existing_resource.name,
            connector=existing_resource.connector,
            llm_client=llm_client,
            table_vector_store=table_vector_store,
            embeddings=embeddings,
            use_smart_comments=use_smart_comments,
            auto_generate_on_init=auto_generate_on_init,
            max_tables=max_tables,
            db_type=getattr(existing_resource, '_db_type', None),
            db_name=getattr(existing_resource, '_db_name', None),
            dialect=getattr(existing_resource, '_dialect', None)
        )
        
        logger.info(f" 数据库资源升级完成: {enhanced_resource}")
        return enhanced_resource
    
    @staticmethod
    def check_enhanced_db_availability(
        connector: BaseConnector,
        llm_client: Optional[LLMClient],
        table_vector_store: Optional[VectorStoreBase],
        embeddings: Optional[Embeddings]
    ) -> Dict[str, Any]:
        """检查增强数据库资源的可用性
        
        Args:
            connector: 数据库连接器
            llm_client: LLM客户端
            table_vector_store: 表结构向量存储
            embeddings: 嵌入模型
            
        Returns:
            包含可用性信息的字典
        """
        availability = {
            "enhanced_db_available": True,
            "issues": []
        }
        
        try:
            # 检查数据库连接
            table_names = list(connector.get_table_names())
            availability["database_accessible"] = True
            availability["total_tables"] = len(table_names)
        except Exception as e:
            availability["enhanced_db_available"] = False
            availability["database_accessible"] = False
            availability["issues"].append(f"数据库连接失败: {e}")
        
        # 检查LLM客户端
        if llm_client is None:
            availability["enhanced_db_available"] = False
            availability["llm_client_available"] = False
            availability["issues"].append("LLM客户端未提供")
        else:
            availability["llm_client_available"] = True
        
        # 检查向量存储
        if table_vector_store is None:
            availability["enhanced_db_available"] = False
            availability["vector_store_available"] = False
            availability["issues"].append("表结构向量存储未提供")
        else:
            try:
                # 尝试查询向量存储
                test_chunks = table_vector_store.similar_search("test", top_k=1, score_threshold=0.0)
                availability["vector_store_available"] = True
                availability["existing_chunks"] = len(test_chunks)
            except Exception as e:
                availability["enhanced_db_available"] = False
                availability["vector_store_available"] = False
                availability["issues"].append(f"向量存储不可访问: {e}")
        
        # 检查嵌入模型
        if embeddings is None:
            availability["embeddings_available"] = False
            availability["issues"].append("嵌入模型未提供")
        else:
            availability["embeddings_available"] = True
        
        return availability
    
    @staticmethod
    def create_demo_workflow(
        connector: BaseConnector,
        llm_client: LLMClient,
        table_vector_store: VectorStoreBase,
        embeddings: Embeddings,
        max_tables: int = 5
    ) -> Dict[str, Any]:
        """创建演示工作流，展示完整的增强数据库资源使用过程
        
        Args:
            connector: 数据库连接器
            llm_client: LLM客户端
            table_vector_store: 表结构向量存储
            embeddings: 嵌入模型
            max_tables: 最大处理表数（演示用，建议较小）
            
        Returns:
            演示结果
        """
        logger.info(" 开始增强数据库资源演示工作流")
        
        # 步骤1: 检查可用性
        logger.info("步骤1: 检查系统可用性")
        availability = EnhancedDBResourceFactory.check_enhanced_db_availability(
            connector, llm_client, table_vector_store, embeddings
        )
        
        if not availability["enhanced_db_available"]:
            return {
                "success": False,
                "step": "availability_check",
                "availability": availability
            }
        
        # 步骤2: 创建增强数据库资源
        logger.info("步骤2: 创建增强数据库资源")
        enhanced_resource = EnhancedDBResourceFactory.create_enhanced_db_resource(
            name="demo_enhanced_db",
            connector=connector,
            llm_client=llm_client,
            table_vector_store=table_vector_store,
            embeddings=embeddings,
            use_smart_comments=True,
            auto_generate_on_init=True,
            max_tables=max_tables
        )
        
        # 步骤3: 获取统计信息
        logger.info("步骤3: 获取智能表结构统计")
        stats = enhanced_resource.get_smart_schema_stats()
        
        # 步骤4: 测试schema检索
        logger.info("步骤4: 测试schema检索")
        test_questions = ["用户相关的表", "订单数据", "产品信息"]
        schema_results = {}
        
        for question in test_questions:
            try:
                schema_info = enhanced_resource.get_schema_link("demo", question)
                schema_results[question] = {
                    "success": True,
                    "schema_count": len(schema_info) if isinstance(schema_info, list) else 1,
                    "has_smart_comments": any("[" in schema for schema in (schema_info if isinstance(schema_info, list) else [schema_info]))
                }
            except Exception as e:
                schema_results[question] = {
                    "success": False,
                    "error": str(e)
                }
        
        result = {
            "success": True,
            "availability": availability,
            "enhanced_resource": str(enhanced_resource),
            "stats": stats,
            "schema_test_results": schema_results
        }
        
        logger.info(" 增强数据库资源演示工作流完成")
        return result
