import { useEffect, useState } from 'react';
import { getHealthData, updateHealthData } from '../api.js';

export default function ProfilePage({ token }) {
    const [form, setForm] = useState({ height: '', weight: '', age: '', gender: '' });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await getHealthData(token);
                setForm({
                    height: data.height ?? '',
                    weight: data.weight ?? '',
                    age: data.age ?? '',
                    gender: data.gender ?? '',
                });
            } catch (e) {
                setError(e.message || '获取健康数据失败');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [token]);

    const handleChange = (key, value) => {
        setForm((f) => ({ ...f, [key]: value }));
    };

    const handleSave = async () => {
        setSaving(true);
        setError('');
        setMessage('');
        try {
            await updateHealthData(token, {
                height: form.height ? Number(form.height) : null,
                weight: form.weight ? Number(form.weight) : null,
                age: form.age ? Number(form.age) : null,
                gender: form.gender || null,
            });
            setMessage('保存成功');
        } catch (e) {
            setError(e.message || '保存失败');
        } finally {
            setSaving(false);
        }
    };

    return (
        <main className="card profile">
            <h2>用户信息</h2>
            {loading ? (
                <div className="muted">加载中...</div>
            ) : (
                <>
                    <div className="field">
                        <label>身高 (cm)</label>
                        <input value={form.height} onChange={(e) => handleChange('height', e.target.value)} />
                    </div>
                    <div className="field">
                        <label>体重 (kg)</label>
                        <input value={form.weight} onChange={(e) => handleChange('weight', e.target.value)} />
                    </div>
                    <div className="field">
                        <label>年龄</label>
                        <input value={form.age} onChange={(e) => handleChange('age', e.target.value)} />
                    </div>
                    <div className="field">
                        <label>性别</label>
                        <select value={form.gender} onChange={(e) => handleChange('gender', e.target.value)}>
                            <option value="">请选择</option>
                            <option value="male">男</option>
                            <option value="female">女</option>
                            <option value="other">其他</option>
                        </select>
                    </div>
                    <button onClick={handleSave} disabled={saving}>{saving ? '保存中...' : '保存'}</button>
                    {message && <div className="ok">{message}</div>}
                    {error && <div className="error">{error}</div>}
                </>
            )}
        </main>
    );
}
