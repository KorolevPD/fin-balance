import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api';

function avatarUrl(avatar) {
  if (!avatar) return null;
  return `${api.defaults.baseURL}/auth/me/avatar/${avatar}`;
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();

  const preview = avatarUrl(user?.avatar);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <Link to="/dashboard" className="logo-link" aria-label="FinBalance — дашборд">
          <img src="/logo2.png" alt="FinBalance" className="logo" />
        </Link>
        <nav className="dashboard-nav">
          <Link to="/family">Создать семью</Link>
          <Link to="/upload">Загрузить</Link>
          <Link to="/dashboard">Дашборд</Link>
        </nav>
        <div className="user-info">
          <Link
            to="/profile"
            className="user-info-name"
            title="Мой профиль"
          >
            {user.name || user.email}
          </Link>
          <Link
            to="/profile"
            className="header-avatar"
            aria-label="Мой профиль"
            title={user.name || user.email}
          >
            {preview ? (
              <img src={preview} alt="Фото профиля" className="header-avatar-img" />
            ) : (
              <span className="header-avatar-letter">
                {(user.name || user.email || '?')[0].toUpperCase()}
              </span>
            )}
          </Link>
          <button onClick={logout} className="logout-btn">
            Выйти
          </button>
        </div>
      </header>
      <main className="dashboard-main">{children}</main>
    </div>
  );
}