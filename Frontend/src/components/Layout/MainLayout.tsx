import { useState, useEffect } from "react";
import type { ReactNode, FC } from "react";
import { Menu } from "lucide-react";
import ModernSidebar from "./ModernSidebar";
import TopNav from "./TopNav";

interface MainLayoutProps {
  children: ReactNode;
}

export const MainLayout: FC<MainLayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => typeof window !== "undefined" ? window.innerWidth >= 768 : true);
  const [isMobile, setIsMobile] = useState(() => typeof window !== "undefined" ? window.innerWidth < 768 : false);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // Automatically close sidebar if transitioning to mobile
      if (mobile) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="min-h-screen bg-[#fefae0] ambient-glow flex overflow-x-hidden">
      {/* Mobile Sidebar Backdrop Overlay */}
      {isMobile && isSidebarOpen && (
        <div 
          onClick={toggleSidebar}
          className="fixed inset-0 bg-[#3d2b1f]/40 backdrop-blur-sm z-40 md:hidden transition-opacity duration-300 animate-in fade-in"
        />
      )}

      {/* Modern Floating Sidebar */}
      <ModernSidebar isOpen={isSidebarOpen} onToggle={toggleSidebar} />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 w-full overflow-hidden">
        {/* Top navigation - Responsive Header */}
        <header className="h-20 flex items-center justify-between px-4 md:px-8 bg-transparent shrink-0">
          <div className="flex items-center min-w-0">
            {isMobile && (
              <button
                onClick={toggleSidebar}
                className="p-2.5 bg-white/40 hover:bg-[#faedcd]/60 border border-[#faedcd]/40 shadow-sm rounded-xl text-[#3d2b1f] mr-3 transition-colors cursor-pointer shrink-0"
                aria-label="Toggle Navigation Menu"
              >
                <Menu size={22} className="text-[#3d2b1f]" />
              </button>
            )}
            <div className="truncate">
              <h2 className="text-xs font-semibold text-[#3d2b1f]/60 uppercase tracking-wider truncate">Sambhaash Admin</h2>
              <p className="text-lg md:text-xl font-extrabold text-[#2d1e18] font-display truncate">Dashboard Intelligence</p>
            </div>
          </div>
          <TopNav onMenuClick={toggleSidebar} hideMenuButton={true} />
        </header>

        {/* Content Area */}
        <main className="flex-1 p-4 md:p-6 lg:p-8 overflow-y-auto w-full">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
