"""DM (Dameng) Dialect support for SQLAlchemy using dmPython."""

from sqlalchemy import util, text, types as sqltypes
from sqlalchemy.dialects import registry
from sqlalchemy.engine import default
from sqlalchemy.engine.reflection import Inspector
from typing import List, Dict, Any, Optional


class DMDialect(default.DefaultDialect):
    """DM (Dameng) dialect based on dmPython driver.
    
    Dameng database uses dmPython as its native Python driver.
    """

    name = "dm"
    driver = "dmpython"
    
    # DM is compatible with Oracle syntax
    supports_statement_cache = True
    supports_unicode_statements = True
    supports_unicode_binds = True
    use_returning = False
    
    # Identifier cases
    identifier_preparer = None
    
    def __init__(self, **kwargs):
        """Initialize DMDialect."""
        super().__init__(**kwargs)

    @classmethod
    def _type_from_string(cls, type_str: str) -> sqltypes.TypeEngine:
        """Convert DM data type string to SQLAlchemy type.
        
        Args:
            type_str: Data type string from DM database (e.g., 'VARCHAR2', 'NUMBER')
            
        Returns:
            SQLAlchemy TypeEngine instance
        """
        type_str = type_str.upper()
        
        # Handle VARCHAR/VARCHAR2 with length
        if type_str.startswith('VARCHAR') or type_str.startswith('CHARACTER VARYING'):
            return sqltypes.VARCHAR()
        elif type_str == 'CHAR' or type_str == 'CHARACTER':
            return sqltypes.CHAR()
        elif type_str == 'CLOB':
            return sqltypes.CLOB()
        elif type_str == 'BLOB':
            return sqltypes.BLOB()
        elif type_str == 'TEXT':
            return sqltypes.TEXT()
        # Handle NUMBER/NUMERIC with precision and scale
        elif type_str.startswith('NUMBER') or type_str.startswith('NUMERIC'):
            return sqltypes.NUMERIC()
        elif type_str == 'INTEGER' or type_str == 'INT':
            return sqltypes.INTEGER()
        elif type_str == 'SMALLINT':
            return sqltypes.SMALLINT()
        elif type_str == 'BIGINT':
            return sqltypes.BIGINT()
        elif type_str == 'FLOAT':
            return sqltypes.FLOAT()
        elif type_str == 'DOUBLE PRECISION' or type_str == 'DOUBLE':
            return sqltypes.DOUBLE_PRECISION()
        elif type_str == 'DATE':
            return sqltypes.DATE()
        elif type_str.startswith('TIMESTAMP'):
            return sqltypes.TIMESTAMP()
        elif type_str == 'BOOLEAN' or type_str == 'BOOL':
            return sqltypes.BOOLEAN()
        else:
            # Default to String for unknown types
            return sqltypes.String()

    @classmethod
    def dbapi(cls):
        """Return the DBAPI module."""
        import dmPython
        return dmPython

    def create_connect_args(self, url):
        """Create connection arguments from URL.
        
        dmPython.connect() signature:
        connect(user, password, host, port, ...)
        Note: DM doesn't use 'database' or 'schema' in connection args.
        Schema should be specified in SQL queries as schema.table_name.
        """
        # Extract parameters from URL
        opts = {
            'user': url.username,
            'password': url.password,
            'host': url.host,
            'port': url.port,
        }
        # Add any query parameters
        opts.update(url.query)
        return [], opts

    def initialize(self, connection):
        """Initialize DM dialect."""
        super().initialize(connection)

    def get_table_names(self, connection, schema=None, **kw) -> List[str]:
        """Return list of table names in the database.
        
        DM is compatible with Oracle, use ALL_TABLES system view.
        Note: DM schema names are case-sensitive and should NOT be uppercased.
        """
        if schema:
            query = text(
                "SELECT table_name FROM all_tables WHERE owner = :schema ORDER BY table_name"
            )
            result = connection.execute(query, {"schema": schema})
        else:
            query = text(
                "SELECT table_name FROM all_tables ORDER BY table_name"
            )
            result = connection.execute(query)
        return [row[0] for row in result.fetchall()]

    def get_columns(self, connection, table_name, schema=None, **kw) -> List[Dict[str, Any]]:
        """Return information about columns in the specified table.
        Note: DM schema names are case-sensitive and should NOT be uppercased.
        """
        if schema:
            query = text("""
                SELECT column_name, data_type, nullable, data_default, char_length
                FROM all_tab_columns
                WHERE table_name = :table_name AND owner = :schema
                ORDER BY column_id
            """)
            result = connection.execute(query, {
                "table_name": table_name.upper(),
                "schema": schema
            })
        else:
            query = text("""
                SELECT column_name, data_type, nullable, data_default, char_length
                FROM all_tab_columns
                WHERE table_name = :table_name
                ORDER BY column_id
            """)
            result = connection.execute(query, {"table_name": table_name.upper()})
        
        columns = []
        for row in result.fetchall():
            col_dict = {
                'name': row[0],
                'type': self._type_from_string(row[1]),
                'nullable': row[2] == 'Y',
                'default': row[3],
            }
            columns.append(col_dict)
        return columns

    def get_pk_constraint(self, connection, table_name, schema=None, **kw) -> Dict[str, Any]:
        """Return primary key constraint information.
        Note: DM schema names are case-sensitive and should NOT be uppercased.
        """
        if schema:
            query = text("""
                SELECT cols.column_name
                FROM all_constraints cons
                JOIN all_cons_columns cols ON cons.constraint_name = cols.constraint_name
                WHERE cons.constraint_type = 'P'
                AND cons.table_name = :table_name
                AND cons.owner = :schema
                ORDER BY cols.position
            """)
            result = connection.execute(query, {
                "table_name": table_name.upper(),
                "schema": schema
            })
        else:
            query = text("""
                SELECT cols.column_name
                FROM all_constraints cons
                JOIN all_cons_columns cols ON cons.constraint_name = cols.constraint_name
                WHERE cons.constraint_type = 'P'
                AND cons.table_name = :table_name
                ORDER BY cols.position
            """)
            result = connection.execute(query, {"table_name": table_name.upper()})
        
        pk_columns = [row[0] for row in result.fetchall()]
        return {
            'constrained_columns': pk_columns,
            'name': None
        }

    def get_foreign_keys(self, connection, table_name, schema=None, **kw) -> List[Dict[str, Any]]:
        """Return foreign key information.
        Note: DM schema names are case-sensitive and should NOT be uppercased.
        """
        if schema:
            query = text("""
                SELECT 
                    a.constraint_name,
                    a.column_name,
                    c.r_owner AS referred_schema,
                    c.r_constraint_name,
                    b.table_name AS referred_table,
                    d.column_name AS referred_column
                FROM all_cons_columns a
                JOIN all_constraints c ON a.constraint_name = c.constraint_name
                JOIN all_constraints b ON c.r_constraint_name = b.constraint_name
                JOIN all_cons_columns d ON c.r_constraint_name = d.constraint_name
                WHERE c.constraint_type = 'R'
                AND a.table_name = :table_name
                AND a.owner = :schema
                ORDER BY a.constraint_name, a.position
            """)
            result = connection.execute(query, {
                "table_name": table_name.upper(),
                "schema": schema
            })
        else:
            query = text("""
                SELECT 
                    a.constraint_name,
                    a.column_name,
                    c.r_owner AS referred_schema,
                    c.r_constraint_name,
                    b.table_name AS referred_table,
                    d.column_name AS referred_column
                FROM all_cons_columns a
                JOIN all_constraints c ON a.constraint_name = c.constraint_name
                JOIN all_constraints b ON c.r_constraint_name = b.constraint_name
                JOIN all_cons_columns d ON c.r_constraint_name = d.constraint_name
                WHERE c.constraint_type = 'R'
                AND a.table_name = :table_name
                ORDER BY a.constraint_name, a.position
            """)
            result = connection.execute(query, {"table_name": table_name.upper()})
        
        foreign_keys = {}
        for row in result.fetchall():
            fk_name = row[0]
            if fk_name not in foreign_keys:
                foreign_keys[fk_name] = {
                    'name': fk_name,
                    'constrained_columns': [],
                    'referred_schema': row[2],
                    'referred_table': row[4],
                    'referred_columns': [],
                }
            foreign_keys[fk_name]['constrained_columns'].append(row[1])
            foreign_keys[fk_name]['referred_columns'].append(row[5])
        
        return list(foreign_keys.values())

    def get_indexes(self, connection, table_name, schema=None, **kw) -> List[Dict[str, Any]]:
        """Return index information.
        Note: DM schema names are case-sensitive and should NOT be uppercased.
        """
        if schema:
            query = text("""
                SELECT 
                    i.index_name,
                    i.uniqueness,
                    ic.column_name,
                    ic.column_position
                FROM all_indexes i
                JOIN all_ind_columns ic ON i.index_name = ic.index_name AND i.owner = ic.index_owner
                WHERE i.table_name = :table_name
                AND i.owner = :schema
                AND i.index_name NOT IN (
                    SELECT constraint_name FROM all_constraints 
                    WHERE constraint_type IN ('P', 'U') AND owner = :schema
                )
                ORDER BY i.index_name, ic.column_position
            """)
            result = connection.execute(query, {
                "table_name": table_name.upper(),
                "schema": schema
            })
        else:
            query = text("""
                SELECT 
                    i.index_name,
                    i.uniqueness,
                    ic.column_name,
                    ic.column_position
                FROM all_indexes i
                JOIN all_ind_columns ic ON i.index_name = ic.index_name
                WHERE i.table_name = :table_name
                AND i.index_name NOT IN (
                    SELECT constraint_name FROM all_constraints 
                    WHERE constraint_type IN ('P', 'U')
                )
                ORDER BY i.index_name, ic.column_position
            """)
            result = connection.execute(query, {"table_name": table_name.upper()})
        
        indexes = {}
        for row in result.fetchall():
            idx_name = row[0]
            if idx_name not in indexes:
                indexes[idx_name] = {
                    'name': idx_name,
                    'column_names': [],
                    'unique': row[1] == 'UNIQUE',
                }
            indexes[idx_name]['column_names'].append(row[2])
        
        return list(indexes.values())

    def get_view_names(self, connection, schema=None, **kw) -> List[str]:
        """Return list of view names in the database.
        Note: DM schema names are case-sensitive and should NOT be uppercased.
        """
        if schema:
            query = text(
                "SELECT view_name FROM all_views WHERE owner = :schema ORDER BY view_name"
            )
            result = connection.execute(query, {"schema": schema})
        else:
            query = text(
                "SELECT view_name FROM all_views ORDER BY view_name"
            )
            result = connection.execute(query)
        return [row[0] for row in result.fetchall()]


# Register the dialect with SQLAlchemy
# This allows using 'dm://' URLs
registry.register("dm", __name__, "DMDialect")
