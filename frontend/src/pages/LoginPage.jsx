import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register } from '../api.js';

export default function LoginPage({ setToken }) {
    const [userId, setUserId] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [mode, setMode] = useState('login');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async () => {
        setError('');
        if (!userId || !password || (mode === 'register' && !username)) {
            setError('请填写所有必填字段');
            return;
        }
        setLoading(true);
        try {
            const apiCall = mode === 'login' ? login : register;
            const res = await apiCall({ user_id: userId, username, password });
            if (res.access_token) {
                setToken(res.access_token);
                navigate('/chat');
            } else {
                setError('未获得 access_token');
            }
        } catch (e) {
            setError(e.message || '请求失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="card auth">
            <div className="auth-switch">
                <button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>登录</button>
                <button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>注册</button>
            </div>
            <div className="field">
                <label>用户ID</label>
                <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="user_id" />
            </div>
            {mode === 'register' && (
                <div className="field">
                    <label>用户名</label>
                    <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" />
                </div>
            )}
            <div className="field">
                <label>密码</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="密码" />
            </div>
            <button onClick={handleSubmit} disabled={loading}>
                {loading ? '请稍候...' : mode === 'login' ? '登录' : '注册并登录'}
            </button>
            {error && <div className="error">{error}</div>}
        </main>
    );
}
