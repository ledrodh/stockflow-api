import React, { useEffect, useRef, useState } from "react";
import {
  Package,
  Boxes,
  AlertTriangle,
  Receipt,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Loader2,
  ShieldAlert,
} from "lucide-react";
import { api } from "../services/api";
import { DashboardSummary } from "../types/api";
import { useAuth } from "../context/AuthContext";

export const DashboardView: React.FC = () => {
  const { user, isAdmin, loading: authLoading } = useAuth();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const isFetchingRef = useRef(false);

  const fetchSummary = async () => {
    if (!isAdmin || isFetchingRef.current) {
      if (!isAdmin) setLoading(false);
      return;
    }
    isFetchingRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const summary = await api.getDashboardSummary();
      setData(summary);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
      isFetchingRef.current = false;
    }
  };

  useEffect(() => {
    let isCancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      if (!isAdmin || isCancelled) return;
      await fetchSummary();
      if (!isCancelled) {
        timer = setTimeout(poll, 30000);
      }
    };

    if (!authLoading && isAdmin) {
      poll();
    }

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [authLoading, isAdmin]);

  if (authLoading || (loading && !data && isAdmin)) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-3">
        <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
        <p className="text-sm text-slate-400">Querying aggregated metrics in PostgreSQL...</p>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="max-w-2xl mx-auto mt-12 p-8 bg-slate-900 border border-slate-800 rounded-3xl text-center space-y-4 shadow-xl">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
          <ShieldAlert className="w-7 h-7" />
        </div>
        <h3 className="text-xl font-bold text-white">Administrator Access Required</h3>
        <p className="text-sm text-slate-400 leading-relaxed">
          Aggregated executive metrics, real-time inventory ledger feeds, and financial revenue summaries are strictly restricted to system administrators (Role: <code>admin</code>).
        </p>
        <p className="text-xs text-slate-400">
          Logged in as: <span className="font-semibold text-slate-300">{user?.email || "Anonymous"}</span> (Role: <span className="font-mono text-brand-400">{user?.role || "none"}</span>)
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Inventory & Sales Dashboard</h2>
          <p className="text-sm text-slate-400 mt-1">
            Consolidated metrics computed directly from PostgreSQL relational engine (non-overlapping 30s auto-refresh)
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-slate-500 font-mono">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={() => fetchSummary()}
            disabled={loading}
            className="self-start sm:self-auto flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Data</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* SKUs */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Products</span>
            <div className="p-2 rounded-xl bg-blue-950/60 text-blue-400 border border-blue-500/20">
              <Package className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white mt-3">{data?.total_products ?? 0}</p>
          <p className="text-[11px] text-slate-400 mt-1">Active catalog SKUs</p>
        </div>

        {/* Total Stock Units */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Physical Units</span>
            <div className="p-2 rounded-xl bg-emerald-950/60 text-emerald-400 border border-emerald-500/20">
              <Boxes className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white mt-3">{data?.total_stock_items ?? 0}</p>
          <p className="text-[11px] text-slate-400 mt-1">Consolidated on-hand</p>
        </div>

        {/* Low Stock Warning */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Critical Stock</span>
            <div className="p-2 rounded-xl bg-amber-950/60 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-amber-400 mt-3">{data?.low_stock_products ?? 0}</p>
          <p className="text-[11px] text-slate-400 mt-1">Below minimum threshold</p>
        </div>

        {/* Total Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Confirmed Orders</span>
            <div className="p-2 rounded-xl bg-indigo-950/60 text-indigo-400 border border-indigo-500/20">
              <Receipt className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-white mt-3">{data?.total_orders ?? 0}</p>
          <p className="text-[11px] text-slate-400 mt-1">Processed atomically</p>
        </div>

        {/* Confirmed Order Value */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Confirmed Order Value</span>
            <div className="p-2 rounded-xl bg-purple-950/60 text-purple-400 border border-purple-500/20">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <p className="text-xl font-bold text-white mt-3">
            ${Number(data?.total_revenue || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Confirmed orders volume</p>
        </div>
      </div>

      {/* Two Column Section: Recent Orders & Recent Movements */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Orders */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white text-base">Recent Orders</h3>
            <span className="text-xs font-mono text-slate-400">Immutable Snapshot</span>
          </div>

          <div className="space-y-3">
            {data?.recent_orders && data.recent_orders.length > 0 ? (
              data.recent_orders.map((order) => (
                <div
                  key={order.id}
                  className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-brand-400">
                        #{order.id.slice(0, 8)}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 font-medium">
                        {order.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      {order.items.length} {order.items.length === 1 ? "item" : "items"} •{" "}
                      {new Date(order.created_at).toLocaleTimeString("en-US")}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-white font-mono">
                      ${Number(order.total_amount).toFixed(2)}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">No orders placed yet.</p>
            )}
          </div>
        </div>

        {/* Recent Inventory Movements */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white text-base">Audit Ledger Feed</h3>
            <span className="text-xs font-mono text-emerald-400">Append-Only</span>
          </div>

          <div className="space-y-3">
            {data?.recent_movements && data.recent_movements.length > 0 ? (
              data.recent_movements.map((mov) => {
                const isOut = mov.type === "OUT" || (mov.type === "ADJUSTMENT" && mov.new_stock < mov.previous_stock);
                return (
                  <div
                    key={mov.id}
                    className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`p-2 rounded-xl ${
                          isOut
                            ? "bg-rose-950/50 text-rose-400 border border-rose-500/20"
                            : "bg-emerald-950/50 text-emerald-400 border border-emerald-500/20"
                        }`}
                      >
                        {isOut ? (
                          <ArrowDownRight className="w-4 h-4" />
                        ) : (
                          <ArrowUpRight className="w-4 h-4" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-200">{mov.type}</span>
                          <span className="text-[11px] text-slate-400 font-mono">
                            {mov.previous_stock} &rarr; {mov.new_stock}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 truncate max-w-[200px] mt-0.5">
                          {mov.reason}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs font-bold font-mono text-slate-200">
                      {isOut ? `-${mov.quantity}` : `+${mov.quantity}`}
                    </span>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">No inventory movements recorded yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
