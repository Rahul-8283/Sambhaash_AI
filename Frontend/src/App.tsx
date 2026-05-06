/**
 * App.tsx - Main application with routing
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";

// Pages
import LeadsPage from "./pages/LeadsPage";
import LeadDetailPage from "./pages/LeadDetailPage";
import CallsPage from "./pages/CallsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import CampaignsPage from "./pages/CampaignsPage";
import AppendixPage from "./pages/AppendixPage";
import PromptSettingsPage from "./pages/PromptSettingsPage";
import LanguageSettingsPage from "./pages/LanguageSettingsPage";
import RetrySettingsPage from "./pages/RetrySettingsPage";
import IntegrationSettingsPage from "./pages/IntegrationSettingsPage";
import UsersPage from "./pages/UsersPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard/leads" replace />} />
        <Route path="/dashboard/*" element={<MainLayout><Routes>
          <Route path="leads" element={<LeadsPage />} />
          <Route path="leads/:id" element={<LeadDetailPage />} />
          <Route path="calls" element={<CallsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="campaigns" element={<CampaignsPage />} />
          <Route path="appendix" element={<AppendixPage />} />
          <Route path="settings/prompt" element={<PromptSettingsPage />} />
          <Route path="settings/language" element={<LanguageSettingsPage />} />
          <Route path="settings/retry" element={<RetrySettingsPage />} />
          <Route path="settings/integrations" element={<IntegrationSettingsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="*" element={<Navigate to="/dashboard/leads" replace />} />
        </Routes></MainLayout>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;