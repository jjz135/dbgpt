import dynamic from 'next/dynamic';
import React, { memo, useContext, useMemo } from 'react';
import { MobileChatContext } from '../';

const ChatDialog = dynamic(() => import('./ChatDialog'), {
  ssr: false,
});

const Content: React.FC = () => {
  const { history } = useContext(MobileChatContext);

  // 过滤出需要展示的消息
  const showMessages = useMemo(() => {
    return history.filter(item => ['view', 'human'].includes(item.role));
  }, [history]);

  return (
    <div className='flex flex-col gap-4'>
      {!!showMessages.length &&
        showMessages.map((message, index) => {
          return <ChatDialog key={message.context + index} message={message} index={index} />;
        })}
    </div>
  );
};

export default memo(Content);
