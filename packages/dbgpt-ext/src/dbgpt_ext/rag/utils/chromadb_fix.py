"""ChromaDB连接问题诊断和修复工具"""

import logging
import os
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ChromaDBFixer:
    """ChromaDB问题诊断和修复工具"""
    
    def __init__(self, chroma_store):
        """初始化修复工具
        
        Args:
            chroma_store: ChromaStore实例
        """
        self.chroma_store = chroma_store
        self.chroma_client = getattr(chroma_store, '_chroma_client', None)
        self.collection = getattr(chroma_store, '_collection', None)
        self.collection_name = getattr(chroma_store, '_collection_name', 'unknown')
        self.persist_dir = getattr(chroma_store, 'persist_dir', None)
    
    def diagnose(self) -> Dict[str, Any]:
        """诊断ChromaDB连接问题"""
        logger.info("🔍 开始诊断ChromaDB连接问题")
        
        diagnosis = {
            "timestamp": time.time(),
            "chroma_client_available": False,
            "collection_available": False,
            "persist_dir_exists": False,
            "persist_dir_writable": False,
            "collection_name": self.collection_name,
            "issues": [],
            "recommendations": []
        }
        
        # 检查ChromaDB客户端
        if self.chroma_client is None:
            diagnosis["issues"].append("ChromaDB客户端未初始化")
            diagnosis["recommendations"].append("重新初始化ChromaStore")
        else:
            diagnosis["chroma_client_available"] = True
            logger.info(" ChromaDB客户端可用")
        
        # 检查持久化目录
        if self.persist_dir:
            persist_path = Path(self.persist_dir)
            if persist_path.exists():
                diagnosis["persist_dir_exists"] = True
                logger.info(f" 持久化目录存在: {self.persist_dir}")
                
                # 检查写入权限
                try:
                    test_file = persist_path / "test_write"
                    test_file.write_text("test")
                    test_file.unlink()
                    diagnosis["persist_dir_writable"] = True
                    logger.info(" 持久化目录可写")
                except Exception as e:
                    diagnosis["issues"].append(f"持久化目录不可写: {e}")
                    diagnosis["recommendations"].append("检查目录权限")
            else:
                diagnosis["issues"].append(f"持久化目录不存在: {self.persist_dir}")
                diagnosis["recommendations"].append("创建持久化目录")
        
        # 检查Collection
        if self.chroma_client:
            try:
                collections = self.chroma_client.list_collections()
                diagnosis["total_collections"] = len(collections)
                
                # 检查目标collection是否存在（兼容ChromaDB v0.6.0+）
                target_exists = self._check_collection_exists_compatible(collections)
                diagnosis["target_collection_exists"] = target_exists
                
                if target_exists:
                    logger.info(f" 目标Collection存在: {self.collection_name}")
                    diagnosis["collection_available"] = True
                    
                    # 获取collection信息
                    if self.collection:
                        try:
                            count = self.collection.count()
                            diagnosis["collection_document_count"] = count
                            logger.info(f"Collection文档数量: {count}")
                        except Exception as e:
                            diagnosis["issues"].append(f"无法获取Collection文档数量: {e}")
                else:
                    diagnosis["issues"].append(f"目标Collection不存在: {self.collection_name}")
                    diagnosis["recommendations"].append("重新创建Collection")
                
            except Exception as e:
                diagnosis["issues"].append(f"无法列出Collections: {e}")
                diagnosis["recommendations"].append("检查ChromaDB服务状态")
        
        # 总结诊断结果
        if diagnosis["issues"]:
            logger.warning(f" 发现 {len(diagnosis['issues'])} 个问题:")
            for issue in diagnosis["issues"]:
                logger.warning(f"   - {issue}")
        else:
            logger.info(" 未发现明显问题")
        
        return diagnosis
    
    def fix_issues(self, diagnosis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """修复发现的问题"""
        if diagnosis is None:
            diagnosis = self.diagnose()
        
        logger.info(" 开始修复ChromaDB问题")
        
        fix_results = {
            "fixed_issues": [],
            "failed_fixes": [],
            "success": False
        }
        
        # 修复持久化目录问题
        if not diagnosis.get("persist_dir_exists") and self.persist_dir:
            try:
                os.makedirs(self.persist_dir, exist_ok=True)
                logger.info(f" 创建持久化目录: {self.persist_dir}")
                fix_results["fixed_issues"].append("创建持久化目录")
            except Exception as e:
                logger.error(f" 创建持久化目录失败: {e}")
                fix_results["failed_fixes"].append(f"创建持久化目录: {e}")
        
        # 重新创建Collection
        if not diagnosis.get("target_collection_exists") and self.chroma_client:
            try:
                logger.info(f" 重新创建Collection: {self.collection_name}")
                
                # 尝试删除可能存在的损坏collection
                try:
                    self.chroma_client.delete_collection(self.collection_name)
                    logger.info("删除旧Collection")
                except Exception:
                    pass  # Collection可能不存在
                
                # 创建新collection
                collection_metadata = {"hnsw:space": "cosine"}
                new_collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=None,
                    metadata=collection_metadata
                )
                
                # 更新ChromaStore的collection引用
                if hasattr(self.chroma_store, '_collection'):
                    self.chroma_store._collection = new_collection
                
                logger.info(" Collection重新创建成功")
                fix_results["fixed_issues"].append("重新创建Collection")
                
            except Exception as e:
                logger.error(f" 重新创建Collection失败: {e}")
                fix_results["failed_fixes"].append(f"重新创建Collection: {e}")
        
        # 重新初始化ChromaDB客户端
        if not diagnosis.get("chroma_client_available"):
            try:
                logger.info(" 重新初始化ChromaDB客户端")
                self._reinitialize_chroma_client()
                logger.info(" ChromaDB客户端重新初始化成功")
                fix_results["fixed_issues"].append("重新初始化ChromaDB客户端")
            except Exception as e:
                logger.error(f" 重新初始化ChromaDB客户端失败: {e}")
                fix_results["failed_fixes"].append(f"重新初始化ChromaDB客户端: {e}")
        
        # 检查修复结果
        if fix_results["fixed_issues"] and not fix_results["failed_fixes"]:
            fix_results["success"] = True
            logger.info(" 所有问题修复成功")
        elif fix_results["fixed_issues"]:
            logger.warning("️ 部分问题修复成功")
        else:
            logger.error(" 问题修复失败")
        
        return fix_results
    
    def _reinitialize_chroma_client(self):
        """重新初始化ChromaDB客户端"""
        try:
            from chromadb import PersistentClient, Settings
        except ImportError:
            raise ImportError("请安装chromadb包")
        
        if not self.persist_dir:
            raise ValueError("持久化目录未设置")
        
        # 确保目录存在
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # 创建新的客户端
        chroma_settings = Settings(
            persist_directory=self.persist_dir,
            anonymized_telemetry=False,
        )
        
        new_client = PersistentClient(
            path=self.persist_dir, 
            settings=chroma_settings
        )
        
        # 更新ChromaStore的客户端引用
        if hasattr(self.chroma_store, '_chroma_client'):
            self.chroma_store._chroma_client = new_client
            self.chroma_client = new_client
        
        # 重新创建collection
        collection_metadata = {"hnsw:space": "cosine"}
        new_collection = new_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=None,
            metadata=collection_metadata
        )
        
        if hasattr(self.chroma_store, '_collection'):
            self.chroma_store._collection = new_collection
            self.collection = new_collection
    
    def test_connection(self) -> bool:
        """测试ChromaDB连接"""
        try:
            logger.info(" 测试ChromaDB连接")
            
            if not self.chroma_client:
                logger.error("ChromaDB客户端不可用")
                return False
            
            # 测试列出collections
            collections = self.chroma_client.list_collections()
            logger.info(f"成功列出 {len(collections)} 个collections")
            
            # 测试目标collection
            if self.collection:
                count = self.collection.count()
                logger.info(f"目标collection包含 {count} 个文档")
            
            logger.info(" ChromaDB连接测试通过")
            return True
            
        except Exception as e:
            logger.error(f" ChromaDB连接测试失败: {e}")
            return False
    
    def cleanup_corrupted_data(self) -> Dict[str, Any]:
        """清理可能损坏的数据"""
        logger.info(" 开始清理可能损坏的ChromaDB数据")
        
        cleanup_results = {
            "cleaned_items": [],
            "errors": []
        }
        
        try:
            if self.chroma_client and self.collection_name:
                # 尝试删除可能损坏的collection
                try:
                    self.chroma_client.delete_collection(self.collection_name)
                    cleanup_results["cleaned_items"].append(f"删除collection: {self.collection_name}")
                    logger.info(f"删除collection: {self.collection_name}")
                except Exception as e:
                    cleanup_results["errors"].append(f"删除collection失败: {e}")
            
            # 清理持久化目录中的临时文件
            if self.persist_dir and os.path.exists(self.persist_dir):
                persist_path = Path(self.persist_dir)
                temp_files = list(persist_path.glob("*.tmp")) + list(persist_path.glob("*.lock"))
                
                for temp_file in temp_files:
                    try:
                        temp_file.unlink()
                        cleanup_results["cleaned_items"].append(f"删除临时文件: {temp_file}")
                    except Exception as e:
                        cleanup_results["errors"].append(f"删除临时文件失败: {e}")
        
        except Exception as e:
            cleanup_results["errors"].append(f"清理过程出错: {e}")
        
        logger.info(f"清理完成: 清理 {len(cleanup_results['cleaned_items'])} 项, 错误 {len(cleanup_results['errors'])} 项")
        return cleanup_results
    
    def _check_collection_exists_compatible(self, collections) -> bool:
        """检查collection是否存在（兼容ChromaDB不同版本）"""
        try:
            if not collections:
                return False
            
            # ChromaDB v0.6.0+ 返回字符串列表
            if isinstance(collections[0], str):
                return self.collection_name in collections
            else:
                # 旧版本返回对象列表
                return any(getattr(c, 'name', str(c)) == self.collection_name for c in collections)
        except Exception as e:
            logger.warning(f"检查collection存在性失败: {e}")
            
            # 回退方案：直接尝试获取collection
            try:
                if self.chroma_client:
                    self.chroma_client.get_collection(self.collection_name)
                    return True
            except Exception:
                pass
            
            return False


def fix_chromadb_issues(chroma_store) -> bool:
    """修复ChromaDB问题的便捷函数
    
    Args:
        chroma_store: ChromaStore实例
        
    Returns:
        bool: 修复是否成功
    """
    fixer = ChromaDBFixer(chroma_store)
    
    # 诊断问题
    diagnosis = fixer.diagnose()
    
    # 如果有问题，尝试修复
    if diagnosis["issues"]:
        # 先清理可能损坏的数据
        fixer.cleanup_corrupted_data()
        
        # 修复问题
        fix_results = fixer.fix_issues(diagnosis)
        
        # 测试连接
        if fix_results["success"]:
            return fixer.test_connection()
    else:
        # 没有问题，测试连接
        return fixer.test_connection()
    
    return False
