import { useState } from 'react';
import api from '../api';

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function isCsv(file) {
  return file.name.toLowerCase().endsWith('.csv');
}

export default function Upload() {
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  const reset = () => {
    setFile(null);
    setProgress(null);
    setResult(null);
    setError('');
  };

  const handleFile = (nextFile) => {
    setError('');
    setResult(null);
    setProgress(null);
    if (!nextFile) return;
    if (!isCsv(nextFile)) {
      setFile(null);
      setError('Допускаются только CSV-файлы с расширением .csv');
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
    if (!file) return;
    setError('');
    setResult(null);
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/upload', formData, {
        onUploadProgress: (event) => {
          if (!event.total) return;
          const percent = Math.round((event.loaded * 100) / event.total);
          setProgress(Math.min(percent, 100));
        },
      });
      setProgress(100);
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось загрузить файл');
      setProgress(null);
    }
  };

  return (
    <div className="page">
      <h1>Загрузка файла</h1>

      {error && <div className="error">{error}</div>}

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
            accept=".csv"
            className="upload-input"
            onChange={handleSelect}
          />
          <span className="upload-icon">&#8681;</span>
          <span className="upload-title">
            {file ? `Выбран файл: ${file.name}` : 'Перетащите CSV-файл сюда'}
          </span>
          <span className="upload-hint">или нажмите, чтобы выбрать файл</span>
        </label>

        {progress !== null && (
          <div className="upload-progress" role="progressbar" aria-valuenow={progress}>
            <div className="progress-bar" style={{ width: `${progress}%` }} />
            <span className="progress-label">Загрузка... {progress}%</span>
          </div>
        )}

        <div className="upload-actions">
          <button
            type="submit"
            disabled={!file || progress !== null}
            className="upload-btn"
          >
            {progress === null ? 'Загрузить' : 'Загружается...'}
          </button>
          {file && (
            <button type="button" onClick={reset} className="upload-reset">
              Сбросить
            </button>
          )}
        </div>
      </form>

      {result && (
        <div className="card">
          <h2>Файл загружен</h2>
          <ul className="upload-result">
            <li><span>Имя файла:</span><strong>{result.filename}</strong></li>
            <li><span>Размер:</span><strong>{formatSize(result.size_bytes)}</strong></li>
            <li><span>Тип:</span><strong>{result.content_type}</strong></li>
          </ul>
          <p className="muted">Файл сохранён и будет разобран при обработке выписки.</p>
        </div>
      )}
    </div>
  );
}