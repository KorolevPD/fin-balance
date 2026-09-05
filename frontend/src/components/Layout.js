import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>FinBalance</h1>
        <nav className="dashboard-nav">
          <Link to="/family">Моя семья</Link>
          <Link to="/upload">Загрузить файл</Link>
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