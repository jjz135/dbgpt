#!/usr/bin/env python3
"""
数据库表结构RAG优化器 - 通用解决方案
解决大量表导致的RAG性能问题和LLM token限制问题
"""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TablePriority(Enum):
    """表优先级枚举"""
    HIGH = "high"        # 高优先级：有数据、经常查询
    MEDIUM = "medium"    # 中优先级：有数据、偶尔查询
    LOW = "low"          # 低优先级：少量数据
    IGNORE = "ignore"    # 忽略：空表、系统表


@dataclass
class TableMetrics:
    """表指标数据"""
    table_name: str
    row_count: int
    column_count: int
    data_size_mb: float
    last_modified: Optional[datetime]
    query_frequency: int = 0  # 查询频率
    importance_score: float = 0.0  # 重要性评分
    priority: TablePriority = TablePriority.LOW


class DatabaseSchemaOptimizer:
    """数据库表结构优化器"""
    
    def __init__(self, 
                 max_tables_per_query: int = 20,
                 max_chunks_total: int = 500,
                 empty_table_threshold: int = 0,
                 small_table_threshold: int = 100,
                 cache_duration_hours: int = 24):
        """
        初始化优化器
        
        Args:
            max_tables_per_query: 单次查询最大表数量
            max_chunks_total: 最大chunk总数
            empty_table_threshold: 空表阈值（行数）
            small_table_threshold: 小表阈值（行数）
            cache_duration_hours: 缓存持续时间（小时）
        """
        self.max_tables_per_query = max_tables_per_query
        self.max_chunks_total = max_chunks_total
        self.empty_table_threshold = empty_table_threshold
        self.small_table_threshold = small_table_threshold
        self.cache_duration = timedelta(hours=cache_duration_hours)
        
        # 缓存
        self._table_metrics_cache = {}
        self._cache_timestamp = None
        
        # 配置
        self.system_table_patterns = [
            'information_schema', 'performance_schema', 'mysql', 'sys',
            'pg_catalog', 'pg_toast', '__', 'sqlite_', 'msreplication_'
        ]
        
        self.business_keywords = [
            'user', 'order', 'product', 'customer', 'sales', 'invoice',
            'payment', 'transaction', 'account', 'item', 'service'
        ]

    def analyze_database_tables(self, db_connector) -> Dict[str, TableMetrics]:
        """分析数据库中的所有表"""
        logger.info("开始分析数据库表结构...")
        
        # 检查缓存
        if self._is_cache_valid():
            logger.info("使用缓存的表指标数据")
            return self._table_metrics_cache
        
        table_metrics = {}
        
        try:
            # 获取所有表名
            table_names = list(db_connector.get_table_names())
            logger.info(f"发现 {len(table_names)} 个表")
            
            for table_name in table_names:
                try:
                    metrics = self._analyze_single_table(db_connector, table_name)
                    table_metrics[table_name] = metrics
                except Exception as e:
                    logger.warning(f"分析表 {table_name} 失败: {e}")
                    # 创建默认指标
                    table_metrics[table_name] = TableMetrics(
                        table_name=table_name,
                        row_count=0,
                        column_count=0,
                        data_size_mb=0.0,
                        last_modified=None,
                        priority=TablePriority.IGNORE
                    )
            
            # 计算重要性评分
            self._calculate_importance_scores(table_metrics)
            
            # 更新缓存
            self._table_metrics_cache = table_metrics
            self._cache_timestamp = datetime.now()
            
            logger.info(f"表分析完成，共分析 {len(table_metrics)} 个表")
            return table_metrics
            
        except Exception as e:
            logger.error(f"数据库表分析失败: {e}")
            return {}

    def _analyze_single_table(self, db_connector, table_name: str) -> TableMetrics:
        """分析单个表的指标"""
        try:
            # 获取表信息（这里需要根据具体的connector实现调整）
            with db_connector.session_scope() as session:
                # 获取行数
                try:
                    result = session.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    row_count = result.fetchone()[0]
                except:
                    row_count = 0
                
                # 获取列数
                try:
                    result = session.execute(f"SHOW COLUMNS FROM `{table_name}`")
                    columns = result.fetchall()
                    column_count = len(columns)
                except:
                    column_count = 0
                
                # 获取表大小（MySQL特定）
                try:
                    result = session.execute(f"""
                        SELECT 
                            ROUND(((data_length + index_length) / 1024 / 1024), 2) as size_mb,
                            update_time
                        FROM information_schema.tables 
                        WHERE table_name = '{table_name}' 
                        AND table_schema = DATABASE()
                    """)
                    table_info = result.fetchone()
                    data_size_mb = float(table_info[0] or 0)
                    last_modified = table_info[1]
                except:
                    data_size_mb = 0.0
                    last_modified = None
            
            # 确定优先级
            priority = self._determine_table_priority(
                table_name, row_count, column_count, data_size_mb
            )
            
            return TableMetrics(
                table_name=table_name,
                row_count=row_count,
                column_count=column_count,
                data_size_mb=data_size_mb,
                last_modified=last_modified,
                priority=priority
            )
            
        except Exception as e:
            logger.warning(f"获取表 {table_name} 信息失败: {e}")
            return TableMetrics(
                table_name=table_name,
                row_count=0,
                column_count=0,
                data_size_mb=0.0,
                last_modified=None,
                priority=TablePriority.IGNORE
            )

    def _determine_table_priority(self, table_name: str, row_count: int, 
                                column_count: int, data_size_mb: float) -> TablePriority:
        """确定表的优先级"""
        table_name_lower = table_name.lower()
        
        # 系统表 - 忽略
        if any(pattern in table_name_lower for pattern in self.system_table_patterns):
            return TablePriority.IGNORE
        
        # 空表 - 忽略
        if row_count <= self.empty_table_threshold:
            return TablePriority.IGNORE
        
        # 业务关键表 - 高优先级
        if any(keyword in table_name_lower for keyword in self.business_keywords):
            if row_count > self.small_table_threshold:
                return TablePriority.HIGH
            else:
                return TablePriority.MEDIUM
        
        # 根据数据量判断
        if row_count > self.small_table_threshold:
            return TablePriority.MEDIUM
        else:
            return TablePriority.LOW

    def _calculate_importance_scores(self, table_metrics: Dict[str, TableMetrics]):
        """计算表的重要性评分"""
        max_rows = max((m.row_count for m in table_metrics.values()), default=1)
        max_size = max((m.data_size_mb for m in table_metrics.values()), default=1)
        
        for metrics in table_metrics.values():
            score = 0.0
            
            # 数据量评分 (40%)
            if max_rows > 0:
                score += (metrics.row_count / max_rows) * 0.4
            
            # 数据大小评分 (20%)
            if max_size > 0:
                score += (metrics.data_size_mb / max_size) * 0.2
            
            # 业务相关性评分 (30%)
            table_name_lower = metrics.table_name.lower()
            business_score = sum(
                0.1 for keyword in self.business_keywords 
                if keyword in table_name_lower
            )
            score += min(business_score, 0.3)
            
            # 最近更新评分 (10%)
            if metrics.last_modified:
                days_ago = (datetime.now() - metrics.last_modified).days
                if days_ago < 30:
                    score += 0.1 * (30 - days_ago) / 30
            
            metrics.importance_score = score

    def filter_tables_for_rag(self, table_metrics: Dict[str, TableMetrics], 
                             user_query: str = "") -> List[str]:
        """为RAG过程筛选相关表"""
        logger.info("开始筛选RAG相关表...")
        
        # 按优先级和重要性过滤
        relevant_tables = []
        
        # 1. 高优先级表 - 全部包含
        high_priority_tables = [
            name for name, metrics in table_metrics.items()
            if metrics.priority == TablePriority.HIGH
        ]
        relevant_tables.extend(high_priority_tables)
        
        # 2. 中优先级表 - 根据查询相关性选择
        medium_priority_tables = [
            (name, metrics) for name, metrics in table_metrics.items()
            if metrics.priority == TablePriority.MEDIUM
        ]
        
        # 根据查询内容筛选中优先级表
        if user_query:
            query_keywords = self._extract_query_keywords(user_query)
            for table_name, metrics in medium_priority_tables:
                if self._is_table_relevant_to_query(table_name, query_keywords):
                    relevant_tables.append(table_name)
        
        # 3. 如果表数量不足，添加一些低优先级表
        if len(relevant_tables) < self.max_tables_per_query // 2:
            low_priority_tables = [
                (name, metrics) for name, metrics in table_metrics.items()
                if metrics.priority == TablePriority.LOW
            ]
            # 按重要性评分排序，选择前几个
            low_priority_tables.sort(key=lambda x: x[1].importance_score, reverse=True)
            remaining_slots = self.max_tables_per_query - len(relevant_tables)
            for table_name, _ in low_priority_tables[:remaining_slots]:
                relevant_tables.append(table_name)
        
        # 限制最大数量
        relevant_tables = relevant_tables[:self.max_tables_per_query]
        
        logger.info(f"筛选出 {len(relevant_tables)} 个相关表用于RAG")
        return relevant_tables

    def _extract_query_keywords(self, query: str) -> List[str]:
        """从用户查询中提取关键词"""
        # 简单的关键词提取，可以根据需要改进
        import re
        
        # 移除常见停用词
        stopwords = {'的', '是', '在', '有', '和', '与', '或', '查询', '显示', '统计', '分析'}
        
        # 提取中英文单词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query.lower())
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        return keywords

    def _is_table_relevant_to_query(self, table_name: str, query_keywords: List[str]) -> bool:
        """判断表是否与查询相关"""
        table_name_lower = table_name.lower()
        
        # 检查表名是否包含查询关键词
        for keyword in query_keywords:
            if keyword in table_name_lower:
                return True
        
        return False

    def optimize_chunk_generation(self, table_names: List[str], 
                                db_connector) -> List[Dict[str, Any]]:
        """优化chunk生成策略"""
        logger.info("开始优化chunk生成...")
        
        optimized_chunks = []
        chunk_count = 0
        
        for table_name in table_names:
            if chunk_count >= self.max_chunks_total:
                logger.warning(f"达到最大chunk限制 {self.max_chunks_total}，停止生成")
                break
            
            try:
                # 获取表结构信息
                table_info = self._get_optimized_table_info(db_connector, table_name)
                
                # 生成紧凑的chunk
                chunk = {
                    "table_name": table_name,
                    "content": self._format_compact_table_info(table_info),
                    "metadata": {
                        "table": table_name,
                        "type": "table_schema",
                        "row_count": table_info.get("row_count", 0)
                    }
                }
                
                optimized_chunks.append(chunk)
                chunk_count += 1
                
            except Exception as e:
                logger.warning(f"生成表 {table_name} 的chunk失败: {e}")
        
        logger.info(f"生成了 {len(optimized_chunks)} 个优化的chunk")
        return optimized_chunks

    def _get_optimized_table_info(self, db_connector, table_name: str) -> Dict[str, Any]:
        """获取优化的表信息"""
        try:
            with db_connector.session_scope() as session:
                # 获取列信息
                result = session.execute(f"DESCRIBE `{table_name}`")
                columns = result.fetchall()
                
                # 获取行数
                result = session.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                row_count = result.fetchone()[0]
                
                # 格式化列信息
                column_info = []
                for col in columns:
                    column_info.append({
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "key": col[3],
                        "default": col[4]
                    })
                
                return {
                    "table_name": table_name,
                    "columns": column_info,
                    "row_count": row_count
                }
                
        except Exception as e:
            logger.warning(f"获取表 {table_name} 信息失败: {e}")
            return {"table_name": table_name, "columns": [], "row_count": 0}

    def _format_compact_table_info(self, table_info: Dict[str, Any]) -> str:
        """格式化紧凑的表信息"""
        table_name = table_info["table_name"]
        columns = table_info.get("columns", [])
        row_count = table_info.get("row_count", 0)
        
        # 生成紧凑的表结构描述
        column_strs = []
        for col in columns:
            col_str = f"{col['name']}({col['type']})"
            if col.get('key') == 'PRI':
                col_str += "[PK]"
            elif col.get('key') == 'MUL':
                col_str += "[FK]"
            column_strs.append(col_str)
        
        content = f"表 {table_name}: {len(columns)}列, {row_count}行\n"
        content += f"字段: {', '.join(column_strs)}"
        
        return content

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache_timestamp or not self._table_metrics_cache:
            return False
        
        return datetime.now() - self._cache_timestamp < self.cache_duration

    def get_optimization_report(self, table_metrics: Dict[str, TableMetrics]) -> Dict[str, Any]:
        """生成优化报告"""
        total_tables = len(table_metrics)
        
        priority_counts = {
            TablePriority.HIGH: 0,
            TablePriority.MEDIUM: 0,
            TablePriority.LOW: 0,
            TablePriority.IGNORE: 0
        }
        
        for metrics in table_metrics.values():
            priority_counts[metrics.priority] += 1
        
        total_rows = sum(m.row_count for m in table_metrics.values())
        total_size_mb = sum(m.data_size_mb for m in table_metrics.values())
        
        return {
            "total_tables": total_tables,
            "priority_distribution": {k.value: v for k, v in priority_counts.items()},
            "total_rows": total_rows,
            "total_size_mb": round(total_size_mb, 2),
            "optimization_ratio": round(
                (priority_counts[TablePriority.IGNORE] / total_tables) * 100, 1
            ),
            "recommended_rag_tables": priority_counts[TablePriority.HIGH] + priority_counts[TablePriority.MEDIUM]
        }


# 使用示例
def optimize_database_rag(db_connector, user_query: str = ""):
    """优化数据库RAG的主函数"""
    
    # 创建优化器
    optimizer = DatabaseSchemaOptimizer(
        max_tables_per_query=15,  # 减少到15个表
        max_chunks_total=300,     # 减少到300个chunk
        empty_table_threshold=0,
        small_table_threshold=50
    )
    
    # 分析数据库表
    table_metrics = optimizer.analyze_database_tables(db_connector)
    
    # 生成优化报告
    report = optimizer.get_optimization_report(table_metrics)
    logger.info(f"优化报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
    
    # 筛选相关表
    relevant_tables = optimizer.filter_tables_for_rag(table_metrics, user_query)
    
    # 生成优化的chunk
    optimized_chunks = optimizer.optimize_chunk_generation(relevant_tables, db_connector)
    
    return {
        "relevant_tables": relevant_tables,
        "optimized_chunks": optimized_chunks,
        "optimization_report": report
    }


if __name__ == "__main__":
    print("数据库表结构RAG优化器已就绪")
    print("使用 optimize_database_rag(db_connector, user_query) 来优化RAG性能")
