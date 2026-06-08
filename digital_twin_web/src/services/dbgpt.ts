import { fetchEventSource } from '@microsoft/fetch-event-source';

import { API_BASE_URL, buildApiUrl } from '@/config/runtime';

export interface PublishedAppInfo {
  appCode: string;
  appName: string;
  appDescribe?: string;
  teamMode: string;
  chatScene: string;
  ownerName?: string;
  published: string;
}

export interface AppParamNeed {
  type: string;
  value: string;
  bindValue?: string;
}

export interface AppInfo {
  appCode: string;
  appName: string;
  chatScene: string;
  paramNeed: AppParamNeed[];
}

export interface ResourceOption {
  label: string;
  value: string;
  type: string;
}

export interface ChatMessage {
  id: string;
  role: 'human' | 'view' | 'system';
  content: string;
  timestamp: string;
  streaming?: boolean;
}

interface ResultEnvelope<T> {
  success?: boolean;
  err_code?: string | null;
  err_msg?: string | null;
  data?: T;
}

interface DialogueInfo {
  conv_uid: string;
}

interface ChatStreamParams {
  convUid: string;
  prompt: string;
  appCode?: string;
  chatMode: string;
  selectParam?: string;
  modelName?: string;
  onDelta: (chunk: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
  signal?: AbortSignal;
}

async function parseEnvelope<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ResultEnvelope<T>;
  if (!response.ok || payload.success === false || payload.err_msg) {
    throw new Error(payload.err_msg || `请求失败: ${response.status}`);
  }
  return payload.data as T;
}

export async function fetchPublishedApps(): Promise<PublishedAppInfo[]> {
  const response = await fetch(buildApiUrl('/api/v1/app/list'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      page_no: '1',
      page_size: '50',
      ignore_user: 'true',
      published: 'true',
      need_owner_info: 'true',
    }),
  });
  const data = await parseEnvelope<{
    app_list?: Array<{
      app_code: string;
      app_name: string;
      app_describe?: string;
      team_mode?: string;
      team_context?: { chat_scene?: string | null } | null;
      owner_name?: string | null;
      published?: string;
    }>;
  }>(response);

  return (data?.app_list || []).map((item) => ({
    appCode: item.app_code,
    appName: item.app_name,
    appDescribe: item.app_describe,
    teamMode: item.team_mode || 'chat_agent',
    chatScene: item.team_context?.chat_scene || 'chat_agent',
    ownerName: item.owner_name || undefined,
    published: item.published || 'false',
  }));
}

export async function fetchAppInfo(chatScene: string, appCode: string): Promise<AppInfo> {
  const search = new URLSearchParams({
    chat_scene: chatScene,
    app_code: appCode,
  });
  const response = await fetch(buildApiUrl(`/api/v1/app/info?${search.toString()}`));
  const data = await parseEnvelope<{
    app_code: string;
    app_name: string;
    team_context?: { chat_scene?: string | null } | null;
    param_need?: Array<{ type: string; value: string; bind_value?: string }>;
  }>(response);

  return {
    appCode: data?.app_code || appCode,
    appName: data?.app_name || appCode,
    chatScene: data?.team_context?.chat_scene || chatScene,
    paramNeed: (data?.param_need || []).map((item) => ({
      type: item.type,
      value: item.value,
      bindValue: item.bind_value,
    })),
  };
}

export async function fetchChatModeResourceOptions(chatMode: string): Promise<ResourceOption[]> {
  const response = await fetch(buildApiUrl(`/api/v1/chat/mode/params/list?chat_mode=${encodeURIComponent(chatMode)}`), {
    method: 'POST',
  });
  const data = await parseEnvelope<Array<{ param: string; type: string }>>(response);
  return (data || []).map((item) => ({
    label: item.param,
    value: item.param,
    type: item.type,
  }));
}

export async function createChatDialogue(chatMode = 'chat_agent'): Promise<string> {
  const response = await fetch(buildApiUrl(`/api/v1/chat/dialogue/new?chat_mode=${encodeURIComponent(chatMode)}`), {
    method: 'POST',
  });
  const data = await parseEnvelope<DialogueInfo>(response);
  if (!data?.conv_uid) {
    throw new Error('未获取到会话 ID');
  }
  return data.conv_uid;
}

export async function fetchChatHistory(convUid: string): Promise<ChatMessage[]> {
  const response = await fetch(
    buildApiUrl(`/api/v1/chat/dialogue/messages/history?con_uid=${encodeURIComponent(convUid)}`),
  );
  const data = await parseEnvelope<Array<{ role: 'human' | 'view' | 'system'; context: string }>>(response);
  const now = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  return (data || []).map((item, index) => ({
    id: `${item.role}-${index}`,
    role: item.role,
    content: item.context || '',
    timestamp: now,
  }));
}

const restoreNewlines = (text: string) => text.replaceAll('\\n', '\n');

const parseStreamChunk = (raw: string): string => {
  if (!raw || raw === '[DONE]') {
    return '';
  }

  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.vis === 'string') {
      return restoreNewlines(parsed.vis);
    }
    if (typeof parsed?.text === 'string') {
      return restoreNewlines(parsed.text);
    }
    const content = parsed?.choices?.[0]?.message?.content ?? parsed?.choices?.[0]?.delta?.content;
    if (typeof content === 'string') {
      return restoreNewlines(content);
    }
    if (typeof parsed === 'string') {
      return restoreNewlines(parsed);
    }
  } catch {
    return restoreNewlines(raw);
  }

  return '';
};

export async function streamAgentChat({
  convUid,
  prompt,
  appCode,
  chatMode,
  selectParam,
  modelName = 'qwen-plus',
  onDelta,
  onDone,
  onError,
  signal,
}: ChatStreamParams): Promise<void> {
  let completed = false;

  await fetchEventSource(buildApiUrl('/api/v1/chat/completions'), {
    method: 'POST',
    body: JSON.stringify({
      conv_uid: convUid,
      chat_mode: chatMode,
      app_code: appCode,
      select_param: selectParam,
      model_name: modelName,
      user_input: prompt,
    }),
    headers: {
      'Content-Type': 'application/json',
    },
    signal,
    openWhenHidden: true,
    async onopen(response) {
      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType?.includes('application/json')) {
          const payload = (await response.json()) as ResultEnvelope<unknown>;
          throw new Error(payload.err_msg || '聊天接口返回异常');
        }
        throw new Error(`聊天接口连接失败: ${response.status}`);
      }
    },
    onmessage(event) {
      if (event.data === '[DONE]') {
        completed = true;
        onDone();
        return;
      }

      if (event.data.startsWith('[ERROR]')) {
        completed = true;
        onError(event.data.replace('[ERROR]', '').trim());
        return;
      }

      const chunk = parseStreamChunk(event.data);
      if (chunk) {
        onDelta(chunk);
      }
    },
    onclose() {
      if (!completed) {
        completed = true;
        onDone();
      }
    },
    onerror(error) {
      if (!completed) {
        completed = true;
        onError(error instanceof Error ? error.message : '对话流中断');
      }
      throw error;
    },
  }).catch((error) => {
    if (!completed && !(error instanceof DOMException && error.name === 'AbortError')) {
      completed = true;
      onError(error instanceof Error ? error.message : '对话请求失败');
    }
  });
}

export { API_BASE_URL };
