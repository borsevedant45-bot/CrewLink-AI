/* Doc #8 §1 — 4 screens: task feed, incident detail, chat bridge, Ask CrewLink + supervisor */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/contexts/AuthContext';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { TaskFeed } from '@/pages/TaskFeed';
import { IncidentDetail } from '@/pages/IncidentDetail';
import { ChatBridge } from '@/pages/ChatBridge';
import { AskCrewLink } from '@/pages/AskCrewLink';
import { SupervisorDashboard } from '@/pages/SupervisorDashboard';
import { Login } from '@/pages/Login';
import { DemoHub } from '@/pages/DemoHub';

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <LanguageProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/tasks"
                element={
                  <ProtectedRoute>
                    <TaskFeed />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/incidents/:id"
                element={
                  <ProtectedRoute>
                    <IncidentDetail />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/chat/:sessionId"
                element={
                  <ProtectedRoute>
                    <ChatBridge />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/ask"
                element={
                  <ProtectedRoute>
                    <AskCrewLink />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/supervisor"
                element={
                  <ProtectedRoute requiredRole="supervisor">
                    <SupervisorDashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="/demo" element={<DemoHub />} />
              <Route path="*" element={<Navigate to="/tasks" replace />} />
            </Routes>
          </LanguageProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
