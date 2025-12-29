import sqlite3
import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path: str = "app.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建用户对话历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建用户信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    username TEXT,
                    password_hash TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建API调用日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    endpoint TEXT NOT NULL,
                    request_data TEXT,
                    response_data TEXT,
                    status_code INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 更新现有表结构（如果需要）
            self._update_table_structure(cursor)
            
            conn.commit()
    
    def _update_table_structure(self, cursor):
        """更新现有表结构"""
        # 检查users表是否有password_hash列，如果没有则添加
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "password_hash" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        
        # 添加健康数据相关列
        if "height" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN height REAL")
        
        if "weight" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN weight REAL")
        
        if "age" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN age INTEGER")
        
        if "gender" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN gender TEXT")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        else:
            conn.commit()
        finally:
            conn.close()
    
    def save_conversation_turn(self, user_id: str, role: str, content: str) -> int:
        """保存对话轮次（有去重）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在完全相同的对话轮次（同一用户，同一角色，同一内容的最后一条）
            cursor.execute(
                "SELECT id FROM conversation_history WHERE user_id = ? AND role = ? AND content = ? ORDER BY timestamp DESC LIMIT 1",
                (user_id, role, content)
            )
            existing = cursor.fetchone()
            
            # 如果已存在，不重复插入
            if existing:
                return existing["id"]
            
            # 新内容才插入
            cursor.execute(
                "INSERT INTO conversation_history (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            return cursor.lastrowid
    
    def get_conversation_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取用户对话历史，限制返回最近的10轮对话（20条消息）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, timestamp FROM conversation_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            # 按时间顺序排序（从旧到新）
            sorted_rows = sorted(rows, key=lambda x: x["timestamp"])
            return [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in sorted_rows]
    
    def clear_conversation_history(self, user_id: str) -> int:
        """清空用户对话历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
            return cursor.rowcount
    
    def create_user(self, user_id: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """创建用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if password:
                    password_hash = self._hash_password(password)
                    cursor.execute(
                        "INSERT OR IGNORE INTO users (user_id, username, password_hash) VALUES (?, ?, ?)",
                        (user_id, username, password_hash)
                    )
                else:
                    cursor.execute(
                        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                        (user_id, username)
                    )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def set_user_password(self, user_id: str, password: str) -> bool:
        """设置用户密码"""
        try:
            password_hash = self._hash_password(password)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE user_id = ?",
                    (password_hash, user_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error setting user password: {e}")
            return False
    
    def verify_user_password(self, user_id: str, password: str) -> bool:
        """验证用户密码"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT password_hash FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return self._verify_password(password, row[0])
                return False
        except Exception as e:
            print(f"Error verifying user password: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """对密码进行哈希处理"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码哈希"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == password_hash
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def log_api_call(self, endpoint: str, user_id: Optional[str] = None, 
                     request_data: Optional[Dict] = None, response_data: Optional[Dict] = None, 
                     status_code: Optional[int] = None) -> int:
        """记录API调用日志"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO api_logs (user_id, endpoint, request_data, response_data, status_code) VALUES (?, ?, ?, ?, ?)",
                (user_id, endpoint, json.dumps(request_data) if request_data else None, 
                 json.dumps(response_data) if response_data else None, status_code)
            )
            return cursor.lastrowid

# 全局数据库实例
db_manager = DatabaseManager()
