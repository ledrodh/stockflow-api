import React from "react";
import { LogIn, LogOut, ExternalLink, Activity } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { isDemoEnvironment } from "../services/api";

interface HeaderProps {
  onOpenLogin: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenLogin }) => {
  const { user, logout } = useAuth();
  const isDemo = isDemoEnvironment();

  return (
    <header className="h-16 bg-slate-900/60 backdrop-blur border-b border-slate-800 px-8 flex items-center justify-between shrink-0">
      <div className="flex items-center space-x-4">
        {isDemo ? (
          <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400 bg-cyan-950/60 px-3 py-1.5 rounded-full border border-cyan-500/30">
            <Activity className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
            <span>Interactive Demo Mode</span>
          </div>
        ) : (
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded-full border border-emerald-500/30">
            <Activity className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
            <span>PostgreSQL 16 ACID Online</span>
          </div>
        )}
        <span className="text-xs text-slate-400 hidden md:inline">
          Concurrency control via <code className="text-slate-300 font-mono">SELECT FOR UPDATE</code>
        </span>
      </div>

      <div className="flex items-center space-x-3">
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="text-xs font-medium text-slate-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-slate-800 flex items-center gap-1.5 transition-colors border border-slate-800"
        >
          <span>Swagger Docs</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>

        {user ? (
          <button
            onClick={logout}
            className="text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors border border-slate-700"
          >
            <LogOut className="w-3.5 h-3.5 text-rose-400" />
            <span>Sign Out</span>
          </button>
        ) : (
          <button
            onClick={onOpenLogin}
            className="text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white px-4 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shadow-sm shadow-brand-500/20"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In / Switch Role</span>
          </button>
        )}
      </div>
    </header>
  );
};
