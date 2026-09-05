import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

function isSupported(file) {
  const name = file.name.toLowerCase();
  return name.endsWith('.csv') || name.endsWith('.pdf');
}

function formatDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('ru-RU');
}

function formatAmount(value) {
  const num = Number(value || 0);
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

export default function Upload() {
  const [file, setFile] = useState(null);
  const [families, setFamilies] = useState([]);
  const [familyId, setFamilyId] = useState('');
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [loadingFamilies, setLoadingFamilies] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);

  useEffect(() => {
    api
      .get('/families/my')
      .then((res) => {
        setFamilies(res.data);
        if (res.data.length === 1) setFamilyId(res.data[0].id);
      })
      .catch((err) => setError(err.response?.data?.detail || 'Не удалось загрузить семьи'))
      .finally(() => setLoadingFamilies(false));
  }, []);

  const selectedFamily = families.find((f) => f.id === familyId);

  const loadTransactions = (family) => {
    if (!family) return;
    setTransactionsLoading(true);
    api
      .get(`/families/${family}/transactions`)
      .then((res) => setTransactions(res.data))
      .catch(() => setError('Не удалось загрузить список операций'))
      .finally(() => setTransactionsLoading(false));
  };

  useEffect(() => {
    if (familyId) loadTransactions(familyId);
  }, [familyId]);

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
    if (!file || !familyId) return;
    setError('');
    setResult(null);
    setInfo('');
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post(`/families/${familyId}/transactions/import`, formData, {
        onUploadProgress: (event) => {
          if (!event.total) return;
          const percent = Math.round((event.loaded * 100) / event.total);
          setProgress(Math.min(percent, 100));
        },
      });
      setProgress(100);
      setResult(res.data);
      setInfo(`${res.data.parsed} операций разобрано, ${res.data.created} сохранено, ${res.data.duplicates_skipped} дублей`);
      loadTransactions(familyId);
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось импортировать выписку');
      setProgress(null);
    }
  };

  if (loadingFamilies) {
    return <p className="muted">Загрузка...</p>;
  }

  if (families.length === 0) {
    return (
      <div className="page">
        <h1>Загрузка выписки</h1>
        <div className="card">
          <h2>Нужна семья</h2>
          <p className="muted">
            Загрузка выписки выполняется в семью. Сначала создайте семью или
            присоединитесь к существующей по коду.
          </p>
          <Link to="/family" className="btn">Перейти к семье</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Загрузка выписки</h1>

      {error && <div className="error">{error}</div>}

      {selectedFamily && (
        <p className="muted">Импорт выписки в семью: {selectedFamily.name}</p>
      )}

      <form onSubmit={handleUpload}>
        <div className="form-group">
          <label htmlFor="familySelect">Семья</label>
          <select
            id="familySelect"
            value={familyId}
            onChange={(e) => setFamilyId(e.target.value)}
            required
          >
            {!familyId && <option value="">Выберите семью</option>}
            {families.map((family) => (
              <option key={family.id} value={family.id}>
                {family.name}
              </option>
            ))}
          </select>
        </div>

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
          <div className="upload-progress" role="progressbar" aria-valuenow={progress}>
            <div className="progress-bar" style={{ width: `${progress}%` }} />
            <span className="progress-label">Загрузка... {progress}%</span>
          </div>
        )}

        <div className="upload-actions">
          <button
            type="submit"
            disabled={!file || !familyId || progress !== null}
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

      {info && <div className="success">{info}</div>}

      {result && (
        <div className="card">
          <h2>Файл импортирован</h2>
          <ul className="upload-result">
            <li><span>Имя файла:</span><strong>{file?.name}</strong></li>
            <li><span>Разобрано:</span><strong>{result.parsed}</strong></li>
            <li><span>Создано:</span><strong>{result.created}</strong></li>
            <li><span>Дублей пропущено:</span><strong>{result.duplicates_skipped}</strong></li>
          </ul>
          <Link className="btn" to={`/family/${result.family_id}/dashboard`}>
            Открыть дашборд
          </Link>
        </div>
      )}

      {familyId && (
        <div className="card">
          <h2>Операции семьи ({transactions.length})</h2>
          {transactionsLoading ? (
            <p className="muted">Загрузка...</p>
          ) : transactions.length === 0 ? (
            <p className="muted">Операций пока нет.</p>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Название</th>
                    <th>Категория</th>
                    <th className="num">Сумма</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((txn) => (
                    <tr key={txn.id}>
                      <td className="nowrap">{formatDate(txn.date)}</td>
                      <td>{txn.cleaned_description || txn.original_description || '—'}</td>
                      <td>{txn.category || 'Прочее'}</td>
                      <td className="num">{formatAmount(txn.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}