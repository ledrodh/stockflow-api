import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { OrdersView } from "../views/OrdersView";
import * as AuthContextModule from "../context/AuthContext";
import { api } from "../services/api";

describe("OrdersView & Idempotency", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders authenticated terminal with valid UUID idempotency key", async () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        id: "c-1",
        email: "customer@stockflow.io",
        full_name: "Customer",
        role: "customer",
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isAdmin: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    vi.spyOn(api, "getProducts").mockResolvedValue({
      items: [
        {
          id: "prod-1",
          sku: "TEST-SKU",
          name: "Test Laptop",
          description: "Desc",
          price: "1500.00",
          stock_quantity: 10,
          min_stock: 5,
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });

    vi.spyOn(api, "getOrders").mockResolvedValue({
      items: [
        {
          id: "ord-1",
          user_id: "c-1",
          status: "CONFIRMED",
          total_amount: "1500.00",
          items: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });

    render(<OrdersView />);

    expect(await screen.findByText("Sales Terminal & Idempotency")).toBeInTheDocument();
    expect(await screen.findByText("Cancel Order")).toBeInTheDocument();

    const input = screen.getByRole("textbox") as HTMLInputElement;
    // UUID v4 format: 8-4-4-4-12 hex characters
    expect(input.value).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it("calls cancelOrder when clicking Cancel Order button", async () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: {
        id: "c-1",
        email: "customer@stockflow.io",
        full_name: "Customer",
        role: "customer",
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isAdmin: false,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    vi.spyOn(api, "getProducts").mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 });
    vi.spyOn(api, "getOrders").mockResolvedValue({
      items: [
        {
          id: "ord-test-cancel",
          user_id: "c-1",
          status: "CONFIRMED",
          total_amount: "500.00",
          items: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    });

    const cancelSpy = vi.spyOn(api, "cancelOrder").mockResolvedValue({
      id: "ord-test-cancel",
      user_id: "c-1",
      status: "CANCELLED",
      total_amount: "500.00",
      items: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<OrdersView />);

    const cancelBtn = await screen.findByText("Cancel Order");
    await act(async () => {
      cancelBtn.click();
    });

    expect(cancelSpy).toHaveBeenCalledWith("ord-test-cancel");
  });
});
