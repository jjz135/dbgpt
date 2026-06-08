import { Badge, Button, Space, Tag } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import type { PageDef } from '@/mock/realtime';

interface ScreenFrameProps {
  pages: PageDef[];
  currentPageId: string;
  onPageChange: (pageId: string) => void;
  deviceName: string;
  shotCount: number;
  onlineStatus: number;
  activeAppName?: string;
  children: ReactNode;
}

const DESIGN_WIDTH = 1920;
const DESIGN_HEIGHT = 1080;

const ScreenFrame = ({
  pages,
  currentPageId,
  onPageChange,
  deviceName,
  shotCount,
  onlineStatus,
  activeAppName,
  children,
}: ScreenFrameProps) => {
  const nowText = dayjs().format('YYYY-MM-DD HH:mm:ss');
  const [viewportSize, setViewportSize] = useState(() => ({
    width: window.innerWidth,
    height: window.innerHeight,
  }));

  useEffect(() => {
    const handleResize = () => {
      setViewportSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const screenScale = useMemo(
    () => Math.min(viewportSize.width / DESIGN_WIDTH, viewportSize.height / DESIGN_HEIGHT),
    [viewportSize.height, viewportSize.width],
  );

  return (
    <div className='screen-viewport'>
      <div
        className='screen-shell'
        style={{
          width: `${DESIGN_WIDTH}px`,
          height: `${DESIGN_HEIGHT}px`,
          transform: `translate(-50%, -50%) scale(${screenScale})`,
        }}
      >
        <header className='screen-header'>
          <div className='screen-branding'>
            <div className='screen-branding__glow' />
            <div>
              <div className='screen-branding__subtitle'>智产 · 注塑大模型</div>
              <h1 className='screen-branding__title'>智产注塑大模型</h1>
            </div>
          </div>
          <Space size={18} className='screen-toolbar'>
            <div className='screen-status'>
              <span className='screen-status__label'>系统时间</span>
              <strong>{nowText}</strong>
            </div>
            <div className='screen-status'>
              <span className='screen-status__label'>设备编号</span>
              <Tag color='blue'>{deviceName}</Tag>
            </div>
            <div className='screen-status'>
              <span className='screen-status__label'>当前模次</span>
              <strong>{shotCount}</strong>
            </div>
            <div className='screen-status'>
              <span className='screen-status__label'>在线状态</span>
              <Badge status={onlineStatus === 1 ? 'processing' : 'error'} text={onlineStatus === 1 ? '在线' : '离线'} />
            </div>
            <div className='screen-status'>
              <span className='screen-status__label'>当前应用</span>
              <Tag color='blue'>{activeAppName || '未选择'}</Tag>
            </div>
            <div className='screen-status'>
              <span className='screen-status__label'>页面切换</span>
              <Space size={4}>
                {pages.map((page) => (
                  <Button
                    key={page.id}
                    size='small'
                    type={page.id === currentPageId ? 'primary' : 'default'}
                    onClick={() => onPageChange(page.id)}
                  >
                    {page.title}
                  </Button>
                ))}
              </Space>
            </div>
          </Space>
        </header>
        {children}
      </div>
    </div>
  );
};

export default ScreenFrame;
