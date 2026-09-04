import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

export default function Families() {
  const [families, setFamilies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [error, setError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [joinLoading, setJoinLoading] = useState(false);

  const loadFamilies = async () => {
    try {
      const res = await api.get('/families/my');
      setFamilies(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось загрузить список семей');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFamilies();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setCreateLoading(true);
    try {
      await api.post('/families', { name });
      setName('');
      await loadFamilies();
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка создания семьи');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleJoin = async (e) => {
    e.preventDefault();
    setError('');
    setJoinLoading(true);
    try {
      await api.post('/families/join', { invite_code: inviteCode });
      setInviteCode('');
      await loadFamilies();
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка при присоединении к семье');
    } finally {
      setJoinLoading(false);
    }
  };

  return (
    <div className="page">
      <h1>Моя семья</h1>

      {error && <div className="error">{error}</div>}

      <div className="card">
        <h2>Создать семью</h2>
        <form onSubmit={handleCreate}>
          <div className="form-group">
            <label htmlFor="familyName">Название семьи</label>
            <input
              id="familyName"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например, Семья Ивановых"
              required
              maxLength={255}
            />
          </div>
          <button type="submit" disabled={createLoading}>
            {createLoading ? 'Создание...' : 'Создать семью'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Присоединиться по коду</h2>
        <form onSubmit={handleJoin}>
          <div className="form-group">
            <label htmlFor="inviteCode">Код приглашения</label>
            <input
              id="inviteCode"
              type="text"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              placeholder="Например, ABC12345"
              required
              maxLength={32}
              autoComplete="off"
            />
          </div>
          <button type="submit" disabled={joinLoading}>
            {joinLoading ? 'Присоединение...' : 'Присоединиться'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Мои семьи</h2>
        {loading ? (
          <p className="muted">Загрузка...</p>
        ) : families.length === 0 ? (
          <p className="muted">Вы пока не состоите в семье. Создайте её или присоединитесь по коду.</p>
        ) : (
          <ul className="family-list">
            {families.map((family) => (
              <li key={family.id}>
                <Link to={`/family/${family.id}`} state={{ family }}>
                  <span className="family-name">{family.name}</span>
                  <span className="family-code">Код: {family.invite_code}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}