import React, { useState, useEffect } from "react";
import { User, Mail, Shield, Save, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";
import { supabase } from "../services/supabase";

export const ProfileSettingsPage: React.FC = () => {
  const [profile, setProfile] = useState({
    name: "ADMIN",
    email: "admin@sambhaash.ai",
    role: "Administrator",
    avatar: ""
  });

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  // Load active session from Supabase on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      // 💾 Check for customized designation in local storage first
      const saved = localStorage.getItem("user_profile");
      let savedRole = "Administrator";
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (parsed.role) savedRole = parsed.role;
        } catch (e) {}
      }

      if (session?.user) {
        const meta = session.user.user_metadata;
        setProfile({
          name: meta?.full_name || session.user.email?.split("@")[0] || "User",
          email: session.user.email || "",
          role: savedRole,
          avatar: meta?.avatar_url || ""
        });
      } else {
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            setProfile({
              name: parsed.name || "ADMIN",
              email: parsed.email || "admin@sambhaash.ai",
              role: parsed.role || "Administrator",
              avatar: parsed.avatar || ""
            });
          } catch (e) {
            console.error("Failed to parse user profile from local storage", e);
          }
        }
      }
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSuccess(false);

    try {
      // ☁️ Update the user metadata directly in Supabase database!
      const { error } = await supabase.auth.updateUser({
        data: { full_name: profile.name }
      });

      if (error) throw error;

      // Update local storage and notify other layout headers
      localStorage.setItem("user_profile", JSON.stringify(profile));
      window.dispatchEvent(new Event("storage"));
      window.dispatchEvent(new Event("user-profile-updated"));
      
      setSuccess(true);
      toast.success("Profile updated in Supabase cloud!");
    } catch (e: any) {
      console.error("Failed to update profile in Supabase:", e);
      toast.error(e.message || "Failed to update cloud profile.");
    } finally {
      setSaving(false);
      setTimeout(() => setSuccess(false), 3000);
    }
  };

  return (
    <div className="p-6 pt-2 max-w-4xl mx-auto space-y-6">
      {/* Page Header with minimized top margin */}
      <div>
        <h1 className="text-3xl font-black text-[#2d1e18] font-display">Account Settings</h1>
        <p className="text-sm font-semibold text-[#3d2b1f]/70 mt-1">Manage your personal profile and system access credentials.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: Avatar Card */}
        <div className="lg:col-span-1 bg-white/50 backdrop-blur-sm border border-[#faedcd]/60 rounded-3xl p-6 shadow-xl flex flex-col items-center justify-center text-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-b from-[#faedcd]/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
          
          {profile.avatar ? (
            <img
              src={profile.avatar}
              alt={profile.name}
              referrerPolicy="no-referrer"
              className="w-24 h-24 rounded-full object-cover border-4 border-[#d4a373]/30 shadow-lg shadow-[#d4a373]/20 mb-4 transform group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-24 h-24 bg-gradient-to-tr from-[#d4a373] to-[#b5835a] rounded-full flex items-center justify-center text-white text-4xl font-black shadow-lg shadow-[#d4a373]/30 mb-4 transform group-hover:scale-105 transition-transform duration-300 font-display">
              {profile.name ? profile.name.charAt(0).toUpperCase() : "S"}
            </div>
          )}
          
          <h2 className="text-xl font-black text-[#2d1e18] font-display">{profile.name || "ADMIN"}</h2>
          <p className="text-[10px] text-[#3d2b1f] uppercase font-black tracking-widest mt-1 bg-[#faedcd] px-3 py-1 rounded-full border border-[#d4a373]/20">{profile.role || "Administrator"}</p>
          <p className="text-xs font-semibold text-[#3d2b1f]/50 mt-2 break-all">{profile.email || "admin@sambhaash.ai"}</p>
        </div>

        {/* Right Side: Edit Form */}
        <div className="lg:col-span-2 glass rounded-3xl p-8 border border-[#faedcd]/60 shadow-xl bg-white/40 space-y-6">
          <h3 className="text-lg font-black text-[#2d1e18] flex items-center gap-2 pb-4 border-b border-[#faedcd]/60 font-display">
            <User size={20} className="text-[#d4a373]" />
            Profile Details
          </h3>

          <div className="space-y-4">
            {/* Full Name Input */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wide">
                Full Name
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-[#3d2b1f]/40">
                  <User size={18} />
                </span>
                <input
                  type="text"
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  className="w-full pl-11 pr-4 py-3 bg-white/70 border border-[#faedcd] rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] transition-all font-semibold text-[#3d2b1f]"
                  placeholder="Enter full name"
                />
              </div>
            </div>

            {/* Email Address Input */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wide">
                Email Address
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-[#3d2b1f]/40">
                  <Mail size={18} />
                </span>
                <input
                  type="email"
                  value={profile.email}
                  readOnly
                  className="w-full pl-11 pr-4 py-3 bg-gray-100/50 border border-[#faedcd]/60 rounded-2xl cursor-not-allowed font-semibold text-[#3d2b1f]/60"
                  placeholder="Enter email address"
                />
              </div>
            </div>

            {/* Role/Designation Input */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#3d2b1f]/60 uppercase tracking-wide">
                Role
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-[#3d2b1f]/40">
                  <Shield size={18} />
                </span>
                <input
                  type="text"
                  value={profile.role}
                  onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                  className="w-full pl-11 pr-4 py-3 bg-white/70 border border-[#faedcd] rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#d4a373]/30 focus:border-[#d4a373] transition-all font-semibold text-[#3d2b1f]"
                  placeholder="Enter role designation"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#faedcd]/60">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 bg-[#d4a373] hover:bg-[#b5835a] text-white font-bold px-6 py-3 rounded-2xl shadow-lg shadow-[#d4a373]/20 hover:shadow-[#d4a373]/30 transition-all cursor-pointer disabled:opacity-50 active:scale-95 text-sm"
            >
              {saving ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : success ? (
                <CheckCircle size={18} />
              ) : (
                <Save size={18} />
              )}
              {saving ? "Saving..." : success ? "Saved!" : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfileSettingsPage;
