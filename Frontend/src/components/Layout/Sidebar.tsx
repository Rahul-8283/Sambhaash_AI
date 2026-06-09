/**
 * Sidebar navigation component
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Users,
  Settings,
  X,
  FileText,
  Target,
  BarChart3,
} from "lucide-react";
import clsx from "clsx";

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onToggle }) => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname.startsWith(path);

  const menuItems = [
    {
      id: "leads",
      label: "Leads",
      path: "/dashboard/leads",
      icon: Users,
    },
    {
      id: "analytics",
      label: "Analytics",
      path: "/dashboard/analytics",
      icon: BarChart3,
    },
    {
      id: "rm",
      label: "RM Desk",
      path: "/dashboard/rm",
      icon: Target,
    },
    {
      id: "appendix",
      label: "Appendix",
      path: "/dashboard/appendix",
      icon: FileText,
    },
    {
      id: "settings",
      label: "Settings",
      path: "/dashboard/settings/profile",
      icon: Settings,
    },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed md:relative z-30 h-screen w-64 bg-white border-r border-gray-200 transition-transform duration-300 flex flex-col",
          !isOpen && "-translate-x-full md:translate-x-0"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-blue-600">Sambhaash</h1>
          <button
            onClick={onToggle}
            aria-label="Close sidebar"
            className="md:hidden p-1 hover:bg-gray-100 rounded"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-2">
          {menuItems.map((item) => (
            <div key={item.id}>
              <Link
                to={item.path}
                className={clsx(
                  "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive(item.path)
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-700 hover:bg-gray-100"
                )}
              >
                {item.icon && <item.icon size={18} />}
                {item.label}
              </Link>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">v0.1.0 • MVP</p>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
