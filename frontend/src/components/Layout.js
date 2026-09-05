import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <Link to="/" className="logo-link" aria-label="FinBalance — на главную">
          <img src="/logo.png" alt="FinBalance" className="logo" />
        </Link>
        <div className="header-actions">
          <nav className="dashboard-nav">
            <Link to="/family">Создать семью</Link>
            <Link to="/upload">Загрузить</Link>
          </nav>
          <div className="user-info">
            <span>{user.email}</span>
            <button onClick={logout} className="logout-btn">
              Выйти
            </button>
          </div>
        </div>
      </header>
      <main className="dashboard-main">{children}</main>
    </div>
  );
}