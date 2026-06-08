# DataInsight Agent 可视化与分析增强 / DataInsight Agent Visualization & Analysis Enhancements

## 更新日期 / Update Date: 2025-12-09

## 概述 / Overview

本次更新大幅增强了 **DataInsight Agent (Visionary)** 的数据可视化能力和分析深度，主要改进包括：
1. 生成更多、更复杂的图表（多维度分析）
2. 提供更深入的数据分析内容
3. 简化日志显示，减少冗余输出

---

## 主要改进 / Key Improvements

### 1. 增强的可视化要求 / Enhanced Visualization Requirements

#### 图表数量提升
- **之前**: 最低60%的查询生成图表
- **现在**: 最低75%的查询生成图表，且每个报告必须包含5-8个可视化

#### 多维度分析 / Multi-Dimensional Analysis
能源报告场景现在必须包含以下8个分析维度：

| 维度 | 图表类型 | 说明 |
|------|---------|------|
| 整体总量对比 | Bar Chart | 各产线/车间总能耗对比 |
| 结构占比分析 | Pie Chart | 能源类型分布（电/水/气） |
| TOP排名 | Bar Chart | TOP5高耗能实体 |
| 单一能源对比 | Bar Chart | 各产线电耗对比 |
| 单一能源TOP | Bar Chart | TOP5高电耗产线 |
| 时间趋势 | Line Chart | 能耗时序变化（如有时间字段） |
| 效率分析 | Bar Chart | 单位产量能耗 |
| 异常检测 | Bar Chart | 超标实体识别 |

#### 强制图表类型规则 / Mandatory Chart Type Rules
```
✓ GROUP BY + SUM/COUNT/AVG     → response_bar_chart (强制)
✓ GROUP BY + 比例/占比          → response_pie_chart (强制)
✓ ORDER BY date/time          → response_line_chart (强制)
✗ response_table              → 仅限明细查询（>6列且无GROUP BY）
```

### 2. 深度数据分析 / Deep Data Analysis

#### thought字段增强
每个可视化的 `thought` 字段现在必须包含以下全部要素：

| 要素 | 要求 | 示例 |
|------|------|------|
| **核心数值** | 最大值、最小值、平均值、总和 | "总能耗范围17.1-42.2kWh，平均28.5" |
| **对比分析** | 倍数关系、超标情况、异常值 | "PL001是PL003的2.5倍，超平均48%" |
| **占比分析** | 主要占比、次要占比、集中度 | "电能占比78%，水耗15%，燃气7%" |
| **趋势判断** | 上升/下降、波动、拐点 | "近3天能耗持续上升，增幅12%" |
| **异常检测** | 超出2倍标准差的异常值 | "PL001和PL002超标(μ+2σ=35.2)" |
| **优化建议** | ≥3条具体可执行的改进措施 | "1.排查PL001设备故障(预计节能15%)；2.推广PL003节能模式；3.峰谷电价优化" |

#### 禁止技术术语
❌ 禁止: "按产线分组统计...属GROUP BY + SUM → 必须用bar_chart..."
✅ 正确: "产线PL001总能耗42.2kWh最高，超出平均值28.5的48%，是PL003的2.5倍。建议优先排查设备异常。"

### 3. 日志简化 / Log Simplification

#### Agent消息日志优化
- **默认模式（verbose=False）**: 只显示关键Action状态
  ```
  [DataCollector → Visionary] Action ✓ (success)
  ```

- **详细模式（verbose=True）**: 显示完整消息内容（用于调试）
  ```
  --------------------------------------------------------------------------------
  DataCollector (to Visionary)-[gpt-4]:
  
  {"role": "assistant", "content": "[{\"title\":\"...\", ...}]", ...}
  
  >>>>>>>>DataCollector Action report: 
  execution succeeded,
  {"charts": [...], "data": [...]}
  
  --------------------------------------------------------------------------------
  ```

#### 日志级别控制
通过环境变量 `DBGPT_LOG_LEVEL` 控制日志详细程度：
- **生产环境**: `DBGPT_LOG_LEVEL=WARNING`
- **开发环境**: `DBGPT_LOG_LEVEL=INFO`
- **调试模式**: `DBGPT_LOG_LEVEL=DEBUG`

---

## 修改的文件 / Modified Files

### 1. 核心Agent配置
**文件**: `packages/dbgpt-core/src/dbgpt/agent/expand/data_insight_agent.py`

**改动**:
- 提升图表比例要求：60% → 75%
- 强制生成5-8个可视化（多维度分析）
- 增强thought字段要求（6大要素）
- 添加能源报告场景的8个必须维度
- 优化图表类型选择规则

### 2. Action定义
**文件**: `packages/dbgpt-core/src/dbgpt/agent/expand/actions/insight_action.py`

**改动**:
- 更新 `thought` 字段描述，要求深度业务分析
- 明确禁止技术术语，要求业务价值导向
- 细化分析要素：核心数值、对比、占比、趋势、异常、建议

### 3. 日志系统优化
**文件**: `packages/dbgpt-core/src/dbgpt/agent/core/base_agent.py`

**改动**:
- 修改 `_print_received_message` 方法
- 根据 `verbose` 参数决定日志详细程度
- 默认只显示Action状态，减少冗余输出

### 4. 新增文档
- **`docs/LOG_SIMPLIFICATION_CONFIG.md`**: 日志简化配置详细说明
- **`AGENT_VISUALIZATION_IMPROVEMENTS.md`**: 本文档

