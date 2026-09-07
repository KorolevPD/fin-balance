import { useEffect, useState } from 'react';
import api from '../api';

function isSupported(file) {
  const name = file.name.toLowerCase();
  return name.endsWith('.csv') || name.endsWith('.pdf');
}

export default function UploadModal({ familyId, adviceScope = 'personal', onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [familyIdState, setFamilyIdState] = useState(familyId || '');
  const [familyLoading, setFamilyLoading] = useState(!familyId);
  const [progress, setProgress] = useState(null);
  const [done, setDone] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    if (familyId) return;
    api
      .get('/families/my')
      .then((res) => {
        const list = res.data || [];
        if (list.length > 0) setFamilyIdState(list[0].id);
      })
      .catch((err) => setError(err.response?.data?.detail || 'Не удалось загрузить данные семьи'))
      .finally(() => setFamilyLoading(false));
  }, [familyId]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !(progress !== null && !done)) onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [progress, done, onClose]);

  const handleClose = () => {
    if (progress !== null && !done) return;
    onClose();
  };

  const reset = () => {
    setFile(null);
    setProgress(null);
    setResult(null);
    setDone(false);
    setError('');
  };

  const handleFile = (nextFile) => {
    setError('');
    setResult(null);
    setProgress(null);
    setDone(false);
    if (!nextFile) return;
    if (!isSupported(nextFile)) {
      setFile(null);
      setError('Допускаются только CSV- и PDF-файлы выписки');
      return;
    }
    setFile(nextFile);
  };

  const handleSelect = (e) => {
    handleFile(e.target.files[0]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const nextFile = e.dataTransfer.files && e.dataTransfer.files[0];
    handleFile(nextFile);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || done) return;
    setError('');
    setResult(null);
    setProgress(0);
    setDone(false);

    if (!familyIdState) {
      setError('Семья не найдена. Перезайдите в аккаунт.');
      setProgress(null);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post(
        `/families/${familyIdState}/transactions/import`,
        formData,
        {
          params: { advice_scope: adviceScope },
          onUploadProgress: (event) => {
            if (!event.total) return;
            const percent = Math.round((event.loaded * 100) / event.total);
            setProgress(Math.min(percent, 100));
          },
        }
      );
      setProgress(100);
      setDone(true);
      setResult(res.data);
      onUploaded?.(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось импортировать выписку');
      setProgress(null);
      setDone(false);
    }
  };

  const handleNewFile = () => {
    const input = document.getElementById('csvFile');
    if (input) input.value = '';
    reset();
    if (input) input.click();
  };

  const isUploading = progress !== null && !done;
  const info = done && result
    ? `${result.parsed} операций разобрано, ${result.created} сохранено, ${result.duplicates_skipped} дублей`
    : '';

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Загрузка выписки"
        onClick={(event) => event.stopPropagation()}
      >
        <h2>Загрузка выписки</h2>

        {error && <div className="error">{error}</div>}

        {familyLoading ? (
          <p className="muted">Загрузка...</p>
        ) : done && info ? (
          <>
            <p className="success">{info}</p>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={handleNewFile}>
                Загрузить ещё
              </button>
              <button type="button" className="btn" onClick={onClose}>
                Готово
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={handleUpload}>
            <label
              htmlFor="csvFile"
              className={`upload-zone${dragOver ? ' drag-over' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <input
                id="csvFile"
                type="file"
                accept=".csv,.pdf,application/pdf"
                className="upload-input"
                onChange={handleSelect}
              />
              <span className="upload-icon">&#8681;</span>
              <span className="upload-title">
                {file ? `Выбран файл: ${file.name}` : 'Перетащите файл выписки (CSV или PDF) сюда'}
              </span>
              <span className="upload-hint">или нажмите, чтобы выбрать файл</span>
            </label>

            {progress !== null && (
              <div
                className={`upload-progress${done ? ' done' : ''}`}
                role="progressbar"
                aria-valuenow={progress}
              >
                <div className="progress-bar" style={{ width: `${progress}%` }} />
                <span className={`progress-label${done ? ' done' : ''}`}>
                  {done ? '\u2713 Готово' : `Загрузка... ${progress}%`}
                </span>
              </div>
            )}

            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={isUploading}>
                Отмена
              </button>
              {file && (
                <button type="button" className="btn btn-secondary" onClick={reset} disabled={isUploading}>
                  Сбросить
                </button>
              )}
              <button
                type="submit"
                className="btn"
                disabled={!file || !familyIdState || isUploading}
              >
                {isUploading ? 'Загружается...' : 'Загрузить'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}