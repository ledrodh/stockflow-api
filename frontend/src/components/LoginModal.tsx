import React, { useState } from "react";
import { X, Shield, User, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Invalid credentials.");
    } finally {
      setLoading(false);
    }
  };

  const fillQuickAccount = (targetEmail: string, targetPass: string) => {
    setEmail(targetEmail);
    setPassword(targetPass);
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="mb-6">
          <h2 className="text-xl font-bold text-white">Access StockFlow Dashboard</h2>
          <p className="text-xs text-slate-400 mt-1">
            JWT-based authentication with strict RBAC access control
          </p>
        </div>

        {/* Quick Demo Fill Buttons */}
        <div className="mb-5 p-3 rounded-xl bg-slate-950 border border-slate-800">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 font-mono">
            Technical Demo Shortcuts:
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => fillQuickAccount("admin@stockflow.io", "AdminPassword123!")}
              className="flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-amber-950/60 hover:bg-amber-900/60 text-amber-300 border border-amber-600/30 rounded-lg transition-colors"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Login as Admin</span>
            </button>
            <button
              type="button"
              onClick={() => fillQuickAccount("customer@stockflow.io", "CustomerSecret#2026")}
              className="flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium bg-indigo-950/60 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-600/30 rounded-lg transition-colors"
            >
              <User className="w-3.5 h-3.5" />
              <span>Login as Customer</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. admin@stockflow.io"
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 text-white font-medium rounded-xl text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-brand-500/20"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>Sign In to Dashboard</span>
          </button>
        </form>
      </div>
    </div>
  );
};
