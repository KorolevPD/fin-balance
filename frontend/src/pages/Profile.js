import { useEffect, useState } from 'react';
import api from '../api';
import { useAuth } from '../context/AuthContext';

function avatarUrl(avatar) {
  if (!avatar) return null;
  return `${api.defaults.baseURL}/auth/me/avatar/${avatar}`;
}

const READONLY_FIELDS = [
  { key: 'email', label: 'Email', type: 'text' },
  { key: 'created_at', label: 'Дата регистрации', type: 'date' },
];

const EDITABLE_FIELDS = [
  { key: 'name', label: 'Имя', type: 'text', maxLength: 255 },
];

function formatDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('ru-RU');
}

function roleLabel(role) {
  return role === 'owner' ? 'Владелец' : 'Участник';
}

export default function Profile() {
  const { user, updateUser } = useAuth();
  const [values, setValues] = useState(() => {
    const initial = {};
    EDITABLE_FIELDS.forEach((field) => {
      initial[field.key] = user?.[field.key] || '';
    });
    return initial;
  });
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [family, setFamily] = useState(null);
  const [members, setMembers] = useState([]);
  const [familyLoading, setFamilyLoading] = useState(true);
  const [familyError, setFamilyError] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [joinLoading, setJoinLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const preview = avatarUrl(user?.avatar);

  const loadFamily = async () => {
    setFamilyLoading(true);
    setFamilyError('');
    try {
      const res = await api.get('/families/my');
      const current = res.data?.[0] || null;
      setFamily(current);
      if (current) {
        const membersRes = await api.get(`/families/${current.id}/members`);
        setMembers(membersRes.data);
      } else {
        setMembers([]);
      }
    } catch (err) {
      setFamilyError(
        err.response?.data?.detail || 'Не удалось загрузить данные семьи'
      );
    } finally {
      setFamilyLoading(false);
    }
  };

  useEffect(() => {
    loadFamily();
  }, []);

  const handleChange = (key) => (e) => {
    setValues((prev) => ({ ...prev, [key]: e.target.value }));
  };

  const handleSaveName = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSaving(true);
    try {
      const res = await api.patch('/auth/me', { name: values.name });
      updateUser(res.data);
      setSuccess('Профиль сохранён.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось сохранить профиль');
    } finally {
      setSaving(false);
    }
  };

  const handleAvatar = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    setSuccess('');
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/auth/me/avatar', formData);
      updateUser(res.data);
      setSuccess('Фото обновлено.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось загрузить фото');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleCopy = async () => {
    if (!family) return;
    try {
      await navigator.clipboard.writeText(family.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setFamilyError('Не удалось скопировать код');
    }
  };

  const handleJoin = async (e) => {
    e.preventDefault();
    setFamilyError('');
    setJoinLoading(true);
    try {
      await api.post('/families/join', { invite_code: inviteCode });
      setInviteCode('');
      await loadFamily();
    } catch (err) {
      setFamilyError(
        err.response?.data?.detail || 'Не удалось присоединиться к семье'
      );
    } finally {
      setJoinLoading(false);
    }
  };

  return (
    <div className="page profile-page">
      <h1>Мой профиль</h1>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <div className="card">
        <h2>Фото профиля</h2>
        <div className="profile-row">
          <div className="avatar-box">
            {preview ? (
              <img src={preview} alt="Фото профиля" className="avatar-img" />
            ) : (
              <div className="avatar-placeholder">
                {(user?.name || user?.email || '?')[0].toUpperCase()}
              </div>
            )}
          </div>
          <div className="avatar-actions">
            <label className="btn btn-secondary avatar-upload-label">
              {uploading ? 'Загрузка...' : 'Выбрать фото'}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                onChange={handleAvatar}
                disabled={uploading}
                className="avatar-file-input"
              />
            </label>
            <p className="muted">JPG, PNG, WEBP или GIF до 5 МБ</p>
          </div>
        </div>
      </div>

      <form className="card" onSubmit={handleSaveName}>
        <h2>Основная информация</h2>
        {EDITABLE_FIELDS.map((field) => (
          <div className="form-group" key={field.key}>
            <label htmlFor={`profile-${field.key}`}>{field.label}</label>
            <input
              id={`profile-${field.key}`}
              type={field.type}
              value={values[field.key]}
              onChange={handleChange(field.key)}
              maxLength={field.maxLength}
            />
          </div>
        ))}
        <button type="submit" className="btn" disabled={saving}>
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
      </form>

      <div className="card">
        <h2>Семья</h2>
        {familyError && <div className="error">{familyError}</div>}
        {familyLoading ? (
          <p className="muted">Загрузка...</p>
        ) : (
          <>
            <p className="muted">
              Семья создаётся автоматически при регистрации. По коду
              приглашения группы объединяются в общий семейный бюджет (до 5
              участников).
            </p>
            <div className="invite-row">
              <span className="family-code">
                Код приглашения: {family ? family.invite_code : '—'}
              </span>
              {family && (
                <button type="button" className="copy-btn" onClick={handleCopy}>
                  {copied ? 'Скопировано' : 'Копировать'}
                </button>
              )}
            </div>
            <h3>Участники ({members.length})</h3>
            {members.length === 0 ? (
              <p className="muted">В семье пока нет участников.</p>
            ) : (
              <ul className="member-list">
                {members.map((member) => (
                  <li key={member.user_id}>
                    <span className="member-email">
                      {member.name || member.email}
                    </span>
                    <span className="member-role">
                      {roleLabel(member.role)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <form onSubmit={handleJoin}>
              <div className="form-group">
                <label htmlFor="familyInviteCode">Код приглашения</label>
                <input
                  id="familyInviteCode"
                  type="text"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  placeholder="Например, ABC12345"
                  maxLength={32}
                  autoComplete="off"
                />
              </div>
              <button type="submit" className="btn" disabled={joinLoading}>
                {joinLoading ? 'Присоединение...' : 'Присоединиться к семье'}
              </button>
            </form>
          </>
        )}
      </div>

      <div className="card">
        <h2>Данные аккаунта</h2>
        {READONLY_FIELDS.map((field) => (
          <div className="form-group" key={field.key}>
            <label htmlFor={`profile-${field.key}`}>{field.label}</label>
            <input
              id={`profile-${field.key}`}
              type={field.type}
              value={field.type === 'date' ? formatDate(user?.[field.key]) : user?.[field.key]}
              readOnly
              disabled
            />
          </div>
        ))}
      </div>
    </div>
  );
}