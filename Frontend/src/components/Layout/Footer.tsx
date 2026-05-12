import React from "react";
import { useNavigate } from "react-router-dom";
import { Zap, Github } from "lucide-react";

export const Footer: React.FC = () => {
  const navigate = useNavigate();

  return (
    <footer className="relative z-10 bg-[#faedcd]/30 border-t border-[#faedcd] pt-16 pb-12 px-6">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 mb-12 text-left">
        {/* Brand Column */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-[#d4a373]/10 text-[#d4a373] flex items-center justify-center">
              <Zap size={20} fill="#d4a373" />
            </span>
            <span className="text-xl font-black text-[#2d1e18] font-display">Sambhaash AI</span>
          </div>
          <p className="text-xs font-semibold text-[#3d2b1f]/70 leading-relaxed">
            Premium multilingual outbound telephony & conversational messaging platform. Powered by state-of-the-art regional voice AI.
          </p>
        </div>

        {/* Quick Links Column */}
        <div className="space-y-3">
          <h4 className="text-xs font-black text-[#2d1e18] uppercase tracking-wider">Platform Desk</h4>
          <ul className="space-y-2 text-xs font-bold text-[#3d2b1f]/70">
            <li>
              <button onClick={() => navigate('/dashboard/leads')} className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">Leads Management</button>
            </li>
            <li>
              <button onClick={() => navigate('/dashboard/calls')} className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">Call Sessions</button>
            </li>
            <li>
              <button onClick={() => navigate('/dashboard/analytics')} className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">System Analytics</button>
            </li>
            <li>
              <button onClick={() => navigate('/dashboard/appendix')} className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">RAG Knowledge Base</button>
            </li>
          </ul>
        </div>

        {/* Settings Column */}
        <div className="space-y-3">
          <h4 className="text-xs font-black text-[#2d1e18] uppercase tracking-wider">AI Config Workspace</h4>
          <ul className="space-y-2 text-xs font-bold text-[#3d2b1f]/70">
            <li>
              <button className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">Prompt Guidelines</button>
            </li>
            <li>
              <button className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">Language Routing</button>
            </li>
            <li>
              <button className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">Retry Policies</button>
            </li>
            <li>
              <button className="hover:text-[#d4a373] transition-colors cursor-pointer bg-transparent border-none p-0">Webhooks & API Keys</button>
            </li>
          </ul>
        </div>

        {/* Core Tech Column */}
        <div className="space-y-3">
          <h4 className="text-xs font-black text-[#2d1e18] uppercase tracking-wider">Our AI Stack</h4>
          <ul className="space-y-2 text-xs font-bold text-[#3d2b1f]/70">
            <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#d4a373]" /> Groq LLaMA 3.3</li>
            <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#d4a373]" /> Sarvam Bulbul V3</li>
            <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#d4a373]" /> Whisper Large V3</li>
            <li className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#d4a373]" /> Supabase pgvector</li>
          </ul>
        </div>
      </div>

      {/* Divider */}
      <div className="max-w-7xl mx-auto h-px bg-[#faedcd] mb-8" />

      {/* Bottom Bar */}
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-semibold text-[#3d2b1f]/60">
        <p>© 2026 Sambhaash AI. Built for Team Batmans. All rights reserved.</p>
        <div className="flex items-center gap-4">
          <a href="https://github.com/Rahul-8283/Sambhaash_AI" target="_blank" rel="noopener noreferrer" className="hover:text-[#d4a373] transition-colors flex items-center gap-1.5">
            <Github size={14} /> GitHub Repository
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
