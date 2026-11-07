import React, { useEffect, useState } from "react";
import {
  Search,
  Plus,
  Trash2,
  Package,
  AlertCircle,
  Loader2,
  X,
} from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Product } from "../types/api";

export const ProductsView: React.FC = () => {
  const { isAdmin } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const limit = 10;

  // Create Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [stock, setStock] = useState("");
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const res = await api.getProducts({
        search: search.trim() || undefined,
        limit,
        offset: page * limit,
        include_inactive: isAdmin,
      });
      setProducts(res.items);
      setTotal(res.total);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [page, isAdmin]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchProducts();
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalLoading(true);
    setModalError(null);
    try {
      await api.createProduct({
        sku,
        name,
        description: description || undefined,
        price: parseFloat(price),
        stock_quantity: parseInt(stock, 10),
      });
      setShowCreateModal(false);
      setSku("");
      setName("");
      setDescription("");
      setPrice("");
      setStock("");
      fetchProducts();
    } catch (err: any) {
      setModalError(err?.message || "Failed to create product.");
    } finally {
      setModalLoading(false);
    }
  };

  const handleSoftDelete = async (product: Product) => {
    if (
      !confirm(
        `Do you want to soft-delete product '${product.name}'? Physical records are retained to protect historical orders.`
      )
    ) {
      return;
    }
    try {
      await api.softDeleteProduct(product.id);
      fetchProducts();
    } catch (err: any) {
      alert(err?.message || "Failed to deactivate product.");
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Product Catalog</h2>
          <p className="text-sm text-slate-400 mt-1">
            Engineered with database invariants (<code className="text-slate-300 font-mono">CHECK price &gt;= 0</code>, <code className="text-slate-300 font-mono">stock &gt;= 0</code>) and Soft Deletion
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-brand-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create Product</span>
          </button>
        )}
      </div>

      {/* Filter / Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by product name or SKU..."
            className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
          />
        </form>

        <div className="text-xs text-slate-400 self-end sm:self-auto font-mono">
          Total products: <strong className="text-slate-200">{total}</strong>
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 font-semibold">SKU</th>
                <th className="px-6 py-4 font-semibold">Product Name</th>
                <th className="px-6 py-4 font-semibold">Unit Price</th>
                <th className="px-6 py-4 font-semibold">Stock</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                {isAdmin && <th className="px-6 py-4 font-semibold text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 text-brand-500 animate-spin mx-auto mb-2" />
                    Loading products...
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                    <Package className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                    No products found.
                  </td>
                </tr>
              ) : (
                products.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-850/50 transition-colors">
                    <td className="px-6 py-4 font-mono font-medium text-brand-400">{p.sku}</td>
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-200">{p.name}</div>
                      {p.description && (
                        <div className="text-[11px] text-slate-500 truncate max-w-xs">
                          {p.description}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-white font-medium">
                      ${Number(p.price).toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold ${
                          p.stock_quantity <= 0
                            ? "bg-rose-950/60 text-rose-400 border border-rose-500/30"
                            : p.stock_quantity < 5
                            ? "bg-amber-950/60 text-amber-400 border border-amber-500/30"
                            : "bg-emerald-950/60 text-emerald-400 border border-emerald-500/30"
                        }`}
                      >
                        {p.stock_quantity} units
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {p.is_active ? (
                        <span className="text-[11px] text-emerald-400 font-medium">Active</span>
                      ) : (
                        <span className="text-[11px] text-slate-500 font-medium">Inactive (Soft Deleted)</span>
                      )}
                    </td>
                    {isAdmin && (
                      <td className="px-6 py-4 text-right">
                        {p.is_active && (
                          <button
                            onClick={() => handleSoftDelete(p)}
                            title="Soft delete product"
                            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-950/50 rounded-lg transition-colors border border-transparent hover:border-rose-500/30"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > limit && (
          <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Page {page + 1} of {Math.ceil(total / limit)}
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

      {/* Create Product Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
            <button
              onClick={() => setShowCreateModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-bold text-white mb-1">New Catalog Product</h3>
            <p className="text-xs text-slate-400 mb-5">
              Initial stock balance automatically creates an immutable ledger entry (<code className="text-slate-300 font-mono">InventoryMovement</code>).
            </p>

            {modalError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleCreateProduct} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">SKU *</label>
                  <input
                    type="text"
                    required
                    value={sku}
                    onChange={(e) => setSku(e.target.value.toUpperCase())}
                    placeholder="e.g. MECH-KEYB-01"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-100 focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Unit Price ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="299.90"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-100 focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Product Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Wireless Mechanical Keyboard"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder="Optional product details..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Initial Stock *</label>
                <input
                  type="number"
                  min="0"
                  required
                  value={stock}
                  onChange={(e) => setStock(e.target.value)}
                  placeholder="10"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>

              <button
                type="submit"
                disabled={modalLoading}
                className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-medium rounded-xl text-xs flex items-center justify-center gap-2 transition-all mt-4"
              >
                {modalLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>Save Product to Catalog</span>
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
