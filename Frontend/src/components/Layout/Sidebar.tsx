/**
 * Sidebar navigation component
 */

import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  BarChart3,
  Phone,
  Users,
  Zap,
  Settings,
  ChevronDown,
  ChevronRight,
  X,
} from "lucide-react";
import clsx from "clsx";

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onToggle }) => {
  const location = useLocation();
  const [openMenus, setOpenMenus] = useState<string[]>(["settings"]);

  const toggleMenu = (id: string) => {
    setOpenMenus((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const isActive = (path: string) => location.pathname.startsWith(path);

  const menuItems = [
    {
      id: "leads",
      label: "Leads",
      path: "/dashboard/leads",
      icon: Users,
    },
    {
      id: "calls",
      label: "Calls",
      path: "/dashboard/calls",
      icon: Phone,
    },
    {
      id: "analytics",
      label: "Analytics",
      path: "/dashboard/analytics",
      icon: BarChart3,
    },
    {
      id: "campaigns",
      label: "Campaigns",
      path: "/dashboard/campaigns",
      icon: Zap,
    },
    {
      id: "settings",
      label: "Settings",
      icon: Settings,
      submenu: [
        { label: "Prompt", path: "/dashboard/settings/prompt" },
        { label: "Language", path: "/dashboard/settings/language" },
        { label: "Retry Logic", path: "/dashboard/settings/retry" },
        { label: "Integrations", path: "/dashboard/settings/integrations" },
      ],
    },
    {
      id: "users",
      label: "Users",
      path: "/dashboard/users",
      icon: Users,
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
              {item.submenu ? (
                // Submenu item
                <button
                  onClick={() => toggleMenu(item.id)}
                  aria-expanded={openMenus.includes(item.id)}
                  className={clsx(
                    "w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    openMenus.includes(item.id)
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  )}
                >
                  <div className="flex items-center gap-3">
                    {item.icon && <item.icon size={18} />}
                    {item.label}
                  </div>
                  {openMenus.includes(item.id) ? (
                    <ChevronDown size={16} />
                  ) : (
                    <ChevronRight size={16} />
                  )}
                </button>
              ) : (
                // Regular link item
                <Link
                  to={item.path || "#"}
                  className={clsx(
                    "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                    isActive(item.path || "/")
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  )}
                >
                  {item.icon && <item.icon size={18} />}
                  {item.label}
                </Link>
              )}

              {/* Submenu items */}
              {item.submenu && openMenus.includes(item.id) && (
                <div className="pl-4 mt-1 space-y-1">
                  {item.submenu.map((subitem) => (
                    <Link
                      key={subitem.path}
                      to={subitem.path}
                      className={clsx(
                        "block px-4 py-2 rounded-lg text-sm transition-colors",
                        isActive(subitem.path)
                          ? "bg-blue-100 text-blue-700 font-medium"
                          : "text-gray-600 hover:bg-gray-100"
                      )}
                    >
                      {subitem.label}
                    </Link>
                  ))}
                </div>
              )}
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
