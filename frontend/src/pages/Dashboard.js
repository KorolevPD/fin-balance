import { useEffect, useState } from 'react';
import { useLocation, useParams, Link } from 'react-router-dom';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import api from '../api';

const CATEGORY_COLORS = [
  '#5b5bea',
  '#f59e0b',
  '#10b981',
  '#ef4444',
  '#06b6d4',
  '#8b5cf6',
  '#ec4899',
  '#84cc16',
  '#f97316',
  '#64748b',
];

function formatAmount(value) {
  const num = Number(value || 0);
  const sign = num < 0 ? '−' : '';
  return `${sign}${Math.abs(num).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

function formatDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('ru-RU');
}

export default function Dashboard() {
  const { id } = useParams();
  const location = useLocation();
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [familyName, setFamilyName] = useState(location.state?.family?.name || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    if (!familyName) {
      api
        .get('/families/my')
        .then((res) => {
          const found = res.data.find((family) => family.id === id);
          if (found && !cancelled) setFamilyName(found.name);
        })
        .catch(() => {});
    }

    api
      .get(`/families/${id}/summary`)
      .then((res) => {
        if (!cancelled) setSummary(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || 'Не удалось загрузить данные дашборда');
      });

    api
      .get(`/families/${id}/transactions`)
      .then((res) => {
        if (!cancelled) setTransactions(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || 'Не удалось загрузить операции');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id, familyName]);

  const categories = summary?.by_category || [];
  const payees = summary?.top_payees || [];
  const monthly = summary?.monthly || [];
  const hasData = categories.length > 0 || transactions.length > 0;

  return (
    <div className="page dashboard-page">
      <p>
        <Link to={`/family/${id}`}>← Назад к семье</Link>
      </p>
      <h1>{familyName ? `Дашборд: ${familyName}` : 'Дашборд расходов'}</h1>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <p className="muted">Загрузка...</p>
      ) : !hasData ? (
        <div className="card">
          <h2>Пока нет данных</h2>
          <p className="muted">Загрузите банковскую выписку, чтобы увидеть статистику расходов.</p>
        </div>
      ) : (
        <>
          <section className="summary-cards" aria-label="Сводка расходов">
            <div className="stat-card">
              <span className="stat-label">Общая сумма расходов</span>
              <span className="stat-value">{summary ? formatAmount(summary.total_amount) : '—'}</span>
            </div>
          </section>

          <section className="card" aria-label="Разбивка по категориям">
            <h2>Расходы по категориям</h2>
            {categories.length === 0 ? (
              <p className="muted">Категорий пока нет.</p>
            ) : (
              <div className="category-layout">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Категория</th>
                      <th className="num">Сумма</th>
                      <th className="num">Операций</th>
                      <th className="num">Доля</th>
                    </tr>
                  </thead>
                  <tbody>
                    {categories.map((item) => {
                      const total = Math.abs(summary.total_amount || 0);
                      const percent = total > 0 ? Math.abs(item.amount) / total * 100 : 0;
                      return (
                        <tr key={item.category}>
                          <td>{item.category}</td>
                          <td className="num">{formatAmount(item.amount)}</td>
                          <td className="num">{item.count ?? 0}</td>
                          <td className="num">
                            <div className="bar-cell">
                              <span className="percent-bar" style={{ width: `${Math.min(percent, 100)}%` }} />
                              <span className="percent-value">{percent.toFixed(1)}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                <div className="chart-box" aria-hidden="true">
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={categories}
                        dataKey="amount"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={(entry) => entry.category}
                      >
                        {categories.map((entry, index) => (
                          <Cell key={entry.category} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatAmount(value)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </section>

          {monthly.length > 0 && (
            <section className="card" aria-label="Динамика по месяцам">
              <h2>Динамика расходов по месяцам</h2>
              <div className="chart-box" aria-hidden="true">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={monthly}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis tickFormatter={(value) => Math.abs(Number(value)).toLocaleString('ru-RU')} />
                    <Tooltip formatter={(value) => formatAmount(value)} />
                    <Bar dataKey="amount" fill="#5b5bea" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}

          <section className="card" aria-label="Топ получателей">
            <h2>Топ получателей платежей</h2>
            {payees.length === 0 ? (
              <p className="muted">Данных пока нет.</p>
            ) : (
              <ul className="payee-list">
                {payees.slice(0, 5).map((item) => (
                  <li key={item.payee}>
                    <span className="payee-name">{item.payee}</span>
                    <span className="payee-count muted">{item.count ?? ''}</span>
                    <span className="payee-amount">{formatAmount(item.amount)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card" aria-label="Список операций">
            <h2>Операции ({transactions.length})</h2>
            {transactions.length === 0 ? (
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
          </section>
        </>
      )}
    </div>
  );
}