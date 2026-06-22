# 达梦数据库（DM Database）连接配置指南

## 概述

DB-GPT 现已支持达梦数据库（DM Database）的连接和查询功能。本文档将指导您如何配置和使用达梦数据库。

## 前置要求

### 1. 安装达梦数据库驱动

根据您的环境选择合适的驱动：

#### 方式一：使用 dmPython（推荐）

```bash
pip install dmPython
```

#### 方式二：使用 pyodbc + ODBC 驱动

```bash
pip install pyodbc
# 同时需要安装达梦 ODBC 驱动
```

### 2. SQLAlchemy DM 方言

确保安装了支持达梦数据库的 SQLAlchemy 方言包：

```bash
pip install sqlalchemy-dm
```

## 配置步骤

### 方法一：通过 Web 界面配置（推荐）

1. **启动 DB-GPT 服务**

   ```bash
   python -m dbgpt.app.webserver
   ```

2. **访问数据库管理页面**
   
   打开浏览器访问：`http://localhost:5670/construct/database`

3. **添加达梦数据库连接**
   
   - 点击"添加数据源"按钮
   - 在数据库类型下拉列表中选择 **"DM (Dameng)"**
   - 填写连接参数：
     - **Host**: 达梦数据库服务器地址（如 `localhost`）
     - **Port**: 端口号（默认 `5236`）
     - **User**: 用户名
     - **Password**: 密码
     - **Database**: 数据库名称
     - **Driver**: 驱动程序（默认 `dm+dmPython`）
   - 点击"测试连接"验证配置
   - 测试成功后点击"提交"保存

### 方法二：通过 API 配置

```python
from dbgpt_ext.datasource.rdbms.conn_dm import DMConnector

# 创建连接器
connector = DMConnector.from_uri_db(
    host="localhost",
    port=5236,
    user="SYSDBA",
    pwd="your_password",
    db_name="YOUR_DB_NAME"
)

# 测试连接
result = connector.run("SELECT * FROM DUAL")
print(result)
```

### 方法三：通过配置文件

编辑您的 TOML 配置文件（如 `dbgpt-proxy-openai.toml`），添加达梦数据库配置：

```toml
[[datasources]]
type = "dm"
name = "my_dm_database"
host = "localhost"
port = 5236
user = "SYSDBA"
password = "your_password"
database = "YOUR_DB_NAME"
driver = "dm+dmPython"
```

## 连接字符串格式

达梦数据库的连接字符串格式如下：

```
dm+dmPython://username:password@hostname:port/database_name
```

示例：
```
dm+dmPython://SYSDBA:SYSDBA@localhost:5236/TEST_DB
```

如果使用 pyodbc：
```
dm+pyodbc://username:password@hostname:port/database_name?driver=DM8 ODBC DRIVER
```

## 常见问题

### 1. 找不到 dmPython 模块

**错误信息**：`ModuleNotFoundError: No module named 'dmPython'`

**解决方案**：
```bash
pip install dmPython
```

### 2. 连接超时或拒绝

**可能原因**：
- 达梦数据库服务未启动
- 防火墙阻止了端口访问
- 连接参数不正确

**解决方案**：
- 检查达梦数据库服务状态
- 确认端口 5236 已开放
- 验证用户名、密码和数据库名称

### 3. 字符集问题

如果遇到中文乱码问题，可以在连接字符串中指定字符集：

```
dm+dmPython://user:pass@host:5236/dbname?charset=UTF8
```

### 4. 权限不足

确保使用的数据库用户具有以下权限：
- SELECT 权限（查询数据）
- 访问系统视图的权限（获取表结构信息）

建议授予以下权限：
```sql
GRANT SELECT ANY TABLE TO your_user;
GRANT SELECT ON ALL_TAB_COLUMNS TO your_user;
GRANT SELECT ON ALL_COL_COMMENTS TO your_user;
GRANT SELECT ON USER_TAB_COMMENTS TO your_user;
GRANT SELECT ON USER_COL_COMMENTS TO your_user;
```

## 支持的 SQL 操作

达梦数据库连接器支持以下操作：

- ✅ SELECT 查询
- ✅ INSERT 插入
- ✅ UPDATE 更新
- ✅ DELETE 删除
- ✅ CREATE TABLE 建表
- ✅ DROP TABLE 删表
- ✅ 获取表结构信息
- ✅ 获取字段注释
- ✅ 获取表注释

## 性能优化建议

1. **使用连接池**：配置合适的连接池大小
2. **索引优化**：为常用查询字段创建索引
3. **批量操作**：大量数据导入时使用批量插入
4. **查询优化**：避免 SELECT *，只查询需要的字段

## 技术支持

如遇到问题，可以通过以下方式获取帮助：

1. 查看日志文件：`dbgpt/logs/dbgpt_webserver.log`
2. 参考达梦数据库官方文档
3. 访问 DB-GPT GitHub 仓库提交 Issue

## 参考资料

- [达梦数据库官方文档](https://www.dameng.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [DB-GPT 文档](https://docs.dbgpt.site/)
