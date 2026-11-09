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

const ADMIN_USER: User = {
  id: "4461ab3d-65f2-4938-abb4-db6865d3673b",
  email: "admin@stockflow.io",
  full_name: "StockFlow Admin (Demo)",
  role: "admin",
  is_active: true,
  created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
};

const CUSTOMER_USER: User = {
  id: "5572bc4e-76f3-4a49-bcc5-ec7976e4784c",
  email: "customer@stockflow.io",
  full_name: "Demo Customer",
  role: "customer",
  is_active: true,
  created_at: new Date(Date.now() - 86400000 * 15).toISOString(),
};

const INITIAL_PRODUCTS: Product[] = [
  {
    id: "p1-macbook",
    sku: "MACBOOK-M3-MAX",
    name: 'MacBook Pro 16" M3 Max 36GB',
    description: "Space Black, 1TB SSD",
    price: "24999.00",
    stock_quantity: 7,
    min_stock: 5,
    is_active: true,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 1).toISOString(),
  },
  {
    id: "p2-dell",
    sku: "DELL-ULTRA-34",
    name: 'Dell UltraSharp 34" Curved WQHD Monitor',
    description: "IPS Black, 90W USB-C Hub",
    price: "4899.00",
    stock_quantity: 11,
    min_stock: 5,
    is_active: true,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 1).toISOString(),
  },
  {
    id: "p3-keyb",
    sku: "KEYB-LOGI-MX",
    name: "Logitech MX Mechanical Keyboard",
    description: "Tactile Quiet switches, Bluetooth & Bolt",
    price: "799.00",
    stock_quantity: 25,
    min_stock: 10,
    is_active: true,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: "p4-mouse",
    sku: "MOUSE-MX-MASTER",
    name: "Logitech MX Master 3S Mouse",
    description: "Quiet 8K DPI optical sensor",
    price: "599.00",
    stock_quantity: 2,
    min_stock: 5,
    is_active: true,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 1).toISOString(),
  },
  {
    id: "p5-ssd",
    sku: "SSD-SAMSUNG-990",
    name: "Samsung 990 Pro 2TB NVMe M.2 SSD",
    description: "PCIe 4.0 up to 7450 MB/s",
    price: "1299.00",
    stock_quantity: 15,
    min_stock: 5,
    is_active: true,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
];

const INITIAL_MOVEMENTS: InventoryMovement[] = [
  {
    id: "m1-init-mac",
    product_id: "p1-macbook",
    movement_sequence: 1,
    type: "OPENING",
    quantity: 8,
    previous_stock: 0,
    new_stock: 8,
    reference_id: "INIT-MACBOOK-M3-MAX",
    reason: "Initial catalog opening stock",
    created_by: ADMIN_USER.id,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: "m2-init-dell",
    product_id: "p2-dell",
    movement_sequence: 1,
    type: "OPENING",
    quantity: 12,
    previous_stock: 0,
    new_stock: 12,
    reference_id: "INIT-DELL-ULTRA-34",
    reason: "Initial catalog opening stock",
    created_by: ADMIN_USER.id,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: "m3-init-keyb",
    product_id: "p3-keyb",
    movement_sequence: 1,
    type: "OPENING",
    quantity: 25,
    previous_stock: 0,
    new_stock: 25,
    reference_id: "INIT-KEYB-LOGI-MX",
    reason: "Initial catalog opening stock",
    created_by: ADMIN_USER.id,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: "m4-init-mouse",
    product_id: "p4-mouse",
    movement_sequence: 1,
    type: "OPENING",
    quantity: 3,
    previous_stock: 0,
    new_stock: 3,
    reference_id: "INIT-MOUSE-MX-MASTER",
    reason: "Initial catalog opening stock",
    created_by: ADMIN_USER.id,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: "m5-init-ssd",
    product_id: "p5-ssd",
    movement_sequence: 1,
    type: "OPENING",
    quantity: 15,
    previous_stock: 0,
    new_stock: 15,
    reference_id: "INIT-SSD-SAMSUNG-990",
    reason: "Initial catalog opening stock",
    created_by: ADMIN_USER.id,
    created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: "m6-out-mac",
    product_id: "p1-macbook",
    movement_sequence: 2,
    type: "OUT",
    quantity: 1,
    previous_stock: 8,
    new_stock: 7,
    reference_id: "ord-demo-001",
    reason: "Order checkout ord-demo-001",
    created_by: CUSTOMER_USER.id,
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
  },
  {
    id: "m7-out-mouse",
    product_id: "p4-mouse",
    movement_sequence: 2,
    type: "OUT",
    quantity: 1,
    previous_stock: 3,
    new_stock: 2,
    reference_id: "ord-demo-001",
    reason: "Order checkout ord-demo-001",
    created_by: CUSTOMER_USER.id,
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
  },
  {
    id: "m8-out-dell",
    product_id: "p2-dell",
    movement_sequence: 2,
    type: "OUT",
    quantity: 1,
    previous_stock: 12,
    new_stock: 11,
    reference_id: "ord-demo-002",
    reason: "Order checkout ord-demo-002",
    created_by: CUSTOMER_USER.id,
    created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
  },
];

