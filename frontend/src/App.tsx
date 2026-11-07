import React, { useState } from "react";
import { AuthProvider } from "./context/AuthContext";
import { Sidebar, NavTab } from "./components/Sidebar";
import { Header } from "./components/Header";
import { LoginModal } from "./components/LoginModal";
import { DashboardView } from "./views/DashboardView";
import { ProductsView } from "./views/ProductsView";
import { OrdersView } from "./views/OrdersView";
import { InventoryView } from "./views/InventoryView";

export const AppContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [showLoginModal, setShowLoginModal] = useState(false);

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden font-sans">
      {/* Fixed Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header onOpenLogin={() => setShowLoginModal(true)} />

        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">
            {activeTab === "dashboard" && <DashboardView />}
            {activeTab === "products" && <ProductsView />}
            {activeTab === "orders" && <OrdersView />}
            {activeTab === "inventory" && <InventoryView />}
          </div>
        </main>
      </div>

      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
