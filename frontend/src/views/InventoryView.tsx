import React, { useEffect, useState } from "react";
import {
  History,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Loader2,
  X,
  AlertCircle,
  ShieldAlert,
  CheckCircle2,
  FileCheck2,
} from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  AdjustmentDirection,
  InventoryMovement,
  MovementType,
  Product,
  StockReconciliationReport,
} from "../types/api";

export const InventoryView: React.FC = () => {
  const { user, isAdmin, loading: authLoading } = useAuth();
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 15;

  // Manual Movement Modal
  const [showModal, setShowModal] = useState(false);
  const [targetProductId, setTargetProductId] = useState("");
  const [movementType, setMovementType] = useState<MovementType>("IN");
  const [quantity, setQuantity] = useState("5");
  const [adjDirection, setAdjDirection] = useState<AdjustmentDirection>("INCREASE");
  const [reason, setReason] = useState("");
  const [refId, setRefId] = useState("");
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Reconciliation Report Modal
  const [showReconModal, setShowReconModal] = useState(false);
  const [reconReport, setReconReport] = useState<StockReconciliationReport | null>(null);
  const [reconLoading, setReconLoading] = useState(false);
  const [reconError, setReconError] = useState<string | null>(null);

  const fetchMovements = async () => {
    if (!isAdmin) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.getInventoryMovements({
        type: typeFilter || undefined,
        limit,
        offset: page * limit,
      });
      setMovements(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(
        err?.status === 403
          ? "HTTP 403 Forbidden: Administrator role is required to view the inventory ledger."
          : err?.message || "Failed to load audit ledger movements."
      );
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    if (!isAdmin) return;
    try {
      const res = await api.getProducts({ limit: 100 });
      setProducts(res.items);
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleRunReconciliation = async () => {
    setShowReconModal(true);
    setReconLoading(true);
    setReconError(null);
    try {
      const report = await api.getReconciliationReport();
      setReconReport(report);
    } catch (err: any) {
      setReconError(err?.message || "Failed to execute inventory reconciliation.");
    } finally {
      setReconLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      fetchMovements();
    }
  }, [authLoading, isAdmin, typeFilter, page]);

  useEffect(() => {
    if (isAdmin) {
      fetchProducts();
    }
  }, [isAdmin]);

  if (authLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-3">
        <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
        <p className="text-sm text-slate-400">Authenticating access...</p>
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
          The Append-Only Inventory Ledger (movements audit trail, stock adjustments, and supplier restock entries) is strictly restricted to system administrators (Role: <code>admin</code>).
        </p>
        <p className="text-xs text-slate-400">
          Current session: <span className="font-semibold text-slate-300">{user?.email || "Anonymous"}</span> (Role: <span className="font-mono text-brand-400">{user?.role || "none"}</span>)
        </p>
      </div>
    );
  }

  const handleCreateMovement = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalLoading(true);
    setModalError(null);

    if (movementType === "RETURN" && !refId.trim()) {
      setModalError("Reference Document ID is required for RETURN movements to ensure auditability.");
      setModalLoading(false);
      return;
    }

    try {
      await api.createInventoryMovement({
        product_id: targetProductId,
        type: movementType,
        quantity: parseInt(quantity, 10),
        adjustment_direction: movementType === "ADJUSTMENT" ? adjDirection : undefined,
        reason,
        reference_id: refId.trim() || undefined,
      });
      setShowModal(false);
      setReason("");
      setRefId("");
      fetchMovements();
    } catch (err: any) {
      setModalError(err?.message || "Failed to register stock movement.");
    } finally {
      setModalLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Append-Only Audit Ledger</h2>
          <p className="text-sm text-slate-400 mt-1">
            Database-enforced append-only inventory history protected by PostgreSQL triggers
          </p>
        </div>

        {isAdmin && (
          <div className="flex items-center gap-2.5 self-start sm:self-auto">
            <button
              onClick={handleRunReconciliation}
              className="flex items-center gap-2 px-3.5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-all shadow-sm"
            >
              <FileCheck2 className="w-4 h-4 text-emerald-400" />
              <span>Verify Reconciliation</span>
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-brand-500/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Record Manual Movement</span>
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Info Callout */}
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <strong className="text-white">Append-Only Immutability:</strong> The{" "}
          <code className="text-emerald-400 font-mono">inventory_movements</code> table is guarded by the{" "}
          <code className="text-emerald-400 font-mono">trg_immutable_inventory_movements</code> PostgreSQL trigger.
          Every row has a strictly incrementing <code className="text-brand-400 font-mono">movement_sequence</code> and arithmetic check constraints, guaranteeing mathematical integrity.
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        {["", "OPENING", "IN", "OUT", "ADJUSTMENT", "RETURN"].map((t) => (
          <button
            key={t}
            onClick={() => {
              setTypeFilter(t);
              setPage(0);
            }}
            className={`px-3.5 py-2 rounded-xl font-medium transition-colors border ${
              typeFilter === t
                ? "bg-brand-600/20 text-brand-300 border-brand-500/30"
                : "bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800 hover:text-slate-200"
            }`}
          >
            {t ? `Type: ${t}` : "All Records"}
          </button>
        ))}
      </div>

      {/* Movements Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="px-5 py-4 font-semibold">Seq #</th>
                <th className="px-5 py-4 font-semibold">Type</th>
                <th className="px-5 py-4 font-semibold">Qty</th>
                <th className="px-5 py-4 font-semibold">Stock Transition</th>
                <th className="px-5 py-4 font-semibold">Audit Justification / Reason</th>
                <th className="px-5 py-4 font-semibold">Ref / Document</th>
                <th className="px-5 py-4 font-semibold">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 text-brand-500 animate-spin mx-auto mb-2" />
                    Querying immutable ledger...
                  </td>
                </tr>
              ) : movements.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                    <History className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                    No movements found for this filter.
                  </td>
                </tr>
              ) : (
                movements.map((m) => {
                  const isOut =
                    m.type === "OUT" ||
                    (m.type === "ADJUSTMENT" &&
                      (m.adjustment_direction === "DECREASE" || m.new_stock < m.previous_stock));
                  const isOpening = m.type === "OPENING";
                  return (
                    <tr key={m.id} className="hover:bg-slate-850/50 transition-colors">
                      <td className="px-5 py-4 font-mono font-bold text-slate-400">
                        #{m.movement_sequence}
                      </td>
                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-mono font-bold ${
                            isOpening
                              ? "bg-indigo-950/60 text-indigo-400 border border-indigo-500/30"
                              : isOut
                              ? "bg-rose-950/60 text-rose-400 border border-rose-500/30"
                              : "bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
                          }`}
                        >
                          {isOut ? (
                            <ArrowDownRight className="w-3.5 h-3.5" />
                          ) : (
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          )}
                          {m.type}
                          {m.type === "ADJUSTMENT" && m.adjustment_direction && ` (${m.adjustment_direction})`}
                        </span>
                      </td>
                      <td className="px-5 py-4 font-mono font-bold text-white">
                        {isOut ? `-${m.quantity}` : `+${m.quantity}`}
                      </td>
                      <td className="px-5 py-4 font-mono text-slate-300">
                        {m.previous_stock} &rarr;{" "}
                        <strong className="text-white">{m.new_stock} units</strong>
                      </td>
                      <td className="px-5 py-4 text-slate-200">{m.reason}</td>
                      <td className="px-5 py-4 font-mono text-[11px] text-slate-400">
                        {m.reference_id || "-"}
                      </td>
                      <td className="px-5 py-4 text-[11px] text-slate-400">
                        {new Date(m.created_at).toLocaleString("en-US")}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > limit && (
          <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Page {page + 1} of {Math.ceil(total / limit)} (Total: {total})
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 disabled:opacity-40 text-slate-200 border border-slate-700 font-medium"
              >
                Previous
              </button>
              <button
                disabled={(page + 1) * limit >= total}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 disabled:opacity-40 text-slate-200 border border-slate-700 font-medium"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Manual Movement Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-bold text-white mb-1">Record Stock Movement</h3>
            <p className="text-xs text-slate-400 mb-5">
              Record a supplier restock, return, or physical inventory adjustment.
            </p>

            {modalError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleCreateMovement} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-300 mb-1">Target Product *</label>
                <select
                  required
                  value={targetProductId}
                  onChange={(e) => setTargetProductId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-brand-500"
                >
                  <option value="">Select a product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      [{p.sku}] {p.name} (Current: {p.stock_quantity})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Type *</label>
                  <select
                    value={movementType}
                    onChange={(e) => setMovementType(e.target.value as MovementType)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-brand-500 font-mono"
                  >
                    <option value="IN">IN (Restock)</option>
                    <option value="RETURN">RETURN (Customer Return)</option>
                    <option value="ADJUSTMENT">ADJUSTMENT (Audit)</option>
                    <option value="OUT">OUT (Manual Exit)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-slate-300 mb-1">Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 font-mono text-center focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              {movementType === "ADJUSTMENT" && (
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Adjustment Direction *</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setAdjDirection("INCREASE")}
                      className={`py-2 px-3 rounded-xl border text-center font-medium ${
                        adjDirection === "INCREASE"
                          ? "bg-emerald-950/60 border-emerald-500/50 text-emerald-400 font-bold"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      + INCREASE (Add)
                    </button>
                    <button
                      type="button"
                      onClick={() => setAdjDirection("DECREASE")}
                      className={`py-2 px-3 rounded-xl border text-center font-medium ${
                        adjDirection === "DECREASE"
                          ? "bg-rose-950/60 border-rose-500/50 text-rose-400 font-bold"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      - DECREASE (Deduct)
                    </button>
                  </div>
                </div>
              )}

              <div>
                <label className="block font-medium text-slate-300 mb-1">
                  Reference Document ID {movementType === "RETURN" && <span className="text-amber-400">*</span>}
                </label>
                <input
                  type="text"
                  required={movementType === "RETURN"}
                  value={refId}
                  onChange={(e) => setRefId(e.target.value)}
                  placeholder={
                    movementType === "RETURN"
                      ? "Original Order ID or RMA Reference (required)"
                      : "e.g. INVOICE-9821 or AUDIT-2026-01"
                  }
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-brand-500 font-mono"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-300 mb-1">Justification / Reason *</label>
                <textarea
                  required
                  rows={2}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain why this inventory movement occurred..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>

              <button
                type="submit"
                disabled={modalLoading}
                className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all mt-4"
              >
                {modalLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>Append Movement to Ledger</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Reconciliation Modal */}
      {showReconModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setShowReconModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-emerald-950/60 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Stock Reconciliation Diagnostic</h3>
                <p className="text-xs text-slate-400">
                  Executed under PostgreSQL <code>REPEATABLE READ, READ ONLY</code> snapshot isolation
                </p>
              </div>
            </div>

            {reconLoading ? (
              <div className="py-16 text-center text-slate-400 space-y-3">
                <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mx-auto" />
                <p className="text-sm font-medium text-slate-300">
                  Verifying sequence, chain continuity, and ledger arithmetic across all products...
                </p>
              </div>
            ) : reconError ? (
              <div className="p-4 my-4 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-sm">
                {reconError}
              </div>
            ) : reconReport ? (
              <div className="space-y-4 my-4 text-xs">
                {/* Metric Cards */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                    <span className="text-[11px] text-slate-400">Products Checked</span>
                    <p className="text-lg font-bold text-white mt-1">{reconReport.total_products_checked}</p>
                  </div>
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                    <span className="text-[11px] text-slate-400">Consistent</span>
                    <p className="text-lg font-bold text-emerald-400 mt-1">
                      {reconReport.consistent_products_count}
                    </p>
                  </div>
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                    <span className="text-[11px] text-slate-400">Discrepancies</span>
                    <p
                      className={`text-lg font-bold mt-1 ${
                        reconReport.discrepant_products_count > 0 ? "text-rose-400" : "text-slate-400"
                      }`}
                    >
                      {reconReport.discrepant_products_count}
                    </p>
                  </div>
                </div>

                {reconReport.is_consistent ? (
                  <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/30 flex items-center gap-3 text-emerald-300">
                    <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                    <div>
                      <p className="font-semibold text-sm text-emerald-200">100% Ledger Consistency Verified</p>
                      <p className="text-xs text-emerald-400/80 mt-0.5">
                        All physical product stock balances perfectly match the sum of their sequential, immutable audit movements.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="font-semibold text-rose-400">Discrepancies Detected:</p>
                    <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
                      {reconReport.discrepancies.map((d) => (
                        <div
                          key={d.product_id}
                          className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-200 space-y-1"
                        >
                          <div className="flex justify-between font-mono font-bold">
                            <span>[{d.sku}] {d.product_name}</span>
                            <span>Delta: {d.discrepancy_delta}</span>
                          </div>
                          <p className="text-[11px] text-slate-400">
                            Current Stock: {d.current_stock_quantity} | Ledger Stock: {d.calculated_ledger_stock}
                          </p>
                          {d.sequence_errors.map((e, idx) => (
                            <p key={idx} className="text-[11px] text-amber-300">• Seq: {e}</p>
                          ))}
                          {d.continuity_errors.map((e, idx) => (
                            <p key={idx} className="text-[11px] text-amber-300">• Chain: {e}</p>
                          ))}
                          {d.arithmetic_errors.map((e, idx) => (
                            <p key={idx} className="text-[11px] text-rose-300">• Math: {e}</p>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowReconModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold"
              >
                Close Diagnostic
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
