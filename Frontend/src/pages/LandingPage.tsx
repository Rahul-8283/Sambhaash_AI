import React from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { 
  ArrowRight, 
  Cpu, 
  Globe, 
  Database, 
  Zap, 
  BarChart3, 
  MessageSquare, 
  ShieldCheck, 
  UserCheck,
  FileText,
  Activity
} from "lucide-react";

const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  const fadeIn = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6 }
  };

  const steps = [
    { 
      title: "Lead Input", 
      desc: "CSV or manual entry with automated priority scoring.",
      icon: Database,
      color: "bg-blue-500"
    },
    { 
      title: "Instant Trigger", 
      desc: "AI initiates calls the moment a lead is added.",
      icon: Zap,
      color: "bg-yellow-500"
    },
    { 
      title: "Conversation Engine", 
      desc: "Dynamic flow with proactive objection handling.",
      icon: MessageSquare,
      color: "bg-purple-500"
    },
    { 
      title: "Language Detection", 
      desc: "Seamless switching between Hindi, English, and Hinglish.",
      icon: Globe,
      color: "bg-green-500"
    },
    { 
      title: "AI Pipeline", 
      desc: "High-fidelity STT → LLM → TTS architecture.",
      icon: Cpu,
      color: "bg-indigo-500"
    },
    { 
      title: "Contextual Memory", 
      desc: "Remembers past interactions for personalized conversations.",
      icon: Activity,
      color: "bg-pink-500"
    },
    { 
      title: "Lead Classification", 
      desc: "Smart scoring: Hot, Warm, or Cold status.",
      icon: UserCheck,
      color: "bg-orange-500"
    },
    { 
      title: "Follow-up System", 
      desc: "Automated WhatsApp alerts and RM assignments.",
      icon: ShieldCheck,
      color: "bg-cyan-500"
    },
    { 
      title: "Post-Call Summary", 
      desc: "Instant transcripts and action-oriented summaries.",
      icon: FileText,
      color: "bg-red-500"
    },
    { 
      title: "Real-time Analytics", 
      desc: "Complete funnel visibility and conversion tracking.",
      icon: BarChart3,
      color: "bg-teal-500"
    },
  ];

  return (
    <div className="min-h-screen bg-[#030712] text-white selection:bg-blue-500/30 overflow-x-hidden">
      {/* Grid Background */}
      <div className="fixed inset-0 z-0 opacity-20 pointer-events-none" 
           style={{ backgroundImage: 'radial-gradient(#1e40af 0.5px, transparent 0.5px)', backgroundSize: '24px 24px' }}></div>

      {/* Hero Section */}
      <section className="relative z-10 pt-32 pb-20 px-6 max-w-7xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 mb-8"
        >
          <Zap size={16} />
          <span className="text-sm font-medium">Enterprise AI Telephony</span>
        </motion.div>

        <motion.h1 
          className="text-6xl md:text-8xl font-bold tracking-tight mb-8 bg-gradient-to-b from-white to-gray-500 bg-clip-text text-transparent"
          {...fadeIn}
        >
          Sambhaash AI
        </motion.h1>

        <motion.p 
          className="text-xl md:text-2xl text-gray-400 max-w-3xl mx-auto mb-12 leading-relaxed"
          {...fadeIn}
          transition={{ delay: 0.2 }}
        >
          The conversational intelligence layer that turns leads into conversions 
          using state-of-the-art agentic voice AI.
        </motion.p>

        <motion.div 
          className="flex flex-wrap justify-center gap-6"
          {...fadeIn}
          transition={{ delay: 0.4 }}
        >
          <button 
            onClick={() => navigate('/dashboard')}
            className="group relative px-8 py-4 rounded-xl bg-blue-600 hover:bg-blue-500 transition-all font-semibold flex items-center gap-2 shadow-[0_0_20px_rgba(37,99,235,0.4)]"
          >
            Go to Admin Dashboard
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
          <button className="px-8 py-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all font-semibold">
            Watch Demo
          </button>
        </motion.div>
      </section>

      {/* Stats/About Section */}
      <section className="relative z-10 py-20 px-6 max-w-7xl mx-auto border-t border-white/5">
        <div className="grid md:grid-cols-3 gap-12 text-center">
          <div className="space-y-4">
            <div className="text-4xl font-bold text-blue-500">98%</div>
            <p className="text-gray-400">Language accuracy in Hinglish</p>
          </div>
          <div className="space-y-4">
            <div className="text-4xl font-bold text-purple-500">&lt;200ms</div>
            <p className="text-gray-400">Response latency for human-like flow</p>
          </div>
          <div className="space-y-4">
            <div className="text-4xl font-bold text-green-500">10x</div>
            <p className="text-gray-400">Increase in lead engagement rates</p>
          </div>
        </div>
      </section>

      {/* The Flow Section */}
      <section className="relative z-10 py-32 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Built for Rupazeey-Grade Performance</h2>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg">
            A complete, end-to-end pipeline designed to handle every stage of the lead lifecycle automatically.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {steps.map((step, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              viewport={{ once: true }}
              className="p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-blue-500/30 transition-all group"
            >
              <div className={`w-12 h-12 rounded-lg ${step.color} bg-opacity-20 flex items-center justify-center text-white mb-6 group-hover:scale-110 transition-transform`}>
                <step.icon size={24} />
              </div>
              <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
              <p className="text-gray-400 leading-relaxed">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Floating CTA */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          className="px-6 py-4 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 flex items-center gap-6 shadow-2xl"
        >
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-sm font-medium text-gray-300">System Ready</span>
          </div>
          <div className="h-4 w-px bg-white/10"></div>
          <button 
            onClick={() => navigate('/dashboard')}
            className="text-sm font-bold text-blue-400 hover:text-blue-300 transition-colors"
          >
            Launch Dashboard
          </button>
        </motion.div>
      </div>

      <footer className="relative z-10 py-20 text-center border-t border-white/5">
        <p className="text-gray-500">© 2026 Sambhaash AI. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default LandingPage;
