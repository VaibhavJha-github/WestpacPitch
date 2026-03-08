import React, { useEffect, useRef } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, 0);
  }, [location.pathname]);
  
  return (
    <div className="h-screen bg-slate-50 font-sans text-slate-900 flex flex-col overflow-hidden">
      {/* Navigation */}
      <nav className="bg-white border-b border-slate-200 px-8 flex items-center justify-between z-50 shrink-0">
        <div className="flex items-center gap-2 py-4">
          {/* Placeholder for logo - using text/icon if image fails but keeping structure */}
          <div className="flex items-center gap-2">
             <img src="/westpac.svg" alt="Westpac" className="h-4" onError={(e) => e.currentTarget.style.display = 'none'}/>
             {/* Fallback if image missing */}
             <span className="text-[#DA1710] font-bold text-xl tracking-tight" style={{display: 'none'}}>Westpac</span> 
          </div>
        </div>
        <div className="flex gap-8 text-base font-medium text-slate-600 h-full">
          <NavLink
            to="/appointment"
            className={({ isActive }) =>
              `flex items-center py-4 border-b-2 -mb-px transition ${
                isActive
                  ? "text-[#DA1710] border-[#DA1710]"
                  : "border-transparent hover:text-slate-900"
              }`
            }
          >
            My Appointments
          </NavLink>
          <NavLink
            to="/calendar"
            className={({ isActive }) =>
              `flex items-center py-4 border-b-2 -mb-px transition ${
                isActive
                  ? "text-[#DA1710] border-[#DA1710]"
                  : "border-transparent hover:text-slate-900"
              }`
            }
          >
            Calendar
          </NavLink>
          <NavLink
            to="/clients"
            className={({ isActive }) =>
              `flex items-center py-4 border-b-2 -mb-px transition ${
                isActive
                  ? "text-[#DA1710] border-[#DA1710]"
                  : "border-transparent hover:text-slate-900"
              }`
            }
          >
            Clients
          </NavLink>
          <NavLink
            to="/live"
            className={({ isActive }) =>
              `flex items-center py-4 border-b-2 -mb-px transition ${
                isActive
                  ? "text-[#DA1710] border-[#DA1710]"
                  : "border-transparent hover:text-slate-900"
              }`
            }
          >
            Live
          </NavLink>
        </div>
        <div className="flex items-center gap-3 py-4">
          <span className="text-sm text-slate-500">Welcome, Mia</span>
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 text-xs font-bold">
            MS
          </div>
        </div>
      </nav>

      <div ref={scrollRef} className="flex-1 overflow-y-auto w-full">
        <div key={location.pathname} className="max-w-7xl mx-auto p-8 page-transition">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Layout;
