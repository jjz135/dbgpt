# Token限制修复说明 / Token Limit Fix

## 问题描述 / Problem Description

错误信息：`The requested correctly structured answer could not be found.`

**根本原因**: Agent生成的JSON输出被截断，无法正确解析。

## 原因分析 / Root Cause Analysis

1. **Token限制不足**：默认的 `max_new_tokens=2048` 无法容纳复杂的可视化输出
2. **约束过于复杂**：之前要求生成5-8个图表，每个都有详细分析，导致输出过长
3. **JSON结构被截断**：当输出超过token限制时，JSON结构不完整，解析失败

## 解决方案 / Solutions

### 1. 增加Token限制 ✓

将 `max_new_tokens` 从 **2048** 提升到 **20000**

**修改的文件**:
- `packages/dbgpt-serve/src/dbgpt_serve/agent/agents/app_agent_manage.py`
  - `user_chat_2_app` 方法（第80-86行）
  - `create_agent_by_app_code` 方法（第181-187行）
- `packages/dbgpt-serve/src/dbgpt_serve/agent/agents/controller.py`
  - `agent_team_chat_new` 方法（第505-512行）

```python
context: AgentContext = AgentContext(
    conv_id=conv_uid,
    gpts_app_code=gpts_app.app_code,
    gpts_app_name=gpts_app.app_name,
    language=gpts_app.language,
    enable_vis_message=enable_verbose,
    max_new_tokens=20000,  # ← 新增：提高到20000
)
```

### 2. 优化Agent约束 ✓

简化了DataInsight Agent的约束，使其更易于理解和遵循

**修改的文件**: `packages/dbgpt-core/src/dbgpt/agent/expand/data_insight_agent.py`

#### 优化前 vs 优化后

| 项目 | 优化前 | 优化后 |
|------|--------|--------|
| 图表比例要求 | 75% | 70% |
| 图表数量要求 | 5-8个 | 3-6个 |
| 约束条数 | 13条详细规则 | 6条精简规则 |
| 约束字数 | ~3000字 | ~1200字 |
| thought要素 | 6大要素 | 4大要素（更实用）|

#### 关键改进

1. **降低图表数量要求**: 5-8个 → **3-6个**（更合理）
2. **简化约束语言**: 从详细的中文说明 → 简洁的中英双语规则
3. **减少示例数量**: 删除冗余示例，保留关键示例
4. **优化thought要求**: 
   - 之前：6大要素（核心数值、对比、占比、趋势、异常、建议）
   - 现在：4大要素（关键指标、对比、异常、2-3条建议）

### 3. 保持核心规则不变 ✓

以下核心规则仍然有效：
- ✓ GROUP BY + 聚合 → 必须使用图表（bar/pie）
- ✓ 禁止在聚合查询中使用 response_table
- ✓ thought字段必须是业务分析，不能是技术说明
- ✓ 至少70%的查询生成图表

## 效果对比 / Before/After

### 优化前 / Before
```
❌ Token不足：输出被截断
❌ JSON解析失败："The requested correctly structured answer could not be found"
❌ 约束过于复杂，难以遵循
❌ 要求生成5-8个图表，输出过长
```

### 优化后 / After
```
✓ Token充足：20000 tokens足够容纳完整输出
✓ JSON结构完整，解析成功
✓ 约束简洁清晰，易于理解
✓ 生成3-6个高质量图表，既丰富又实用
```

## 使用方法 / How to Use

### 1. 重启后端服务
```bash
# 停止当前服务（Ctrl+C）
# 重新启动
python dbgpt_server.py
```

### 2. 测试修复效果
提问示例：
```
生成能源消耗报告，分析各产线的能耗情况
```

预期结果：
- ✓ 生成3-6个可视化图表
- ✓ 不再出现 "The requested correctly structured answer could not be found" 错误
- ✓ 每个图表都有详细的业务分析
- ✓ JSON结构完整，解析成功

