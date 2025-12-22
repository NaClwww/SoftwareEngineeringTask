# Frontend (React + Vite)

A minimal UI to chat with the PJGQ Health Agent backend, with login, chat, and user profile editing.

## Quick start

```bash
cd frontend
npm install
npm run dev
```

- Default API base: `http://localhost:8001` (override with `VITE_API_BASE` env var).
- 页面说明：
	- 登录/注册：输入 user_id / password（注册还需 username），成功后自动保存 token。
	- 对话：输入问题，实时流式展示助手回复。
	- 用户信息：查看/修改健康数据（身高/体重/年龄/性别）。

## Notes
- Streaming is handled via `fetch` + `ReadableStream` parsing SSE `data:` lines, accumulating `content`.
