import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Stub the auth API so the AuthProvider's initial /me probe doesn't try to
// hit the network. We return a 401-shaped rejection so the provider settles
// into the "not authenticated" state.
vi.mock("@/services/auth-api", () => ({
  authApi: {
    me: vi.fn().mockRejectedValue({ response: { status: 401 } }),
    login: vi.fn(),
    logout: vi.fn(),
  },
}));

import { AuthProvider } from "@/contexts/AuthContext";
import { LoginForm } from "@/components/LoginForm";

describe("LoginForm", () => {
  it("renders the email and password inputs and a submit button", () => {
    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );

    expect(screen.getByPlaceholderText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByLabelText(/密碼/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /登入/ })).toBeInTheDocument();
  });
});
