const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001';

async function request(path, { method = 'GET', token, body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    throw new Error('认证已过期，请重新登录');
  }
  if (!res.ok || data.error) {
    throw new Error(data.error || res.statusText || '请求失败');
  }
  return data;
}

export async function login({ user_id, password }) {
  return request('/login', { method: 'POST', body: { user_id, password } });
}

export async function register({ user_id, username, password }) {
  return request('/register', { method: 'POST', body: { user_id, username, password } });
}

export async function getHealthData(token) {
  return request('/health-data', { method: 'GET', token });
}

export async function updateHealthData(token, payload) {
  return request('/health-data', { method: 'PUT', token, body: payload });
}

/**
 * 调用 /stream，读取 SSE 片段并回调。
 */
export async function streamLLM({ prompt, token, onChunk, onDone, onError }) {
  try {
    const res = await fetch(`${API_BASE}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ prompt, stream: true }),
    });

    if (!res.body) throw new Error('响应体为空，可能是网络或 CORS 问题');

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const payload = trimmed.slice('data:'.length).trim();

        if (!payload) continue;
        if (payload === '[DONE]') continue;

        // 记录当前 event，后续只处理 conversation.message.delta 的数据行
        if (payload.startsWith('event:')) {
          currentEvent = payload.slice('event:'.length).trim();
          continue;
        }

        if (currentEvent && currentEvent !== 'conversation.message.delta') {
          continue;
        }

        try {
          const start = payload.indexOf('{');
          const end = payload.lastIndexOf('}');
          if (start !== -1 && end !== -1 && end > start) {
            const obj = JSON.parse(payload.slice(start, end + 1));
            const parts = [];
            if (obj.content) parts.push(obj.content);
            if (obj.data && obj.data.content) parts.push(obj.data.content);
            if (obj.data && Array.isArray(obj.data.contents)) {
              for (const c of obj.data.contents) {
                if (c && typeof c.content === 'string') parts.push(c.content);
              }
            }
            if (parts.length === 0) parts.push(payload);
            for (const p of parts) onChunk(p);
          } else {
            onChunk(payload);
          }
        } catch (e) {
          onChunk(payload);
        }
      }
    }

    onDone();
  } catch (err) {
    console.error(err);
    onError(err);
  }
}
