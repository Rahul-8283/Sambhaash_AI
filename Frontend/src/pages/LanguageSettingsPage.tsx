import React, { useState } from "react";
import { Globe, Save, HelpCircle } from "lucide-react";
import toast from "react-hot-toast";

const LANGUAGES = [
  { code: "en", name: "English", native: "English", status: "Primary" },
  { code: "hi", name: "Hindi", native: "हिन्दी", status: "Active" },
  { code: "ta", name: "Tamil", native: "தமிழ்", status: "Active" },
  { code: "te", name: "Telugu", native: "తెలుగు", status: "Active" },
  { code: "kn", name: "Kannada", native: "கன்னடம்", status: "Inactive" },
  { code: "ml", name: "Malayalam", native: "മലയാളം", status: "Inactive" },
  { code: "bn", name: "Bengali", native: "বাংলা", status: "Inactive" },
];

export const LanguageSettingsPage: React.FC = () => {
  const [activeLanguages, setActiveLanguages] = useState<string[]>(["en", "hi", "ta", "te"]);
  const [primaryLang, setPrimaryLang] = useState("en");
  const [sttProvider, setSttProvider] = useState("deepgram");
  const [ttsProvider, setTtsProvider] = useState("sarvam");
  const [saving, setSaving] = useState(false);

  const toggleLanguage = (code: string) => {
    if (code === primaryLang) return; // Cannot disable primary
    setActiveLanguages(prev => 
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const handleSaveSettings = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("Multilingual voice routing preferences updated!");
    }, 1200);
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-[#2d1e18] font-display flex items-center gap-2">
          Language Router Settings <Globe className="text-[#d4a373] animate-pulse" size={24} />
        </h1>
        <p className="text-sm font-semibold text-[#3d2b1f]/70 mt-1">Configure active customer call languages, primary speech fallbacks, and regional voice synthesis models.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Languages Checklist */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider">
              Supported Regional Channels
            </h2>
            <p className="text-xs font-semibold text-[#3d2b1f]/60">Select languages to activate during inbound & outbound call routing campaigns.</p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              {LANGUAGES.map((lang) => {
                const isActive = activeLanguages.includes(lang.code);
                const isPrimary = primaryLang === lang.code;

                return (
                  <div
                    key={lang.code}
                    className={`p-4 rounded-2xl border transition-all flex items-center justify-between ${
                      isActive 
                        ? "bg-white/70 border-[#d4a373] shadow-sm" 
                        : "bg-white/20 border-[#faedcd]/40 opacity-60"
                    }`}
                  >
                    <div>
                      <p className="font-bold text-[#2d1e18] text-sm flex items-center gap-1.5">
                        {lang.name} <span className="text-xs text-[#3d2b1f]/50 font-normal">({lang.native})</span>
                      </p>
                      <p className="text-xs font-semibold text-[#3d2b1f]/60 mt-0.5">
                        {isPrimary ? "Primary Channel" : isActive ? "Active campaign routing" : "Inactive"}
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {!isPrimary && (
                        <button
                          onClick={() => setPrimaryLang(lang.code)}
                          className="px-2 py-1 text-[10px] font-black bg-[#faedcd] text-[#3d2b1f] border border-[#d4a373]/20 rounded-lg hover:bg-[#f5e3b8]"
                        >
                          Make Primary
                        </button>
                      )}
                      <input
                        type="checkbox"
                        checked={isActive}
                        disabled={isPrimary}
                        onChange={() => toggleLanguage(lang.code)}
                        className="w-4 h-4 text-[#d4a373] border-[#faedcd] rounded focus:ring-[#d4a373]/30 cursor-pointer"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Synthesis Options */}
        <div className="space-y-6">
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider flex items-center gap-2">
              Speech Pipeline Engine
            </h2>
            <p className="text-xs font-semibold text-[#3d2b1f]/60">Configure transcription and regional Indian voice synthesis engines.</p>

            <div className="space-y-4 pt-2">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide flex items-center gap-1">
                  Speech-to-Text (STT) <HelpCircle size={12} className="text-[#3d2b1f]/40" />
                </label>
                <select
                  value={sttProvider}
                  onChange={(e) => setSttProvider(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 text-sm text-[#3d2b1f] font-bold"
                >
                  <option value="deepgram">Deepgram Nova-2 (Recommended)</option>
                  <option value="whisper">OpenAI Whisper (Cloud)</option>
                  <option value="sarvam-stt">Sarvam.ai Whisper (Fine-tuned)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide flex items-center gap-1">
                  Text-to-Speech (TTS) <HelpCircle size={12} className="text-[#3d2b1f]/40" />
                </label>
                <select
                  value={ttsProvider}
                  onChange={(e) => setTtsProvider(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 text-sm text-[#3d2b1f] font-bold"
                >
                  <option value="sarvam">Sarvam.ai (Accent-Perfect Indic)</option>
                  <option value="google">Google Cloud TTS (Indic)</option>
                  <option value="elevenlabs">ElevenLabs Multi-lingual</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-6 py-2.5 mt-4 bg-[#d4a373] text-white font-bold rounded-xl hover:bg-[#b5835a] transition-all shadow-md shadow-[#d4a373]/20 disabled:opacity-50 cursor-pointer active:scale-95 text-xs"
            >
              <Save size={14} />
              {saving ? "Saving routing..." : "Save Route Mapping"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LanguageSettingsPage;