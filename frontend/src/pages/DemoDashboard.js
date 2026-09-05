import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
import api from '../api';

const DEMO_COLORS = [
  '#5b5bea',
  '#f59e0b',
  '#10b981',
  '#ef4444',
  '#06b6d4',
  '#8b5cf6',
  '#64748b',
];

function formatAmount(value) {
  const num = Number(value || 0);
  return `${num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

function formatDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString('ru-RU');
}

export default function DemoDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [redirectTo, setRedirectTo] = useState(null);

  useEffect(() => {
    let cancelled = false;

    api
      .get('/families/my')
      .then((res) => {
        const families = res.data || [];
        const checks = families.map((family) =>
          api
            .get(`/families/${family.id}/summary`)
            .then((summaryRes) => ({ family, summary: summaryRes.data }))
            .catch(() => null)
        );
        return Promise.all(checks);
      })
      .then((results) => {
        if (cancelled) return;
        const found = results.find(
          (item) =>
            item && (item.summary?.total_amount > 0 ||
              (item.summary?.by_category || []).length > 0 ||
              (item.summary?.uploaded_files || []).length > 0)
        );
        if (found) {
          setRedirectTo(`/family/${found.family.id}/dashboard`);
          return;
        }
        return api
          .get('/demo/dashboard')
          .then((res) => setData(res.data))
          .catch((err) =>
            setError(err.response?.data?.detail || 'Не удалось загрузить примерные данные')
          );
      })
      .catch((err) =>
        setError(err.response?.data?.detail || 'Не удалось загрузить данные дашборда')
      )
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (redirectTo) {
    return <Navigate to={redirectTo} replace />;
  }

  if (loading) {
    return <p className="muted">Загрузка...</p>;
  }

  if (error) {
    return (
      <div className="page dashboard-page">
        <h1>Дашборд</h1>
        <div className="error">{error}</div>
      </div>
    );
  }

  const members = data?.family_members || [];
  const categories = data?.categories || [];
  const files = data?.uploaded_files || [];

  return (
    <div className="page dashboard-page">
      <h1>Примерный дашборд</h1>
      <p className="muted">Демонстрационный макет без реальных данных.</p>

      <div className="demo-grid">
        <section className="card demo-block" aria-label="Члены семьи">
          <h2>Члены семьи</h2>
          {members.length === 0 ? (
            <p className="muted">Нет данных.</p>
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
                  <tr key={member.name}>
                    <td>{member.name}</td>
                    <td className="num">{formatAmount(member.total_expenses)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="card demo-block" aria-label="Траты по категориям">
          <h2>Траты по категориям</h2>
          {categories.length === 0 ? (
            <p className="muted">Нет данных.</p>
          ) : (
            <div className="chart-box demo-chart">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={categories}
                    dataKey="amount"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={(entry) => entry.category}
                  >
                    {categories.map((entry, index) => (
                      <Cell key={entry.category} fill={DEMO_COLORS[index % DEMO_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatAmount(value)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>

        <section className="card demo-block demo-block-empty" aria-label="Пустой блок">
          <h2>Резерв</h2>
          <p className="muted">Здесь появится новый блок.</p>
        </section>

        <section className="card demo-block" aria-label="Загруженные файлы">
          <h2>Загруженные файлы</h2>
          {files.length === 0 ? (
            <p className="muted">Файлы пока не загружались.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Файл</th>
                  <th>Период</th>
                  <th className="num">Операций</th>
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
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}