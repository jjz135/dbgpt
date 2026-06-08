#!/usr/bin/env python3
"""
检查ChromaDB collections和实际存储内容的脚本
"""

import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_chromadb_sqlite():
    """检查ChromaDB的SQLite数据库"""
    sqlite_path = "D:/zhusu-DBGPT/pilot/data/chromadb/chroma.sqlite3"
    
    if not os.path.exists(sqlite_path):
        logger.error(f"ChromaDB SQLite文件不存在: {sqlite_path}")
        return
    
    logger.info(f"检查ChromaDB SQLite: {sqlite_path}")
    
    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # 查看所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.info(f"发现 {len(tables)} 个表:")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        # 检查collections表
        if any('collections' in str(table) for table in tables):
            logger.info("\n=== Collections信息 ===")
            cursor.execute("SELECT * FROM collections ORDER BY created_at DESC LIMIT 10;")
            collections = cursor.fetchall()
            
            # 获取列名
            cursor.execute("PRAGMA table_info(collections);")
            columns = [col[1] for col in cursor.fetchall()]
            logger.info(f"Collections表列: {columns}")
            
            logger.info(f"最近的 {len(collections)} 个collections:")
            for i, coll in enumerate(collections):
                logger.info(f"\n--- Collection {i+1} ---")
                for j, col_name in enumerate(columns):
                    if j < len(coll):
                        value = coll[j]
                        if col_name == 'name' and 'tongjia_data' in str(value):
                            logger.info(f" {col_name}: {value} (目标数据库!)")
                        else:
                            logger.info(f"  {col_name}: {value}")
        
        # 检查segments表（存储实际数据）
        if any('segments' in str(table) for table in tables):
            logger.info("\n=== Segments信息 ===")
            cursor.execute("SELECT * FROM segments ORDER BY created_at DESC LIMIT 5;")
            segments = cursor.fetchall()
            
            cursor.execute("PRAGMA table_info(segments);")
            columns = [col[1] for col in cursor.fetchall()]
            logger.info(f"Segments表列: {columns}")
            
            for i, seg in enumerate(segments):
                logger.info(f"\n--- Segment {i+1} ---")
                for j, col_name in enumerate(columns):
                    if j < len(seg):
                        value = seg[j]
                        logger.info(f"  {col_name}: {value}")
        
        # 检查embeddings表
        if any('embeddings' in str(table) or 'embedding' in str(table) for table in tables):
            logger.info("\n=== Embeddings信息 ===")
            for table in tables:
                table_name = table[0]
                if 'embedding' in table_name.lower():
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = cursor.fetchone()[0]
                    logger.info(f"表 {table_name}: {count} 条记录")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"检查SQLite失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

def check_latest_collection_content():
    """检查最新collection的内容"""
    logger.info("\n=== 检查最新Collection内容 ===")
    
    try:
        import chromadb
        
        # 连接ChromaDB
        client = chromadb.PersistentClient(path="D:/zhusu-DBGPT/pilot/data/chromadb")
        
        # 获取所有collections
        collections = client.list_collections()
        logger.info(f"发现 {len(collections)} 个collections")
        
        # 查找与tongjia_data相关的collection
        target_collections = []
        for coll in collections:
            coll_name = coll if isinstance(coll, str) else (coll.name if hasattr(coll, 'name') else str(coll))
            if 'tongjia_data' in coll_name or 'profile' in coll_name:
                target_collections.append(coll_name)
        
        logger.info(f"找到目标collections: {target_collections}")
        
        # 检查每个目标collection
        for coll_name in target_collections:
            logger.info(f"\n--- 检查Collection: {coll_name} ---")
            try:
                collection = client.get_collection(coll_name)
                count = collection.count()
                logger.info(f"文档数量: {count}")
                
                if count > 0:
                    # 获取前几个文档
                    result = collection.get(limit=3, include=['documents', 'metadatas'])
                    
                    documents = result.get('documents', [])
                    metadatas = result.get('metadatas', [])
                    
                    for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                        logger.info(f"\n  文档 {i+1}:")
                        logger.info(f"  元数据: {meta}")
                        
                        # 检查内容类型
                        if "表名:" in doc:
                            logger.info("   发现智能注释格式")
                            # 提取表名
                            lines = doc.split('\n')
                            for line in lines:
                                if line.strip().startswith('表名:'):
                                    table_name = line.split(':', 1)[1].strip()
                                    logger.info(f"   表名: {table_name}")
                                elif line.strip().startswith('表说明:'):
                                    desc = line.split(':', 1)[1].strip()
                                    logger.info(f"   表说明: {desc}")
                                elif line.strip().startswith('字段:'):
                                    fields = line.split(':', 1)[1].strip()
                                    logger.info(f"   字段: {fields[:100]}...")
                        else:
                            logger.info(f"   内容预览: {doc[:200]}...")
                            if any(keyword in doc for keyword in ["CREATE TABLE", "column", "field"]):
                                logger.info("    可能是原始表结构格式")
                            else:
                                logger.info("   未知格式")
                        
            except Exception as e:
                logger.warning(f"检查collection {coll_name} 失败: {e}")
        
        # 如果没有找到目标collections，列出所有collections
        if not target_collections:
            logger.warning("未找到目标collections，列出所有collections:")
            for i, coll in enumerate(collections):
                coll_name = coll if isinstance(coll, str) else (coll.name if hasattr(coll, 'name') else str(coll))
                try:
                    collection = client.get_collection(coll_name)
                    count = collection.count()
                    logger.info(f"  {i+1}. {coll_name}: {count} 文档")
                except:
                    logger.info(f"  {i+1}. {coll_name}: 无法访问")
        
    except Exception as e:
        logger.error(f"检查ChromaDB内容失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    print(" 开始检查ChromaDB存储...")
    
    print("\n" + "="*50)
    print("步骤1: 检查SQLite数据库")
    print("="*50)
    check_chromadb_sqlite()
    
    print("\n" + "="*50)
    print("步骤2: 检查Collection内容")
    print("="*50)
    check_latest_collection_content()

if __name__ == "__main__":
    main()
