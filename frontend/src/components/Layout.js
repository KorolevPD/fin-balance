import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();

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
          <span>{user.email}</span>
          <button onClick={logout} className="logout-btn">
            Выйти
          </button>
        </div>
      </header>
      <main className="dashboard-main">{children}</main>
    </div>
  );
}