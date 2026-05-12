import React, { useState } from "react";
import { Link2, Save, RefreshCw, Eye, EyeOff } from "lucide-react";
import toast from "react-hot-toast";
import SettingsTabs from "../components/Layout/SettingsTabs";

export const IntegrationSettingsPage: React.FC = () => {
  const [webhookUrl, setWebhookUrl] = useState("https://crm.yourcompany.com/v1/webhooks/sambhaash");
  const [apiKey, setApiKey] = useState("sambhaash_token_mock_live_6824901538abc901a");
  const [showKey, setShowKey] = useState(false);
  const [syncZapier, setSyncZapier] = useState(true);
  const [syncHubspot, setSyncHubspot] = useState(false);
  const [syncSalesforce, setSyncSalesforce] = useState(false);

  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);

  const handleSaveSettings = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("External webhook endpoints and CRM sync rules updated!");
    }, 1200);
  };

  const handleGenerateKey = () => {
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      const newKey = "sambhaash_token_mock_live_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
      setApiKey(newKey);
      toast.success("Generated new system REST API key!");
    }, 1000);
  };

  // Mock JSON payload output
  const MOCK_PAYLOAD = `{
  "event": "lead.score_updated",
  "timestamp": "${new Date().toISOString()}",
  "lead": {
    "id": "lead_9013A8",
    "name": "Rajesh Patel",
    "phone": "+91 98765 43210",
    "status": "Connected"
  },
  "score": {
    "classification": "Hot 🔥",
    "composite": 0.89,
    "sentiment": "Highly Positive"
  }
}`;

  return (
    <div className="p-6 pt-2 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-[#2d1e18] font-display flex items-center gap-2">
          CRM Integrations & Webhooks <Link2 className="text-[#d4a373] animate-pulse" size={24} />
        </h1>
        <p className="text-sm font-semibold text-[#3d2b1f]/70 mt-1">Connect your active CRM systems, configure automated webhook events, and manage API keys for system data syncs.</p>
      </div>

      <SettingsTabs />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core Integration Forms */}
        <div className="lg:col-span-2 space-y-6">
          {/* Webhooks Section */}
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider">
              Automated CRM Sync Webhook
            </h2>
            <p className="text-xs font-semibold text-[#3d2b1f]/60">Sambhaash will POST a JSON payload to this URL as soon as a call completes and a lead score gets classified.</p>

            <div className="space-y-2">
              <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide">Webhook Endpoint URL</label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full px-4 py-2.5 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-sm text-[#3d2b1f] font-semibold"
                placeholder="https://yourdomain.com/webhook"
              />
            </div>
          </div>

          {/* API Keys */}
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider flex items-center gap-2">
              REST API Authentication
            </h2>
            <p className="text-xs font-semibold text-[#3d2b1f]/60">Authenticate your backend servers to fetch leads and push speech recording files.</p>

            <div className="space-y-2">
              <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide">Secret API Key</label>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  readOnly
                  className="w-full pl-4 pr-24 py-2.5 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none text-xs font-mono text-[#3d2b1f] font-bold"
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="p-1.5 text-[#3d2b1f]/50 hover:text-[#3d2b1f] transition-colors cursor-pointer"
                  >
                    {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                  <button
                    onClick={handleGenerateKey}
                    disabled={generating}
                    className="p-1.5 bg-[#faedcd] border border-[#d4a373]/20 text-[#3d2b1f] hover:bg-[#f5e3b8] rounded-lg transition-colors cursor-pointer"
                  >
                    <RefreshCw size={14} className={generating ? "animate-spin" : ""} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* CRM Connectors & JSON Sandbox */}
        <div className="space-y-6">
          {/* Native Connectors */}
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider">
              Native CRM Sync
            </h2>
            <div className="space-y-3 pt-2">
              {[
                { name: "Zapier Sync", desc: "Automate app rows pushes", checked: syncZapier, setChecked: setSyncZapier },
                { name: "HubSpot Sync", desc: "Sync deals & customer profile", checked: syncHubspot, setChecked: setSyncHubspot },
                { name: "Salesforce Cloud", desc: "Push Leads into sales pipe", checked: syncSalesforce, setChecked: setSyncSalesforce }
              ].map((crm, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-2xl bg-white/40 border border-[#faedcd]/60">
                  <div>
                    <p className="text-xs font-bold text-[#2d1e18]">{crm.name}</p>
                    <p className="text-[10px] font-semibold text-[#3d2b1f]/50 mt-0.5">{crm.desc}</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={crm.checked}
                    onChange={(e) => crm.setChecked(e.target.checked)}
                    className="w-4 h-4 text-[#d4a373] border-[#faedcd] rounded focus:ring-[#d4a373]/30 cursor-pointer"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Webhook JSON Simulator preview */}
          <div className="bg-[#2d1e18] rounded-3xl p-6 text-white border border-[#3d2b1f]/80 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-black text-[#d4a373] tracking-widest uppercase">Mock JSON Outbound Payload</p>
              <span className="text-[8px] font-black bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">POST</span>
            </div>
            <pre className="text-[10px] font-mono text-[#faedcd] leading-relaxed overflow-x-auto whitespace-pre-wrap">
              {MOCK_PAYLOAD}
            </pre>
          </div>

          {/* Master Save Trigger */}
          <button
            onClick={handleSaveSettings}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-[#d4a373] text-white font-bold rounded-2xl hover:bg-[#b5835a] transition-all shadow-lg shadow-[#d4a373]/25 disabled:opacity-50 cursor-pointer active:scale-95 text-sm"
          >
            <Save size={16} />
            {saving ? "Saving settings..." : "Save Integrations Config"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default IntegrationSettingsPage;