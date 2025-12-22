import { useState } from 'react';
import { streamLLM } from '../api.js';

export default function ChatPage({ token }) {
    const [prompt, setPrompt] = useState('');
    const [messages, setMessages] = useState([]); // {role:'user'|'assistant', text:string}
    const [streaming, setStreaming] = useState(false);
    const [error, setError] = useState('');

    const handleSend = () => {
        if (!prompt.trim()) return;
        setError('');
        const userMsg = { role: 'user', text: prompt };
        setMessages((prev) => [...prev, userMsg, { role: 'assistant', text: '' }]);
        setPrompt('');
        setStreaming(true);

        streamLLM({
            prompt: userMsg.text,
            token,
            onChunk: (chunk) => {
                setMessages((prev) => {
                    const updated = [...prev];
                    const lastIdx = updated.length - 1;
                    if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                        updated[lastIdx] = { ...updated[lastIdx], text: updated[lastIdx].text + chunk };
                    }
                    return updated;
                });
            },
            onDone: () => setStreaming(false),
            onError: (err) => {
                setStreaming(false);
                setError(err.message || '请求失败');
            },
        });
    };

    return (
        <main className="chat-shell">
            <section className="card chat-panel">
                <label className="label">对话</label>
                <div className="chat-window">
                    {messages.length === 0 && <div className="muted">还没有消息</div>}
                    {messages.map((m, idx) => (
                        <div key={idx} className={`bubble ${m.role}`}>
                            <span className="role">{m.role === 'user' ? '我' : '助手'}</span>
                            <div className="text">{m.text || (streaming && m.role === 'assistant' ? '生成中...' : '')}</div>
                        </div>
                    ))}
                </div>
                {error && <div className="error">{error}</div>}
            </section>
            <section className="card input-panel">
                <label className="label">提问</label>
                <textarea
                    rows={4}
                    placeholder="输入你的问题"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                />
                <div className="actions">
                    <button onClick={handleSend} disabled={streaming}>发送</button>
                    <button className="ghost" disabled={!streaming}>等待完成</button>
                </div>
            </section>
        </main>
    );
}