const INITIAL_ORDERS: Order[] = [
  {
    id: "ord-demo-001",
    user_id: CUSTOMER_USER.id,
    status: "CONFIRMED",
    total_amount: "25598.00",
    items: [
      {
        id: "item-1",
        product_id: "p1-macbook",
        product_name_snapshot: 'MacBook Pro 16" M3 Max 36GB',
        unit_price: "24999.00",
        quantity: 1,
        subtotal: "24999.00",
      },
      {
        id: "item-2",
        product_id: "p4-mouse",
        product_name_snapshot: "Logitech MX Master 3S Mouse",
        unit_price: "599.00",
        quantity: 1,
        subtotal: "599.00",
      },
    ],
    created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 2).toISOString(),
  },
  {
    id: "ord-demo-002",
    user_id: CUSTOMER_USER.id,
    status: "CONFIRMED",
    total_amount: "4899.00",
    items: [
      {
        id: "item-3",
        product_id: "p2-dell",
        product_name_snapshot: 'Dell UltraSharp 34" Curved WQHD Monitor',
        unit_price: "4899.00",
        quantity: 1,
        subtotal: "4899.00",
      },
    ],
    created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 1).toISOString(),
  },
];

export class MockDemoStore {
  private products: Product[] = [];
  private movements: InventoryMovement[] = [];
  private orders: Order[] = [];
  private currentUser: User = ADMIN_USER;
  private idempotencyCache = new Map<string, Order>();

  constructor() {
    this.loadState();
  }

  private loadState() {
    const p = localStorage.getItem("stockflow_demo_products");
    const m = localStorage.getItem("stockflow_demo_movements");
    const o = localStorage.getItem("stockflow_demo_orders");

    this.products = p ? JSON.parse(p) : [...INITIAL_PRODUCTS];
    this.movements = m ? JSON.parse(m) : [...INITIAL_MOVEMENTS];
    this.orders = o ? JSON.parse(o) : [...INITIAL_ORDERS];
  }

  private saveState() {
    localStorage.setItem("stockflow_demo_products", JSON.stringify(this.products));
    localStorage.setItem("stockflow_demo_movements", JSON.stringify(this.movements));
    localStorage.setItem("stockflow_demo_orders", JSON.stringify(this.orders));
  }

  async login(email: string): Promise<TokenResponse> {
    if (email.toLowerCase().includes("admin")) {
      this.currentUser = ADMIN_USER;
    } else {
      this.currentUser = CUSTOMER_USER;
    }
    return {
      access_token: "mock-jwt-token-demo",
      token_type: "bearer",
      expires_in: 3600,
    };
  }

  async getMe(): Promise<User> {
    return this.currentUser;
  }

  async getDashboardSummary(): Promise<DashboardSummary> {
    const activeProducts = this.products.filter((p) => p.is_active);
    const totalPhysicalUnits = activeProducts.reduce((acc, p) => acc + p.stock_quantity, 0);
    const lowStockCount = activeProducts.filter((p) => p.stock_quantity <= p.min_stock).length;

    const confirmedOrders = this.orders.filter((o) => o.status === "CONFIRMED");
    const totalConfirmedRevenue = confirmedOrders.reduce(
      (acc, o) => acc + parseFloat(o.total_amount),
      0
    );

    return {
      total_products: activeProducts.length,
      total_stock_items: totalPhysicalUnits,
      low_stock_products: lowStockCount,
      total_orders: this.orders.length,
      total_revenue: totalConfirmedRevenue.toFixed(2),
      recent_orders: this.orders.slice(0, 5),
      recent_movements: this.movements.slice(-5).reverse(),
    };
  }

