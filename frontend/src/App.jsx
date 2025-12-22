import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage.jsx';
import ChatPage from './pages/ChatPage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';

function AppShell() {
    const [token, setToken] = useState(() => localStorage.getItem('token') || '');
    const navigate = useNavigate();

    useEffect(() => {
        if (token) {
            localStorage.setItem('token', token);
        } else {
            localStorage.removeItem('token');
        }
    }, [token]);

    const handleLogout = () => {
        setToken('');
        navigate('/login');
    };

    const isAuthed = Boolean(token);

    return (
        <div className="page">
            <header className="card header">
                <div>
                    <h1>PJGQ Health Agent</h1>
                    <p className="sub">登录后可聊天与编辑健康数据</p>
                </div>
                <nav className="nav">
                    <Link to="/chat">对话</Link>
                    <Link to="/profile">用户信息</Link>
                    {isAuthed ? (
                        <button className="ghost" onClick={handleLogout}>退出</button>
                    ) : (
                        <Link to="/login">登录/注册</Link>
                    )}
                </nav>
            </header>

            <Routes>
                <Route path="/login" element={<LoginPage setToken={setToken} />} />
                <Route path="/chat" element={isAuthed ? <ChatPage token={token} /> : <Navigate to="/login" replace />} />
                <Route path="/profile" element={isAuthed ? <ProfilePage token={token} /> : <Navigate to="/login" replace />} />
                <Route path="*" element={<Navigate to={isAuthed ? '/chat' : '/login'} replace />} />
            </Routes>
        </div>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <AppShell />
        </BrowserRouter>
    );
}
