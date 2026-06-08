import {
  App as AntdApp,
  Button,
  Empty,
  Input,
  Select,
  Skeleton,
  Space,
  Tag,
} from 'antd';
import dayjs from 'dayjs';
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import RichMessageContent from '@/components/chat/RichMessageContent';
import {
  type AppInfo,
  type ChatMessage,
  createChatDialogue,
  fetchAppInfo,
  fetchChatModeResourceOptions,
  fetchChatHistory,
  fetchPublishedApps,
  type PublishedAppInfo,
  type ResourceOption,
  streamAgentChat,
} from '@/services/dbgpt';

const { TextArea } = Input;

interface AgentChatPanelProps {
  activeAppName?: string;
  onActiveAppChange?: (appName: string) => void;
}

const createMessage = (role: ChatMessage['role'], content: string, streaming = false): ChatMessage => ({
  id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
  role,
  content,
  timestamp: dayjs().format('HH:mm:ss'),
  streaming,
});

const mergeStreamText = (current: string, incoming: string) => {
  if (!incoming) {
    return current;
  }

  if (!current) {
    return incoming;
  }

  if (incoming === current) {
    return current;
  }

  if (incoming.startsWith(current)) {
    return incoming;
  }

  if (current.startsWith(incoming)) {
    return current;
  }

  for (let overlap = Math.min(current.length, incoming.length); overlap > 0; overlap -= 1) {
    if (current.slice(-overlap) === incoming.slice(0, overlap)) {
      return current + incoming.slice(overlap);
    }
  }

  return current + incoming;
};

