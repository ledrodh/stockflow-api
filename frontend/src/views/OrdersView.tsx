import React, { useEffect, useState } from "react";
import {
  ShoppingCart,
  Zap,
  Plus,
  Trash2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Lock,
} from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Order, Product } from "../types/api";

export const OrdersView: React.FC = () => {
  const { user } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  // Cart state
  const [cart, setCart] = useState<Array<{ product: Product; quantity: number }>>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [selectedQuantity, setSelectedQuantity] = useState<number>(1);

  // Idempotency state
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() => `checkout-${Date.now()}`);

  // Feedback states
  const [submitting, setSubmitting] = useState(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [successOrder, setSuccessOrder] = useState<Order | null>(null);
  const [errorFeedback, setErrorFeedback] = useState<{ status?: number; message: string } | null>(
    null
  );

  const fetchData = async () => {
    setLoading(true);
    try {
      const [prodsRes, ordersRes] = await Promise.all([
        api.getProducts({ limit: 100 }),
        api.getOrders(10, 0),
      ]);
      setProducts(prodsRes.items.filter((p) => p.is_active));
      setOrders(ordersRes.items);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);

  const handleAddToCart = () => {
    if (!selectedProductId) return;
    const prod = products.find((p) => p.id === selectedProductId);
    if (!prod) return;

    setCart((prev) => {
      const exists = prev.find((item) => item.product.id === prod.id);
      if (exists) {
        return prev.map((item) =>
          item.product.id === prod.id
            ? { ...item, quantity: item.quantity + selectedQuantity }
            : item
        );
      }
      return [...prev, { product: prod, quantity: selectedQuantity }];
    });
    setSelectedQuantity(1);
  };

  const handleRemoveFromCart = (productId: string) => {
    setCart((prev) => prev.filter((item) => item.product.id !== productId));
  };

  const generateNewIdempotencyKey = () => {
    setIdempotencyKey(`checkout-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`);
    setSuccessOrder(null);
    setErrorFeedback(null);
  };

  const calculateCartTotal = () => {
    return cart.reduce((acc, item) => acc + Number(item.product.price) * item.quantity, 0);
  };

  const handleCheckout = async () => {
    if (cart.length === 0) return;
    setSubmitting(true);
    setErrorFeedback(null);
    setSuccessOrder(null);

    const payload = {
      items: cart.map((item) => ({
        product_id: item.product.id,
        quantity: item.quantity,
      })),
    };

    try {
      const order = await api.createOrder(payload, idempotencyKey);
      setSuccessOrder(order);
      setCart([]);
      generateNewIdempotencyKey();
      fetchData();
    } catch (err: any) {
      setErrorFeedback({
        status: err?.status,
        message: err?.message || "Atomic transaction failed.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelOrder = async (orderId: string) => {
    setCancellingId(orderId);
    setErrorFeedback(null);
    try {
      await api.cancelOrder(orderId);
      await fetchData();
    } catch (err: any) {
      setErrorFeedback({
        status: err?.status,
        message: err?.message || "Failed to cancel order.",
      });
    } finally {
      setCancellingId(null);
    }
  };

  if (!user) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center max-w-lg mx-auto">
        <Lock className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-white mb-2">Authentication Required</h3>
        <p className="text-xs text-slate-400">
          Sign in as Customer or Administrator to place orders and test transactional idempotency.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Sales Terminal & Idempotency</h2>
        <p className="text-sm text-slate-400 mt-1">
          Atomic PostgreSQL checkout with pessimistic locking (<code className="text-slate-300 font-mono">SELECT FOR UPDATE</code>) and duplicate prevention
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Cart Builder */}
        <div className="lg:col-span-2 space-y-6">
          {/* Item Selector */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="font-semibold text-white text-base mb-4 flex items-center gap-2">
              <ShoppingCart className="w-4 h-4 text-brand-400" />
              <span>Shopping Cart Builder</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Select Product
                </label>
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 focus:outline-none focus:border-brand-500"
                >
                  <option value="">Choose an available product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      [{p.sku}] {p.name} - ${Number(p.price).toFixed(2)} (Stock: {p.stock_quantity})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Quantity</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={selectedQuantity}
                    onChange={(e) => setSelectedQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-20 px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-center text-slate-100 focus:outline-none focus:border-brand-500"
                  />
                  <button
                    onClick={handleAddToCart}
                    disabled={!selectedProductId}
                    className="flex-1 py-2 px-3 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-1 transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Cart Table */}
            <div className="mt-6 border-t border-slate-800/80 pt-4">
              <h4 className="text-xs font-mono text-slate-400 uppercase tracking-wider mb-3">
                Cart Items ({cart.length})
              </h4>
              {cart.length === 0 ? (
                <p className="text-xs text-slate-500 py-6 text-center border border-dashed border-slate-800 rounded-xl">
                  Your cart is empty. Add items above.
                </p>
              ) : (
                <div className="divide-y divide-slate-800/60 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                  {cart.map((item) => (
                    <div
                      key={item.product.id}
                      className="p-3.5 flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="font-semibold text-slate-200">
                          {item.product.name}{" "}
                          <span className="font-mono text-brand-400 text-[11px]">
                            ({item.product.sku})
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {item.quantity}x @ ${Number(item.product.price).toFixed(2)}
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-mono font-bold text-white text-sm">
                          ${(Number(item.product.price) * item.quantity).toFixed(2)}
                        </span>
                        <button
                          onClick={() => handleRemoveFromCart(item.product.id)}
                          className="text-slate-500 hover:text-rose-400 p-1"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                  <div className="p-4 bg-slate-950 flex items-center justify-between border-t border-slate-800">
                    <span className="text-xs font-bold text-slate-300 uppercase font-mono">
                      Order Subtotal
                    </span>
                    <span className="text-lg font-bold font-mono text-emerald-400">
                      ${calculateCartTotal().toFixed(2)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Past Orders List */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="font-semibold text-white text-base mb-4">Confirmed Orders History</h3>
            <div className="space-y-3">
              {loading ? (
                <div className="py-6 text-center text-xs text-slate-400">Loading orders...</div>
              ) : orders.length === 0 ? (
                <p className="text-xs text-slate-500 py-6 text-center">No orders placed yet.</p>
              ) : (
                orders.map((o) => (
                  <div
                    key={o.id}
                    className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-brand-400">#{o.id}</span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                            o.status === "CONFIRMED"
                              ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/20"
                              : "bg-rose-500/15 text-rose-400 border-rose-500/20"
                          }`}
                        >
                          {o.status}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">
                        {new Date(o.created_at).toLocaleString("en-US")} • {o.items.length} items (Frozen snapshots)
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className="text-sm font-bold font-mono text-white">
                          ${Number(o.total_amount).toFixed(2)}
                        </span>
                      </div>
                      {o.status === "CONFIRMED" && (
                        <button
                          onClick={() => handleCancelOrder(o.id)}
                          disabled={cancellingId === o.id}
                          className="px-2.5 py-1 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-500/30 text-rose-300 hover:text-white rounded-lg text-[11px] font-semibold transition-colors disabled:opacity-50"
                        >
                          {cancellingId === o.id ? "Restocking..." : "Cancel Order"}
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Idempotency & Execution Box */}
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm sticky top-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white text-base flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>ACID Idempotency Control</span>
              </h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Idempotency Key (<code className="text-slate-300 font-mono">Idempotency-Key</code>)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={idempotencyKey}
                    onChange={(e) => setIdempotencyKey(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-brand-500"
                  />
                  <button
                    type="button"
                    onClick={generateNewIdempotencyKey}
                    title="Generate new UUID key"
                    className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                  <strong>Demo Tip:</strong> Submit the order twice with this exact key.
                  PostgreSQL replays the confirmed order instantly without duplicate charging or secondary stock deductions.
                </p>
              </div>

              {/* Feedback messages */}
              {successOrder && (
                <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs space-y-1 animate-fade-in">
                  <div className="flex items-center gap-2 font-bold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Atomic Transaction Completed!</span>
                  </div>
                  <p className="text-[11px] text-emerald-200/80 font-mono">
                    Order ID: {successOrder.id}
                  </p>
                  <p className="text-[11px] text-emerald-200/80">
                    Stock deducted and immutable ledger recorded in PostgreSQL.
                  </p>
                </div>
              )}

              {errorFeedback && (
                <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs space-y-1 animate-fade-in">
                  <div className="flex items-center gap-2 font-bold">
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    <span>HTTP Error {errorFeedback.status || "500"}</span>
                  </div>
                  <p className="text-[11px] text-rose-200/90 leading-relaxed">
                    {errorFeedback.message}
                  </p>
                </div>
              )}

              <button
                onClick={handleCheckout}
                disabled={cart.length === 0 || submitting}
                className="w-full py-3 bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 disabled:opacity-40 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-lg shadow-brand-500/20 transition-all"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Executing ACID Transaction...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    <span>Execute Atomic Checkout</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