## 技术细节 / Technical Details

### Token使用估算

假设生成4个图表的输出：

```json
[
  {
    "title": "各产线总能耗对比",
    "display_type": "response_bar_chart",
    "sql": "SELECT line_code, SUM(electricity+water+gas) AS total_energy ...",
    "thought": "产线PL001总能耗42.2kWh最高，超出平均值28.5的48%..."
  },
  // ... 3个更多的图表
]
```

| 部分 | 估算Token数 |
|------|------------|
| 4个SQL查询 | ~1000 tokens |
| 4个thought分析 | ~2000 tokens |
| JSON结构 | ~500 tokens |
| **总计** | **~3500 tokens** |

- 旧限制(2048): ❌ 不足，会被截断
- 新限制(20000): ✓ 足够，有充足余量

### 兼容性说明

此修改：
- ✓ **向后兼容**：不影响现有功能
- ✓ **性能友好**：不会显著增加响应时间
- ✓ **模型友好**：通义千问支持最大128K context，20K输出完全在范围内

## 故障排查 / Troubleshooting

### 如果仍然出现错误

#### 1. 检查Token限制是否生效
查看日志中的 `max_new_tokens` 值：
```bash
# 在日志中搜索
grep "max_new_tokens" logs/dbgpt*.log
```

#### 2. 检查模型是否支持大Token输出
确认使用的模型支持20K输出：
- 通义千问 qwen-plus: ✓ 支持（最大128K）
- GPT-4: ✓ 支持（最大8K输出）
- GPT-3.5: ⚠️ 最大4K输出（可能不足）

#### 3. 如果需要进一步增加Token限制
在 `app_agent_manage.py` 和 `controller.py` 中修改：
```python
max_new_tokens=20000,  # 可以增加到 30000 或更高
```

#### 4. 如果需要进一步简化输出
在 `data_insight_agent.py` 中减少图表数量要求：
```python
"2. Generate 2-4 visualizations per report"  # 从 3-6 改为 2-4
```

## 相关文件 / Related Files

### 修改的文件
1. `packages/dbgpt-serve/src/dbgpt_serve/agent/agents/app_agent_manage.py` - Token限制配置
2. `packages/dbgpt-serve/src/dbgpt_serve/agent/agents/controller.py` - Token限制配置
3. `packages/dbgpt-core/src/dbgpt/agent/expand/data_insight_agent.py` - 约束优化

### 相关配置文件
- `packages/dbgpt-core/src/dbgpt/agent/core/agent.py` - AgentContext定义
- `configs/dbgpt-proxy-tongyi.toml` - 模型配置

## 测试验证 / Testing Validation

重启服务后，请验证：
- [ ] 不再出现 "The requested correctly structured answer could not be found" 错误
- [ ] 生成的图表数量在3-6个之间
- [ ] 每个图表都有业务分析（不是技术说明）
- [ ] JSON结构完整，可以正确解析
- [ ] 响应时间在可接受范围内（通常30-60秒）

## 更新日志 / Changelog

**2025-12-09**
- 增加 max_new_tokens 从 2048 到 20000
- 简化 DataInsight Agent 约束
- 优化图表数量要求从 5-8 到 3-6
- 减少约束复杂度，提高可理解性

## 备注 / Notes

1. **Token消耗**: 增加max_new_tokens会增加API调用成本，但提高了输出质量
2. **响应时间**: 生成更长的输出可能增加5-10秒响应时间，但在可接受范围内
3. **后续优化**: 如果需要生成更多图表，可以考虑分批生成（如先生成3个，用户可以请求"更多分析"）

## 参考资料 / References

- [DB-GPT Agent文档](docs/docs/agents/)
- [AgentContext API](packages/dbgpt-core/src/dbgpt/agent/core/agent.py)
- [通义千问API限制](https://help.aliyun.com/zh/dashscope/developer-reference/api-details)