const AgentChatPanel = ({ activeAppName, onActiveAppChange }: AgentChatPanelProps) => {
  const { message } = AntdApp.useApp();
  const [apps, setApps] = useState<PublishedAppInfo[]>([]);
  const [loadingApps, setLoadingApps] = useState(true);
  const [selectedAppCode, setSelectedAppCode] = useState<string>();
  const [selectedAppDetail, setSelectedAppDetail] = useState<AppInfo>();
  const [loadingAppDetail, setLoadingAppDetail] = useState(false);
  const [resourceOptions, setResourceOptions] = useState<ResourceOption[]>([]);
  const [loadingResourceOptions, setLoadingResourceOptions] = useState(false);
  const [selectedResource, setSelectedResource] = useState<string>();
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [convUid, setConvUid] = useState<string>();
  const abortRef = useRef<AbortController | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    fetchPublishedApps()
      .then((list) => {
        if (!active) {
          return;
        }
        const sorted = [...list].sort((first, second) => {
          if (first.teamMode === 'native_app' && second.teamMode !== 'native_app') {
            return 1;
          }
          if (first.teamMode !== 'native_app' && second.teamMode === 'native_app') {
            return -1;
          }
          return first.appName.localeCompare(second.appName);
        });
        setApps(sorted);
        const preferred = activeAppName ? sorted.find((item) => item.appName === activeAppName) : undefined;
        const nextApp = preferred || sorted[0];
        setSelectedAppCode(nextApp?.appCode);
        if (nextApp?.appName) {
          onActiveAppChange?.(nextApp.appName);
        }
      })
      .catch((error) => {
        message.error(error instanceof Error ? error.message : '加载探索广场应用失败');
      })
      .finally(() => {
        if (active) {
          setLoadingApps(false);
        }
      });

    return () => {
      active = false;
    };
  }, [activeAppName, message, onActiveAppChange]);

  useEffect(() => {
    viewportRef.current?.scrollTo({
      top: viewportRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  const selectedAppInfo = useMemo(
    () => apps.find((app) => app.appCode === selectedAppCode),
    [apps, selectedAppCode],
  );

  const resourceParam = useMemo(
    () => selectedAppDetail?.paramNeed.find((item) => item.type === 'resource'),
    [selectedAppDetail],
  );

  const needsResourceSelection = useMemo(() => {
    if (!resourceParam) {
      return false;
    }
    return ['knowledge', 'database', 'plugin', 'awel_flow'].includes(resourceParam.value) && !resourceParam.bindValue;
  }, [resourceParam]);

  const resourceLabel = useMemo(() => {
    switch (resourceParam?.value) {
      case 'knowledge':
        return '知识库';
      case 'database':
        return '数据库';
      case 'plugin':
        return '插件';
      case 'awel_flow':
        return '流程';
      default:
        return '资源';
    }
  }, [resourceParam?.value]);

  const selectedAppHint = useMemo(() => {
    if (!selectedAppInfo) {
      return '请选择探索广场中已发布的应用。';
    }
    const ownerText = selectedAppInfo.ownerName ? `发布者：${selectedAppInfo.ownerName}` : '平台应用';
    const modeText =
      selectedAppInfo.teamMode === 'native_app'
        ? `原生场景：${selectedAppInfo.chatScene}`
        : `应用编码：${selectedAppInfo.appCode}`;
    const resourceText = resourceParam
      ? resourceParam.bindValue
        ? `绑定${resourceLabel}：${resourceParam.bindValue}`
        : `可选${resourceLabel}`
      : '';
    return [ownerText, modeText, resourceText].filter(Boolean).join(' · ');
  }, [resourceLabel, resourceParam, selectedAppInfo]);

  useEffect(() => {
    if (!selectedAppInfo) {
      setSelectedAppDetail(undefined);
      setResourceOptions([]);
      setSelectedResource(undefined);
      setLoadingAppDetail(false);
      setLoadingResourceOptions(false);
      return;
    }

    let active = true;
    setLoadingAppDetail(true);
    setLoadingResourceOptions(false);
    setSelectedAppDetail(undefined);
    setResourceOptions([]);
    setSelectedResource(undefined);

    fetchAppInfo(selectedAppInfo.chatScene, selectedAppInfo.appCode)
      .then(async (detail) => {
        if (!active) {
          return;
        }
        setSelectedAppDetail(detail);

        const nextResourceParam = detail.paramNeed.find((item) => item.type === 'resource');
        if (!nextResourceParam) {
          setLoadingResourceOptions(false);
          setResourceOptions([]);
          setSelectedResource(undefined);
          return;
        }

        if (nextResourceParam.bindValue) {
          setLoadingResourceOptions(false);
          setSelectedResource(nextResourceParam.bindValue);
          setResourceOptions([
            {
              label: nextResourceParam.bindValue,
              value: nextResourceParam.bindValue,
              type: nextResourceParam.value,
            },
          ]);
          return;
        }

        if (!['knowledge', 'database', 'plugin', 'awel_flow'].includes(nextResourceParam.value)) {
          setLoadingResourceOptions(false);
          setResourceOptions([]);
          setSelectedResource(undefined);
          return;
        }

        setLoadingResourceOptions(true);
        try {
          const options = await fetchChatModeResourceOptions(detail.chatScene);
          if (!active) {
            return;
          }
          setResourceOptions(options);
          setSelectedResource(options[0]?.value);
        } finally {
          if (active) {
            setLoadingResourceOptions(false);
          }
        }
      })
      .catch((error) => {
        if (active) {
          setSelectedAppDetail(undefined);
          setResourceOptions([]);
          setSelectedResource(undefined);
          message.error(error instanceof Error ? error.message : '加载应用详情失败');
        }
      })
      .finally(() => {
        if (active) {
          setLoadingAppDetail(false);
        }
      });

    return () => {
      active = false;
    };
  }, [message, selectedAppInfo]);

  const resetConversation = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setSending(false);
    setConvUid(undefined);
    setMessages([]);
  }, []);

  const ensureConversation = useCallback(async () => {
    if (convUid) {
      return convUid;
    }
    const nextConvUid = await createChatDialogue(selectedAppDetail?.chatScene || selectedAppInfo?.chatScene || 'chat_agent');
    setConvUid(nextConvUid);
    const history = await fetchChatHistory(nextConvUid).catch(() => []);
    if (history.length > 0) {
      setMessages(history);
    }
    return nextConvUid;
  }, [convUid, selectedAppDetail?.chatScene, selectedAppInfo?.chatScene]);

  const handleSend = useCallback(async () => {
    const content = prompt.trim();
    if (!content || sending) {
      return;
    }
    if (!selectedAppInfo) {
      message.warning('请先选择探索广场中的已发布应用');
      return;
    }
    if (needsResourceSelection && !selectedResource) {
      message.warning(`请先选择${resourceLabel}`);
      return;
    }

    setPrompt('');
    setSending(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const humanMessage = createMessage('human', content);
    const aiMessage = createMessage('view', '', true);
    setMessages((current) => [...current, humanMessage, aiMessage]);

    try {
      const currentConvUid = await ensureConversation();
      const isNativeApp = selectedAppInfo.teamMode === 'native_app';
      const selectParam = resourceParam ? selectedResource : isNativeApp ? undefined : selectedAppInfo.appCode;
      await streamAgentChat({
        convUid: currentConvUid,
        prompt: content,
        appCode: selectedAppInfo.appCode,
        chatMode: isNativeApp ? selectedAppDetail?.chatScene || selectedAppInfo.chatScene : 'chat_agent',
        selectParam,
        signal: controller.signal,
        onDelta: (chunk) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === aiMessage.id ? { ...item, content: mergeStreamText(item.content, chunk) } : item,
            ),
          );
        },
        onDone: () => {
          setMessages((current) =>
            current.map((item) => (item.id === aiMessage.id ? { ...item, streaming: false } : item)),
          );
          setSending(false);
          abortRef.current = null;
        },
        onError: (errorMessage) => {
          setMessages((current) =>
            current.map((item) =>
              item.id === aiMessage.id
                ? { ...item, content: item.content || errorMessage || '对话失败', streaming: false }
                : item,
            ),
          );
          setSending(false);
          abortRef.current = null;
          message.error(errorMessage || '对话失败');
        },
      });
    } catch (error) {
      setMessages((current) =>
        current.map((item) =>
          item.id === aiMessage.id
            ? { ...item, content: error instanceof Error ? error.message : '发送失败', streaming: false }
            : item,
        ),
      );
      setSending(false);
      abortRef.current = null;
      message.error(error instanceof Error ? error.message : '发送失败');
    }
  }, [
    ensureConversation,
    message,
    needsResourceSelection,
    prompt,
    resourceLabel,
    resourceParam,
    selectedAppDetail?.chatScene,
    selectedAppInfo,
    selectedResource,
    sending,
  ]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setSending(false);
    setMessages((current) => current.map((item) => (item.streaming ? { ...item, streaming: false } : item)));
  }, []);

  return (
    <section className='chat-panel'>
      <div className='chat-panel__header'>
        <div>
          <span className='chat-panel__label'>DB-GPT 对话面板</span>
          <h3>探索广场已发布应用对话</h3>
        </div>
        <Space size={12}>
          <Button onClick={resetConversation}>新建会话</Button>
          <Tag color='gold'>{convUid ? `会话 ${convUid.slice(0, 8)}` : '未创建会话'}</Tag>
        </Space>
      </div>

      <div className='chat-panel__toolbar'>
        {loadingApps ? (
          <Skeleton.Input active style={{ width: 320 }} />
        ) : (
          <Select
            className='chat-panel__agent-select'
            value={selectedAppCode}
            options={apps.map((app) => ({
              label: `${app.appName}${app.teamMode === 'native_app' ? '' : ' · 多Agent'}`,
              value: app.appCode,
            }))}
            onChange={(value) => {
              const targetApp = apps.find((app) => app.appCode === value);
              setSelectedAppCode(value);
              onActiveAppChange?.(targetApp?.appName || value);
              resetConversation();
            }}
          />
        )}
        <div className='chat-panel__agent-desc'>{selectedAppHint}</div>
      </div>

      {(loadingAppDetail || resourceParam) && (
        <div className='chat-panel__resource-row'>
          <span className='chat-panel__resource-label'>{resourceLabel || '资源选择'}</span>
          <Select
            className='chat-panel__resource-select'
            value={selectedResource}
            placeholder={`请选择${resourceLabel || '资源'}`}
            loading={loadingAppDetail || loadingResourceOptions}
            disabled={!needsResourceSelection}
            options={resourceOptions}
            onChange={setSelectedResource}
          />
        </div>
      )}

      {selectedAppInfo ? (
        <div className='chat-panel__app-meta'>
          {resourceParam?.bindValue ? <Tag color='cyan'>{`${resourceLabel}：${resourceParam.bindValue}`}</Tag> : null}
          {needsResourceSelection && selectedResource ? <Tag color='geekblue'>{`${resourceLabel}：${selectedResource}`}</Tag> : null}
        </div>
      ) : null}

      <div ref={viewportRef} className='chat-panel__messages'>
        {messages.length === 0 ? (
          <Empty description='请选择探索广场中的已发布应用并开始对话' image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          messages.map((item) => (
            <article key={item.id} className={`chat-message chat-message--${item.role}`}>
              <div className='chat-message__meta'>
                <span>{item.role === 'human' ? '你' : item.role === 'view' ? '应用回复' : '系统'}</span>
                <time>{item.timestamp}</time>
              </div>
              <div className='chat-message__content'>
                <RichMessageContent
                  content={item.content || (item.streaming ? '正在生成回复...' : '-')}
                  streaming={item.streaming}
                />
              </div>
            </article>
          ))
        )}
      </div>

      <div className='chat-panel__input'>
        <TextArea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={3}
          placeholder='输入问题后，消息会发送给当前选中的探索广场已发布应用'
          onPressEnter={(event) => {
            if (!event.shiftKey) {
              event.preventDefault();
              void handleSend();
            }
          }}
        />
        <div className='chat-panel__actions'>
          <span className='chat-panel__hint'>Enter 发送，Shift+Enter 换行</span>
          <Space>
            <Button onClick={handleStop} disabled={!sending}>
              停止
            </Button>
            <Button type='primary' onClick={() => void handleSend()} loading={sending}>
              发送
            </Button>
          </Space>
        </div>
      </div>
    </section>
  );
};

export default memo(AgentChatPanel);
