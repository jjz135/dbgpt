"""DM (Dameng) connector using pyodbc or dmPython."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Type
from urllib.parse import quote_plus

from sqlalchemy import text

from dbgpt.core.awel.flow import (
    TAGS_ORDER_HIGH,
    ResourceCategory,
    auto_register_resource,
)
from dbgpt.datasource.rdbms.base import RDBMSConnector, RDBMSDatasourceParameters
from dbgpt.util.i18n_utils import _

logger = logging.getLogger(__name__)

# Import DM dialect to register it with SQLAlchemy
from dbgpt_ext.datasource.rdbms.dialect.dm.dm_dialect import DMDialect  # noqa: F401


@auto_register_resource(
    label=_("DM datasource"),
    category=ResourceCategory.DATABASE,
    tags={"order": TAGS_ORDER_HIGH},
    description=_(
        "Enterprise-grade relational database with DM driver (pyodbc/dmPython)."
    ),
)
@dataclass
class DMParameters(RDBMSDatasourceParameters):
    """DM connection parameters."""

    __type__ = "dm"

    driver: str = field(
        default="dm",  # dmPython 的 SQLAlchemy 方言名称为 'dm'
        metadata={
            "help": _("Driver name for DM, default is dm."),
        },
    )

    def db_url(self, ssl: bool = False, charset: Optional[str] = None) -> str:
        """Return database engine url."""
        bm_pwd = quote_plus(self.password)
        url = f"{self.driver}://{self.user}:{bm_pwd}@{self.host}:{str(self.port)}/{self.database}"
        if charset:
            url += f"?charset={charset}"
        return url

    def create_connector(self) -> "DMConnector":
        return DMConnector.from_parameters(self)


class DMConnector(RDBMSConnector):
    """DM (Dameng) connector."""

    db_type: str = "dm"
    db_dialect: str = "dm"
    driver: str = "dm"  # dmPython 的 SQLAlchemy 方言名称为 'dm'

    def __init__(self, *args, **kwargs):
        """Initialize DM connector.
        
        Override to handle metadata reflection with schema for DM database.
        """
        # Call parent __init__ first
        super().__init__(*args, **kwargs)
        
        # For DM, re-reflect metadata with specific schema (case-sensitive lowercase)
        schema = self._engine.url.database
        if schema:
            try:
                from sqlalchemy import MetaData
                # Create new metadata and reflect with schema
                new_metadata = MetaData()
                new_metadata.reflect(bind=self._engine, schema=schema)
                self._metadata = new_metadata
                logger.info(f"DM metadata reflected successfully for schema: {schema}")
            except Exception as e:
                logger.warning(f"DM metadata reflection failed for schema '{schema}': {e}", exc_info=True)
                # Continue with existing metadata

    def _sync_tables_from_db(self):
        """Read table information from database.
        
        Override to handle DM schema names correctly (case-sensitive, lowercase).
        """
        # For DM, use the database name from URL as schema, but keep it lowercase
        _schema = self._engine.url.database
        
        # including view support by adding the views as well as tables
        try:
            table_names = self._inspector.get_table_names(schema=_schema)
        except Exception as e:
            logger.warning(f"Failed to get table names, using empty list: {e}")
            table_names = []
        
        try:
            view_names = self._inspector.get_view_names(schema=_schema) if self.view_support else []
        except Exception as e:
            logger.warning(f"Failed to get view names, using empty list: {e}")
            view_names = []
        
        self._all_tables = set(table_names + view_names)
        return self._all_tables

    @classmethod
    def param_class(cls) -> Type[RDBMSDatasourceParameters]:
        """Return the parameter class."""
        return DMParameters

    @classmethod
    def from_uri_db(
        cls,
        host: str,
        port: int,
        user: str,
        pwd: str,
        db_name: str,
        engine_args: Optional[dict] = None,
        **kwargs,
    ) -> "DMConnector":
        """Construct a SQLAlchemy engine from uri database.

        Args:
            host (str): database host.
            port (int): database port.
            user (str): database user.
            pwd (str): database password.
            db_name (str): database name.
            engine_args (Optional[dict]): other engine_args.
        """
        bm_pwd = quote_plus(pwd)
        db_url = f"{cls.driver}://{user}:{bm_pwd}@{host}:{str(port)}/{db_name}"
        return cls.from_uri(db_url, engine_args=engine_args, **kwargs)

    def get_simple_fields(self, table_name):
        """Get column fields about specified table."""
        return self.get_fields(table_name)

    def get_fields(self, table_name: str, db_name=None) -> List[Tuple]:
        """Get column information about specified table.

        Args:
            table_name (str): table name
            db_name (Optional[str]): database name

        Returns:
            List[Tuple]: Column information
        """
        with self.session_scope() as session:
            query = f"""
                SELECT col.column_name,
                       col.data_type,
                       col.data_default,
                       col.nullable,
                       comm.comments
                FROM all_tab_columns col
                LEFT JOIN all_col_comments comm
                ON col.owner = comm.owner
                AND col.table_name = comm.table_name
                AND col.column_name = comm.column_name
                WHERE col.table_name = '{table_name.upper()}'
            """
            result = session.execute(text(query))
            return result.fetchall()

    def get_charset(self) -> str:
        """Get character set."""
        # DM doesn't have NLS_DATABASE_PARAMETERS, return default
        return "UTF8"

    def get_grants(self):
        """Get grant info."""
        with self.session_scope() as session:
            cursor = session.execute(text("SELECT privilege FROM user_sys_privs"))
            return cursor.fetchall()

    def get_users(self) -> List[Tuple[str, None]]:
        """Get user info."""
        with self.session_scope() as session:
            cursor = session.execute(text("SELECT username FROM all_users"))
            return [(row[0], None) for row in cursor.fetchall()]

    def get_database_names(self) -> List[str]:
        """Return a list of database names available in the database.

        Returns:
            List[str]: database list
        """
        with self.session_scope() as session:
            # DM数据库通常只有一个实例，返回当前连接的数据库名
            return [self._engine.url.database] if self._engine.url.database else []

    def get_table_comments(self, db_name: str) -> List[Tuple[str, str]]:
        """Return table comments.

        Args:
            db_name (str): database name

        Returns:
            List[Tuple[str, str]]: table comments
        """
        with self.session_scope() as session:
            result = session.execute(
                text("SELECT table_name, comments FROM user_tab_comments")
            )
            return [(row[0], row[1]) for row in result.fetchall()]

    def get_table_comment(self, table_name: str) -> Dict:
        """Get table comment.

        Args:
            table_name (str): table name

        Returns:
            Dict: table comment
        """
        with self.session_scope() as session:
            cursor = session.execute(
                text(
                    f"SELECT comments FROM user_tab_comments "
                    f"WHERE table_name = '{table_name.upper()}'"
                )
            )
            row = cursor.fetchone()
            return {"text": row[0] if row else ""}

    def get_column_comments(
        self, db_name: str, table_name: str
    ) -> List[Tuple[str, str]]:
        """Return column comments.

        Args:
            db_name (str): database name
            table_name (str): table name

        Returns:
            List[Tuple[str, str]]: column comments
        """
        with self.session_scope() as session:
            cursor = session.execute(
                text(f"""
                    SELECT column_name, comments
                    FROM user_col_comments
                    WHERE table_name = '{table_name.upper()}'
                """)
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]

    def get_collation(self) -> str:
        """Get collation."""
        # DM doesn't have NLS_DATABASE_PARAMETERS, return default
        return "BINARY"

    def _format_sql(self, sql: str) -> str:
        """Format SQL command and add schema prefix for DM database.
        
        Override to handle DM schema name qualification.
        DM requires schema prefix for tables when not using default schema.
        """
        if not sql:
            return sql
        
        sql = sql.strip()
        
        # Add schema prefix if not already present
        schema = self._engine.url.database
        if schema:
            import re
            # Match FROM or JOIN followed by table name without schema prefix
            # Pattern: FROM table_name or JOIN table_name
            pattern = r'(\bFROM\s+|\bJOIN\s+)([a-zA-Z_][a-zA-Z0-9_]*)(?!\.)'
            
            def add_schema_prefix(match):
                keyword = match.group(1)
                table_name = match.group(2)
                # Skip if it's a subquery or already has schema
                if table_name.startswith('(') or '.' in table_name:
                    return match.group(0)
                # Add schema prefix with double quotes for DM
                return f'{keyword}"{schema}"."{table_name}"'
            
            sql = re.sub(pattern, add_schema_prefix, sql, flags=re.IGNORECASE)
        
        return sql

    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table.
        
        Override to use DM-compatible SQL (no backticks, specify schema).
        """
        try:
            with self.session_scope() as session:
                # DM requires schema specification and uses double quotes
                schema = self._engine.url.database
                if schema:
                    result = session.execute(
                        text(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"')
                    )
                else:
                    result = session.execute(
                        text(f'SELECT COUNT(*) FROM "{table_name}"')
                    )
                return result.fetchone()[0]
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {e}")
            return 0

    def describe_table(self, table_name: str):
        """Describe table structure.
        
        Override to use DM-compatible SQL (no backticks, no DESCRIBE command).
        Returns list of tuples: (column_name, data_type, nullable, key, default, extra)
        """
        try:
            with self.session_scope() as session:
                # DM doesn't support DESCRIBE or backticks, query all_tab_columns instead
                query = text("""
                    SELECT 
                        column_name,
                        data_type,
                        CASE WHEN nullable = 'Y' THEN 'YES' ELSE 'NO' END as nullable,
                        '' as "key",
                        data_default,
                        '' as extra
                    FROM all_tab_columns
                    WHERE table_name = :table_name
                    ORDER BY column_id
                """)
                result = session.execute(query, {"table_name": table_name.upper()})
                return result.fetchall()
        except Exception as e:
            logger.warning(f"Failed to describe table {table_name}: {e}")
            return []
