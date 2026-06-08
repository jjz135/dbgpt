import ReactECharts from 'echarts-for-react';

import type { TrendPoint, TrendSeriesConfig } from '@/mock/realtime';

interface TrendPanelProps {
  title: string;
  trends: TrendPoint[];
  seriesConfig: TrendSeriesConfig[];
}

const TrendPanel = ({ title, trends, seriesConfig }: TrendPanelProps) => {
  const hasSecondYAxis = seriesConfig.some((s) => s.yAxisIndex === 1);

  const trendOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(7, 19, 41, 0.8)',
      borderColor: 'rgba(78, 176, 255, 0.3)',
      textStyle: {
        color: '#d8efff',
      },
    },
    grid: {
      left: 10,
      right: 10,
      top: 36,
      bottom: 20,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: trends.map((point) => point.label),
      axisLine: {
        lineStyle: {
          color: 'rgba(255,255,255,0.1)',
        },
      },
      axisLabel: {
        color: 'rgba(180, 218, 246, 0.6)',
      },
    },
    yAxis: [
      {
        type: 'value',
        splitLine: {
          lineStyle: {
            color: 'rgba(255,255,255,0.06)',
          },
        },
        axisLabel: {
          color: 'rgba(180, 218, 246, 0.6)',
        },
      },
      ...(hasSecondYAxis
        ? [
            {
              type: 'value',
              splitLine: { show: false },
              axisLabel: { color: 'rgba(180, 218, 246, 0.6)' },
            },
          ]
        : []),
    ],
    legend: {
      top: 0,
      right: 0,
      textStyle: {
        color: 'rgba(180, 218, 246, 0.7)',
      },
    },
    series: seriesConfig.map((cfg) => {
      const base: Record<string, unknown> = {
        name: cfg.name,
        type: cfg.type,
        smooth: cfg.type === 'line',
        symbol: cfg.type === 'line' ? 'none' : undefined,
        data: trends.map((point) => point.values[cfg.key] ?? 0),
        lineStyle: cfg.type === 'line' ? { color: cfg.color, width: 2 } : undefined,
        itemStyle: cfg.type === 'bar' ? { color: cfg.color, borderRadius: [4, 4, 0, 0] } : undefined,
        barWidth: cfg.type === 'bar' ? 8 : undefined,
      };
      if (cfg.yAxisIndex !== undefined) base.yAxisIndex = cfg.yAxisIndex;
      if (cfg.areaColor) base.areaStyle = { color: cfg.areaColor };
      return base;
    }),
  };

  return (
    <section className='panel-card panel-card--stretch' style={{ minHeight: 180 }}>
      <div className='panel-card__heading'>
        <span className='panel-card__line' />
        <h3>{title}</h3>
      </div>
      <div className='trend-chart' style={{ flex: 1, minHeight: 0, marginTop: 10 }}>
        <ReactECharts option={trendOption} style={{ width: '100%', height: '100%' }} notMerge lazyUpdate />
      </div>
    </section>
  );
};

export default TrendPanel;
