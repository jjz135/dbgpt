import clsx from 'clsx';
import ReactECharts from 'echarts-for-react';

interface RadarIndicator {
  name: string;
  max: number;
}

interface RadarSeriesItem {
  name: string;
  value: number[];
  color: string;
}

interface RadarChartPanelProps {
  title: string;
  indicators: RadarIndicator[];
  series: RadarSeriesItem[];
  className?: string;
}

const RadarChartPanel = ({ title, indicators, series, className }: RadarChartPanelProps) => {
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
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
    radar: {
      center: ['50%', '58%'],
      radius: '62%',
      indicator: indicators,
      axisName: {
        color: 'rgba(216, 239, 255, 0.76)',
        fontSize: 11,
      },
      splitLine: {
        lineStyle: { color: 'rgba(255,255,255,0.08)' },
      },
      splitArea: {
        areaStyle: { color: ['rgba(47, 182, 255, 0.03)', 'rgba(47, 182, 255, 0.015)'] },
      },
      axisLine: {
        lineStyle: { color: 'rgba(255,255,255,0.1)' },
      },
    },
    series: [
      {
        type: 'radar',
        data: series.map((item) => ({
          name: item.name,
          value: item.value,
          lineStyle: { color: item.color, width: 2 },
          itemStyle: { color: item.color },
          areaStyle: { color: `${item.color}22` },
        })),
      },
    ],
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

export default RadarChartPanel;
