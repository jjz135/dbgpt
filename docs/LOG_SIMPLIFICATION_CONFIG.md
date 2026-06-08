# 日志简化配置说明 / Log Simplification Configuration

## 概述 / Overview

DB-GPT提供多种方式来简化和控制日志输出，减少冗余信息，提高可读性。

## 1. Agent消息日志简化 / Agent Message Log Simplification

### 默认行为 / Default Behavior
- 默认情况下，Agent消息日志已简化（`verbose=False`）
- 只显示关键的Action状态转换：`[Sender → Receiver] Action ✓/✗ (success/failed)`
- 不显示完整的消息内容和中间步骤细节

### 启用详细日志 / Enable Verbose Logging
如果需要查看完整的调试信息，可以设置 `verbose=True`：

#### 方法1：在AgentContext中设置
```python
from dbgpt.agent.core.agent import AgentContext

agent_context = AgentContext(
    conv_id="your_conversation_id",
    verbose=True  # 启用详细日志
)
```

#### 方法2：在环境变量中设置
```bash
# 在.env文件中添加
AGENT_VERBOSE=true
```

## 2. Python日志级别控制 / Python Logging Level Control

### 调整日志级别
通过环境变量 `DBGPT_LOG_LEVEL` 控制Python日志输出级别：

```bash
# 在.env文件中设置
DBGPT_LOG_LEVEL=WARNING  # 只显示WARNING及以上级别的日志

# 可选值：
# - FATAL: 只显示严重错误
# - ERROR: 显示错误信息
# - WARNING: 显示警告信息（推荐用于生产环境）
# - INFO: 显示一般信息（默认）
# - DEBUG: 显示调试信息（最详细）
# - NOTSET: 不设置级别
```

### 推荐配置 / Recommended Configuration

#### 开发环境 / Development
```bash
DBGPT_LOG_LEVEL=INFO
# 或者启用verbose模式查看完整agent消息
```

#### 生产环境 / Production
```bash
DBGPT_LOG_LEVEL=WARNING
# 保持verbose=False（默认）
```

## 3. 特定Logger控制 / Specific Logger Control

### 禁用特定模块的日志
在代码中设置特定logger的级别：

```python
import logging

# 禁用SQLAlchemy的详细日志
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

# 禁用httpx的详细日志
logging.getLogger('httpx').setLevel(logging.WARNING)

# 禁用特定agent的日志
logging.getLogger('dbgpt.agent.expand.data_insight_agent').setLevel(logging.WARNING)
```

## 4. 前端日志显示优化 / Frontend Log Display Optimization

前端会自动过滤和优化显示的消息：
- 只显示最终结果和关键状态
- 中间步骤会被折叠或隐藏
- Action报告会以简洁格式显示

## 5. 日志简化效果对比 / Before/After Comparison

### 简化前（verbose=True）
```
--------------------------------------------------------------------------------
DataCollector (to Visionary)-[gpt-4]:

{"role": "assistant", "content": "[{\"title\":\"...\", \"sql\":\"...\", ...}]", ...}

>>>>>>>>DataCollector Action report: 
execution succeeded,
{"charts": [...], "data": [...]}

--------------------------------------------------------------------------------
```

### 简化后（verbose=False，默认）
```
[DataCollector → Visionary] Action ✓ (success)
```

## 6. 故障排查 / Troubleshooting

如果需要调试问题：
1. 临时启用verbose模式查看完整消息
2. 将DBGPT_LOG_LEVEL设置为DEBUG
3. 检查logs目录下的日志文件获取历史记录

## 7. 最佳实践 / Best Practices

1. **生产环境**：保持verbose=False，设置DBGPT_LOG_LEVEL=WARNING
2. **开发调试**：临时启用verbose=True，设置DBGPT_LOG_LEVEL=DEBUG
3. **性能优化**：减少日志输出可以提高系统性能
4. **问题诊断**：遇到问题时，优先查看ERROR和WARNING级别的日志

## 8. 相关文件 / Related Files

- Agent消息打印逻辑：`packages/dbgpt-core/src/dbgpt/agent/core/base_agent.py`
- 日志配置：`packages/dbgpt-core/src/dbgpt/util/utils.py`
- AgentContext定义：`packages/dbgpt-core/src/dbgpt/agent/core/agent.py`

## 9. 更新日志 / Changelog

- **2025-12-09**: 实现了基于verbose参数的Agent消息日志简化
  - 默认模式下只显示Action状态
  - verbose=True时显示完整消息内容
  - 大幅减少日志冗余和重复

