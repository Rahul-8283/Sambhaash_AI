import React, { useState } from "react";
import { Menu, Bell, LogOut, Settings, User } from "lucide-react";

interface TopNavProps {
  onMenuClick: () => void;
  hideMenuButton?: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({ onMenuClick, hideMenuButton }) => {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [notifications] = useState(3);

  const [currentUser, setCurrentUser] = React.useState(() => {
    const saved = localStorage.getItem("user_profile");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    return {
      name: "ADMIN",
      email: "admin@sambhaash.ai",
      role: "sambhaash ai",
    };
  });

  React.useEffect(() => {
    const handleProfileChange = () => {
      const saved = localStorage.getItem("user_profile");
      if (saved) {
        try {
          setCurrentUser(JSON.parse(saved));
        } catch (e) {}
      }
    };
    window.addEventListener("user-profile-updated", handleProfileChange);
    window.addEventListener("storage", handleProfileChange);
    return () => {
      window.removeEventListener("user-profile-updated", handleProfileChange);
      window.removeEventListener("storage", handleProfileChange);
    };
  }, []);

  return (
    <div className="flex items-center gap-4">
      {/* Left side - Menu button */}
      {!hideMenuButton && (
        <button
          onClick={onMenuClick}
          aria-label="Open menu"
          className="md:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Menu size={20} />
        </button>
      )}

      {/* Right side - Notifications and User menu */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <div className="relative">
          <button 
            aria-label="Show notifications"
            className="p-2.5 bg-white/40 hover:bg-[#faedcd]/60 rounded-xl transition-colors relative border border-[#faedcd]/40 shadow-sm">
            <Bell size={20} className="text-[#3d2b1f]" />
            {notifications > 0 && (
              <span className="absolute top-2 right-2 bg-[#d4a373] text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center border-2 border-[#fefae0]">
                {notifications}
              </span>
            )}
          </button>
        </div>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            aria-haspopup="menu"
            aria-expanded={isUserMenuOpen}
            className="flex items-center gap-3 px-3 py-1.5 bg-white/40 hover:bg-[#faedcd]/60 rounded-xl transition-colors border border-[#faedcd]/40 shadow-sm"
          >
            <div className="w-9 h-9 bg-gradient-to-br from-[#d4a373] to-[#b5835a] rounded-full flex items-center justify-center text-white font-bold shadow-md shadow-[#d4a373]/20">
              {currentUser.name.charAt(0)}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-sm font-bold text-[#2d1e18] leading-tight">
                {currentUser.name}
              </p>
              <p className="text-[10px] text-[#3d2b1f]/60 uppercase tracking-wider font-semibold">{currentUser.role}</p>
            </div>
          </button>

          {/* Dropdown menu */}
          {isUserMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-30"
                onClick={() => setIsUserMenuOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-56 bg-[#fefae0]/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-[#faedcd] z-40 overflow-hidden py-2 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="px-4 py-3 mb-2 border-b border-[#faedcd]">
                  <p className="text-sm font-bold text-[#2d1e18]">
                    {currentUser.name}
                  </p>
                  <p className="text-xs text-[#3d2b1f]/60">{currentUser.email}</p>
                </div>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#3d2b1f] hover:bg-[#faedcd]/50 hover:text-[#2d1e18] transition-colors">
                  <User size={16} />
                  Profile Details
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#3d2b1f] hover:bg-[#faedcd]/50 hover:text-[#2d1e18] transition-colors">
                  <Settings size={16} />
                  Account Settings
                </button>
                <div className="px-2 mt-2 pt-2 border-t border-[#faedcd]">
                  <button className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-red-600 hover:bg-red-50/50 rounded-xl transition-colors">
                    <LogOut size={16} />
                    Sign Out
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default TopNav;
