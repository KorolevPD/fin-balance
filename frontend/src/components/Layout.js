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
            <img
              src={preview || '/avatar.jpg'}
              alt="Фото профиля"
              className="header-avatar-img"
            />
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