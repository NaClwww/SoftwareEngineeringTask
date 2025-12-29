import asyncio
import json
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from agent import LLMAgent, QueryRequest, QueryResponse
from user import user_manager, get_current_user_from_token
from database import db_manager
import os
from difflib import SequenceMatcher

# 加载环境变量
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                # 移除export和可能的引号
                key = key.replace("export ", "").strip()
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

app = FastAPI(title="PJGQ Health Agent", description="Health agent with LLM capabilities")

# CORS 设置，允许前端的 POST/OPTIONS 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加安全方案
security = HTTPBearer()

# 初始化LLM代理
llm_agent = LLMAgent()

# 全局锁，确保流式请求串行执行，避免并发交叉
stream_lock = asyncio.Lock()

def is_duplicate_content(content: str, sent_contents: set, min_length: int = 20, similarity_threshold: float = 0.85) -> bool:
    """
    检查内容是否重复。
    只对足够长的内容启用相似度匹配，短内容使用精确匹配。
    
    Args:
        content: 当前内容
        sent_contents: 已发送内容的集合
        min_length: 启用相似度检测的最小内容长度，默认20个字符
        similarity_threshold: 相似度阈值（0-1），默认0.85表示85%相似就认为是重复
    
    Returns:
        True 如果是重复，False 如果是新内容
    """
    if not content.strip():
        return True
    
    # 对于很短的内容，使用精确匹配
    if len(content) < min_length:
        return content in sent_contents
    
    # 对于较长的内容，使用相似度匹配
    for sent in sent_contents:
        # 只有当两个内容都足够长时，才进行相似度计算
        if len(sent) >= min_length:
            similarity = SequenceMatcher(None, content, sent).ratio()
            if similarity >= similarity_threshold:
                return True
        else:
            # 如果已发送内容较短，使用精确匹配
            if content == sent:
                return True
    
    return False

# 用户注册和登录的数据模型
class UserCreate(BaseModel):
    user_id: str
    username: str
    password: str

class UserLogin(BaseModel):
    user_id: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# 健康数据的数据模型
