import {
  CheckCircleFilled,
  ClockCircleFilled,
  DownOutlined,
  LoadingOutlined,
  RightOutlined,
  CloseCircleFilled,
  BulbOutlined,
  OrderedListOutlined,
} from '@ant-design/icons';
import { Tag } from 'antd';
import { memo, useMemo, useState } from 'react';

type PluginStatus = 'todo' | 'runing' | 'failed' | 'complete' | 'completed' | string;

interface PluginBlockData {
  name?: string;
  status?: PluginStatus;
  result?: string;
  err_msg?: string | null;
  args?: Record<string, unknown>;
}

interface PlanStepData {
  name?: string;
  num?: number;
  status?: PluginStatus;
  agent?: string;
  markdown?: string;
}

type ContentSegment =
  | { type: 'text'; value: string }
  | { type: 'thinking'; value: string }
  | { type: 'plugin'; value: PluginBlockData }
  | { type: 'plans'; value: PlanStepData[] };

interface RichMessageContentProps {
  content: string;
  streaming?: boolean;
}

const BLOCK_REGEX = /`{3,6}(vis-plugin|vis-thinking|agent-plans)\n([\s\S]*?)\n`{3,6}/g;

const cleanReferenceTags = (text: string): string =>
  text
    .replace(/<references[^>]*>[\s\S]*?<\/references>/gi, '')
    .replace(/<references[^>]*\/>/gi, '');

const parseJsonSafely = <T,>(raw: string): T | null => {
  try {
    return JSON.parse(raw) as T;
  } catch {
    /* noop */
  }
  try {
    const escaped = raw.replace(/\n/g, '\\n').replace(/\r/g, '\\r');
    return JSON.parse(escaped) as T;
  } catch {
    /* noop */
  }
  try {
    const cleaned = cleanReferenceTags(raw);
    const escaped = cleaned.replace(/\n/g, '\\n').replace(/\r/g, '\\r');
    return JSON.parse(escaped) as T;
  } catch {
    return null;
  }
};

const normalizeText = (value: string) => value.replace(/\n{3,}/g, '\n\n').trim();

const splitSegments = (content: string): ContentSegment[] => {
  if (!content) {
    return [];
  }

  const segments: ContentSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = BLOCK_REGEX.exec(content)) !== null) {
    const [rawBlock, tag, body] = match;
    const textBefore = content.slice(lastIndex, match.index);
    if (textBefore.trim()) {
      segments.push({ type: 'text', value: normalizeText(textBefore) });
    }

    const trimmedBody = body.trim();
    if (tag === 'vis-thinking') {
      segments.push({ type: 'thinking', value: trimmedBody });
    } else if (tag === 'vis-plugin') {
      const parsed = parseJsonSafely<PluginBlockData>(trimmedBody);
      if (parsed) {
        segments.push({ type: 'plugin', value: parsed });
      } else {
        segments.push({ type: 'text', value: rawBlock });
      }
    } else if (tag === 'agent-plans') {
      const parsed = parseJsonSafely<PlanStepData[]>(trimmedBody);
      if (parsed) {
        segments.push({ type: 'plans', value: parsed });
      } else {
        segments.push({ type: 'text', value: rawBlock });
      }
    }

    lastIndex = match.index + rawBlock.length;
  }

  const tail = content.slice(lastIndex);
  if (tail.trim()) {
    segments.push({ type: 'text', value: normalizeText(tail) });
  }

  if (segments.length === 0) {
    return [{ type: 'text', value: content }];
  }

  return deduplicatePlugins(segments);
};

const extractStepBaseName = (name: string | undefined): string => {
  if (!name) {
    return '';
  }
  return name.replace(/完成$/, '').replace(/失败$/, '').trim();
};

const isTerminalStatus = (status?: string) =>
  status === 'complete' || status === 'completed' || status === 'failed';

const deduplicatePlugins = (segments: ContentSegment[]): ContentSegment[] => {
  const terminalBaseNames = new Set<string>();
  for (const segment of segments) {
    if (segment.type !== 'plugin') {
      continue;
    }
    if (isTerminalStatus(segment.value.status)) {
      terminalBaseNames.add(extractStepBaseName(segment.value.name));
    }
  }

  if (terminalBaseNames.size === 0) {
    return segments;
  }

  return segments.filter((segment) => {
    if (segment.type !== 'plugin') {
      return true;
    }
    if (isTerminalStatus(segment.value.status)) {
      return true;
    }
    return !terminalBaseNames.has(extractStepBaseName(segment.value.name));
  });
};

