import dataclasses
import logging
from typing import Any, List, Optional, Type, Union, cast

from dbgpt._private.config import Config
from dbgpt.agent.resource.database import (
    _DEFAULT_PROMPT_TEMPLATE,
    _DEFAULT_PROMPT_TEMPLATE_ZH,
    DBParameters,
    RDBMSConnectorResource,
)
from dbgpt.core.awel.flow import (
    TAGS_ORDER_HIGH,
    FunctionDynamicOptions,
    OptionValue,
    Parameter,
    ResourceCategory,
    register_resource,
)
from dbgpt.util import ParameterDescription
from dbgpt.util.i18n_utils import _

CFG = Config()

logger = logging.getLogger(__name__)


def _load_datasource() -> List[OptionValue]:
    dbs = CFG.local_db_manager.get_db_list()
    results = [
        OptionValue(
            label="[" + db["db_type"] + "]" + db["db_name"],
            name=db["db_name"],
            value=db["db_name"],
        )
        for db in dbs
    ]
    return results


@dataclasses.dataclass
class DatasourceDBParameters(DBParameters):
    """The DB parameters for the datasource."""

    db_name: str = dataclasses.field(metadata={"help": "DB name"})

    @classmethod
    def _resource_version(cls) -> str:
        """Return the resource version."""
        return "v1"

    @classmethod
    def to_configurations(
        cls,
        parameters: Type["DatasourceDBParameters"],
        version: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Convert the parameters to configurations."""
        conf: List[ParameterDescription] = cast(
            List[ParameterDescription],
            super().to_configurations(
                parameters,
                **kwargs,
            ),
        )
        version = version or cls._resource_version()
        if version != "v1":
            return conf
        # Compatible with old version
        for param in conf:
            if param.param_name == "db_name":
                return param.valid_values or []
        return []

    @classmethod
    def from_dict(
        cls, data: dict, ignore_extra_fields: bool = True
    ) -> "DatasourceDBParameters":
        """Create a new instance from a dictionary."""
        copied_data = data.copy()
        if "db_name" not in copied_data and "value" in copied_data:
            copied_data["db_name"] = copied_data.pop("value")
        return super().from_dict(copied_data, ignore_extra_fields=ignore_extra_fields)


@register_resource(
    _("Datasource Resource"),
    "datasource",
    category=ResourceCategory.DATABASE,
    description=_(
        "Connect to a datasource(retrieve table schemas and execute SQL to fetch data)."
    ),
    tags={"order": TAGS_ORDER_HIGH},
    parameters=[
        Parameter.build_from(
            _("Datasource Name"),
            "name",
            str,
            optional=True,
            default="datasource",
            description=_("The name of the datasource, default is 'datasource'."),
        ),
        Parameter.build_from(
            _("DB Name"),
            "db_name",
            str,
            description=_("The name of the database."),
            options=FunctionDynamicOptions(func=_load_datasource),
        ),
        Parameter.build_from(
            _("Prompt Template"),
            "prompt_template",
            str,
            optional=True,
            default=(
                _DEFAULT_PROMPT_TEMPLATE_ZH
                if CFG.LANGUAGE == "zh"
                else _DEFAULT_PROMPT_TEMPLATE
            ),
            description=_("The prompt template to build a database prompt."),
        ),
    ],
)
class DatasourceResource(RDBMSConnectorResource):
    def __init__(self, name: str, db_name: Optional[str] = None, **kwargs):
        conn = CFG.local_db_manager.get_connector(db_name)
        super().__init__(name, connector=conn, db_name=db_name, **kwargs)

    @classmethod
    def resource_parameters_class(cls, **kwargs) -> Type[DatasourceDBParameters]:
        dbs = CFG.local_db_manager.get_db_list(user_id=kwargs.get("user_id", None))
        results = [
            {
                "label": "[" + db["db_type"] + "]" + db["db_name"],
                "key": db["db_name"],
                "description": db["comment"],
            }
            for db in dbs
        ]

        @dataclasses.dataclass
        class _DynDBParameters(DatasourceDBParameters):
            db_name: str = dataclasses.field(
                metadata={"help": "DB name", "valid_values": results}
            )

        return _DynDBParameters

    def get_schema_link(
        self, db: str, question: Optional[str] = None
    ) -> Union[str, List[str]]:
        """Return the schema link of the database."""
        logger.info(f" DatasourceResource.get_schema_link 被调用: db={db}, question={question}")
        
        try:
            from dbgpt_serve.datasource.service.db_summary_client import DBSummaryClient
        except ImportError:
            raise ValueError("Could not import DBSummaryClient. ")
        
        client = DBSummaryClient(system_app=CFG.SYSTEM_APP)
        table_infos = None
        
        try:
            logger.info(f"调用 DBSummaryClient.get_db_summary: db={db}, topk={CFG.KNOWLEDGE_SEARCH_TOP_SIZE}")
            table_infos = client.get_db_summary(
                db,
                question,
                CFG.KNOWLEDGE_SEARCH_TOP_SIZE,
            )
            
            if table_infos:
                logger.info(f"DBSummaryClient 返回了 {len(table_infos)} 个表结构")
                # 记录前几个结果的格式
                for i, info in enumerate(table_infos[:3]):
                    if "表名:" in str(info):
                        logger.info(f" 结果 {i+1}: 智能注释格式 - {str(info)[:100]}...")
                    else:
                        logger.info(f" 结果 {i+1}: 原始格式 - {str(info)[:100]}...")
            else:
                logger.warning("DBSummaryClient 返回了空结果")
                
        except Exception as e:
            logger.warning(f" db summary find error!{str(e)}")
            import traceback
            logger.warning(f"详细错误信息: {traceback.format_exc()}")
        
        if not table_infos:
            logger.info("回退到原始数据库连接器获取表结构")
            conn = CFG.local_db_manager.get_connector(db)
            table_infos = conn.table_simple_info()
            logger.info(f"原始连接器返回了 {len(table_infos)} 个表结构")

        #  格式化：每个表结构单独一行，提高可读性
        if isinstance(table_infos, list):
            # 将列表转换为字符串，每个表之间用换行符分隔
            formatted_schemas = "\n".join(str(info) for info in table_infos)
            logger.info(f"格式化后的表结构长度: {len(formatted_schemas)} 字符")
            return formatted_schemas
        
        return table_infos
