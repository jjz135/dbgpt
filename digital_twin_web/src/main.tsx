import { App as AntdApp, ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App.tsx';
import './index.css';
import './styles/screen.css';
import 'antd/dist/reset.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#2fb6ff',
          colorInfo: '#2fb6ff',
          borderRadius: 10,
          colorText: '#d8efff',
          colorTextSecondary: 'rgba(216, 239, 255, 0.72)',
          colorBgContainer: 'rgba(7, 18, 40, 0.72)',
          colorBorder: 'rgba(47, 182, 255, 0.25)',
          wireframe: false,
        },
      }}
    >
      <AntdApp>
        <App />
      </AntdApp>
    </ConfigProvider>
  </StrictMode>,
);