const getStatusMeta = (status?: PluginStatus) => {
  switch (status) {
    case 'todo':
      return {
        className: 'is-todo',
        icon: <ClockCircleFilled />,
        label: '待执行',
      };
    case 'runing':
      return {
        className: 'is-running',
        icon: <LoadingOutlined />,
        label: '执行中',
      };
    case 'failed':
      return {
        className: 'is-failed',
        icon: <CloseCircleFilled />,
        label: '失败',
      };
    case 'complete':
    case 'completed':
      return {
        className: 'is-complete',
        icon: <CheckCircleFilled />,
        label: '完成',
      };
    default:
      return {
        className: 'is-default',
        icon: <ClockCircleFilled />,
        label: status || '处理中',
      };
  }
};

const PlainTextBlock = ({ value }: { value: string }) => (
  <div className='chat-rich__text'>
    {value}
  </div>
);

const ThinkingBlock = ({ value }: { value: string }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <section className='chat-rich-card chat-rich-card--thinking'>
      <button className='chat-rich-card__header' type='button' onClick={() => setExpanded((prev) => !prev)}>
        <span className='chat-rich-card__title'>
          {expanded ? <DownOutlined /> : <RightOutlined />}
          <BulbOutlined />
          智能体规划中
        </span>
      </button>
      {expanded ? <div className='chat-rich-card__body chat-rich-card__body--thinking'>{value}</div> : null}
    </section>
  );
};

const PluginBlock = ({ value, streaming }: { value: PluginBlockData; streaming?: boolean }) => {
  const meta = getStatusMeta(value.status);
  const detail = value.err_msg || value.result || '';
  const hasDetail = !!detail;
  const [expanded, setExpanded] = useState(Boolean(streaming && hasDetail));

  return (
    <section className={`chat-rich-card chat-rich-card--plugin ${meta.className}`}>
      <button
        className='chat-rich-card__header'
        type='button'
        onClick={() => {
          if (hasDetail) {
            setExpanded((prev) => !prev);
          }
        }}
      >
        <span className='chat-rich-card__title'>
          {hasDetail ? expanded ? <DownOutlined /> : <RightOutlined /> : null}
          {meta.icon}
          {value.name || '执行步骤'}
        </span>
        <Tag>{meta.label}</Tag>
      </button>
      {expanded && hasDetail ? <div className='chat-rich-card__body'>{detail}</div> : null}
    </section>
  );
};

const PlansBlock = ({ value }: { value: PlanStepData[] }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <section className='chat-rich-card chat-rich-card--plans'>
      <button className='chat-rich-card__header' type='button' onClick={() => setExpanded((prev) => !prev)}>
        <span className='chat-rich-card__title'>
          {expanded ? <DownOutlined /> : <RightOutlined />}
          <OrderedListOutlined />
          执行规划
        </span>
        <Tag>{value.length} 步</Tag>
      </button>
      {expanded ? (
        <div className='chat-rich-plans'>
          {value.map((step, index) => {
            const meta = getStatusMeta(step.status);
            return (
              <div key={`${step.name || 'step'}-${index}`} className='chat-rich-plan'>
                <div className='chat-rich-plan__head'>
                  <span className='chat-rich-plan__index'>{step.num || index + 1}</span>
                  <div className='chat-rich-plan__main'>
                    <div className='chat-rich-plan__title-row'>
                      <strong>{step.name || `步骤 ${index + 1}`}</strong>
                      <Tag>{step.agent || 'Agent'}</Tag>
                    </div>
                    {step.markdown ? <div className='chat-rich-plan__desc'>{step.markdown}</div> : null}
                  </div>
                  <span className={`chat-rich-plan__status ${meta.className}`}>
                    {meta.icon}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
};

const RichMessageContent = ({ content, streaming }: RichMessageContentProps) => {
  const segments = useMemo(() => splitSegments(content), [content]);

  return (
    <div className='chat-rich'>
      {segments.map((segment, index) => {
        switch (segment.type) {
          case 'thinking':
            return <ThinkingBlock key={`thinking-${index}`} value={segment.value} />;
          case 'plugin':
            return <PluginBlock key={`plugin-${index}`} value={segment.value} streaming={streaming} />;
          case 'plans':
            return <PlansBlock key={`plans-${index}`} value={segment.value} />;
          case 'text':
          default:
            return <PlainTextBlock key={`text-${index}`} value={segment.value} />;
        }
      })}
    </div>
  );
};

export default memo(RichMessageContent);
