import clsx from 'clsx';

import type { MetricCard } from '@/mock/realtime';
import { formatFieldValue } from '@/mock/realtime';

interface ParameterPanelProps {
  title: string;
  metrics: MetricCard[];
  columns?: 2 | 3;
  className?: string;
}

const ParameterPanel = ({ title, metrics, columns = 2, className }: ParameterPanelProps) => {
  return (
    <section className={clsx('panel-card', 'parameter-panel', className)}>
      <div className='panel-card__heading'>
        <span className='panel-card__line' />
        <h3>{title}</h3>
      </div>
      <div className={clsx('parameter-panel__grid', columns === 3 && 'parameter-panel__grid--3')}>
        {metrics.map((metric) => (
          <article key={metric.id} className='parameter-panel__item'>
            <span className='parameter-panel__title'>{metric.title}</span>
            <div className='parameter-panel__value-wrap'>
              <strong className='parameter-panel__value'>{formatFieldValue(metric.id, metric.value)}</strong>
              <span className='parameter-panel__unit'>{metric.unit}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
};

export default ParameterPanel;
