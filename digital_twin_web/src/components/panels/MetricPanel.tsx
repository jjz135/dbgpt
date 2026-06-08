import clsx from 'clsx';

import type { MetricCard } from '@/mock/realtime';

interface MetricPanelProps {
  title: string;
  metrics: MetricCard[];
  className?: string;
}

const DENSE_THRESHOLD = 8;

const formatValue = (metric: MetricCard) => {
  const precision = metric.precision ?? 0;
  return `${metric.value.toFixed(precision)}`;
};

const MetricPanel = ({ title, metrics, className }: MetricPanelProps) => {
  const isDense = metrics.length > DENSE_THRESHOLD;

  return (
    <section className={clsx('panel-card', className)}>
      <div className='panel-card__heading'>
        <span className='panel-card__line' />
        <h3>{title}</h3>
      </div>
      <div className={clsx('metric-grid', isDense && 'metric-grid--dense')}>
        {metrics.map((metric) => (
          <article
            key={metric.id}
            className={clsx('metric-card', `metric-card--${metric.tone}`, isDense && 'metric-card--dense')}
          >
            <span className='metric-card__title'>{metric.title}</span>
            <div className='metric-card__value-wrap'>
              <strong className='metric-card__value'>{formatValue(metric)}</strong>
              <span className='metric-card__unit'>{metric.unit}</span>
            </div>
            <span className={clsx('metric-card__delta', metric.delta >= 0 ? 'up' : 'down')}>
              {metric.delta >= 0 ? '较上次 +' : '较上次 '}
              {metric.delta.toFixed(1)}%
            </span>
          </article>
        ))}
      </div>
    </section>
  );
};

export default MetricPanel;
