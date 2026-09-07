import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api';
import { CATEGORIES } from '../categories';
import TransactionEditModal from '../components/TransactionEditModal';

const PAGE_SIZE = 50;

function formatAmount(value, type) {
  const num = Number(value || 0);
  const isIncome = type === 'income';
  const sign = isIncome ? '+' : '−';
  return `${sign} ${Math.abs(num).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

function amountClassName(type) {
  return type === 'income' ? 'amount-income' : 'amount-expense';
}

function formatDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('ru-RU');
}

export default function Operations() {
  const { id } = useParams();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null);
  const [hideIncomes, setHideIncomes] = useState(true);

  const loadData = useCallback(() => {
    setLoading(true);
    setError('');
    api
      .get(`/families/${id}/transactions`)
      .then((res) => setTransactions(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Не удалось загрузить операции'))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    setPage(1);
  }, [id]);

  useEffect(() => {
    loadData();
  }, [id, loadData]);

  const visibleTransactions = useMemo(() => {
    const visible = transactions.filter((txn) => !txn.is_self_transfer);
    if (!hideIncomes) return visible;
    return visible.filter((txn) => txn.type !== 'income');
  }, [transactions, hideIncomes]);

  const sorted = useMemo(() => {
    return [...visibleTransactions].sort((a, b) => {
      const da = a.date ? new Date(a.date).getTime() : 0;
      const db = b.date ? new Date(b.date).getTime() : 0;
      return db - da;
    });
  }, [visibleTransactions]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = sorted.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const handleSaved = () => {
    setEditing(null);
    loadData();
  };

  return (
    <div className="page">
      <p>
        <Link to={`/family/${id}/dashboard`}>← Назад к дашборду</Link>
      </p>
      <h1>Все операции</h1>

      {error && <div className="error">{error}</div>}

      {loading && transactions.length === 0 ? (
        <p className="muted">Загрузка...</p>
      ) : (
        <div className="card">
          <div className="card-header">
            <h2>Операции ({sorted.length})</h2>
            {transactions.length > 0 && (
              <div className="card-header-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-small"
                  aria-pressed={hideIncomes}
                  onClick={() => setHideIncomes((value) => !value)}
                >
                  {hideIncomes ? 'Показать пополнения' : 'Убрать пополнения'}
                </button>
              </div>
            )}
          </div>
          {pageItems.length === 0 ? (
            <p className="muted">
              {transactions.length > 0 ? 'Все пополнения скрыты кнопкой выше.' : 'Операций пока нет.'}
            </p>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Название</th>
                    <th>Категория</th>
                    <th className="num">Сумма</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((txn) => (
                    <tr key={txn.id}>
                      <td className="nowrap">{formatDate(txn.date)}</td>
                      <td>{txn.cleaned_description || txn.original_description || '—'}</td>
                      <td>{txn.category || 'Прочее'}</td>
                      <td className={`num ${amountClassName(txn.type)}`}>{formatAmount(txn.amount, txn.type)}</td>
                      <td className="actions-cell">
                        <button
                          type="button"
                          className="btn btn-small"
                          onClick={() => setEditing(txn)}
                        >
                          Изменить
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {totalPages > 1 && (
            <div className="pagination">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={safePage <= 1}
                onClick={() => setPage(safePage - 1)}
              >
                ← Назад
              </button>
              <span className="muted">
                Страница {safePage} из {totalPages}
              </span>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={safePage >= totalPages}
                onClick={() => setPage(safePage + 1)}
              >
                Далее →
              </button>
            </div>
          )}
        </div>
      )}

      {editing && (
        <TransactionEditModal
          transaction={editing}
          familyId={id}
          categories={CATEGORIES}
          onClose={() => setEditing(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}