-- ufdata_002_2017 数据库诊断SQL脚本
-- 请在MySQL客户端中执行这些查询来排查问题表

USE ufdata_002_2017;

-- 1. 检查数据库基本信息
SELECT 
    SCHEMA_NAME as '数据库名',
    DEFAULT_CHARACTER_SET_NAME as '默认字符集',
    DEFAULT_COLLATION_NAME as '默认排序规则'
FROM information_schema.SCHEMATA 
WHERE SCHEMA_NAME = 'ufdata_002_2017';

-- 2. 获取所有表的基本信息
SELECT 
    TABLE_NAME as '表名',
    ENGINE as '存储引擎',
    TABLE_ROWS as '行数',
    TABLE_COLLATION as '排序规则',
    CREATE_TIME as '创建时间'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
ORDER BY TABLE_NAME;

-- 3. 查找可能有问题的表名（包含特殊字符）
SELECT 
    TABLE_NAME as '可能有问题的表名',
    CASE 
        WHEN TABLE_NAME REGEXP '[^a-zA-Z0-9_]' THEN '包含特殊字符'
        WHEN LENGTH(TABLE_NAME) > 64 THEN '表名过长'
        WHEN TABLE_NAME REGEXP '^[0-9]' THEN '以数字开头'
        ELSE '其他问题'
    END as '问题类型'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
    AND (
        TABLE_NAME REGEXP '[^a-zA-Z0-9_]' OR  -- 包含特殊字符
        LENGTH(TABLE_NAME) > 64 OR           -- 表名过长
        TABLE_NAME REGEXP '^[0-9]'          -- 以数字开头
    )
ORDER BY TABLE_NAME;

-- 4. 查找MySQL关键词表名
SELECT TABLE_NAME as 'MySQL关键词表名'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
    AND UPPER(TABLE_NAME) IN (
        'ADD', 'ALL', 'ALTER', 'AND', 'AS', 'ASC', 'BETWEEN', 'BY', 'CASE', 'CHECK', 
        'COLUMN', 'CREATE', 'DATABASE', 'DELETE', 'DESC', 'DISTINCT', 'DROP', 'FROM', 
        'GROUP', 'HAVING', 'IN', 'INDEX', 'INSERT', 'INTO', 'IS', 'JOIN', 'KEY', 
        'LEFT', 'LIKE', 'LIMIT', 'NOT', 'NULL', 'ON', 'OR', 'ORDER', 'PRIMARY', 
        'RIGHT', 'SELECT', 'SET', 'TABLE', 'UNION', 'UNIQUE', 'UPDATE', 'VALUES', 
        'WHERE', 'WITH'
    );

-- 5. 检查表的字符集和排序规则不一致的情况
SELECT 
    TABLE_NAME as '表名',
    TABLE_COLLATION as '表排序规则',
    COLUMN_NAME as '列名',
    COLLATION_NAME as '列排序规则'
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
    AND COLLATION_NAME IS NOT NULL
    AND COLLATION_NAME != (
        SELECT TABLE_COLLATION 
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = 'ufdata_002_2017' 
            AND TABLE_NAME = information_schema.COLUMNS.TABLE_NAME
    )
ORDER BY TABLE_NAME, COLUMN_NAME;

-- 6. 查找包含大量NULL值的表（可能导致反射问题）
SELECT 
    TABLE_NAME as '表名',
    COLUMN_NAME as '列名',
    DATA_TYPE as '数据类型',
    IS_NULLABLE as '允许NULL',
    COLUMN_DEFAULT as '默认值'
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
    AND (
        DATA_TYPE IN ('text', 'blob', 'longtext', 'longblob') OR  -- 大字段类型
        COLUMN_DEFAULT = 'NULL' OR
        (IS_NULLABLE = 'YES' AND COLUMN_DEFAULT IS NULL)
    )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- 7. 检查外键约束（可能导致反射问题）
SELECT 
    CONSTRAINT_NAME as '约束名',
    TABLE_NAME as '表名',
    COLUMN_NAME as '列名',
    REFERENCED_TABLE_NAME as '引用表',
    REFERENCED_COLUMN_NAME as '引用列'
FROM information_schema.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
    AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, COLUMN_NAME;

-- 8. 查找可能有问题的数据类型
SELECT 
    TABLE_NAME as '表名',
    COLUMN_NAME as '列名',
    DATA_TYPE as '数据类型',
    COLUMN_TYPE as '完整类型',
    CASE 
        WHEN DATA_TYPE = 'enum' THEN 'ENUM类型可能有兼容性问题'
        WHEN DATA_TYPE = 'set' THEN 'SET类型可能有兼容性问题'
        WHEN DATA_TYPE LIKE '%text' AND CHARACTER_MAXIMUM_LENGTH IS NULL THEN 'TEXT类型长度未定义'
        WHEN DATA_TYPE = 'timestamp' AND COLUMN_DEFAULT = 'CURRENT_TIMESTAMP' THEN 'TIMESTAMP默认值可能有问题'
        ELSE '其他潜在问题'
    END as '潜在问题'
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
    AND (
        DATA_TYPE IN ('enum', 'set') OR
        (DATA_TYPE LIKE '%text' AND CHARACTER_MAXIMUM_LENGTH IS NULL) OR
        (DATA_TYPE = 'timestamp' AND COLUMN_DEFAULT = 'CURRENT_TIMESTAMP')
    )
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- 9. 检查表名长度分布
SELECT 
    CASE 
        WHEN LENGTH(TABLE_NAME) <= 10 THEN '1-10字符'
        WHEN LENGTH(TABLE_NAME) <= 20 THEN '11-20字符'
        WHEN LENGTH(TABLE_NAME) <= 30 THEN '21-30字符'
        WHEN LENGTH(TABLE_NAME) <= 40 THEN '31-40字符'
        WHEN LENGTH(TABLE_NAME) <= 50 THEN '41-50字符'
        WHEN LENGTH(TABLE_NAME) <= 60 THEN '51-60字符'
        ELSE '超过60字符'
    END as '表名长度范围',
    COUNT(*) as '表数量'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
GROUP BY 
    CASE 
        WHEN LENGTH(TABLE_NAME) <= 10 THEN '1-10字符'
        WHEN LENGTH(TABLE_NAME) <= 20 THEN '11-20字符'
        WHEN LENGTH(TABLE_NAME) <= 30 THEN '21-30字符'
        WHEN LENGTH(TABLE_NAME) <= 40 THEN '31-40字符'
        WHEN LENGTH(TABLE_NAME) <= 50 THEN '41-50字符'
        WHEN LENGTH(TABLE_NAME) <= 60 THEN '51-60字符'
        ELSE '超过60字符'
    END
ORDER BY MIN(LENGTH(TABLE_NAME));

-- 10. 获取前20个表的详细信息用于手动检查
SELECT 
    TABLE_NAME as '表名',
    ENGINE as '引擎',
    TABLE_ROWS as '行数',
    AVG_ROW_LENGTH as '平均行长度',
    DATA_LENGTH as '数据长度',
    CREATE_TIME as '创建时间',
    TABLE_COMMENT as '表注释'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'ufdata_002_2017'
ORDER BY TABLE_NAME
LIMIT 20;
