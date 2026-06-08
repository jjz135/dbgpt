# 图表类型支持分析 / Chart Type Support Analysis

## 📊 您展示的图表分析

### 图表1：COMPLETEQTY 时间序列折线图
**特征**：
- 显示2023-12-19至2024-01-24期间的COMPLETEQTY变化
- 标准折线图（Line Chart）
- 有tooltip显示具体数值
- 有两次显著的变化（波动）

**系统支持状态**：✅ **完全支持**

### 图表2：COMPLETEQTY Change Point（变化点）分析
**特征**：
- 标注了关键变化点（2023-12-25: 100, 2024-01-02: 23等）
- 识别数据中的突变/变化点
- 高级时间序列分析功能

**系统支持状态**：⚠️ **部分支持**（需要扩展）

---

## 🎯 当前系统完整支持的图表类型

| 后端类型 | 前端渲染 | 使用场景 | 示例SQL |
|---------|---------|---------|---------|
| `response_line_chart` | 折线图 | ✅ 时间序列趋势 | `SELECT date, SUM(qty) FROM tbl GROUP BY date ORDER BY date` |
| `response_bar_chart` | 柱状图 | ✅ 类别对比 | `SELECT category, SUM(value) FROM tbl GROUP BY category` |
| `response_pie_chart` | 饼图 | ✅ 占比分布 | `SELECT type, COUNT(*) FROM tbl GROUP BY type` |
| `response_area_chart` | 面积图 | ✅ 累积趋势 | `SELECT date, SUM(value) FROM tbl GROUP BY date` |
| `response_scatter_chart` | 散点图 | ✅ 相关性分析 | `SELECT x_value, y_value FROM tbl` |
| `response_heatmap_chart` | 热力图 | ✅ 交叉分析 | `SELECT dim1, dim2, COUNT(*) FROM tbl GROUP BY dim1, dim2` |
| `response_table` | 表格 | ✅ 明细数据 | `SELECT * FROM tbl WHERE ...` |

---

## 🔍 针对您的图表的具体分析

### ✅ 图表1可以直接生成

**生成方法**：
```sql
-- 示例SQL（假设表名为production_data）
SELECT 
    record_date,
    SUM(COMPLETEQTY) as total_qty
FROM production_data
WHERE record_date BETWEEN '2023-12-19' AND '2024-01-24'
GROUP BY record_date
ORDER BY record_date
```

**Agent会自动识别**：
- 看到 `ORDER BY date` → 自动使用 `response_line_chart`
- 生成类似您图中的折线图
- 前端会自动添加tooltip显示具体数值

**提问示例**：
```
分析2023年12月19日到2024年1月24日期间的COMPLETEQTY变化趋势
```

### ⚠️ 图表2需要增强实现

**当前限制**：
- ❌ 系统没有内置的 **Change Point Detection（变化点检测）** 算法
- ❌ 无法自动识别和标注数据中的显著变化点

**可以实现的替代方案**：

#### 方案1：在分析中识别变化点（推荐，快速实现）
通过增强Agent的分析能力，在 `thought` 字段中识别和说明变化点：

```python
# 修改 data_insight_agent.py，添加变化点检测规则
"Rule 4 - Change Point Detection:\n"
"For time series data, identify and highlight significant changes:\n"
"- Compare each point with moving average\n"
"- Flag points with >50% deviation as change points\n"
"- Annotate change points with specific dates and values\n"
"Example: 'Detected 2 major changes: 2023-12-25 (100, +150%), 2024-01-02 (23, -77%)'"
```

#### 方案2：SQL中计算变化率
在SQL查询中计算环比变化，标注显著变化：

```sql
WITH daily_data AS (
    SELECT 
        record_date,
        SUM(COMPLETEQTY) as qty
    FROM production_data
    GROUP BY record_date
),
changes AS (
    SELECT 
        record_date,
        qty,
        LAG(qty) OVER (ORDER BY record_date) as prev_qty,
        (qty - LAG(qty) OVER (ORDER BY record_date)) / 
        NULLIF(LAG(qty) OVER (ORDER BY record_date), 0) * 100 as change_pct
    FROM daily_data
)
SELECT 
    record_date,
    qty,
    change_pct,
    CASE 
        WHEN ABS(change_pct) > 50 THEN 'Change Point'
        ELSE 'Normal'
    END as status
FROM changes
ORDER BY record_date
```

