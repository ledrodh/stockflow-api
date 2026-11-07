import React from "react";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  History,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export type NavTab = "dashboard" | "products" | "orders" | "inventory";

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const { user, isAdmin } = useAuth();

  const navItems = [
    {
      id: "dashboard" as NavTab,
      label: "Dashboard",
      icon: LayoutDashboard,
      desc: "Overview & key metrics",
      adminOnly: true,
    },
    {
      id: "products" as NavTab,
      label: "Catalog",
      icon: Package,
      desc: "Products & inventory",
      adminOnly: false,
    },
    {
      id: "orders" as NavTab,
      label: "Sales Terminal",
      icon: ShoppingCart,
      desc: "Atomic orders & idempotency",
      adminOnly: false,
    },
    {
      id: "inventory" as NavTab,
      label: "Audit Ledger",
      icon: History,
      desc: "Immutable stock trail",
      adminOnly: true,
    },
  ];

  const visibleNavItems = navItems.filter((item) => {
    // Hide administrative management options for customer accounts
    if (user && !isAdmin && item.adminOnly) {
      return false;
    }
    return true;
  });

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
              StockFlow
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400 border border-brand-500/30">
                API
              </span>
            </h1>
            <p className="text-xs text-slate-400">ACID Inventory Engine</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1.5">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center space-x-3 px-3.5 py-3 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-brand-600/15 text-brand-400 border border-brand-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? "text-brand-400" : "text-slate-400"}`} />
                <div className="text-left">
                  <div className="leading-none">{item.label}</div>
                  <div className="text-[11px] text-slate-400 font-normal mt-0.5">{item.desc}</div>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center space-x-3 p-2 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center">
            <ShieldCheck className={`w-4 h-4 ${isAdmin ? "text-amber-400" : "text-emerald-400"}`} />
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-semibold text-slate-200 truncate">
              {user ? user.full_name : "Guest Visitor"}
            </p>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-mono">
              {user ? user.role : "Unauthenticated"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};
