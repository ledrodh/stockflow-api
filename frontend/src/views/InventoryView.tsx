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
} from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { InventoryMovement, MovementType, Product } from "../types/api";

export const InventoryView: React.FC = () => {
  const { isAdmin } = useAuth();
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 15;

  // Manual Movement Modal
  const [showModal, setShowModal] = useState(false);
  const [targetProductId, setTargetProductId] = useState("");
  const [movementType, setMovementType] = useState<MovementType>("IN");
  const [quantity, setQuantity] = useState("5");
  const [isDeduction, setIsDeduction] = useState(false);
  const [reason, setReason] = useState("");
  const [refId, setRefId] = useState("");
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchMovements = async () => {
    setLoading(true);
    try {
      const res = await api.getInventoryMovements({
        type: typeFilter || undefined,
        limit,
        offset: page * limit,
      });
      setMovements(res.items);
      setTotal(res.total);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await api.getProducts({ limit: 100 });
      setProducts(res.items);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchMovements();
  }, [typeFilter, page]);

  useEffect(() => {
    if (isAdmin) {
      fetchProducts();
    }
  }, [isAdmin]);

  const handleCreateMovement = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalLoading(true);
    setModalError(null);

    try {
      await api.createInventoryMovement({
        product_id: targetProductId,
        type: movementType,
        quantity: parseInt(quantity, 10),
        is_deduction: movementType === "ADJUSTMENT" ? isDeduction : false,
        reason,
        reference_id: refId || undefined,
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
          <h2 className="text-2xl font-bold text-white tracking-tight">Audit Ledger (Double-Entry Feed)</h2>
          <p className="text-sm text-slate-400 mt-1">
            Immutable transaction history enforced by native PostgreSQL database triggers
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-brand-500/20 transition-all self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Record Manual Movement</span>
          </button>
        )}
      </div>

      {/* Info Callout */}
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 leading-relaxed">
          <strong className="text-white">Append-Only Immutability:</strong> The{" "}
          <code className="text-emerald-400 font-mono">inventory_movements</code> table is guarded by the{" "}
          <code className="text-emerald-400 font-mono">trg_immutable_inventory_movements</code> PostgreSQL trigger.
          Any raw <code className="text-rose-400 font-mono">UPDATE</code> or{" "}
          <code className="text-rose-400 font-mono">DELETE</code> attempt is terminated by the RDBMS engine, ensuring regulatory compliance and accounting integrity.
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        {["", "IN", "OUT", "ADJUSTMENT", "RETURN"].map((t) => (
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
                <th className="px-6 py-4 font-semibold">Type</th>
                <th className="px-6 py-4 font-semibold">Qty</th>
                <th className="px-6 py-4 font-semibold">Stock Transition</th>
                <th className="px-6 py-4 font-semibold">Audit Justification / Reason</th>
                <th className="px-6 py-4 font-semibold">Ref / Document</th>
                <th className="px-6 py-4 font-semibold">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 text-brand-500 animate-spin mx-auto mb-2" />
                    Querying immutable ledger...
                  </td>
                </tr>
              ) : movements.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    <History className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                    No movements found for this filter.
                  </td>
                </tr>
              ) : (
                movements.map((m) => {
                  const isOut = m.type === "OUT" || (m.type === "ADJUSTMENT" && m.new_stock < m.previous_stock);
                  return (
                    <tr key={m.id} className="hover:bg-slate-850/50 transition-colors">
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-mono font-bold ${
                            isOut
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
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono font-bold text-white">
                        {isOut ? `-${m.quantity}` : `+${m.quantity}`}
                      </td>
                      <td className="px-6 py-4 font-mono text-slate-300">
                        {m.previous_stock} &rarr;{" "}
                        <strong className="text-white">{m.new_stock} units</strong>
                      </td>
                      <td className="px-6 py-4 text-slate-200">{m.reason}</td>
                      <td className="px-6 py-4 font-mono text-[11px] text-slate-400">
                        {m.reference_id || "-"}
                      </td>
                      <td className="px-6 py-4 text-[11px] text-slate-400">
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
                    <option value="ADJUSTMENT">ADJUSTMENT (Audit / Damaged)</option>
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
                <div className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                  <input
                    type="checkbox"
                    id="deduct"
                    checked={isDeduction}
                    onChange={(e) => setIsDeduction(e.target.checked)}
                    className="rounded text-brand-600 focus:ring-0"
                  />
                  <label htmlFor="deduct" className="text-slate-300 cursor-pointer">
                    Deduct from stock (damaged goods, loss, or count discrepancy)
                  </label>
                </div>
              )}

              <div>
                <label className="block font-medium text-slate-300 mb-1">Reference Document ID</label>
                <input
                  type="text"
                  value={refId}
                  onChange={(e) => setRefId(e.target.value)}
                  placeholder="e.g. INVOICE-9821 or AUDIT-2026-01"
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
    </div>
  );
};
