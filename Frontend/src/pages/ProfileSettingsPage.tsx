import React, { useState, useEffect } from "react";
import { User, Mail, Shield, Save, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";

export const ProfileSettingsPage: React.FC = () => {
  const [profile, setProfile] = useState({
    name: "Sambhaash ADMIN",
    email: "admin@sambhaash.ai",
    role: "CAMPAIGN MANAGER",
  });

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  // Load from local storage on mount
  useEffect(() => {
    const saved = localStorage.getItem("user_profile");
    if (saved) {
      try {
        setProfile(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse user profile from local storage", e);
      }
    }
  }, []);

  const handleSave = () => {
    setSaving(true);
    setSuccess(false);

    setTimeout(() => {
      localStorage.setItem("user_profile", JSON.stringify(profile));
      
      // Dispatch both standard and custom event to notify components
      window.dispatchEvent(new Event("storage"));
      window.dispatchEvent(new Event("user-profile-updated"));
      
      setSaving(false);
      setSuccess(true);
      toast.success("Profile updated successfully!");

      setTimeout(() => setSuccess(false), 3000);
    }, 800);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">Settings</h1>
        <p className="text-gray-500 mt-2 text-lg">Manage your personal profile and account credentials</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Side: Avatar Card */}
        <div className="lg:col-span-1 bg-white border border-gray-100 rounded-3xl p-6 shadow-xl shadow-gray-100/50 flex flex-col items-center justify-center text-center relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-b from-blue-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
          
          <div className="w-24 h-24 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-full flex items-center justify-center text-white text-4xl font-black shadow-lg shadow-blue-500/30 mb-4 transform group-hover:scale-105 transition-transform duration-300">
            {profile.name ? profile.name.charAt(0).toUpperCase() : "S"}
          </div>
          
          <h2 className="text-xl font-bold text-gray-900">{profile.name || "Sambhaash ADMIN"}</h2>
          <p className="text-xs text-blue-600 uppercase font-bold tracking-widest mt-1 bg-blue-50 px-3 py-1 rounded-full">{profile.role || "CAMPAIGN MANAGER"}</p>
          <p className="text-sm text-gray-400 mt-2 break-all">{profile.email || "admin@sambhaash.ai"}</p>
        </div>

        {/* Right Side: Edit Form */}
        <div className="lg:col-span-2 bg-white border border-gray-100 rounded-3xl p-8 shadow-xl shadow-gray-100/50 space-y-6">
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 pb-4 border-b border-gray-100">
            <User size={20} className="text-blue-600" />
            Profile Details
          </h3>

          <div className="space-y-4">
            {/* Full Name Input */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Full Name
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
                  <User size={18} />
                </span>
                <input
                  type="text"
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  className="w-full pl-11 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium text-gray-900"
                  placeholder="Enter full name"
                />
              </div>
            </div>

            {/* Email Input */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Email Address
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
                  <Mail size={18} />
                </span>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  className="w-full pl-11 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium text-gray-900"
                  placeholder="Enter email address"
                />
              </div>
            </div>

            {/* Role/Designation Input */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Role / Designation
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
                  <Shield size={18} />
                </span>
                <input
                  type="text"
                  value={profile.role}
                  onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                  className="w-full pl-11 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium text-gray-900"
                  placeholder="Enter role designation"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-2xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 disabled:opacity-50 transition-all active:scale-95"
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
