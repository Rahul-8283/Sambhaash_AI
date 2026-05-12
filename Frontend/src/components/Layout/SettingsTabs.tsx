import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { User, Sparkles, Globe, RefreshCw, Key } from "lucide-react";
import clsx from "clsx";

export const SettingsTabs: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const tabs = [
    {
      id: "profile",
      label: "Account Profile",
      path: "/dashboard/settings/profile",
      icon: User,
    },
    {
      id: "prompt",
      label: "Prompt Workspace",
      path: "/dashboard/settings/prompt",
      icon: Sparkles,
    },
    {
      id: "language",
      label: "Language Router",
      path: "/dashboard/settings/language",
      icon: Globe,
    },
    {
      id: "retry",
      label: "Retry Policies",
      path: "/dashboard/settings/retry",
      icon: RefreshCw,
    },
    {
      id: "integrations",
      label: "API Integrations",
      path: "/dashboard/settings/integrations",
      icon: Key,
    },
  ];

  return (
    <div className="w-full border-b border-[#faedcd]/60 pb-2 mb-6 overflow-x-auto scrollbar-none">
      <div className="flex items-center gap-1.5 min-w-max">
        {tabs.map((tab) => {
          const isActive = location.pathname === tab.path;
          const Icon = tab.icon;

          return (
            <button
              key={tab.id}
              onClick={() => navigate(tab.path)}
              className={clsx(
                "relative flex items-center gap-2 px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-wider cursor-pointer transition-all duration-300",
                isActive
                  ? "text-[#3d2b1f] bg-[#faedcd] shadow-md border border-[#d4a373]/30"
                  : "text-[#3d2b1f]/50 hover:text-[#3d2b1f] hover:bg-[#faedcd]/20"
              )}
            >
              <Icon size={14} className={clsx(isActive ? "text-[#d4a373]" : "text-[#3d2b1f]/40")} />
              <span>{tab.label}</span>
              
              {isActive && (
                <motion.div
                  layoutId="active-settings-tab"
                  className="absolute bottom-0 left-6 right-6 h-0.5 bg-[#d4a373] rounded-full"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SettingsTabs;
