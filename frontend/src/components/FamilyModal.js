import { useEffect, useRef, useState } from 'react';
import api from '../api';

const TABS = [
  { key: 'create', label: 'Создать' },
  { key: 'join', label: 'Войти' },
];

export default function FamilyModal({ onClose, onJoined }) {
  const [tab, setTab] = useState('create');
  const [family, setFamily] = useState(null);
  const [familyLoading, setFamilyLoading] = useState(true);
  const [familyError, setFamilyError] = useState('');
  const [copied, setCopied] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [joinLoading, setJoinLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    api
      .get('/families/my')
      .then((res) => {
        setFamily(res.data?.[0] || null);
      })
      .catch((err) =>
        setFamilyError(
          err.response?.data?.detail || 'Не удалось загрузить данные семьи'
        )
      )
      .finally(() => setFamilyLoading(false));
  }, []);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (tab === 'join' && inputRef.current) inputRef.current.focus();
  }, [tab]);

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
      const res = await api.post('/families/join', { invite_code: inviteCode });
      onJoined?.(res.data);
    } catch (err) {
      setFamilyError(
        err.response?.data?.detail || 'Не удалось присоединиться к семье'
      );
      setJoinLoading(false);
    }
  };

  const handleTabKeys = (e) => {
    const index = TABS.findIndex((item) => item.key === tab);
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      setTab(TABS[(index + 1) % TABS.length].key);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setTab(TABS[(index - 1 + TABS.length) % TABS.length].key);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setTab(TABS[index].key);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Семья"
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Семья</h2>

        <div
          className="modal-tabs"
          role="tablist"
          aria-label="Действие с семьёй"
          onKeyDown={handleTabKeys}
        >
          {TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              role="tab"
              aria-selected={tab === item.key}
              className={`modal-tab${tab === item.key ? ' active' : ''}`}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {familyError && <div className="error">{familyError}</div>}

        {tab === 'create' ? (
          <div className="family-create-tab">
            {familyLoading ? (
              <p className="muted">Загрузка...</p>
            ) : family ? (
              <>
                <p className="muted">
                  Ваша семья уже создана. Поделитесь кодом — семьи участников
                  объединятся в общий семейный бюджет (до 5 участников).
                </p>
                <div className="invite-row">
                  <span className="family-code">
                    Код приглашения: {family.invite_code}
                  </span>
                  <button
                    type="button"
                    className="copy-btn"
                    onClick={handleCopy}
                  >
                    {copied ? 'Скопировано' : 'Копировать'}
                  </button>
                </div>
              </>
            ) : (
              <p className="muted">Семья не найдена.</p>
            )}
          </div>
        ) : (
          <form className="family-join-tab" onSubmit={handleJoin}>
            <div className="form-group">
              <label htmlFor="familyModalInviteCode">Код приглашения</label>
              <input
                id="familyModalInviteCode"
                ref={inputRef}
                type="text"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                placeholder="Например, ABC12345"
                maxLength={32}
                autoComplete="off"
              />
            </div>
            <p className="muted">
              По коду ваша семья объединится с семьёй владельца кода.
            </p>
            <button
              type="submit"
              className="btn"
              disabled={joinLoading || !inviteCode.trim()}
            >
              {joinLoading ? 'Присоединение...' : 'Присоединиться'}
            </button>
          </form>
        )}

        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={joinLoading}
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}