---

## 使用方法 / How to Use

### 1. 重启后端服务
```bash
# 停止当前服务
# Ctrl+C

# 重新启动
python dbgpt_server.py
```

### 2. 测试增强的可视化
提问示例：
```
生成能源消耗报告，分析各产线的能耗情况
```

预期结果：
- ✓ 5-8个不同维度的图表
- ✓ 75%以上为图表（bar/pie/line）
- ✓ 每个图表都有深度分析（包含具体数值、对比、异常、建议）
- ✓ 日志输出简洁（只显示关键状态）

### 3. 调整日志详细程度
在 `.env` 文件中配置：
```bash
# 简化日志（生产环境推荐）
DBGPT_LOG_LEVEL=WARNING

# 详细日志（开发调试）
DBGPT_LOG_LEVEL=DEBUG
```

或在代码中设置verbose：
```python
agent_context = AgentContext(
    conv_id="your_conv_id",
    verbose=True  # 启用详细日志
)
```

---

## 验证要点 / Validation Checklist

重启服务后测试时，请验证以下要点：

- [ ] 图表数量：每个报告包含5-8个可视化
- [ ] 图表比例：≥75%为图表类型（bar/pie/line）
- [ ] 多维度分析：包含总量、占比、TOP、趋势等多个角度
- [ ] 聚合查询：所有 GROUP BY + SUM/COUNT/AVG 都使用bar_chart或pie_chart
- [ ] 深度分析：thought字段包含具体数值、对比、异常、建议
- [ ] 无技术术语：thought不包含"GROUP BY"、"bar_chart"等技术词汇
- [ ] 日志简化：控制台日志简洁，只显示关键状态（verbose=False时）

---

## 预期效果对比 / Before/After Comparison

### 之前的输出 / Before
```json
[
  {
    "title": "产线能耗统计",
    "display_type": "response_table",  // ❌ 聚合查询使用了table
    "sql": "SELECT line, SUM(energy) FROM energy GROUP BY line",
    "thought": "按产线分组统计总能耗，属GROUP BY + SUM，应使用bar_chart"  // ❌ 技术说明
  }
]
```
- 只有2-3个可视化
- 大量使用 `response_table`
- thought字段是技术解释
- 日志冗长重复

### 现在的输出 / After
```json
[
  {
    "title": "各产线总能耗对比",
    "display_type": "response_bar_chart",  // ✓ 使用图表
    "sql": "SELECT line, SUM(electricity+water+gas) total FROM energy GROUP BY line",
    "thought": "产线总能耗范围17.1-42.2kWh，平均28.5。PL001最高42.2占比32%，是PL003(17.1)的2.5倍，超平均48%。PL001和PL002超标(μ+2σ=35.2)。建议：1.立即排查PL001设备故障(预计节能15%)；2.推广PL003节能模式(预计节能10%)；3.实施峰谷电价优化(预计降本8%)"  // ✓ 深度业务分析
  },
  {
    "title": "能源类型占比分析",
    "display_type": "response_pie_chart",
    "sql": "SELECT '电' type, SUM(electricity) val UNION SELECT '水', SUM(water) ...",
    "thought": "电能301.2kWh占总能耗78%，水耗18.6吨(15%)，燃气27.4(7%)。电能主导，建议：1.峰谷电价优化；2.余热回收降低燃气；3.循环水系统节水"
  },
  // ... 5-8个图表，涵盖多个分析维度
]
```
- 5-8个多维度可视化
- 75%以上为图表
- thought字段是深度业务分析（含数值、对比、建议）
- 日志简洁：`[DataCollector → Visionary] Action ✓ (success)`

---

## 故障排查 / Troubleshooting

### 问题1：图表数量仍然不足
**解决方案**:
1. 检查后端是否重启
2. 清除conversation历史，重新提问
3. 使用更明确的提问：`生成多维度能源分析报告，包括总量对比、占比分析、TOP排名、趋势分析`

### 问题2：thought字段仍然是技术说明
**解决方案**:
1. 确认 `insight_action.py` 和 `data_insight_agent.py` 已更新
2. 重启后端服务
3. 如果使用缓存的模型，清除缓存

### 问题3：日志仍然很冗长
**解决方案**:
1. 检查 `.env` 文件中的 `DBGPT_LOG_LEVEL` 设置
2. 确认 `base_agent.py` 已更新
3. 重启后端服务
4. 在 `.env` 中设置: `DBGPT_LOG_LEVEL=WARNING`

### 问题4：需要查看详细日志进行调试
**解决方案**:
设置 `verbose=True` 或 `DBGPT_LOG_LEVEL=DEBUG`，然后查看完整输出

---

## 进一步优化建议 / Future Enhancements

1. **前端可视化增强**: 为复杂图表添加交互功能（钻取、筛选）
2. **自动异常检测**: 基于统计模型自动标注异常数据点
3. **趋势预测**: 对时序数据进行预测分析
4. **对比分析**: 支持同比、环比自动计算
5. **导出功能**: 支持将报告导出为PDF/Excel

---

## 相关文档 / Related Documentation

- [日志简化配置说明](docs/LOG_SIMPLIFICATION_CONFIG.md)
- [Observability文档](docs/docs/application/advanced_tutorial/observability.md)
- [Agent开发指南](docs/docs/agents/)

---

## 贡献者 / Contributors

本次更新由AI Assistant完成，基于用户反馈持续优化。

## 许可证 / License

遵循DB-GPT项目的原始许可证。

