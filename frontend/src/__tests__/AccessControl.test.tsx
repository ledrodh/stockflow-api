import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardView } from "../views/DashboardView";
import { InventoryView } from "../views/InventoryView";
import * as AuthContextModule from "../context/AuthContext";
import { api } from "../services/api";

describe("Access Control & RBAC in Views", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("DashboardView blocks non-admin and renders Administrator Access Required", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        id: "cust-1",
        email: "customer@stockflow.io",
        full_name: "Customer Demo",
        role: "customer",
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isAdmin: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<DashboardView />);

    expect(screen.getByText("Administrator Access Required")).toBeInTheDocument();
    expect(screen.getByText("customer@stockflow.io")).toBeInTheDocument();
  });

  it("InventoryView blocks non-admin and renders Administrator Access Required", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        id: "cust-1",
        email: "customer@stockflow.io",
        full_name: "Customer Demo",
        role: "customer",
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isAdmin: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<InventoryView />);

    expect(screen.getByText("Administrator Access Required")).toBeInTheDocument();
  });

  it("DashboardView queries metrics when authenticated as admin", async () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        id: "admin-1",
        email: "admin@stockflow.io",
        full_name: "Admin User",
        role: "admin",
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isAdmin: true,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    vi.spyOn(api, "getDashboardSummary").mockResolvedValue({
      total_products: 10,
      total_stock_items: 250,
      low_stock_products: 2,
      total_orders: 15,
      total_revenue: "45000.00",
      recent_orders: [],
      recent_movements: [],
    });

    render(<DashboardView />);

    expect(await screen.findByText("Inventory & Sales Dashboard")).toBeInTheDocument();
    expect(await screen.findByText("Physical Units")).toBeInTheDocument();
  });
});
