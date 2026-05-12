import { useState } from "react";
import type { ReactNode, FC } from "react";
import ModernSidebar from "./ModernSidebar";
import TopNav from "./TopNav";

interface MainLayoutProps {
  children: ReactNode;
}

export const MainLayout: FC<MainLayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="min-h-screen bg-[#fefae0] ambient-glow flex">
      {/* Modern Floating Sidebar */}
      <ModernSidebar isOpen={isSidebarOpen} onToggle={toggleSidebar} />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top navigation - Optional, can be integrated into content or sidebar */}
        <header className="h-20 flex items-center justify-between px-8 bg-transparent">
          <div>
            <h2 className="text-sm font-semibold text-[#3d2b1f]/60 uppercase tracking-wider">Sambhaash Admin</h2>
            <p className="text-xl font-extrabold text-[#2d1e18] font-display">Dashboard Intelligence</p>
          </div>
          <TopNav onMenuClick={toggleSidebar} hideMenuButton={true} />
        </header>

        {/* Content Area */}
        <main className="flex-1 p-6 lg:p-8 overflow-auto">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
