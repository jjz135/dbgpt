import sqlite3

try:
    conn = sqlite3.connect('D:/zhusu-DBGPT/pilot/data/chromadb/chroma.sqlite3')
    cursor = conn.cursor()

    # 检查表
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = [row[0] for row in cursor.fetchall()]
    print('Tables:', tables)

    # 检查embeddings表
    if 'embeddings' in tables:
        cursor.execute('SELECT COUNT(*) FROM embeddings')
        count = cursor.fetchone()[0]
        print(f'Total embeddings: {count}')
        
        # 查找material_condition相关记录
        cursor.execute('SELECT document FROM embeddings WHERE document LIKE "%material_condition%" LIMIT 1')
        result = cursor.fetchone()
        if result:
            print('Found material_condition:')
            print('---')
            print(result[0])
            print('---')
        else:
            print('No material_condition found')
            
        # 查看所有记录的前几个
        cursor.execute('SELECT document FROM embeddings LIMIT 3')
        results = cursor.fetchall()
        print(f'\nFirst 3 documents:')
        for i, (doc,) in enumerate(results):
            print(f'{i+1}. {doc[:100]}...')

    conn.close()
    print('Done')
    
except Exception as e:
    print(f'Error: {e}')
