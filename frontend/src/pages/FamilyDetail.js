import { useEffect, useState } from 'react';
import { useLocation, useParams, Link } from 'react-router-dom';
import api from '../api';

export default function FamilyDetail() {
  const { id } = useParams();
  const location = useLocation();
  const [family, setFamily] = useState(location.state?.family || null);
  const [members, setMembers] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!family) {
      api
        .get('/families/my')
        .then((res) => {
          const found = res.data.find((f) => f.id === id);
          if (found) setFamily(found);
        })
        .catch(() => setError('Не удалось загрузить данные семьи'));
    }
  }, [family, id]);

  useEffect(() => {
    api
      .get(`/families/${id}/members`)
      .then((res) => setMembers(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Не удалось загрузить участников'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleCopy = () => {
    if (!family) return;
    navigator.clipboard
      .writeText(family.invite_code)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => setError('Не удалось скопировать код'));
  };

  const roleLabel = (role) => (role === 'owner' ? 'Владелец' : 'Участник');

  return (
    <div className="page">
      <p>
        <Link to="/family">← Моя семья</Link>
      </p>

      {!family && loading && <p className="muted">Загрузка...</p>}

      {family && (
        <div className="card">
          <h1>{family.name}</h1>
          <div className="invite-row">
            <span className="family-code">Код приглашения: {family.invite_code}</span>
            <button type="button" className="copy-btn" onClick={handleCopy}>
              {copied ? 'Скопировано' : 'Копировать'}
            </button>
          </div>
          <p className="muted">Поделитесь этим кодом, чтобы пригласить члена семьи.</p>
        </div>
      )}

      {error && <div className="error">{error}</div>}

      <div className="card">
        <h2>Участники ({members.length})</h2>
        {loading ? (
          <p className="muted">Загрузка...</p>
        ) : members.length === 0 ? (
          <p className="muted">В семье пока нет участников.</p>
        ) : (
          <ul className="member-list">
            {members.map((member) => (
              <li key={member.user_id}>
                <span className="member-email">{member.email}</span>
                <span className="member-role">{roleLabel(member.role)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}