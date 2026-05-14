import React from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import Snowfall from "react-snowfall";
import {
  ArrowRight,
  Cpu,
  Globe,
  Database,
  MessageSquare,
  ShieldCheck,
  UserCheck
} from "lucide-react";
import Footer from "../components/Layout/Footer";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const fadeIn = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6 }
  };

  const steps = [
    {
      title: "Multilingual Speech Engine",
      desc: "Whisper STT, Groq LLaMA, and Sarvam Bulbul TTS pipeline optimized for sub-second, natural phone conversations.",
      icon: Cpu,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Dynamic RAG Knowledge Base",
      desc: "Indexes custom guidelines, sales scripts, and objection manuals to answer complex queries contextually.",
      icon: Database,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Real-Time Language Switching",
      desc: "Seamlessly detects and transitions between English, Hindi, Hinglish, and other major regional Indian languages.",
      icon: Globe,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Intelligent Lead Scoring",
      desc: "Analyzes conversation sentiments and intents dynamically to segregate leads into Hot, Warm, or Cold status.",
      icon: UserCheck,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Relationship Manager Desk",
      desc: "Instantly alerts and routes High-Intent (Hot) leads to human agents alongside rich call transcripts and summaries.",
      icon: ShieldCheck,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "WhatsApp Follow-up Agent",
      desc: "Nurtures warm leads via automated, context-aware WhatsApp chat interactions driven by the core LLM brain.",
      icon: MessageSquare,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
  ];

  return (
    <div className="min-h-screen bg-[#fefae0] ambient-glow text-[#3d2b1f] selection:bg-[#d4a373]/20 overflow-x-hidden relative">
      {/* Grid Background */}
      <div
        className="fixed inset-0 z-0 opacity-15 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(#d4a373 0.6px, transparent 0.6px)',
          backgroundSize: '32px 32px'
        }}
      />

      {/* Dynamic Golden Snowfall Background */}
      <Snowfall
        color="#d4a373"
        snowflakeCount={190}
        style={{
          position: "fixed",
          width: "100vw",
          height: "100vh",
          zIndex: 1,
          opacity: 0.85,
          pointerEvents: "none",
        }}
      />

      {/* Hero Section */}
      <section className="relative z-10 pt-32 pb-20 px-6 max-w-7xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#faedcd] border border-[#d4a373]/30 text-[#a87440] mb-8 shadow-sm"
        >
          <img src="/logo.png" className="w-5 h-5 object-contain" alt="" />
          <span className="text-xs font-bold uppercase tracking-wider">Enterprise AI Telephony</span>
        </motion.div>

        <motion.h1
          className="text-6xl md:text-8xl font-black tracking-tight mb-8 bg-gradient-to-r from-[#3d2b1f] via-[#b5835a] to-[#d4a373] bg-clip-text text-transparent font-display leading-[1.1]"
          {...fadeIn}
        >
          Sambhaash AI
        </motion.h1>

        <motion.p
          className="text-xl md:text-2xl text-[#3d2b1f]/80 max-w-3xl mx-auto mb-12 leading-relaxed font-sans"
          {...fadeIn}
          transition={{ delay: 0.2 }}
        >
          Automate your outbound phone calls and WhatsApp follow-ups with a smart multilingual AI that answers questions, handles objections, and routes hot prospects directly to your team.
        </motion.p>

        <motion.div
          className="flex flex-wrap justify-center gap-6"
          {...fadeIn}
          transition={{ delay: 0.4 }}
        >
          <button
            onClick={() => navigate('/dashboard')}
            className="group relative px-8 py-4 rounded-2xl bg-[#d4a373] text-white hover:bg-[#c39162] transition-all duration-300 font-bold flex items-center gap-2 shadow-lg shadow-[#d4a373]/20 hover:shadow-[#d4a373]/30 active:scale-95"
          >
            Go to Admin Dashboard
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
          <button className="px-8 py-4 rounded-2xl bg-[#faedcd] border border-[#d4a373]/20 text-[#3d2b1f] font-bold hover:bg-[#f5e3b8] transition-all duration-300 shadow-sm active:scale-95">
            Watch Demo
          </button>
        </motion.div>
      </section>

      {/* Stats/About Section */}
      <section className="relative z-10 py-20 px-6 max-w-7xl mx-auto border-t border-[#d4a373]/20">
        <div className="grid md:grid-cols-3 gap-12 text-center">
          <div className="space-y-2 bg-[#faedcd] rounded-3xl p-6 border border-[#faedcd] shadow-sm hover:scale-[1.02] transition-transform relative z-10">
            <div className="text-5xl font-black text-[#d4a373] font-display">98%</div>
            <p className="text-[#3d2b1f]/80 font-bold">Language accuracy in Hinglish</p>
          </div>
          <div className="space-y-2 bg-[#faedcd] rounded-3xl p-6 border border-[#faedcd] shadow-sm hover:scale-[1.02] transition-transform relative z-10">
            <div className="text-5xl font-black text-[#d4a373] font-display">&lt;200ms</div>
            <p className="text-[#3d2b1f]/80 font-bold">Response latency for human-like flow</p>
          </div>
          <div className="space-y-2 bg-[#faedcd] rounded-3xl p-6 border border-[#faedcd] shadow-sm hover:scale-[1.02] transition-transform relative z-10">
            <div className="text-5xl font-black text-[#d4a373] font-display">10x</div>
            <p className="text-[#3d2b1f]/80 font-bold">Increase in lead engagement rates</p>
          </div>
        </div>
      </section>

      {/* The Flow Section */}
      <section className="relative z-10 py-24 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-black mb-6 text-[#2d1e18] font-display leading-tight">Built for Rupazeey-Grade Performance</h2>
          <p className="text-[#3d2b1f]/80 max-w-2xl mx-auto text-lg font-medium">
            A complete, end-to-end pipeline designed to handle every stage of the lead lifecycle automatically.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {steps.map((step, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              viewport={{ once: true }}
              className="p-8 rounded-3xl bg-[#faedcd] border border-[#faedcd] hover:border-[#d4a373]/50 hover:scale-[1.03] transition-all duration-300 group shadow-sm flex flex-col relative z-10"
            >
              <div className="absolute inset-0 bg-[#fefae0]/40 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none z-0" />
              <div className="w-12 h-12 rounded-2xl bg-[#d4a373]/20 flex items-center justify-center text-[#d4a373] mb-6 group-hover:scale-110 transition-all duration-300 shadow-inner shrink-0 relative z-10">
                <step.icon size={24} />
              </div>
              <h3 className="text-xl font-bold mb-3 text-[#2d1e18] font-display relative z-10">{step.title}</h3>
              <p className="text-[#3d2b1f]/80 leading-relaxed font-medium relative z-10">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Floating CTA */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          className="px-6 py-4 rounded-3xl bg-[#faedcd]/90 backdrop-blur-2xl border border-[#d4a373]/30 flex items-center gap-6 shadow-2xl shadow-[#3d2b1f]/10"
        >
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-bold text-[#3d2b1f]">System Active</span>
          </div>
          <div className="h-4 w-px bg-[#d4a373]/30" />
          <button
            onClick={() => navigate('/dashboard')}
            className="text-sm font-black text-[#d4a373] hover:text-[#b5835a] transition-colors"
          >
            Launch Dashboard
          </button>
        </motion.div>
      </div>

      <Footer />
    </div>
  );
};

export default LandingPage;
