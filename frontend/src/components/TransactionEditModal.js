import { useState, useEffect, useRef } from 'react';
import api from '../api';

function formatError(err) {
  return err.response?.data?.detail || 'Не удалось сохранить изменения';
}

export default function TransactionEditModal({ transaction, familyId, categories, onClose, onSaved }) {
  const [title, setTitle] = useState(transaction.cleaned_description || transaction.original_description || '');
  const [category, setCategory] = useState(transaction.category || categories[0] || 'Прочее');
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const titleRef = useRef(null);

  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) {
      setError('Название не может быть пустым');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await api.patch(`/families/${familyId}/transactions/${transaction.id}`, {
        cleaned_description: trimmed,
        category,
      });
      onSaved();
    } catch (err) {
      setError(formatError(err));
    } finally {
      setSaving(false);
    }
  };

const handleGenerate = async () => {
    if (generating) return;
    setGenerating(true);
    setError('');
    try {
      const res = await api.post(
        `/families/${familyId}/transactions/${transaction.id}/ai-description`
      );
      const cleaned = res.data?.cleaned_description;
      if (cleaned) {
        setTitle(cleaned);
        titleRef.current?.focus();
      } else {
        setError('AI не смог сформировать описание для этой операции');
      }
    } catch (err) {
      setError(formatError(err));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Редактирование операции"
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Редактирование операции</h2>
        <form onSubmit={handleSubmit}>
          {transaction.cleaned_description && (
            <div className="form-group">
              <label htmlFor="txnOriginal">Оригинальное название</label>
              <input
                id="txnOriginal"
                type="text"
                value={transaction.original_description || ''}
                disabled
                readOnly
              />
            </div>
          )}
          <div className="form-group">
            <label htmlFor="txnTitle">Название</label>
            <div className="field-with-action">
              <input
                id="txnTitle"
                type="text"
                ref={titleRef}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={255}
              />
              <button
                type="button"
                className="advice-generate-btn"
                onClick={handleGenerate}
                disabled={generating}
                aria-label={generating ? 'Генерация...' : 'Сгенерировать название с помощью ИИ'}
                title={generating ? 'Генерация...' : 'Сгенерировать название с помощью ИИ'}
              >
                <img src="/pale-button.png" alt="" />
              </button>
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="txnCategory">Категория</label>
            <select
              id="txnCategory"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {categories.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          {error && <div className="error">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Отмена
            </button>
            <button type="submit" className="btn" disabled={saving}>
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}