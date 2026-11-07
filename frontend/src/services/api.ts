import {
  DashboardSummary,
  InventoryMovement,
  InventoryMovementCreatePayload,
  Order,
  OrderCreatePayload,
  PaginatedResponse,
  Product,
  ProductCreatePayload,
  TokenResponse,
  User,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem("stockflow_token");
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
  }

  // --- Auth ---
  async login(email: string, password: string): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<User> {
    return this.request<User>("/auth/me");
  }

  // --- Dashboard ---
  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.request<DashboardSummary>("/dashboard/summary");
  }

  // --- Products ---
  async getProducts(params?: {
    search?: string;
    limit?: number;
    offset?: number;
    include_inactive?: boolean;
  }): Promise<PaginatedResponse<Product>> {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    if (params?.include_inactive) query.set("include_inactive", "true");

    const qs = query.toString() ? `?${query.toString()}` : "";
    return this.request<PaginatedResponse<Product>>(`/products${qs}`);
  }

  async createProduct(payload: ProductCreatePayload): Promise<Product> {
    return this.request<Product>("/products", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async softDeleteProduct(productId: string): Promise<Product> {
    return this.request<Product>(`/products/${productId}`, {
      method: "DELETE",
    });
  }

  // --- Orders & Checkout ---
  async createOrder(payload: OrderCreatePayload, idempotencyKey: string): Promise<Order> {
    return this.request<Order>("/orders", {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(payload),
    });
  }

  async getOrders(limit = 20, offset = 0): Promise<PaginatedResponse<Order>> {
    return this.request<PaginatedResponse<Order>>(`/orders?limit=${limit}&offset=${offset}`);
  }

  async cancelOrder(orderId: string): Promise<Order> {
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
    const query = new URLSearchParams();
    if (params?.product_id) query.set("product_id", params.product_id);
    if (params?.type) query.set("type", params.type);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());

    const qs = query.toString() ? `?${query.toString()}` : "";
    return this.request<PaginatedResponse<InventoryMovement>>(`/inventory/movements${qs}`);
  }

  async createInventoryMovement(
    payload: InventoryMovementCreatePayload
  ): Promise<InventoryMovement> {
    return this.request<InventoryMovement>("/inventory/movements", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}

export const api = new ApiClient();
