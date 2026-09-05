import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import Families from './pages/Families';
import FamilyDetail from './pages/FamilyDetail';
import Upload from './pages/Upload';
import Dashboard from './pages/Dashboard';
import PrivateRoute from './components/PrivateRoute';
import Layout from './components/Layout';

export default function App() {
  const { loading } = useAuth();

  if (loading) {
    return <div className="loading">Загрузка...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout>
              <p>Добро пожаловать!</p>
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/family"
        element={
          <PrivateRoute>
            <Layout>
              <Families />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/family/:id"
        element={
          <PrivateRoute>
            <Layout>
              <FamilyDetail />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/upload"
        element={
          <PrivateRoute>
            <Layout>
              <Upload />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/family/:id/dashboard"
        element={
          <PrivateRoute>
            <Layout>
              <Dashboard />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}