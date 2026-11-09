import {
  DashboardSummary,
  InventoryMovement,
  InventoryMovementCreatePayload,
  Order,
  OrderCreatePayload,
  PaginatedResponse,
  Product,
  ProductCreatePayload,
  StockReconciliationReport,
  TokenResponse,
  User,
} from "../types/api";
import { mockDemoStore } from "./mockDemoStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export const isDemoEnvironment = (): boolean => {
  if (typeof window === "undefined") return false;
  return (
    window.location.hostname.includes("github.io") ||
    import.meta.env.VITE_DEMO_MODE === "true"
  );
};

class ApiClient {
  private token: string | null = null;
  public isDemo: boolean = false;

  constructor() {
    this.token = localStorage.getItem("stockflow_token");
    this.isDemo = isDemoEnvironment();
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("stockflow_token", token);
    } else {
      localStorage.removeItem("stockflow_token");
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");

    if (this.token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${this.token}`);
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorBody: any = null;
        try {
          errorBody = await response.json();
        } catch {
          errorBody = { detail: response.statusText };
        }
        const message =
          errorBody?.error?.message || errorBody?.detail || "Erro inesperado na requisição.";
        const error = new Error(message) as Error & { status: number; payload: any };
        error.status = response.status;
        error.payload = errorBody;
        throw error;
      }

      return response.json();
    } catch (err: any) {
      // If error is network unreachable (e.g. static host without backend), enable demo fallback
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        console.warn("[StockFlow] Backend unreachable. Engaging interactive in-browser demo engine.");
        this.isDemo = true;
      }
      throw err;
    }
  }

  // --- Auth ---
  async login(email: string, password: string): Promise<TokenResponse> {
    if (this.isDemo) {
      const res = await mockDemoStore.login(email);
      this.setToken(res.access_token);
      return res;
    }
    try {
      const data = await this.request<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      this.setToken(data.access_token);
      return data;
    } catch (err: any) {
      if (this.isDemo) {
        const res = await mockDemoStore.login(email);
        this.setToken(res.access_token);
        return res;
      }
      throw err;
    }
  }

  async getMe(): Promise<User> {
    if (this.isDemo) return mockDemoStore.getMe();
    try {
      return await this.request<User>("/auth/me");
    } catch (err) {
      if (this.isDemo) return mockDemoStore.getMe();
      throw err;
    }
  }

  // --- Dashboard ---
  async getDashboardSummary(): Promise<DashboardSummary> {
    if (this.isDemo) return mockDemoStore.getDashboardSummary();
    try {
      return await this.request<DashboardSummary>("/dashboard/summary");
    } catch (err) {
      if (this.isDemo) return mockDemoStore.getDashboardSummary();
      throw err;
    }
  }

  // --- Products ---
  async getProducts(params?: {
    search?: string;
    limit?: number;
    offset?: number;
    include_inactive?: boolean;
  }): Promise<PaginatedResponse<Product>> {
    if (this.isDemo) return mockDemoStore.getProducts(params);
    try {
      const query = new URLSearchParams();
      if (params?.search) query.set("search", params.search);
      if (params?.limit) query.set("limit", params.limit.toString());
      if (params?.offset) query.set("offset", params.offset.toString());
      if (params?.include_inactive) query.set("include_inactive", "true");

      const qs = query.toString() ? `?${query.toString()}` : "";
      return await this.request<PaginatedResponse<Product>>(`/products${qs}`);
    } catch (err) {
      if (this.isDemo) return mockDemoStore.getProducts(params);
      throw err;
    }
  }

  async createProduct(payload: ProductCreatePayload): Promise<Product> {
    if (this.isDemo) return mockDemoStore.createProduct(payload);
    return this.request<Product>("/products", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async softDeleteProduct(productId: string): Promise<Product> {
    if (this.isDemo) return mockDemoStore.softDeleteProduct(productId);
    return this.request<Product>(`/products/${productId}`, {
      method: "DELETE",
    });
  }

  // --- Orders & Checkout ---
  async createOrder(payload: OrderCreatePayload, idempotencyKey: string): Promise<Order> {
    if (this.isDemo) return mockDemoStore.createOrder(payload, idempotencyKey);
    return this.request<Order>("/orders", {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(payload),
    });
  }

  async getOrders(limit = 20, offset = 0): Promise<PaginatedResponse<Order>> {
    if (this.isDemo) return mockDemoStore.getOrders(limit, offset);
    try {
      return await this.request<PaginatedResponse<Order>>(`/orders?limit=${limit}&offset=${offset}`);
    } catch (err) {
      if (this.isDemo) return mockDemoStore.getOrders(limit, offset);
      throw err;
    }
  }

  async cancelOrder(orderId: string): Promise<Order> {
    if (this.isDemo) return mockDemoStore.cancelOrder(orderId);
    return this.request<Order>(`/orders/${orderId}/cancel`, {
      method: "POST",
    });
  }

  // --- Inventory Movements ---
  async getInventoryMovements(params?: {
    product_id?: string;
    type?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<InventoryMovement>> {
    if (this.isDemo) return mockDemoStore.getInventoryMovements(params);
    try {
      const query = new URLSearchParams();
      if (params?.product_id) query.set("product_id", params.product_id);
      if (params?.type) query.set("type", params.type);
      if (params?.limit) query.set("limit", params.limit.toString());
      if (params?.offset) query.set("offset", params.offset.toString());

      const qs = query.toString() ? `?${query.toString()}` : "";
      return await this.request<PaginatedResponse<InventoryMovement>>(`/inventory/movements${qs}`);
    } catch (err) {
      if (this.isDemo) return mockDemoStore.getInventoryMovements(params);
      throw err;
    }
  }

  async createInventoryMovement(
    payload: InventoryMovementCreatePayload
  ): Promise<InventoryMovement> {
    if (this.isDemo) return mockDemoStore.createInventoryMovement(payload);
    return this.request<InventoryMovement>("/inventory/movements", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getReconciliationReport(): Promise<StockReconciliationReport> {
    if (this.isDemo) return mockDemoStore.getReconciliationReport();
    try {
      return await this.request<StockReconciliationReport>("/inventory/reconcile");
    } catch (err) {
      if (this.isDemo) return mockDemoStore.getReconciliationReport();
      throw err;
    }
  }
}

export const api = new ApiClient();
