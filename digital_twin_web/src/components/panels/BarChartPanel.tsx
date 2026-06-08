import clsx from 'clsx';
import ReactECharts from 'echarts-for-react';

interface BarChartSeries {
  name: string;
  data: number[];
  color: string;
  type?: 'bar' | 'line';
}

interface BarChartPanelProps {
  title: string;
  categories: string[];
  series: BarChartSeries[];
  className?: string;
}

const BarChartPanel = ({ title, categories, series, className }: BarChartPanelProps) => {
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(7, 19, 41, 0.8)',
      borderColor: 'rgba(78, 176, 255, 0.3)',
      textStyle: { color: '#d8efff' },
    },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: 'rgba(180, 218, 246, 0.7)' },
    },
    grid: {
      left: 12,
      right: 12,
      top: 36,
      bottom: 18,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: {
        lineStyle: { color: 'rgba(255,255,255,0.1)' },
      },
      axisLabel: {
        color: 'rgba(180, 218, 246, 0.6)',
        fontSize: 11,
      },
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: { color: 'rgba(255,255,255,0.06)' },
      },
      axisLabel: {
        color: 'rgba(180, 218, 246, 0.6)',
        fontSize: 11,
      },
    },
    series: series.map((item) => ({
      name: item.name,
      type: item.type || 'bar',
      data: item.data,
      smooth: item.type === 'line',
      symbol: item.type === 'line' ? 'none' : undefined,
      barMaxWidth: item.type !== 'line' ? 18 : undefined,
      lineStyle: item.type === 'line' ? { color: item.color, width: 2 } : undefined,
      itemStyle: {
        color: item.color,
        borderRadius: item.type === 'line' ? undefined : [4, 4, 0, 0],
      },
      areaStyle: item.type === 'line' ? { color: `${item.color}22` } : undefined,
    })),
  };

  return (
    <section className={clsx('panel-card', 'panel-card--stretch', className)} style={{ minHeight: 168 }}>
      <div className='panel-card__heading'>
        <span className='panel-card__line' />
        <h3>{title}</h3>
      </div>
      <div style={{ flex: 1, minHeight: 0, marginTop: 10 }}>
        <ReactECharts option={option} style={{ width: '100%', height: '100%' }} notMerge lazyUpdate />
      </div>
    </section>
  );
};

export default BarChartPanel;