  async getProducts(params?: {
    search?: string;
    limit?: number;
    offset?: number;
    include_inactive?: boolean;
  }): Promise<PaginatedResponse<Product>> {
    let filtered = this.products.filter((p) => (params?.include_inactive ? true : p.is_active));
    if (params?.search) {
      const q = params.search.toLowerCase();
      filtered = filtered.filter(
        (p) => p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
      );
    }
    const limit = params?.limit || 20;
    const offset = params?.offset || 0;
    return {
      items: filtered.slice(offset, offset + limit),
      total: filtered.length,
      limit,
      offset,
    };
  }

  async createProduct(payload: ProductCreatePayload): Promise<Product> {
    const id = "p-" + crypto.randomUUID().slice(0, 8);
    const newProd: Product = {
      id,
      sku: payload.sku.toUpperCase(),
      name: payload.name,
      description: payload.description || null,
      price: payload.price.toFixed(2),
      stock_quantity: payload.stock_quantity,
      min_stock: payload.min_stock ?? 5,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    this.products.unshift(newProd);

    // Initial opening movement
    const movement: InventoryMovement = {
      id: "m-" + crypto.randomUUID().slice(0, 8),
      product_id: id,
      movement_sequence: 1,
      type: "OPENING",
      quantity: payload.stock_quantity,
      previous_stock: 0,
      new_stock: payload.stock_quantity,
      reference_id: `INIT-${newProd.sku}`,
      reason: "Initial catalog opening stock",
      created_by: this.currentUser.id,
      created_at: new Date().toISOString(),
    };
    this.movements.push(movement);
    this.saveState();
    return newProd;
  }

  async softDeleteProduct(productId: string): Promise<Product> {
    const prod = this.products.find((p) => p.id === productId);
    if (!prod) throw new Error("Product not found.");
    prod.is_active = false;
    prod.updated_at = new Date().toISOString();
    this.saveState();
    return prod;
  }

  async createOrder(payload: OrderCreatePayload, idempotencyKey: string): Promise<Order> {
    // Check idempotency replay
    if (this.idempotencyCache.has(idempotencyKey)) {
      return this.idempotencyCache.get(idempotencyKey)!;
    }

    // Verify stock availability
    let total = 0;
    const items = [];

    for (const item of payload.items) {
      const prod = this.products.find((p) => p.id === item.product_id);
      if (!prod || !prod.is_active) {
        throw new Error(`Product not available.`);
      }
      if (prod.stock_quantity < item.quantity) {
        const err = new Error(
          `Insufficient stock for '${prod.name}'. Requested ${item.quantity}, available: ${prod.stock_quantity}`
        ) as any;
        err.status = 409;
        throw err;
      }
      const unitPrice = parseFloat(prod.price);
      const subtotal = unitPrice * item.quantity;
      total += subtotal;
      items.push({
        id: "item-" + crypto.randomUUID().slice(0, 8),
        product_id: prod.id,
        product_name_snapshot: prod.name,
        unit_price: prod.price,
        quantity: item.quantity,
        subtotal: subtotal.toFixed(2),
      });
    }

    // Deduct stock and append OUT movements
    const orderId = "ord-" + crypto.randomUUID().slice(0, 8);
    for (const item of payload.items) {
      const prod = this.products.find((p) => p.id === item.product_id)!;
      const prev = prod.stock_quantity;
      prod.stock_quantity -= item.quantity;
      prod.updated_at = new Date().toISOString();

      const lastSeq = this.movements
        .filter((m) => m.product_id === prod.id)
        .reduce((max, m) => Math.max(max, m.movement_sequence), 0);

      this.movements.push({
        id: "m-" + crypto.randomUUID().slice(0, 8),
        product_id: prod.id,
        movement_sequence: lastSeq + 1,
        type: "OUT",
        quantity: item.quantity,
        previous_stock: prev,
        new_stock: prod.stock_quantity,
        reference_id: orderId,
        reason: `Order checkout ${orderId}`,
        created_by: this.currentUser.id,
        created_at: new Date().toISOString(),
      });
    }

    const newOrder: Order = {
      id: orderId,
      user_id: this.currentUser.id,
      status: "CONFIRMED",
      total_amount: total.toFixed(2),
      items,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    this.orders.unshift(newOrder);
    this.idempotencyCache.set(idempotencyKey, newOrder);
    this.saveState();
    return newOrder;
  }

  async getOrders(limit = 20, offset = 0): Promise<PaginatedResponse<Order>> {
    return {
      items: this.orders.slice(offset, offset + limit),
      total: this.orders.length,
      limit,
      offset,
    };
  }

  async cancelOrder(orderId: string): Promise<Order> {
    const order = this.orders.find((o) => o.id === orderId);
    if (!order) throw new Error("Order not found.");
    if (order.status !== "CONFIRMED") {
      throw new Error("Only CONFIRMED orders can be cancelled.");
    }
    order.status = "CANCELLED";
    order.updated_at = new Date().toISOString();

    // Restock items with RETURN movements
    for (const item of order.items) {
      const prod = this.products.find((p) => p.id === item.product_id);
      if (prod) {
        const prev = prod.stock_quantity;
        prod.stock_quantity += item.quantity;
        prod.updated_at = new Date().toISOString();

        const lastSeq = this.movements
          .filter((m) => m.product_id === prod.id)
          .reduce((max, m) => Math.max(max, m.movement_sequence), 0);

        this.movements.push({
          id: "m-" + crypto.randomUUID().slice(0, 8),
          product_id: prod.id,
          movement_sequence: lastSeq + 1,
          type: "RETURN",
          quantity: item.quantity,
          previous_stock: prev,
          new_stock: prod.stock_quantity,
          reference_id: order.id,
          reason: `Restocked after order cancellation ${order.id}`,
          created_by: this.currentUser.id,
          created_at: new Date().toISOString(),
        });
      }
    }

    this.saveState();
    return order;
  }

  async getInventoryMovements(params?: {
    product_id?: string;
    type?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<InventoryMovement>> {
    let filtered = [...this.movements].reverse();
    if (params?.product_id) {
      filtered = filtered.filter((m) => m.product_id === params.product_id);
    }
    if (params?.type) {
      filtered = filtered.filter((m) => m.type === params.type);
    }
    const limit = params?.limit || 20;
    const offset = params?.offset || 0;
    return {
      items: filtered.slice(offset, offset + limit),
      total: filtered.length,
      limit,
      offset,
    };
  }

  async createInventoryMovement(
    payload: InventoryMovementCreatePayload
  ): Promise<InventoryMovement> {
    const prod = this.products.find((p) => p.id === payload.product_id);
    if (!prod) throw new Error("Product not found.");

    const prev = prod.stock_quantity;
    let newStock = prev;

    if (payload.type === "IN" || payload.type === "RETURN") {
      newStock += payload.quantity;
    } else if (payload.type === "OUT") {
      if (prev < payload.quantity) {
        throw new Error("Insufficient stock for manual deduction.");
      }
      newStock -= payload.quantity;
    } else if (payload.type === "ADJUSTMENT") {
      if (payload.adjustment_direction === "DECREASE") {
        if (prev < payload.quantity) {
          throw new Error("Insufficient stock for adjustment decrease.");
        }
        newStock -= payload.quantity;
      } else {
        newStock += payload.quantity;
      }
    }

    prod.stock_quantity = newStock;
    prod.updated_at = new Date().toISOString();

    const lastSeq = this.movements
      .filter((m) => m.product_id === prod.id)
      .reduce((max, m) => Math.max(max, m.movement_sequence), 0);

    const movement: InventoryMovement = {
      id: "m-" + crypto.randomUUID().slice(0, 8),
      product_id: prod.id,
      movement_sequence: lastSeq + 1,
      type: payload.type,
      adjustment_direction: payload.adjustment_direction,
      quantity: payload.quantity,
      previous_stock: prev,
      new_stock: newStock,
      reference_id: payload.reference_id || `MANUAL-${Date.now()}`,
      reason: payload.reason,
      created_by: this.currentUser.id,
      created_at: new Date().toISOString(),
    };

    this.movements.push(movement);
    this.saveState();
    return movement;
  }

  async getReconciliationReport(): Promise<StockReconciliationReport> {
    return {
      generated_at: new Date().toISOString(),
      snapshot_isolation_level: "REPEATABLE READ, READ ONLY",
      total_products_checked: this.products.length,
      consistent_products_count: this.products.length,
      discrepant_products_count: 0,
      is_consistent: true,
      discrepancies: [],
    };
  }
}

export const mockDemoStore = new MockDemoStore();
