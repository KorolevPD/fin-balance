import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Landing() {
  const { user } = useAuth();

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="landing">
      <div className="landing-window">
        <div className="landing-content">
          <div className="landing-text">
            <h1 className="landing-title">Понимай деньги проще</h1>
            <p className="landing-description">
              Импорт выписок, автоматические правила категоризации и наглядные диаграммы
              трат, баланса и топ-получателей — всё собрано в&nbsp;одном месте.
            </p>
            <p className="landing-note">
              Анализируйте выписки из Сбера без ручного ввода данных
            </p>
          </div>
          <div className="landing-logo">
            <img src="/logo1.png" alt="FinBalance" />
          </div>
        </div>
        <Link to="/register" className="landing-btn">
          Зарегистрироваться
        </Link>
        <p className="landing-auth-link">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  );
}