然后标注为 `response_line_chart`，在thought中说明变化点。

#### 方案3：集成专业算法（需要开发）
集成Change Point Detection算法库：

```python
# 需要新增功能模块
from ruptures import Pelt  # 或其他CPD算法

class ChangePointDetectionAction(Action):
    """Change Point Detection for time series."""
    
    async def detect_change_points(self, data):
        # 使用PELT、Binary Segmentation等算法
        model = Pelt(model="rbf").fit(data)
        change_points = model.predict(pen=10)
        return change_points
```

---

## 💡 快速实现建议

### 立即可用的方法（无需修改代码）

**1. 使用折线图 + 详细分析**
提问时明确要求分析变化点：
```
分析COMPLETEQTY在2023-12-19至2024-01-24的变化趋势，
特别标注发生显著变化的日期和变化幅度
```

Agent会生成折线图，并在thought字段中分析：
```
"2023-12-25出现峰值100，较前一天上升150%，疑似异常批次或数据录入错误。
2024-01-02突降至23，下降77%，可能是节假日停产或设备故障。
建议重点排查这两个时间点的生产记录。"
```

**2. 分段查询突变点**
```sql
-- Agent可以自动生成类似查询
SELECT 
    record_date,
    SUM(COMPLETEQTY) as qty,
    LAG(SUM(COMPLETEQTY)) OVER (ORDER BY record_date) as prev_qty
FROM production_data
GROUP BY record_date
HAVING ABS(SUM(COMPLETEQTY) - LAG(SUM(COMPLETEQTY)) OVER (ORDER BY record_date)) > 20
ORDER BY record_date
```

### 需要代码修改的增强（推荐）

我可以为您添加Change Point Detection功能：

**步骤1**：增强 `DataInsightAgent` 的约束
**步骤2**：在 `InsightAction` 中添加变化点检测逻辑
**步骤3**：在thought字段中自动标注变化点

---

## 🎨 前端渲染能力

当前前端支持的折线图功能：
- ✅ 多条折线（multi_line_chart）
- ✅ 多指标折线（multi_measure_line_chart）
- ✅ Tooltip悬浮显示
- ✅ 数据点标注
- ❌ 自动变化点标注（需要开发）

**可以通过前端增强**：
在 `web/components/chart/autoChart/charts/` 中添加变化点标注组件。

---

## 📋 总结

### 您的两个图表支持情况

| 图表 | 基础功能 | 高级功能 | 实现难度 |
|------|---------|---------|---------|
| **图表1：折线图** | ✅ 完全支持 | ✅ 完全支持 | - |
| **图表2：变化点图** | ✅ 折线图支持 | ⚠️ 变化点检测需增强 | 🟡 中等 |

### 建议方案

**立即可用（0开发）**：
1. 使用 `response_line_chart` 生成折线图
2. 在提问时要求分析变化点
3. Agent在thought中识别和说明显著变化

**短期增强（1-2小时开发）**：
1. 在Agent约束中添加变化点检测规则
2. 在SQL中计算环比变化率
3. 自动标注>50%的变化为Change Point

**长期完善（1-2天开发）**：
1. 集成专业CPD算法（ruptures、bayesian-changepoint-detection等）
2. 添加新的图表类型：`response_change_point_chart`
3. 前端添加变化点可视化组件

---

## 🚀 下一步行动

### 您现在就可以做的：

**测试折线图功能**：
```
生成COMPLETEQTY在2023年12月到2024年1月的趋势分析报告，
包括：
1. 每日变化趋势（折线图）
2. 识别出现显著波动的日期
3. 分析波动原因和建议
```

### 需要我帮您实现的：

1. **增强变化点检测**：修改Agent配置，自动识别变化点
2. **添加CPD算法**：集成专业的变化点检测算法
3. **前端可视化增强**：添加变化点标注组件

请告诉我您希望采用哪种方案，我可以立即为您实现！

