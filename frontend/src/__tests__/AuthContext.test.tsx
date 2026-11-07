import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import type React from "react";
import { AuthProvider, useAuth } from "../context/AuthContext";
import { api } from "../services/api";

const TestConsumer: React.FC = () => {
  const { user, isAdmin, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="user-email">{user?.email || "anonymous"}</span>
      <span data-testid="is-admin">{isAdmin ? "yes" : "no"}</span>
      <button onClick={() => login("admin@stockflow.io", "AdminPassword123!")}>Login Admin</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("initializes as unauthenticated when no token is present", () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId("user-email").textContent).toBe("anonymous");
    expect(screen.getByTestId("is-admin").textContent).toBe("no");
  });

  it("authenticates admin user and updates isAdmin flag", async () => {
    vi.spyOn(api, "login").mockResolvedValue({
      access_token: "fake-jwt",
      token_type: "bearer",
      expires_in: 3600,
    });
    vi.spyOn(api, "getMe").mockResolvedValue({
      id: "u-1",
      email: "admin@stockflow.io",
      full_name: "StockFlow Admin",
      role: "admin",
      is_active: true,
      created_at: new Date().toISOString(),
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText("Login Admin").click();
    });

    expect(screen.getByTestId("user-email").textContent).toBe("admin@stockflow.io");
    expect(screen.getByTestId("is-admin").textContent).toBe("yes");
  });
});
