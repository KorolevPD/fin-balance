import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
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
import { CATEGORIES } from '../categories';
import TransactionEditModal from '../components/TransactionEditModal';
import UploadModal from '../components/UploadModal';
import { useAuth } from '../context/AuthContext';

const CATEGORY_COLORS = [
  '#5b5bea',
  '#41dc6f',
  '#8a1dd7',
  '#d4c349',
  '#26b3cf',
  '#e43a96',
  '#54c62f',
  '#4841dc',
  '#d75c1d',
  '#49d4a0',
  '#c126cf',
  '#c0e43a',
  '#2f7ac6',
  '#dc4161',
  '#1dd72d',
  '#7e49d4',
  '#cf9726',
  '#3ae4dd',
  '#c62fa0',
  '#88dc41',
  '#1d3cd7',
  '#d45b49',
  '#26cf6d',
  '#b33ae4',
];

const FALLBACK_COLORS = [
  '#94a3b8',
  '#57534e',
  '#a8a29e',
  '#78716c',
  '#cbd5e1',
  '#64748b',
];

const DYNAMICS_PERIODS = {
  year: { source: 'yearly', dataKey: 'year', label: 'По годам' },
  month: { source: 'monthly', dataKey: 'month', label: 'По месяцам' },
  day: { source: 'daily', dataKey: 'day', label: 'По дням' },
};

function formatDynamicsTick(value, period) {
  const parts = String(value || '').split('-');
  if (period === 'day' && parts.length === 3) {
    return `${parts[2]}.${parts[1]}`;
  }
  if (period === 'month' && parts.length === 2) {
    return `${parts[1]}.${parts[0]}`;
  }
  return String(value || '');
}

