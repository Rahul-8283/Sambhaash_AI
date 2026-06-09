import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users,
  Settings,
  FileText,
  Target,
  Home,
  ChevronRight,
  LogOut,
  BarChart3
} from "lucide-react";
import clsx from "clsx";

interface ModernSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const ModernSidebar: React.FC<ModernSidebarProps> = ({ isOpen, onToggle }) => {
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(typeof window !== "undefined" ? window.innerWidth < 768 : false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const isActive = (path: string) => location.pathname.startsWith(path);

  const menuItems = [
    { id: "leads", label: "Leads", path: "/dashboard/leads", icon: Users },
    { id: "analytics", label: "Analytics", path: "/dashboard/analytics", icon: BarChart3 },
    { id: "rm", label: "RM Desk", path: "/dashboard/rm", icon: Target },
    { id: "appendix", label: "Appendix", path: "/dashboard/appendix", icon: FileText },
    { 
      id: "settings", 
      label: "Settings", 
      path: "/dashboard/settings/profile", 
      icon: Settings,
    },
  ];

  return (
    <>
      {/* Sidebar Container */}
      <motion.aside
        initial={false}
        animate={{ 
          width: isMobile ? (isOpen ? 260 : 0) : (isOpen ? 260 : 80),
          x: isMobile ? (isOpen ? 0 : -320) : 0,
          opacity: isMobile ? (isOpen ? 1 : 0) : 1
        }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={clsx(
          "fixed left-4 top-4 bottom-4 z-50 bg-[#faedcd]/90 backdrop-blur-2xl border border-[#d4a373]/30 rounded-[1rem] shadow-2xl flex flex-col overflow-hidden",
          isMobile && !isOpen && "pointer-events-none"
        )}
      >
        {/* Header */}
        <div className="p-6 flex items-center">
          <Link to="/" className="flex items-center gap-4 group">
            <img 
              src="/logo.png" 
              className="w-10 h-10 object-contain shrink-0 group-hover:scale-105 transition-transform duration-200" 
              alt="Sambhaash logo" 
            />
            <AnimatePresence mode="wait">
              {isOpen && (
                <motion.span
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                  className="font-bold text-2xl text-[#2d1e18] whitespace-nowrap tracking-tight font-display"
                >
                  Sambhaash
                </motion.span>
              )}
            </AnimatePresence>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-1 py-4 overflow-y-auto overflow-x-hidden">
          {menuItems.map((item) => (
            <Link
              key={item.id}
              to={item.path}
              onMouseEnter={() => setHoveredItem(item.id)}
              onMouseLeave={() => setHoveredItem(null)}
              className={clsx(
                "relative flex items-center gap-4 px-3 py-3 rounded-lg transition-all duration-200",
                isActive(item.path)
                  ? "bg-[#d4a373] text-white shadow-lg shadow-[#d4a373]/20"
                  : "text-[#3d2b1f]/70 hover:bg-[#fefae0] hover:text-[#3d2b1f]"
              )}
            >
              <div className="shrink-0 w-6 flex justify-center">
                <item.icon size={22} className={clsx(isActive(item.path) ? "text-white" : "text-[#3d2b1f]/75")} />
              </div>
              
              <AnimatePresence mode="wait">
                {isOpen && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.15 }}
                    className="font-semibold whitespace-nowrap text-[15px]"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>

              {!isOpen && hoveredItem === item.id && (
                <div className="fixed left-24 px-3 py-2 bg-[#2d1e18] text-[#fefae0] text-xs font-semibold rounded-lg shadow-xl pointer-events-none z-[60]">
                  {item.label}
                </div>
              )}
              
              {isActive(item.path) && isOpen && (
                <motion.div
                  layoutId="active-indicator"
                  className="ml-auto text-white"
                >
                  <ChevronRight size={16} />
                </motion.div>
              )}
            </Link>
          ))}
        </nav>

        {/* Footer Actions */}
        <div className="p-3 border-t border-[#d4a373]/20 space-y-1">
          <Link
            to="/"
            className="flex items-center gap-4 px-3 py-3 rounded-lg text-[#3d2b1f]/70 hover:bg-[#fefae0] hover:text-[#3d2b1f] transition-all duration-200"
          >
            <div className="shrink-0 w-6 flex justify-center">
              <Home size={22} className="text-[#3d2b1f]/75" />
            </div>
            {isOpen && <span className="font-semibold text-[15px]">Home</span>}
          </Link>
          <button
            onClick={onToggle}
            className="w-full flex items-center gap-4 px-3 py-3 rounded-lg text-[#3d2b1f]/70 hover:bg-[#fefae0] hover:text-[#3d2b1f] transition-all duration-200"
          >
            <div className={clsx("shrink-0 w-6 flex justify-center transition-transform duration-300", !isOpen && "rotate-180")}>
              <LogOut size={22} className="rotate-180 text-[#3d2b1f]/75" />
            </div>
            {isOpen && <span className="font-semibold text-[15px]">Collapse</span>}
          </button>
        </div>
      </motion.aside>

      {/* Synchronized Spacer */}
      <motion.div 
        initial={false}
        animate={{ width: isMobile ? 0 : (isOpen ? 260 : 80) }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="shrink-0 hidden md:block"
      />
    </>
  );
};

export default ModernSidebar;
