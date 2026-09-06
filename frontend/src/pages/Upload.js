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

function formatAmount(value, type) {
  const num = Number(value || 0);
  const isIncome = type === 'income';
  const sign = isIncome ? '+' : '−';
  return `${sign} ${Math.abs(num).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

function amountClassName(type) {
  return type === 'income' ? 'amount-income' : 'amount-expense';
}

export default function Upload() {
  const [file, setFile] = useState(null);
  const [familyId, setFamilyId] = useState('');
  const [familyLoading, setFamilyLoading] = useState(true);
  const [progress, setProgress] = useState(null);
  const [done, setDone] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);

  useEffect(() => {
    api
      .get('/families/my')
      .then((res) => {
        const list = res.data || [];
        if (list.length > 0) setFamilyId(list[0].id);
      })
      .catch((err) => setError(err.response?.data?.detail || 'Не удалось загрузить данные семьи'))
      .finally(() => setFamilyLoading(false));
  }, []);

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
    setInfo('');
    setProgress(0);
    setDone(false);

    if (!familyId) {
      setError('Семья не найдена. Перезайдите в аккаунт.');
      setProgress(null);
      return;
    }

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
      setDone(true);
      setResult(res.data);
      setInfo(`${res.data.parsed} операций разобрано, ${res.data.created} сохранено, ${res.data.duplicates_skipped} дублей`);
      loadTransactions(familyId);
      const input = document.getElementById('csvFile');
      if (input) input.value = '';
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось импортировать выписку');
      setProgress(null);
      setDone(false);
    }
  };

  const handleBtnClick = (e) => {
    if (done) {
      e.preventDefault();
      const input = document.getElementById('csvFile');
      if (input) input.click();
    }
  };

  if (familyLoading) {
    return <p className="muted">Загрузка...</p>;
  }

  return (
    <div className="page">
      <h1>Загрузка выписки</h1>

      {error && <div className="error">{error}</div>}

      <p className="muted">
        Выписка импортируется в семейный бюджет. Семья создаётся автоматически
        при регистрации, участники добавляются по коду приглашения в профиле.
      </p>

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
          <div className={`upload-progress${done ? ' done' : ''}`} role="progressbar" aria-valuenow={progress}>
            <div className="progress-bar" style={{ width: `${progress}%` }} />
            <span className={`progress-label${done ? ' done' : ''}`}>
              {done ? '\u2713 Готово' : `Загрузка... ${progress}%`}
            </span>
          </div>
        )}

        <div className="upload-actions">
          <button
            type="submit"
            onClick={handleBtnClick}
            disabled={!file || !familyId || (progress !== null && !done)}
            className="upload-btn"
          >
            {done ? 'Загрузите файл' : progress === null ? 'Загрузить' : 'Загружается...'}
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
                      <td className={`num ${amountClassName(txn.type)}`}>{formatAmount(txn.amount, txn.type)}</td>
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