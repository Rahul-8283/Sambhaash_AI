import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";

// Pages
import LandingPage from "./pages/LandingPage";
import LeadsPage from "./pages/LeadsPage";
import LeadDetailPage from "./pages/LeadDetailPage";
import CallsPage from "./pages/CallsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import AppendixPage from "./pages/AppendixPage";
import RMPage from "./pages/RMPage";
import ProfileSettingsPage from "./pages/ProfileSettingsPage";
import PromptSettingsPage from "./pages/PromptSettingsPage";
import LanguageSettingsPage from "./pages/LanguageSettingsPage";
import RetrySettingsPage from "./pages/RetrySettingsPage";
import IntegrationSettingsPage from "./pages/IntegrationSettingsPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard/*" element={<MainLayout><Routes>
          <Route path="leads" element={<LeadsPage />} />
          <Route path="leads/:id" element={<LeadDetailPage />} />
          <Route path="calls" element={<CallsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="appendix" element={<AppendixPage />} />
          <Route path="rm" element={<RMPage />} />
          <Route path="settings/profile" element={<ProfileSettingsPage />} />
          <Route path="settings/prompt" element={<PromptSettingsPage />} />
          <Route path="settings/language" element={<LanguageSettingsPage />} />
          <Route path="settings/retry" element={<RetrySettingsPage />} />
          <Route path="settings/integrations" element={<IntegrationSettingsPage />} />
          <Route path="*" element={<Navigate to="/dashboard/leads" replace />} />
        </Routes></MainLayout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;