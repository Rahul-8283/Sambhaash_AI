import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import ProtectedRoute from "./components/Auth/ProtectedRoute";
import { Toaster } from "react-hot-toast";

// Pages
const LandingPage = lazy(() => import("./pages/LandingPage"));
const LeadsPage = lazy(() => import("./pages/LeadsPage"));
const LeadDetailPage = lazy(() => import("./pages/LeadDetailPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const AppendixPage = lazy(() => import("./pages/AppendixPage"));
const RMPage = lazy(() => import("./pages/RMPage"));
const ProfileSettingsPage = lazy(() => import("./pages/ProfileSettingsPage"));
const QueueDashboard = lazy(() => import("./pages/QueueDashboard"));
const CallSummaries = lazy(() => import("./pages/CallSummaries"));
const CallsPage = lazy(() => import("./pages/CallsPage"));
import ErrorBoundary from "./components/ErrorBoundary";

const PageFallback = () => (
  <div className="flex h-screen items-center justify-center text-sm text-gray-500">Loading...</div>
);

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" reverseOrder={false} />
      <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard/*" element={
          <ProtectedRoute>
            <MainLayout>
              <ErrorBoundary>
              <Routes>
                <Route path="leads" element={<LeadsPage />} />
                <Route path="leads/:id" element={<LeadDetailPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="appendix" element={<AppendixPage />} />
                <Route path="rm" element={<RMPage />} />
                <Route path="queue" element={<QueueDashboard />} />
                <Route path="summaries" element={<CallSummaries />} />
                <Route path="calls" element={<CallsPage />} />
                <Route path="settings/profile" element={<ProfileSettingsPage />} />
                <Route path="*" element={<Navigate to="/dashboard/leads" replace />} />
              </Routes>
              </ErrorBoundary>
            </MainLayout>
          </ProtectedRoute>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