class HealthData(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None

class HealthDataResponse(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    bmi: Optional[float] = None

@app.post("/register", response_model=Token)
async def register_user(user_data: UserCreate):
    """用户注册"""
    try:
        # 创建用户
        success = user_manager.create_user(user_data.user_id, user_data.username, user_data.password)
        if not success:
            return {"error": "用户创建失败"}
        
        # 生成访问令牌
        access_token = user_manager.create_access_token(
            data={"sub": user_data.user_id}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"注册过程中出现错误: {str(e)}"}

@app.post("/login", response_model=Token)
async def login_user(user_data: UserLogin):
    """用户登录"""
    try:
        # 验证用户凭据
        user = user_manager.authenticate_user(user_data.user_id, user_data.password)
        if not user:
            return {"error": "用户名或密码错误"}
        
        # 生成访问令牌
        access_token = user_manager.create_access_token(
            data={"sub": user_data.user_id}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        return {"error": f"登录过程中出现错误: {str(e)}"}

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """受保护的路由示例"""
    try:
        user = get_current_user_from_token(credentials.credentials)
        return {"message": f"Hello, {user['username']}!", "user_id": user["user_id"]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def root():
    return {"message": "Hello from PJGQ Health Agent with LLM capabilities!"}

@app.put("/health-data")
async def update_health_data(health_data: HealthData, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """更新用户的健康数据"""
    try:
        # 验证JWT令牌并获取用户信息
        user = get_current_user_from_token(credentials.credentials)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")
        
        user_id = user.get("user_id")
        if not user_id:
            return {"error": "无法从令牌中获取用户ID"}
        
        # 更新健康数据
        success = user_manager.update_health_data(
            user_id=user_id,
            height=health_data.height,
            weight=health_data.weight,
            age=health_data.age,
            gender=health_data.gender
        )
        
        if success:
            return {"message": "健康数据更新成功"}
        else:
            return {"error": "健康数据更新失败"}
    except Exception as e:
        return {"error": f"更新健康数据时出现错误: {str(e)}"}

@app.get("/health-data", response_model=HealthDataResponse)
async def get_health_data(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取用户的健康数据"""
    try:
        # 验证JWT令牌并获取用户信息
        user = get_current_user_from_token(credentials.credentials)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")
    
        user_id = user.get("user_id")
        if not user_id:
            return {"error": "无法从令牌中获取用户ID"}
        
        # 获取健康数据
        health_data = user_manager.get_health_data(user_id)
        if health_data is None:
            return {"error": "无法获取健康数据"}
        
        # 计算BMI（如果提供了身高和体重）
        bmi = None
        if health_data.get("height") and health_data.get("weight"):
            # BMI = 体重(kg) / (身高(m))^2
            height_m = health_data["height"] / 100  # 将厘米转换为米
            bmi = round(health_data["weight"] / (height_m ** 2), 2)
        
        # 返回包含BMI的健康数据
        return HealthDataResponse(
            height=health_data["height"],
            weight=health_data["weight"],
            age=health_data["age"],
            gender=health_data["gender"],
            bmi=bmi
        )
    except Exception as e:
        return {"error": f"获取健康数据时出现错误: {str(e)}"}

@app.delete("/conversation-history")
async def clear_conversation_history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """清除用户的对话历史"""
    try:
        # 验证JWT令牌并获取用户信息
        user = get_current_user_from_token(credentials.credentials)
        if not user:
            return {"error": "无效的认证令牌"}
        
        user_id = user.get("user_id")
        if not user_id:
            return {"error": "无法从令牌中获取用户ID"}
        
        # 清除对话历史
        deleted_count = db_manager.clear_conversation_history(user_id)
        
        return {"message": f"成功清除 {deleted_count} 条对话历史"}
    except Exception as e:
        return {"error": f"清除对话历史时出现错误: {str(e)}"}

@app.get("/conversation-history")
async def get_conversation_history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取用户的对话历史"""
    try:
        # 验证JWT令牌并获取用户信息
        user = get_current_user_from_token(credentials.credentials)
        if not user:
            return {"error": "无效的认证令牌"}
        
        user_id = user.get("user_id")
        if not user_id:
            return {"error": "无法从令牌中获取用户ID"}
        
        # 获取对话历史
        history = db_manager.get_conversation_history(user_id)
        
        # 按时间顺序排序（从旧到新）
        history.sort(key=lambda x: x["timestamp"])
        
        return {"history": history}
    except Exception as e:
        return {"error": f"获取对话历史时出现错误: {str(e)}"}

@app.post("/stream")
async def stream_llm(request: QueryRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    流式传输LLM响应（使用模拟响应）
    
    Args:
        request: 包含提示词和其他参数的请求对象
        credentials: JWT认证凭据
        
    Returns:
        流式响应
    """
    # 验证JWT令牌并获取用户信息
    try:
        user = get_current_user_from_token(credentials.credentials)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"认证失败: {str(e)}")
    
    # 从JWT令牌中获取user_id并更新请求
    user_id = user.get("user_id")
    if not user_id:
        return {"error": "无法从令牌中获取用户ID"}
    
    # 保存用户的问题到对话历史
    db_manager.create_user(user_id)
    db_manager.save_conversation_turn(user_id, "user", request.prompt)
    
    # 创建新的请求对象，使用从JWT获取的user_id
    updated_request = QueryRequest(
        prompt=request.prompt,
        model=request.model,
        headers=request.headers,
        stream=request.stream,
        bot_id=request.bot_id,
        user_id=user_id  # 使用从JWT获取的user_id
    )
    
    # 定义一个包装器来保存LLM的响应
    async def save_response_and_stream():
        async with stream_lock:  # 串行化流式处理，避免并发导致顺序错乱
            full_response = ""
            
            # 生产者-消费者缓冲区：用来存储完整的行
            line_queue = asyncio.Queue()
            
            # 生产者：读取 chunk 并按行分割放入队列
            async def producer():
                try:
                    async for chunk in llm_agent.stream_custom_llm(updated_request):
                        # 将 chunk 按行分割并放入队列
                        for line in chunk.splitlines():
                            await line_queue.put(line)
                finally:
                    # 发送结束标记
                    await line_queue.put(None)
            
            # 消费者：从队列读取行并处理
            async def consumer():
                nonlocal full_response
                while True:
                    line = await line_queue.get()

                    # None 表示流结束
                    if line is None:
                        break
                    
                    line = line.strip()
                    
                    # 跳过空行
                    if not line:
                        continue
                    # 读取下一行进行配对
                    next_line = await line_queue.get()
                    print(line,"\n",next_line)
                    if line.startswith("event:conversation.message.delta"):

                        next_line = next_line.strip()
                        
                        if next_line.startswith("data:"):
                            try:
                                payload = next_line[5:]  # 移除 "data:" 前缀
                                data_obj = json.loads(payload)
                                content = data_obj.get("content", "")
                                
                                full_response += content
                                yield f"data: {json.dumps({'content': content})}\n\n"
                                
                            except (json.JSONDecodeError, ValueError) as e:
                                # JSON 解析失败
                                print(f"JSON parse error: {e}, payload: {next_line[:100]}")
                        else:
                            # 下一行不是 data:，忽略这一行
                            pass
                    else:
                        continue
            # 同时运行生产者
            producer_task = asyncio.create_task(producer())
            
            # 直接消费消费者产生的值
            async for item in consumer():
                yield item
            
            # 等待生产者完成
            await producer_task
            
            # 保存完整的响应到对话历史
            if full_response:
                print("Full LLM Response:", full_response)
                db_manager.save_conversation_turn(user_id, "assistant", full_response)
            
            # 发送完成标记
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        save_response_and_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )
        
if __name__ == "__main__":
    import uvicorn
    print(f"API-KEY: {os.getenv('COZE_API_KEY')}")
    uvicorn.run(app, host="0.0.0.0", port=8001)
