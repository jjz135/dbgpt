import {
  CheckOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  DownOutlined,
  LoadingOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { GPTVis } from '@antv/gpt-vis';
import classNames from 'classnames';
import { ReactNode, useState } from 'react';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import markdownComponents from './config';

interface IVisPlugin {
  name: string;
  args: {
    query: string;
  };
  status: 'todo' | 'runing' | 'failed' | 'complete' | (string & {});
  logo: string | null;
  result: string;
  err_msg: string | null;
}

interface Props {
  data: IVisPlugin;
}

const pluginViewStatusMapper: Record<IVisPlugin['status'], { bgClass: string; icon: ReactNode }> = {
  todo: {
    bgClass: 'bg-gray-500',
    icon: <ClockCircleOutlined className='ml-2' />,
  },
  runing: {
    bgClass: 'bg-blue-500',
    icon: <LoadingOutlined className='ml-2' />,
  },
  failed: {
    bgClass: 'bg-red-500',
    icon: <CloseOutlined className='ml-2' />,
  },
  complete: {
    bgClass: 'bg-green-500',
    icon: <CheckOutlined className='ml-2' />,
  },
};

function VisPlugin({ data }: Props) {
  const { bgClass, icon } = pluginViewStatusMapper[data.status] ?? {};
  const hasDetail = !!(data.result || data.err_msg);
  const [expanded, setExpanded] = useState(false);

  return (
    <div className='bg-theme-light dark:bg-theme-dark-container rounded overflow-hidden my-2 flex flex-col'>
      <div
        className={classNames('flex px-4 md:px-6 py-2 items-center text-white text-sm', bgClass, {
          'cursor-pointer': hasDetail,
        })}
        onClick={() => {
          if (hasDetail) {
            setExpanded(prev => !prev);
          }
        }}
      >
        {hasDetail ? (
          <span className='mr-2'>{expanded ? <DownOutlined /> : <RightOutlined />}</span>
        ) : null}
        {data.name}
        {icon}
      </div>
      {expanded &&
        (data.result ? (
          <div className='px-4 md:px-6 py-4 text-sm whitespace-normal'>
            <GPTVis components={markdownComponents} rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]}>
              {data.result ?? ''}
            </GPTVis>
          </div>
        ) : (
          <div className='px-4 md:px-6 py-4 text-sm'>{data.err_msg}</div>
        ))}
    </div>
  );
}

export default VisPlugin;
