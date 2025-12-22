import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database import db_manager
from fastapi import HTTPException, status

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))

class UserManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_user(self, user_id: str, username: str, password: str) -> bool:
        """创建新用户"""
        if not user_id or not username or not password:
            raise ValueError("用户ID、用户名和密码不能为空")
        
        # 检查用户是否已存在
        existing_user = self.db_manager.get_user(user_id)
        if existing_user:
            raise ValueError("用户已存在")
        
        # 创建用户并设置密码
        return self.db_manager.create_user(user_id, username, password)
    
    def authenticate_user(self, user_id: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户凭据"""
        user = self.db_manager.get_user(user_id)
        if not user:
            return None
        
        if self.db_manager.verify_user_password(user_id, password):
            return user
        
        return None
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证访问令牌"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            # 令牌过期
            return None
        except jwt.PyJWTError:
            # 令牌无效
            return None
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """根据令牌获取当前用户"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = self.db_manager.get_user(user_id)
        return user
    
    def update_health_data(self, user_id: str, height: Optional[float] = None, 
                          weight: Optional[float] = None, age: Optional[int] = None, 
                          gender: Optional[str] = None) -> bool:
        """更新用户的健康数据"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建更新语句
                update_fields = []
                params = []
                
                if height is not None:
                    update_fields.append("height = ?")
                    params.append(height)
                
                if weight is not None:
                    update_fields.append("weight = ?")
                    params.append(weight)
                
                if age is not None:
                    update_fields.append("age = ?")
                    params.append(age)
                
                if gender is not None:
                    update_fields.append("gender = ?")
                    params.append(gender)
                
                if not update_fields:
                    return True  # 没有要更新的字段
                
                # 添加用户ID到参数列表
                params.append(user_id)
                
                # 执行更新
                sql = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
                cursor.execute(sql, params)
                
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating health data: {e}")
            return False
    
    def get_health_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的健康数据"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT height, weight, age, gender FROM users WHERE user_id = ?", 
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "height": row[0],
                        "weight": row[1],
                        "age": row[2],
                        "gender": row[3]
                    }
                return None
        except Exception as e:
            print(f"Error getting health data: {e}")
            return None

# 创建全局用户管理实例
user_manager = UserManager(db_manager)

# 认证依赖函数
def get_current_user_from_token(token: str) -> Dict[str, Any]:
    """从令牌获取当前用户信息的依赖函数"""
    user = user_manager.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# 认证装饰器
def auth_required(token: str):
    """认证装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            user = get_current_user_from_token(token)
            kwargs["current_user"] = user
            return func(*args, **kwargs)
        return wrapper
    return decorator
