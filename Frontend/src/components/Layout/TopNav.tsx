import React, { useState } from "react";
import { Menu, Bell, LogOut, Settings, User } from "lucide-react";

interface TopNavProps {
  onMenuClick: () => void;
  hideMenuButton?: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({ onMenuClick, hideMenuButton }) => {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [notifications] = useState(3);

  const currentUser = {
    name: "Alice Manager",
    email: "alice@example.com",
    role: "Campaign Manager",
  };

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
            className="p-2.5 hover:bg-white/80 rounded-xl transition-colors relative border border-transparent hover:border-gray-100 shadow-sm">
            <Bell size={20} className="text-gray-600" />
            {notifications > 0 && (
              <span className="absolute top-2 right-2 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center border-2 border-white">
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
            className="flex items-center gap-3 px-3 py-1.5 hover:bg-white/80 rounded-xl transition-colors border border-transparent hover:border-gray-100 shadow-sm"
          >
            <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
              {currentUser.name.charAt(0)}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-sm font-bold text-gray-900 leading-tight">
                {currentUser.name}
              </p>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">{currentUser.role}</p>
            </div>
          </button>

          {/* Dropdown menu */}
          {isUserMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-30"
                onClick={() => setIsUserMenuOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-56 bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-gray-100 z-40 overflow-hidden py-2 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="px-4 py-3 mb-2 border-b border-gray-50">
                  <p className="text-sm font-bold text-gray-900">
                    {currentUser.name}
                  </p>
                  <p className="text-xs text-gray-500">{currentUser.email}</p>
                </div>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-600 hover:bg-blue-50 hover:text-blue-600 transition-colors">
                  <User size={16} />
                  Profile Details
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-600 hover:bg-blue-50 hover:text-blue-600 transition-colors">
                  <Settings size={16} />
                  Account Settings
                </button>
                <div className="px-2 mt-2 pt-2 border-t border-gray-50">
                  <button className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-red-500 hover:bg-red-50 rounded-xl transition-colors">
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
