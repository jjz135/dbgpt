import clsx from 'clsx';
import ReactECharts from 'echarts-for-react';

interface PieChartPanelProps {
  title: string;
  data: Array<{ name: string; value: number }>;
  colors?: string[];
  className?: string;
}

const PieChartPanel = ({ title, data, colors, className }: PieChartPanelProps) => {
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(7, 19, 41, 0.8)',
      borderColor: 'rgba(78, 176, 255, 0.3)',
      textStyle: { color: '#d8efff' },
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: 'rgba(180, 218, 246, 0.7)' },
    },
    series: [
      {
        name: title,
        type: 'pie',
        radius: ['50%', '80%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderColor: 'rgba(5, 16, 36, 0.8)',
          borderWidth: 2,
        },
        label: { show: false, position: 'center' },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
            color: '#eff9ff'
          }
        },
        labelLine: { show: false },
        data: data,
        color: colors || ['#2fb6ff', '#8be7ff', '#3478f6', '#135cba'],
      }
    ]
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

export default PieChartPanel;
