import React, { useState } from "react";
import { Sparkles, Save, Code, Play } from "lucide-react";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import SettingsTabs from "../components/Layout/SettingsTabs";

const PRESETS = [
  {
    id: "financial-greeting",
    name: "Standard Loan Greeting (English/Hindi)",
    prompt: "You are Sambhaash AI, an automated voice assistant calling {{customer_name}} on behalf of Bharat Finance. Your relationship manager {{rm_name}} is assigned to this account. Talk politely, explain that their credit line is approved up to {{loan_amount}}, and ask if they are interested."
  },
  {
    id: "urgent-collection",
    name: "Premium Account Collections",
    prompt: "You are Sambhaash AI from Bharat Finance. Call {{customer_name}} regarding their overdue balance of {{loan_amount}} which was due on {{due_date}}. Explain that if they pay today, {{rm_name}} can offer them a 5% interest fee waiver. Guide them to install the application."
  },
  {
    id: "survey-feedback",
    name: "Post-Call Customer Satisfaction Survey",
    prompt: "You are calling {{customer_name}} to request feedback on their recent conversation with relationship manager {{rm_name}}. Keep your greeting very warm, ask them to rate their satisfaction from 1 to 5, and note any objections."
  }
];

export const PromptSettingsPage: React.FC = () => {
  const [selectedPresetId, setSelectedPresetId] = useState(PRESETS[0].id);
  const [promptContent, setPromptContent] = useState(PRESETS[0].prompt);
  
  // Sandbox Variables simulation
  const [customerName, setCustomerName] = useState("Rajesh Patel");
  const [rmName, setRmName] = useState("Priya Singh");
  const [loanAmount, setLoanAmount] = useState("₹75,000");
  const [dueDate, setDueDate] = useState("May 20th");

  const [saving, setSaving] = useState(false);
  const [simulatedDialog, setSimulatedDialog] = useState<string | null>(null);

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId);
    const selected = PRESETS.find(p => p.id === presetId);
    if (selected) {
      setPromptContent(selected.prompt);
      setSimulatedDialog(null);
    }
  };

  const handleSavePrompt = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("System prompt saved successfully!");
    }, 1200);
  };

  // Compile variables in prompt
  const getCompiledPrompt = () => {
    return promptContent
      .replace(/\{\{customer_name\}\}/g, customerName)
      .replace(/\{\{rm_name\}\}/g, rmName)
      .replace(/\{\{loan_amount\}\}/g, loanAmount)
      .replace(/\{\{due_date\}\}/g, dueDate);
  };

  const handleSimulateCall = () => {
    const compiled = getCompiledPrompt();
    setSimulatedDialog(
      `Compiled System Instructions:\n"${compiled}"\n\nSimulated Voice Greeting:\n"Hello ${customerName}, this is Sambhaash AI calling on behalf of Bharat Finance. Your relationship manager ${rmName} has pre-approved a credit line of ${loanAmount} for your account. Would you like to proceed with the activation?"\n\nSimulated Confidence Score: 98% | Primary Tone Detected: Friendly, Salesy`
    );
    toast.success("Simulating voice greeting context...");
  };

  return (
    <div className="p-6 pt-2 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-[#2d1e18] font-display flex items-center gap-2">
          System Prompt Workspace <Sparkles className="text-[#d4a373] animate-pulse" size={24} />
        </h1>
        <p className="text-sm font-semibold text-[#3d2b1f]/70 mt-1">Configure LLM prompts, setup custom variables, and test AI greetings live.</p>
      </div>

      <SettingsTabs />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Presets and Editor */}
        <div className="lg:col-span-2 space-y-6">
          {/* Presets Panel */}
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider mb-4 flex items-center gap-2">
              <Code size={18} className="text-[#d4a373]" /> Choose Preset Templates
            </h2>
            <div className="grid grid-cols-1 gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => handlePresetChange(p.id)}
                  className={`p-3 text-left rounded-2xl border transition-all text-xs font-bold cursor-pointer ${
                    selectedPresetId === p.id
                      ? "bg-[#faedcd] border-[#d4a373] text-[#3d2b1f] shadow-sm"
                      : "bg-white/50 border-[#faedcd]/60 text-[#3d2b1f]/60 hover:bg-white"
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          {/* Active Prompt Textarea */}
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider">
                System Guidelines Editor
              </h2>
              <span className="text-[10px] font-black bg-[#faedcd] text-[#3d2b1f] px-2.5 py-1 rounded-full border border-[#d4a373]/20">
                GPT-4o Agent
              </span>
            </div>
            
            <textarea
              value={promptContent}
              onChange={(e) => setPromptContent(e.target.value)}
              className="w-full h-48 px-4 py-3 bg-white/70 border border-[#faedcd] rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] text-sm text-[#3d2b1f] font-semibold leading-relaxed"
              placeholder="Enter system prompt instructions..."
            />

            <div className="flex justify-end">
              <button
                onClick={handleSavePrompt}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-2.5 bg-[#d4a373] text-white font-bold rounded-xl hover:bg-[#b5835a] transition-all shadow-md shadow-[#d4a373]/20 disabled:opacity-50 cursor-pointer active:scale-95 text-sm"
              >
                <Save size={16} />
                {saving ? "Saving..." : "Save System Prompt"}
              </button>
            </div>
          </div>
        </div>

        {/* Live Variables & Simulator Sandbox */}
        <div className="space-y-6">
          <div className="glass rounded-3xl p-6 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-4">
            <h2 className="text-base font-black text-[#2d1e18] font-display uppercase tracking-wider flex items-center gap-2">
              <Play size={18} className="text-[#d4a373]" /> Sandbox Simulation
            </h2>
            <p className="text-xs font-semibold text-[#3d2b1f]/60">Customize variables values to compile and review prompts in real-time.</p>

            <div className="space-y-3 pt-2">
              <div>
                <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide">Customer Name</label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 text-xs font-bold text-[#3d2b1f]"
                />
              </div>

              <div>
                <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide">RM Name</label>
                <input
                  type="text"
                  value={rmName}
                  onChange={(e) => setRmName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 text-xs font-bold text-[#3d2b1f]"
                />
              </div>

              <div>
                <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide">Loan Amount</label>
                <input
                  type="text"
                  value={loanAmount}
                  onChange={(e) => setLoanAmount(e.target.value)}
                  className="w-full px-3.5 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 text-xs font-bold text-[#3d2b1f]"
                />
              </div>

              <div>
                <label className="text-[10px] font-black text-[#3d2b1f]/60 uppercase tracking-wide">Due Date Offset</label>
                <input
                  type="text"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="w-full px-3.5 py-2 bg-white/70 border border-[#faedcd] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 text-xs font-bold text-[#3d2b1f]"
                />
              </div>
            </div>

            <button
              onClick={handleSimulateCall}
              className="w-full py-2.5 mt-2 bg-[#faedcd] text-[#3d2b1f] border border-[#d4a373]/30 font-bold rounded-xl text-xs hover:bg-[#f5e3b8] transition-all shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <Play size={14} /> Run Voice Generator
            </button>
          </div>

          {/* Sandbox Live Stream Result */}
          {simulatedDialog && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-[#2d1e18] rounded-3xl p-6 text-white border border-[#3d2b1f]/80 space-y-3 shadow-2xl"
            >
              <p className="text-[10px] font-black text-[#d4a373] tracking-widest uppercase">Compiled Response Sandbox</p>
              <p className="text-xs font-mono text-[#faedcd] leading-relaxed whitespace-pre-wrap">
                {simulatedDialog}
              </p>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PromptSettingsPage;