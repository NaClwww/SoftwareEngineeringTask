import httpx
import os
import json
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator, List
from pydantic import BaseModel
from database import db_manager

class LLMResponse(BaseModel):
    content: str
    is_complete: bool = False

class QueryRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    stream: bool = False
    bot_id: Optional[str] = None
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str

class LLMAgent:
    def __init__(self):
        self.client = httpx.AsyncClient()
    
    async def query_simulation(self, request: QueryRequest) -> QueryResponse:
        """模拟查询"""
        return QueryResponse(response=f"模拟响应: {request.prompt}")
    
    async def query_openai(self, request: QueryRequest) -> QueryResponse:
        """查询OpenAI API"""
        # 这里是简化的实现
        return QueryResponse(response=f"OpenAI响应: {request.prompt}")
    
    async def query_custom_llm(self, request: QueryRequest) -> QueryResponse:
        """查询自定义LLM API"""
        # 这里是简化的实现
        return QueryResponse(response=f"自定义LLM响应: {request.prompt}")
    
    async def stream_simulation(self, request: QueryRequest) -> AsyncGenerator[str, None]:
        """模拟流式传输"""
        response_text = f"模拟流式响应: {request.prompt}"
        for i in range(0, len(response_text), 10):
            chunk = response_text[i:i+10]
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            await asyncio.sleep(0.1)
        yield "data: [DONE]\n\n"
    
    async def stream_openai(self, request: QueryRequest) -> AsyncGenerator[str, None]:
        """流式传输OpenAI API响应"""
        # 简化实现
        response_text = f"OpenAI流式响应: {request.prompt}"
        for i in range(0, len(response_text), 10):
            chunk = response_text[i:i+10]
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            await asyncio.sleep(0.1)
        yield "data: [DONE]\n\n"
    
    async def stream_custom_llm(self, request: QueryRequest) -> AsyncGenerator[str, None]:
        # 实现Coze API的流式传输
        coze_api_url = "https://api.coze.cn/v3/chat?"
        
        # 获取环境变量中的API密钥
        api_key = os.getenv('COZE_API_KEY')
        
        # 处理API密钥，移除可能的"Bearer "前缀后再添加
        if api_key:
            # 移除可能存在的"Bearer "前缀
            clean_api_key = api_key.replace("Bearer ", "")
            authorization_header = f"Bearer {clean_api_key}"
        else:
            authorization_header = ""
        
        # 构建请求头
        headers = {
            "Authorization": authorization_header,
            "Content-Type": "application/json"
        }
        print(headers)
    
        # 加载用户的对话历史作为上下文（现在数据库层已限制返回数量）
        context = self.load_context(request.user_id) if request.user_id else []
        
        # 构建请求体，根据用户反馈bot_id是固定的，不从请求中获取
        body = {
            "bot_id": os.getenv("DEFAULT_BOT_ID", "default_bot_id"),
            "user_id": request.user_id or "anonymous_user",
            "stream": True,
            "additional_messages": [
            ],
            "parameters": {}
        }
        
        # 如果有对话历史，则将其添加到请求中作为上下文
        if context:
            # 将历史对话添加到additional_messages的开头
            for msg in context:
                body["additional_messages"].append({
                    "content": msg["content"],
                    "content_type": "text",
                    "role": msg["role"],
                    "type": "question" if msg["role"] == "user" else "answer"
                })
        print("Request Body:", json.dumps(body, ensure_ascii=False, indent=2))
        try:
            # 发起流式请求
            async with self.client.stream(
                "POST", 
                coze_api_url, 
                headers=headers, 
                json=body
            ) as response:
                async for chunk in response.aiter_text():
                    if chunk:
                        yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    def load_context(self, user_id: str) -> List[Dict[str, Any]]:
        """加载用户对话历史"""
        # 使用数据库加载对话历史
        history = db_manager.get_conversation_history(user_id)
        # 转换为旧格式以保持兼容性
        return [{"role": item["role"], "content": item["content"]} for item in history]
    
    def save_context(self, user_id: str, context: List[Dict[str, Any]]) -> None:
        """保存用户对话历史"""
        # 确保用户存在
        db_manager.create_user(user_id)
        
        # 保存每个对话轮次
        for turn in context:
            db_manager.save_conversation_turn(user_id, turn["role"], turn["content"])
    
    async def __del__(self):
        if hasattr(self, 'client'):
            await self.client.aclose()
