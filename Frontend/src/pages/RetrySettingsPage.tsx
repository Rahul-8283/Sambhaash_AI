import React, { useState } from "react";
import { PhoneCall, Save, AlertTriangle, ShieldCheck } from "lucide-react";
import toast from "react-hot-toast";

export const RetrySettingsPage: React.FC = () => {
  const [maxRetries, setMaxRetries] = useState(3);
  const [retryInterval, setRetryInterval] = useState(30); // in minutes
  const [retryOnNoAnswer, setRetryOnNoAnswer] = useState(true);
  const [retryOnFailed, setRetryOnFailed] = useState(true);
  const [retryOnBusy, setRetryOnBusy] = useState(true);
  const [smsFallback, setSmsFallback] = useState(true);
  const [timeRestriction, setTimeRestriction] = useState(true);
  
  const [saving, setSaving] = useState(false);

  const handleSaveSettings = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("Outbound campaign retry parameters updated!");
    }, 1200);
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-[#2d1e18] font-display flex items-center gap-2">
          Call Retry Parameters <PhoneCall className="text-[#d4a373] animate-pulse" size={24} />
        </h1>
        <p className="text-sm font-semibold text-[#3d2b1f]/70 mt-1">Configure automated dialer retry frequencies, triggers for busy states, and regional call-time compliance rules.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Retry Rules Panel */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-6">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider flex items-center gap-2">
              Dialer Aggression & Speed
            </h2>

            {/* Slider 1: Max Retries */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="font-bold text-[#3d2b1f]">Maximum Attempts per Lead</span>
                <span className="font-black text-[#d4a373] text-base">{maxRetries} calls</span>
              </div>
              <input
                type="range"
                min="1"
                max="5"
                value={maxRetries}
                onChange={(e) => setMaxRetries(parseInt(e.target.value))}
                className="w-full accent-[#d4a373]"
              />
              <p className="text-[10px] font-semibold text-[#3d2b1f]/50">Maximum number of outbound attempts our automated voice agent will trigger per lead before flagging as exhausted.</p>
            </div>

            {/* Slider 2: Retry Interval */}
            <div className="space-y-2 pt-2">
              <div className="flex justify-between items-center text-sm">
                <span className="font-bold text-[#3d2b1f]">Retry Backoff Interval</span>
                <span className="font-black text-[#d4a373] text-base">{retryInterval} minutes</span>
              </div>
              <input
                type="range"
                min="10"
                max="120"
                step="10"
                value={retryInterval}
                onChange={(e) => setRetryInterval(parseInt(e.target.value))}
                className="w-full accent-[#d4a373]"
              />
              <p className="text-[10px] font-semibold text-[#3d2b1f]/50">Cool-down timer delay applied before attempting another call connection to a lead with temporary busy or network issues.</p>
            </div>
          </div>

          {/* Trigger States */}
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider">
              Rescheduling Triggers
            </h2>
            <div className="space-y-3">
              {[
                { label: "Retry on No Answer", desc: "Redial if the customer's phone rings to timeout without response", state: retryOnNoAnswer, setState: setRetryOnNoAnswer },
                { label: "Retry on Dial Failed", desc: "Redial if call connection fails due to network carriers issues", state: retryOnFailed, setState: setRetryOnFailed },
                { label: "Retry on Busy Line", desc: "Redial if customer rejects the call or line returns busy state", state: retryOnBusy, setState: setRetryOnBusy },
              ].map((trigger, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-2xl bg-white/40 border border-[#faedcd]/60">
                  <div>
                    <p className="text-xs font-bold text-[#2d1e18]">{trigger.label}</p>
                    <p className="text-[10px] font-semibold text-[#3d2b1f]/50 mt-0.5">{trigger.desc}</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={trigger.state}
                    onChange={(e) => trigger.setState(e.target.checked)}
                    className="w-4 h-4 text-[#d4a373] border-[#faedcd] rounded focus:ring-[#d4a373]/30 cursor-pointer"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Guardrails Panel */}
        <div className="space-y-6">
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck size={18} className="text-[#d4a373]" /> DND Compliance
            </h2>
            <p className="text-xs font-semibold text-[#3d2b1f]/60">Ensure campaign dials operate inside regional regulatory rules and customer convenience guardrails.</p>

            <div className="space-y-4 pt-2">
              {/* DND Toggle */}
              <div className="flex items-start justify-between gap-3 p-3 rounded-2xl bg-white/40 border border-[#faedcd]/60">
                <div className="space-y-0.5">
                  <p className="text-xs font-bold text-[#2d1e18]">TRAI Time Restrict</p>
                  <p className="text-[10px] font-semibold text-[#3d2b1f]/50 leading-tight">Restrict outbound calls between 9 PM and 8 AM to avoid spam flags.</p>
                </div>
                <input
                  type="checkbox"
                  checked={timeRestriction}
                  onChange={(e) => setTimeRestriction(e.target.checked)}
                  className="w-4 h-4 text-[#d4a373] border-[#faedcd] rounded focus:ring-[#d4a373]/30 cursor-pointer mt-1"
                />
              </div>

              {/* SMS Fallback Toggle */}
              <div className="flex items-start justify-between gap-3 p-3 rounded-2xl bg-white/40 border border-[#faedcd]/60">
                <div className="space-y-0.5">
                  <p className="text-xs font-bold text-[#2d1e18]">Auto SMS Fallback</p>
                  <p className="text-[10px] font-semibold text-[#3d2b1f]/50 leading-tight">Trigger an SMS/WhatsApp text immediately when a call is flagged as No Answer.</p>
                </div>
                <input
                  type="checkbox"
                  checked={smsFallback}
                  onChange={(e) => setSmsFallback(e.target.checked)}
                  className="w-4 h-4 text-[#d4a373] border-[#faedcd] rounded focus:ring-[#d4a373]/30 cursor-pointer mt-1"
                />
              </div>
            </div>

            {timeRestriction && (
              <div className="p-3 bg-amber-50 rounded-2xl border border-amber-200/50 flex gap-2 text-amber-800 text-[10px] font-semibold leading-relaxed">
                <AlertTriangle size={16} className="shrink-0 text-amber-600" />
                <span>Regulatory Guard: Outbound dialing campaigns will pause daily at 21:00 IST and resume at 08:00 IST automatically.</span>
              </div>
            )}

            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-6 py-2.5 mt-2 bg-[#d4a373] text-white font-bold rounded-xl hover:bg-[#b5835a] transition-all shadow-md shadow-[#d4a373]/20 disabled:opacity-50 cursor-pointer active:scale-95 text-xs"
            >
              <Save size={14} />
              {saving ? "Saving dialer..." : "Save Guardrails"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RetrySettingsPage;