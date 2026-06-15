import React, { useState } from "react";
import { motion } from "framer-motion";
import { Send, Phone, User, Mail, Globe2, ChevronDown, X, MessageSquare, PhoneCall } from "lucide-react";
import toast from "react-hot-toast";
import { apiService } from "../services/apiService";

export const LeadCaptureForm: React.FC = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    language: "en"
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showVerificationModal, setShowVerificationModal] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formattedPhone = `+91${formData.phone.replace(/\D/g, '')}`;
    if (formattedPhone.length < 13) {
      toast.error("Please enter a valid 10-digit mobile number");
      return;
    }
    setShowVerificationModal(true);
  };

  const handleProceed = async () => {
    setIsSubmitting(true);

    try {
      const formattedPhone = `+91${formData.phone.replace(/\D/g, '')}`;

      await apiService.submitPublicLead({
        name: formData.name,
        email: formData.email,
        phone: formattedPhone,
        language: formData.language
      });

      toast.success("Thanks! We have received your request and will contact you soon.", {
        style: {
          background: "#fefae0",
          color: "#3d2b1f",
          border: "2px solid #faedcd"
        },
        iconTheme: {
          primary: "#d4a373",
          secondary: "#fefae0"
        }
      });

      setFormData({ name: "", email: "", phone: "", language: "en" });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || "Failed to submit form");
    } finally {
      setIsSubmitting(false);
      setShowVerificationModal(false);
    }
  };

  return (
    <>
      <section className="relative z-10 py-24 px-6 max-w-4xl mx-auto border-t border-[#d4a373]/20">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="bg-[#faedcd] p-10 rounded-2xl border border-[#d4a373]/30 shadow-lg"
      >
        <div className="text-center mb-10">
          <h2 className="text-3xl font-black mb-4 text-[#2d1e18] font-display">Experience the AI Agent Live</h2>
          <p className="text-[#3d2b1f]/80 font-medium max-w-lg mx-auto">
            Drop your number below and our AI agent will call you instantly to demonstrate its multilingual capabilities.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl mx-auto">
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-bold text-[#3d2b1f]/80 ml-1">Full Name</label>
              <div className="relative">
                <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#d4a373]" />
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Your Name"
                  className="w-full bg-[#fefae0] border border-[#d4a373]/30 rounded-xl py-3 pl-12 pr-4 text-[#3d2b1f] placeholder:text-[#3d2b1f]/40 focus:outline-none focus:border-[#d4a373] focus:ring-2 focus:ring-[#d4a373]/20 transition-all font-medium"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-bold text-[#3d2b1f]/80 ml-1">Email Address</label>
              <div className="relative">
                <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#d4a373]" />
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="user@example.com"
                  className="w-full bg-[#fefae0] border border-[#d4a373]/30 rounded-xl py-3 pl-12 pr-4 text-[#3d2b1f] placeholder:text-[#3d2b1f]/40 focus:outline-none focus:border-[#d4a373] focus:ring-2 focus:ring-[#d4a373]/20 transition-all font-medium"
                />
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-bold text-[#3d2b1f]/80 ml-1">Mobile Number</label>
              <div className="relative">
                <Phone size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#d4a373] z-10" />
                <div className="absolute left-10 top-1/2 -translate-y-1/2 text-[#3d2b1f] font-bold z-10 border-r border-[#d4a373]/30 pr-2">
                  +91
                </div>
                <input
                  type="tel"
                  required
                  maxLength={10}
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="9876543210"
                  className="w-full bg-[#fefae0] border border-[#d4a373]/30 rounded-xl py-3 pl-24 pr-4 text-[#3d2b1f] placeholder:text-[#3d2b1f]/40 focus:outline-none focus:border-[#d4a373] focus:ring-2 focus:ring-[#d4a373]/20 transition-all font-medium"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-bold text-[#3d2b1f]/80 ml-1">Preferred Language</label>
              <div className="relative bg-[#fefae0] rounded-xl border border-[#d4a373]/30 focus-within:border-[#d4a373] focus-within:ring-2 focus-within:ring-[#d4a373]/20 transition-all">
                <Globe2 size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#d4a373] pointer-events-none" />
                <select
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                  className="w-full bg-transparent py-3 pl-12 pr-10 text-[#3d2b1f] focus:outline-none font-medium appearance-none cursor-pointer"
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi (हिंदी)</option>
                  <option value="bn">Bengali (বাংলা)</option>
                  <option value="te">Telugu (తెలుగు)</option>
                  <option value="mr">Marathi (मराठी)</option>
                  <option value="ta">Tamil (தமிழ்)</option>
                  <option value="ur">Urdu (اردو)</option>
                  <option value="gu">Gujarati (ગુજરાતી)</option>
                  <option value="kn">Kannada (ಕನ್ನಡ)</option>
                  <option value="ml">Malayalam (മലയാളം)</option>
                  <option value="pa">Punjabi (ਪੰਜਾਬੀ)</option>
                </select>
                <ChevronDown size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-[#d4a373] pointer-events-none" />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-8 px-8 py-4 rounded-xl bg-[#d4a373] text-white font-bold hover:bg-[#c39162] transition-all duration-300 shadow-lg shadow-[#d4a373]/20 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 group"
          >
            {isSubmitting ? "Connecting..." : "Request Call Now"}
            <Send size={18} className={isSubmitting ? "animate-pulse" : "group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform"} />
          </button>
        </form>
      </motion.div>

      </section>

      {/* Verification Splash Modal */}
      {showVerificationModal && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowVerificationModal(false);
          }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-[#fefae0] rounded-3xl max-w-lg w-full p-8 shadow-2xl relative border border-[#d4a373]/30"
          >
            <button 
              onClick={() => setShowVerificationModal(false)}
              className="absolute top-5 right-5 text-[#3d2b1f]/60 hover:text-[#d4a373] transition-colors"
            >
              <X size={24} strokeWidth={3} />
            </button>
            
            <div className="text-center mb-6">
              <h3 className="text-2xl font-black text-[#2d1e18] font-display mb-2">Sandbox Verification</h3>
              <p className="text-[#3d2b1f]/70 font-medium text-sm">
                Before proceeding, please ensure you've completed the Twilio test environment setup for this phone number.
              </p>
            </div>

            <div className="space-y-4 mb-8">
              <div className="bg-[#faedcd]/40 p-4 rounded-2xl border border-[#d4a373]/20 flex gap-4 items-start">
                <div className="p-2 bg-[#d4a373]/10 text-[#d4a373] rounded-xl shrink-0">
                  <PhoneCall size={20} />
                </div>
                <div>
                  <h4 className="font-bold text-[#3d2b1f] text-sm mb-1">1. Voice Call Verification</h4>
                  <p className="text-xs text-[#3d2b1f]/70 leading-relaxed">
                    Make sure this number is added and verified in the Twilio Caller IDs list, as we are using a trial account.
                  </p>
                </div>
              </div>
              
              <div className="bg-[#faedcd]/40 p-4 rounded-2xl border border-[#d4a373]/20 flex gap-4 items-start">
                <div className="p-2 bg-[#d4a373]/10 text-[#d4a373] rounded-xl shrink-0">
                  <MessageSquare size={20} />
                </div>
                <div>
                  <h4 className="font-bold text-[#3d2b1f] text-sm mb-1">2. WhatsApp Sandbox</h4>
                  <p className="text-xs text-[#3d2b1f]/70 leading-relaxed">
                    To receive AI follow-up texts, you must join the Twilio WhatsApp Sandbox by sending the join code to our sandbox number first.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => setShowVerificationModal(false)}
                className="flex-1 px-4 py-3 rounded-xl border-2 border-[#d4a373]/20 text-[#3d2b1f]/70 font-bold hover:bg-[#faedcd]/50 hover:text-[#3d2b1f] transition-all"
              >
                Deny
              </button>
              <button
                type="button"
                onClick={handleProceed}
                disabled={isSubmitting}
                className="flex-1 px-4 py-3 rounded-xl bg-[#d4a373] text-white font-bold hover:bg-[#c39162] transition-all shadow-lg flex justify-center items-center gap-2"
              >
                {isSubmitting ? "Submitting..." : "Completed"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </>
  );
};

export default LeadCaptureForm;