function getCategoryColor(category) {
  const index = CATEGORIES.indexOf(category);
  if (index !== -1) return CATEGORY_COLORS[index];
  let hash = 0;
  for (let i = 0; i < category.length; i += 1) {
    hash = (hash * 31 + category.charCodeAt(i)) | 0;
  }
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
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

function formatAmountPlain(value) {
  return `${Math.abs(Number(value || 0)).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

function formatDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('ru-RU');
}

function sortIndicator(key, sortBy, sortDir) {
  if (sortBy === key) return sortDir === 'asc' ? '▲' : '▼';
  return '▼';
}

export default function Dashboard() {
  const { id } = useParams();
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(null);
  const [sortBy, setSortBy] = useState('date');
  const [sortDir, setSortDir] = useState('desc');
  const [catSortBy, setCatSortBy] = useState('amount');
  const [catSortDir, setCatSortDir] = useState('desc');
  const [hideIncomes, setHideIncomes] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [viewScope, setViewScope] = useState('personal');
  const [dynamicsPeriod, setDynamicsPeriod] = useState('month');
  const [advices, setAdvices] = useState([]);
  const [adviceIndex, setAdviceIndex] = useState(0);
  const [advicesLoading, setAdvicesLoading] = useState(true);
  const [adviceGenerating, setAdviceGenerating] = useState(false);
  const [adviceError, setAdviceError] = useState('');

  const members = summary?.family_members || [];
  const userIsAlone = members.length <= 1;
  const otherMembersHaveStatements = !!summary?.other_members_have_statements;
  const personalOnly = userIsAlone || !otherMembersHaveStatements;
  const effectiveScope = personalOnly ? 'personal' : viewScope;
  const hasAiAccess = user?.server_ai_key || user?.has_ai_key;

  const handleSort = (key) => {
    if (sortBy === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortDir(key === 'category' ? 'asc' : 'desc');
    }
  };

  const handleCatSort = (key) => {
    if (catSortBy === key) {
      setCatSortDir(catSortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setCatSortBy(key);
      setCatSortDir(key === 'category' ? 'asc' : 'desc');
    }
  };

  const visibleTransactions = useMemo(() => {
    const visible = transactions.filter((txn) => !txn.is_self_transfer);
    if (!hideIncomes) return visible;
    return visible.filter((txn) => txn.type !== 'income');
  }, [transactions, hideIncomes]);

  const sortedTransactions = useMemo(() => {
    if (visibleTransactions.length === 0) return visibleTransactions;
    const sorted = [...visibleTransactions].sort((a, b) => {
      let cmp = 0;
      if (sortBy === 'date') {
        const da = a.date ? new Date(a.date).getTime() : 0;
        const db = b.date ? new Date(b.date).getTime() : 0;
        cmp = da - db;
      } else if (sortBy === 'category') {
        const ca = (a.category || 'Прочее').toLowerCase();
        const cb = (b.category || 'Прочее').toLowerCase();
        cmp = ca.localeCompare(cb, 'ru');
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [visibleTransactions, sortBy, sortDir]);

  const loadData = useCallback(() => {
    setLoading(true);
    setError('');
    const params = effectiveScope === 'personal' && user?.id ? { user_id: user.id } : undefined;
    api
      .get(`/families/${id}/summary`, { params })
      .then((res) => setSummary(res.data))
      .catch((err) => {
        setError(err.response?.data?.detail || 'Не удалось загрузить данные дашборда');
      });

    api
      .get(`/families/${id}/transactions`, { params })
      .then((res) => setTransactions(res.data))
      .catch((err) => {
        setError(err.response?.data?.detail || 'Не удалось загрузить операции');
      })
      .finally(() => setLoading(false));
  }, [id, user?.id, effectiveScope]);

  useEffect(() => {
    loadData();
  }, [id, loadData, effectiveScope]);

  const handleSaved = () => {
    setEditing(null);
    loadData();
  };

  const handleDeleteFile = async (filename) => {
    const confirmed = window.confirm(
      `Удалить выписку «${filename}»? Все её операции будут удалены безвозвратно.`
    );
    if (!confirmed) return;
    setError('');
    try {
      await api.delete(`/families/${id}/transactions`, {
        params: { source_file: filename },
      });
      loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось удалить выписку');
    }
  };

  const generateAdvice = useCallback(async () => {
    setAdviceGenerating(true);
    setAdviceError('');
    try {
      const res = await api.post(`/families/${id}/advices`);
      const advice = res.data?.advice;
      if (advice) {
        setAdvices((prev) => [advice, ...prev]);
        setAdviceIndex(0);
      }
    } catch (err) {
      setAdviceError(err.response?.data?.detail || 'Не удалось получить новый совет');
      throw err;
    } finally {
      setAdviceGenerating(false);
    }
  }, [id]);

  const loadAdvices = useCallback(async () => {
    setAdvicesLoading(true);
    setAdviceError('');
    try {
      const res = await api.get(`/families/${id}/advices`);
      const list = res.data || [];
      setAdvices(list);
      setAdviceIndex(0);
      if (list.length === 0 && hasAiAccess) {
        await generateAdvice();
      }
    } catch (err) {
      setAdviceError(err.response?.data?.detail || 'Не удалось загрузить советы');
    } finally {
      setAdvicesLoading(false);
    }
  }, [id, hasAiAccess, generateAdvice]);

  useEffect(() => {
    loadAdvices();
  }, [id, hasAiAccess, loadAdvices]);

  const handleUploaded = () => {
    loadData();
    if (hasAiAccess) {
      generateAdvice().catch(() => {});
    }
  };

  const currentAdvice = advices.length > 0 ? advices[adviceIndex] : null;

  const files = summary?.uploaded_files || [];
  const total = Math.abs(summary?.total_amount || 0);
  const categoryList = useMemo(() => {
    const source = summary?.by_category || [];
    if (source.length === 0) return source;
    let list = source;
    if (!source.some((entry) => entry.category === 'Прочее')) {
      list = [...source, { category: 'Прочее', amount: 0, count: 0 }];
    }
    return list;
  }, [summary]);
  const categories = useMemo(() => {
    if (categoryList.length === 0) return categoryList;
    return [...categoryList].sort((a, b) => {
      let cmp = 0;
      if (catSortBy === 'category') {
        cmp = (a.category || '').localeCompare(b.category || '', 'ru');
      } else if (catSortBy === 'amount') {
        cmp = Math.abs(Number(a.amount || 0)) - Math.abs(Number(b.amount || 0));
      } else if (catSortBy === 'count') {
        cmp = (a.count ?? 0) - (b.count ?? 0);
      } else if (catSortBy === 'share') {
        const sa = total > 0 ? (Math.abs(Number(a.amount || 0)) / total) * 100 : 0;
        const sb = total > 0 ? (Math.abs(Number(b.amount || 0)) / total) * 100 : 0;
        cmp = sa - sb;
      }
      return catSortDir === 'asc' ? cmp : -cmp;
    });
  }, [categoryList, catSortBy, catSortDir, total]);
  const chartCategories = categoryList.filter((item) => Math.abs(Number(item.amount || 0)) > 0);
  const payees = summary?.top_payees || [];
  const dynamics = DYNAMICS_PERIODS[dynamicsPeriod];
  const dynamicsData = summary?.[dynamics.source] || [];
  const hasData = categories.length > 0 || transactions.length > 0;

  return (
    <div className="page dashboard-page">
      {error && <div className="error">{error}</div>}

      {loading ? (
        <p className="muted">Загрузка...</p>
      ) : (
        <>
          {(hasData || effectiveScope === 'personal') && (
            <section className="summary-cards" aria-label="Сводка расходов">
              <div className="stat-card">
                <span className="stat-label">Общая сумма расходов</span>
                <div className="stat-card-row">
                  <span className="stat-value">
                    {summary ? formatAmountPlain(summary.total_amount) : '—'}
                  </span>
                  {!personalOnly && (
                    <div
                      className="scope-toggle"
                      role="group"
                      aria-label="Область расходов"
                    >
                      <button
                        type="button"
                        className={`scope-toggle-btn${viewScope === 'family' ? ' active' : ''}`}
                        aria-pressed={viewScope === 'family'}
                        onClick={() => setViewScope('family')}
                      >
                        В семье
                      </button>
                      <button
                        type="button"
                        className={`scope-toggle-btn${viewScope === 'personal' ? ' active' : ''}`}
                        aria-pressed={viewScope === 'personal'}
                        onClick={() => setViewScope('personal')}
                      >
                        Личные
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          <div className="demo-grid">
            {effectiveScope === 'family' && (
              <section className="card demo-block" aria-label="Члены семьи">
                <h2>Члены семьи</h2>
                {members.length === 0 ? (
                  <p className="muted">В семье пока нет участников.</p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Имя</th>
                        <th className="num">Траты</th>
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((member) => (
                        <tr key={member.user_id || member.email}>
                          <td>{member.name || member.email}</td>
                          <td className="num">{formatAmountPlain(member.total_expenses)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </section>
            )}

            <section
              className={`card demo-block${effectiveScope === 'family' ? '' : ' demo-block-wide'}`}
              aria-label="Траты по категориям"
            >
              <h2>Траты по категориям</h2>
              {chartCategories.length === 0 ? (
                <p className="muted">Категорий пока нет.</p>
              ) : (
                <div className="chart-box demo-chart">
                  <ResponsiveContainer width="100%" height={308}>
                    <PieChart>
                      <Pie
                        data={chartCategories}
                        dataKey="amount"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                      >
                        {chartCategories.map((entry) => (
                          <Cell
                            key={entry.category}
                            fill={getCategoryColor(entry.category)}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatAmount(value)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </section>

            <section className="card demo-block" aria-label="AI-совет">
              <div className="card-header">
                <h2>Совет от AI</h2>
                {currentAdvice && (
                  <button
                    type="button"
                    className="advice-generate-btn"
                    onClick={() => generateAdvice()}
                    disabled={adviceGenerating}
                    aria-label={adviceGenerating ? 'Генерация...' : 'Новый совет'}
                    title={adviceGenerating ? 'Генерация...' : 'Новый совет'}
                  >
                    <img src="/pale-button.png" alt="" />
                  </button>
                )}
              </div>
              {!hasAiAccess ? (
                <p className="muted">
                  Подключите ключ GigaChat в профиле, чтобы получать советы по
                  расходам.{' '}
                  <Link to="/profile" className="card-header-link">
                    Настроить →
                  </Link>
                </p>
              ) : advicesLoading ? (
                <p className="muted">Загрузка советов...</p>
              ) : adviceError ? (
                <>
                  <p className="muted">{adviceError}</p>
                  <button
                    type="button"
                    className="btn btn-small"
                    onClick={() => generateAdvice()}
                    disabled={adviceGenerating}
                  >
                    {adviceGenerating ? 'Генерация...' : 'Получить совет'}
                  </button>
                </>
              ) : currentAdvice ? (
                <>
                  <p className="advice-text">{currentAdvice.text}</p>
                  <div className="advice-controls">
                    <button
                      type="button"
                      className="advice-nav-btn"
                      disabled={adviceIndex === 0 || adviceGenerating}
                      aria-label="Предыдущий совет"
                      onClick={() => setAdviceIndex((i) => Math.max(0, i - 1))}
                    >
                      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" aria-hidden="true">
                        <path
                          d="M15 5 L8 12 L15 19"
                          stroke="#BDBDBD"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                    <button
                      type="button"
                      className="advice-nav-btn"
                      disabled={adviceIndex >= advices.length - 1 || adviceGenerating}
                      aria-label="Следующий совет"
                      onClick={() =>
                        setAdviceIndex((i) => Math.min(advices.length - 1, i + 1))
                      }
                    >
                      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" aria-hidden="true">
                        <path
                          d="M9 5 L16 12 L9 19"
                          stroke="#BDBDBD"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                    {advices.length > 1 && (
                      <span className="muted advice-counter">
                        Совет {adviceIndex + 1} из {advices.length}
                      </span>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <p className="muted">Совет ещё не сгенерирован.</p>
                  <button
                    type="button"
                    className="btn btn-small"
                    onClick={() => generateAdvice()}
                    disabled={adviceGenerating}
                  >
                    {adviceGenerating ? 'Генерация...' : 'Получить совет'}
                  </button>
                </>
              )}
            </section>

            <section className="card demo-block" aria-label="Банковские выписки">
              <div className="card-header">
                <h2>Банковские выписки</h2>
                <button
                  type="button"
                  className="btn btn-small"
                  onClick={() => setUploadOpen(true)}
                >
                  Загрузить
                </button>
              </div>
              {files.length === 0 ? (
                <p className="muted">Выписки пока не загружались.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Файл</th>
                      <th>Период</th>
                      <th className="num">Операций</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((file) => (
                      <tr key={file.filename}>
                        <td>{file.filename}</td>
                        <td className="nowrap">
                          {formatDate(file.period_start)} — {formatDate(file.period_end)}
                        </td>
                        <td className="num">{file.operations_count}</td>
                        <td className="files-remove-cell">
                          <button
                            type="button"
                            className="icon-btn icon-btn-danger"
                            aria-label={`Удалить выписку ${file.filename}`}
                            title="Удалить"
                            onClick={() => handleDeleteFile(file.filename)}
                          >
                            <svg
                              viewBox="0 0 24 24"
                              width="18"
                              height="18"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              aria-hidden="true"
                            >
                              <line x1="18" y1="6" x2="6" y2="18" />
                              <line x1="6" y1="6" x2="18" y2="18" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>

          {!hasData ? (
            <div className="card">
              <h2>Пока нет данных</h2>
              <p className="muted">
                Загрузите банковскую выписку, чтобы увидеть статистику расходов.
              </p>
              <button
                type="button"
                className="btn"
                onClick={() => setUploadOpen(true)}
              >
                Загрузить выписку
              </button>
            </div>
          ) : (
            <>
              <section className="card" aria-label="Разбивка по категориям">
                <h2>Расходы по категориям</h2>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th
                        aria-sort={
                          catSortBy === 'category'
                            ? catSortDir === 'asc'
                              ? 'ascending'
                              : 'descending'
                            : 'none'
                        }
                      >
                        <button
                          type="button"
                          className="sort-btn"
                          onClick={() => handleCatSort('category')}
                        >
                          Категория{' '}
                          <span className={`sort-indicator${catSortBy === 'category' ? ' active' : ''}`}>
                            {sortIndicator('category', catSortBy, catSortDir)}
                          </span>
                        </button>
                      </th>
                      <th
                        className="num"
                        aria-sort={
                          catSortBy === 'amount'
                            ? catSortDir === 'asc'
                              ? 'ascending'
                              : 'descending'
                            : 'none'
                        }
                      >
                        <button
                          type="button"
                          className="sort-btn"
                          onClick={() => handleCatSort('amount')}
                        >
                          Сумма{' '}
                          <span className={`sort-indicator${catSortBy === 'amount' ? ' active' : ''}`}>
                            {sortIndicator('amount', catSortBy, catSortDir)}
                          </span>
                        </button>
                      </th>
                      <th
                        className="num"
                        aria-sort={
                          catSortBy === 'count'
                            ? catSortDir === 'asc'
                              ? 'ascending'
                              : 'descending'
                            : 'none'
                        }
                      >
                        <button
                          type="button"
                          className="sort-btn"
                          onClick={() => handleCatSort('count')}
                        >
                          Операций{' '}
                          <span className={`sort-indicator${catSortBy === 'count' ? ' active' : ''}`}>
                            {sortIndicator('count', catSortBy, catSortDir)}
                          </span>
                        </button>
                      </th>
                      <th
                        className="num"
                        aria-sort={
                          catSortBy === 'share'
                            ? catSortDir === 'asc'
                              ? 'ascending'
                              : 'descending'
                            : 'none'
                        }
                      >
                        <button
                          type="button"
                          className="sort-btn"
                          onClick={() => handleCatSort('share')}
                        >
                          Доля{' '}
                          <span className={`sort-indicator${catSortBy === 'share' ? ' active' : ''}`}>
                            {sortIndicator('share', catSortBy, catSortDir)}
                          </span>
                        </button>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {categories.map((item) => {
                      const percent = total > 0 ? Math.abs(item.amount) / total * 100 : 0;
                      return (
                        <tr key={item.category}>
                          <td>{item.category}</td>
                          <td className="num">{formatAmount(item.amount)}</td>
                          <td className="num">{item.count ?? 0}</td>
                          <td className="num">
                            <div className="bar-cell">
                              <span
                                className="percent-bar"
                                style={{ width: `${Math.min(percent, 100)}%` }}
                              />
                              <span className="percent-value">{percent.toFixed(1)}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </section>

              {dynamicsData.length > 0 && (
                <section className="card" aria-label="Динамика расходов">
                  <div className="card-header">
                    <h2>Динамика расходов</h2>
                    <div
                      className="period-toggle"
                      role="group"
                      aria-label="Период динамики расходов"
                    >
                      {Object.entries(DYNAMICS_PERIODS).map(([key, config]) => (
                        <button
                          key={key}
                          type="button"
                          className={`period-toggle-btn${dynamicsPeriod === key ? ' active' : ''}`}
                          aria-pressed={dynamicsPeriod === key}
                          onClick={() => setDynamicsPeriod(key)}
                        >
                          {config.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="chart-box" aria-hidden="true">
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={dynamicsData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey={dynamics.dataKey}
                          tickFormatter={(value) => formatDynamicsTick(value, dynamicsPeriod)}
                        />
                        <YAxis tickFormatter={(value) => Math.abs(Number(value)).toLocaleString('ru-RU')} />
                        <Tooltip
                          content={({ active, payload, label }) => {
                            if (!active || !payload?.length) return null;
                            return (
                              <div className="dynamics-tooltip">
                                <div className="dynamics-tooltip-label">
                                  {formatDynamicsTick(label, dynamicsPeriod)}
                                </div>
                                <div className="dynamics-tooltip-value">
                                  {formatAmount(payload[0].value)}
                                </div>
                              </div>
                            );
                          }}
                        />
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
                <div className="card-header">
                  <h2>Операции ({sortedTransactions.length})</h2>
                  <div className="card-header-actions">
                    {transactions.length > 0 && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-small"
                        aria-pressed={hideIncomes}
                        onClick={() => setHideIncomes((value) => !value)}
                      >
                        {hideIncomes ? 'Показать пополнения' : 'Убрать пополнения'}
                      </button>
                    )}
                  </div>
                </div>
                {transactions.length === 0 ? (
                  <p className="muted">Операций пока нет.</p>
                ) : (
                  <div className="table-scroll">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th
                            aria-sort={
                              sortBy === 'date'
                                ? sortDir === 'asc'
                                  ? 'ascending'
                                  : 'descending'
                                : 'none'
                            }
                          >
                            <button
                              type="button"
                              className="sort-btn"
                              onClick={() => handleSort('date')}
                            >
                              Дата{' '}
                              <span className={`sort-indicator${sortBy === 'date' ? ' active' : ''}`}>
                                {sortIndicator('date', sortBy, sortDir)}
                              </span>
                            </button>
                          </th>
                          <th>Название</th>
                          <th
                            aria-sort={
                              sortBy === 'category'
                                ? sortDir === 'asc'
                                  ? 'ascending'
                                  : 'descending'
                                : 'none'
                            }
                          >
                            <button
                              type="button"
                              className="sort-btn"
                              onClick={() => handleSort('category')}
                            >
                              Категория{' '}
                              <span className={`sort-indicator${sortBy === 'category' ? ' active' : ''}`}>
                                {sortIndicator('category', sortBy, sortDir)}
                              </span>
                            </button>
                          </th>
                          <th className="num">Сумма</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {sortedTransactions.slice(0, 10).map((txn) => (
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
                {sortedTransactions.length > 0 && (
                  <div className="card-footer-link">
                    <Link to={`/family/${id}/operations`} className="card-header-link">
                      Все операции
                    </Link>
                  </div>
                )}
                {transactions.length > 0 && sortedTransactions.length === 0 && (
                  <p className="muted">Все пополнения скрыты кнопкой выше.</p>
                )}
              </section>
            </>
          )}
        </>
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

      {uploadOpen && (
        <UploadModal
          familyId={id}
          onClose={() => setUploadOpen(false)}
          onUploaded={handleUploaded}
        />
      )}
    </div>
  );
}