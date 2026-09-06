import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import api from '../api';
import UploadModal from '../components/UploadModal';

export default function DemoDashboard() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [redirectTo, setRedirectTo] = useState(null);
  const [uploadOpen, setUploadOpen] = useState(false);

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
        }
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

  return (
    <div className="page dashboard-page">
      {error && <div className="error">{error}</div>}

      <div className="card upload-welcome">
        <h1>Добро пожаловать!</h1>
        <p className="upload-welcome-text">
          Чтобы начать работать с нашим сервисом, загрузите вашу банковскую выписку.
        </p>
        <p className="muted">
          Мы принимаем файлы в формате CSV или PDF и автоматически разберём операции,
          распределим их по категориям и покажем наглядную статистику расходов.
        </p>
        <div className="upload-welcome-actions">
          <button
            type="button"
            className="btn"
            onClick={() => setUploadOpen(true)}
          >
            Загрузить выписку
          </button>
        </div>
      </div>

      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onUploaded={(result) => {
            if (result?.family_id) {
              setRedirectTo(`/family/${result.family_id}/dashboard`);
            }
          }}
        />
      )}
    </div>
  );
}
