# PJGQ Health Agent with LLM Capabilities

这是一个基于FastAPI的LLM代理服务，支持多种LLM API的流式传输转发功能。

## 功能特性

- 模拟LLM查询和流式传输
- OpenAI API集成
- 自定义LLM API集成
- Coze API流式传输支持

## 安装依赖

使用uv安装依赖：

```bash
uv sync
```

## 配置

在 `.env` 文件中设置你的API密钥：

```
COZE_API_KEY=your_coze_api_key_here
DEFAULT_BOT_ID=your_default_bot_id_here
```

## 启动服务

```bash
uvicorn main:app --reload
```

或者直接运行：

```bash
python main.py
```

服务将在 `http://localhost:8000` 上运行。

## API 端点

### 查询端点

- `POST /query` - 模拟LLM查询
- `POST /query-openai` - OpenAI API查询
- `POST /query-custom` - 自定义LLM API查询

### 流式传输端点

- `POST /stream` - 模拟LLM流式传输
- `POST /stream-openai` - OpenAI API流式传输
- `POST /stream-coze` - Coze API流式传输

## 使用示例

### Coze API流式传输示例

```bash
curl -X POST "http://localhost:8000/stream-coze" \
-H "Content-Type: application/json" \
-d '{
  "prompt": "你好，世界！",
  "bot_id": "your_bot_id",
  "user_id": "your_user_id"
}'
```

### 自定义头部示例

```bash
curl -X POST "http://localhost:8000/stream-coze" \
-H "Content-Type: application/json" \
-d '{
  "prompt": "你好，世界！",
  "headers": {
    "Authorization": "Bearer your_api_key"
  },
  "bot_id": "your_bot_id"
}'


