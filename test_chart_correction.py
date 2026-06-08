"""Test chart type correction logic."""

import pandas as pd
from dbgpt.agent.expand.actions.reporter_action import ReporterAction


def test_chart_type_correction():
    """Test the chart type correction logic."""
    
    # Create a mock action instance
    action = ReporterAction()
    
    # Test case 1: Proportion analysis should use pie chart
    print("Test 1: Proportion analysis")
    sql1 = """
    SELECT w.workshop_name AS 车间名称, 
           SUM(e.consumption_value * en.carbon_emission_factor) AS 碳排放量 
    FROM fact_energy_consumption e 
    JOIN dim_equipment eq ON e.equipment_id = eq.equipment_id 
    JOIN dim_energy_type en ON e.energy_id = en.energy_id 
    JOIN dim_workshop w ON eq.workshop_id = w.workshop_id 
    WHERE DATE(e.collect_time) = '2026-05-08' 
    GROUP BY w.workshop_id, w.workshop_name
    """
    
    # Mock data with 2 columns (category + value)
    data1 = pd.DataFrame({
        '车间名称': ['一车间', '二车间', '三车间', '四车间', '动力中心'],
        '碳排放量': [250.5537, 207.4267, 21.9566, 359.2890, 259.4865]
    })
    
    title1 = "各车间昨日碳排放量汇总（吨CO₂e）"
    description1 = "分析各车间碳排放占比情况"
    
    corrected1 = action._correct_chart_type(
        sql=sql1,
        current_type='response_table',
        data_df=data1,
        title=title1,
        description=description1
    )
    
    print(f"  Original type: response_table")
    print(f"  Corrected type: {corrected1}")
    print(f"  Expected: response_pie_chart")
    print(f"  Result: {'✓ PASS' if corrected1 == 'response_pie_chart' else '✗ FAIL'}")
    print()
    
    # Test case 2: Aggregated data without time dimension should use bar chart
    print("Test 2: Aggregated comparison")
    sql2 = """
    SELECT product_category, SUM(sales_amount) as total_sales
    FROM sales_data
    GROUP BY product_category
    """
    
    data2 = pd.DataFrame({
        'product_category': ['Electronics', 'Clothing', 'Food'],
        'total_sales': [100000, 75000, 50000]
    })
    
    corrected2 = action._correct_chart_type(
        sql=sql2,
        current_type='response_table',
        data_df=data2,
        title="Sales by Category",
        description="Compare sales across categories"
    )
    
    print(f"  Original type: response_table")
    print(f"  Corrected type: {corrected2}")
    print(f"  Expected: response_bar_chart")
    print(f"  Result: {'✓ PASS' if corrected2 == 'response_bar_chart' else '✗ FAIL'}")
    print()
    
    # Test case 3: Time series data should use line chart
    print("Test 3: Time series data")
    sql3 = """
    SELECT DATE(collect_time) as date, SUM(consumption) as total
    FROM energy_data
    GROUP BY DATE(collect_time)
    ORDER BY date
    """
    
    data3 = pd.DataFrame({
        'date': ['2026-05-01', '2026-05-02', '2026-05-03'],
        'total': [100, 120, 115]
    })
    
    corrected3 = action._correct_chart_type(
        sql=sql3,
        current_type='response_table',
        data_df=data3,
        title="Daily Energy Consumption",
        description="Trend over time"
    )
    
    print(f"  Original type: response_table")
    print(f"  Corrected type: {corrected3}")
    print(f"  Expected: response_line_chart")
    print(f"  Result: {'✓ PASS' if corrected3 == 'response_line_chart' else '✗ FAIL'}")
    print()
    
    # Test case 4: No correction needed
    print("Test 4: Already correct chart type")
    corrected4 = action._correct_chart_type(
        sql=sql1,
        current_type='response_pie_chart',
        data_df=data1,
        title=title1,
        description=description1
    )
    
    print(f"  Original type: response_pie_chart")
    print(f"  Corrected type: {corrected4}")
    print(f"  Expected: response_pie_chart (no change)")
    print(f"  Result: {'✓ PASS' if corrected4 == 'response_pie_chart' else '✗ FAIL'}")
    print()


if __name__ == '__main__':
    print("=" * 60)
    print("Chart Type Correction Test")
    print("=" * 60)
    print()
    
    test_chart_type_correction()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
