export type UserRole = "admin" | "customer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  description: string | null;
  price: string;
  stock_quantity: number;
  min_stock: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductCreatePayload {
  sku: string;
  name: string;
  description?: string;
  price: number;
  stock_quantity: number;
  min_stock?: number;
}

export interface OrderItem {
  id: string;
  product_id: string;
  product_name_snapshot: string;
  unit_price: string;
  quantity: number;
  subtotal: string;
}

export interface Order {
  id: string;
  user_id: string;
  status: "PENDING" | "CONFIRMED" | "CANCELLED";
  total_amount: string;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}

export interface OrderCreatePayload {
  items: Array<{
    product_id: string;
    quantity: number;
  }>;
}

export type MovementType = "IN" | "OUT" | "ADJUSTMENT" | "RETURN";

export interface InventoryMovement {
  id: string;
  product_id: string;
  type: MovementType;
  quantity: number;
  previous_stock: number;
  new_stock: number;
  reference_id: string | null;
  reason: string;
  created_by: string | null;
  created_at: string;
}

export interface InventoryMovementCreatePayload {
  product_id: string;
  type: MovementType;
  quantity: number;
  is_deduction?: boolean;
  reference_id?: string;
  reason: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface DashboardSummary {
  total_products: number;
  total_stock_items: number;
  low_stock_products: number;
  total_orders: number;
  total_revenue: string;
  recent_orders: Order[];
  recent_movements: InventoryMovement[];
}

export interface ApiError {
  detail?: string;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
